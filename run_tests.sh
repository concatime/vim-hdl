#!/usr/bin/env bash
# This file is part of vim-hdl.
#
# Copyright (c) 2015-2016 Andre Souto
#
# vim-hdl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# vim-hdl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with vim-hdl.  If not, see <http://www.gnu.org/licenses/>.

##############################################################################
# Parse CLI arguments ########################################################
##############################################################################
RUNNER_ARGS=()

while [ -n "$1" ]; do
  case "$1" in
    -C) CLEAN_AND_QUIT="1";;
    -c) CLEAN="1";;
    *)	RUNNER_ARGS+=($1)
  esac
  shift
done

##############################################################################
# If we're not running inside CI, adjust some variables to mimic it ##########
##############################################################################
if [ -z "${CI}" ]; then
  if [ -z "${CI_TARGET}" ]; then
    CI_TARGET=vim
  fi

  VIRTUAL_ENV_DEST=~/dev/vimhdl_venv

  if [ -z "${VERSION}" ]; then
    VERSION=master
  fi

fi

##############################################################################
# Functions ##################################################################
##############################################################################
function _setup_ci_env {
  cmd="virtualenv --clear ${VIRTUAL_ENV_DEST}"

  if [ -n "${PYTHON}" ]; then
    cmd="$cmd --python=${PYTHON}"
  else
    cmd="$cmd --python=python3"
  fi

  $cmd
  # shellcheck disable=SC1090
  source ${VIRTUAL_ENV_DEST}/bin/activate
  
}

function _install_packages {
  pip install git+https://github.com/google/vroom
  pip install neovim

  pip install -r ./.ci/requirements.txt

  # Default Vim on Travis is always Python 2, install stuff for that as well
  if [ "${CI_TARGET}" == "vim" ]                  \
    && [ -n "${CI}" ]                             \
    && [[ ${TRAVIS_PYTHON_VERSION} == 3* ]]; then
      echo "sudo pip2 installing .ci/requirements.txt with"
      sudo -H pip2 install -r ./.ci/requirements.txt
      pip2 install -r ./.ci/requirements.txt --user
  fi

}

function _cleanup_if_needed {
  if [ -n "${CLEAN_AND_QUIT}${CLEAN}" ]; then
    git clean -fdx || exit -1
    git submodule foreach --recursive git clean -fdx || exit -1
    pushd ../hdlcc_ci/hdl_lib
    git reset HEAD --hard
    popd
    pushd ../hdlcc_ci/vim-hdl-examples
    git reset HEAD --hard
    popd

    if [ -n "${CLEAN_AND_QUIT}" ]; then exit; fi
  fi
}

function _setup_dotfiles {
  if [ "${CI}" == "true" ]; then
    DOT_VIM="$HOME/.vim"
    DOT_VIMRC="$HOME/.vimrc"
  else
    DOT_VIM="$HOME/dot_vim"
    DOT_VIMRC="$DOT_VIM/vimrc"
  fi

  mkdir -p "$DOT_VIM"
  if [ ! -d "$DOT_VIM/syntastic" ]; then
    git clone https://github.com/scrooloose/syntastic "$DOT_VIM/syntastic"
  fi
  if [ ! -d "$DOT_VIM/vim-hdl" ]; then
    ln -s "$PWD" "$DOT_VIM/vim-hdl"
  fi

  cp ./.ci/vimrc "$DOT_VIMRC"
}

##############################################################################
# Now to the script itself ###################################################
##############################################################################

set -e

# If we're not running on a CI server, create a virtual env to mimic its
# behaviour
if [ -z "${CI}" ]; then
  if [ -n "${CLEAN}" ] && [ -d "${VIRTUAL_ENV_DEST}" ]; then
    echo "Removing previous virtualenv"
    rm -rf ${VIRTUAL_ENV_DEST}
  fi
  _setup_ci_env
fi

_cleanup_if_needed
_install_packages

export PATH=${HOME}/builders/ghdl/bin/:${PATH}

_setup_dotfiles

if [ "${CI_TARGET}" == "vim" ]; then vim --version; fi
if [ "${CI_TARGET}" == "neovim" ]; then nvim --version; fi

echo "Terminal size is $COLUMNS x $LINES"

set +e

python -m coverage run -m nose2 -s .ci/ "${RUNNER_ARGS[@]}"

RESULT=$?

python -m coverage combine
python -m coverage report
python -m coverage html

[ -z "${CI}" ] && [ -n "${VIRTUAL_ENV}" ] && deactivate

exit ${RESULT}
