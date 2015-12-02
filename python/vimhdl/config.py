# This file is part of vim-hdl.
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

import logging, os, sys
try:
    from rainbow_logging_handler import RainbowLoggingHandler
    _COLOR_LOGGING = True
except ImportError:
    _COLOR_LOGGING = False

class Config(object):
    is_toolchain = None
    thread_limit = 20

    # Only for running in standlone mode
    log_level = logging.DEBUG
    log_format = "%(levelname)-8s || %(name)s || %(message)s"

    show_only_current_file = False

    # When building a specific source, we can build its first level
    # dependencies and display their errors and/or warnings. Notice
    # that no dependency tracking will be done when none of them
    # are enabled!
    show_reverse_dependencies_errors = True
    show_reverse_dependencies_warnings = False
    max_reverse_dependency_sources = 20

    # When we find errors, we can cache them to avoid recompiling a
    # specific source file or consider the file as changed. Notice this
    # is changed from True to False, the errors reported for a given
    # source will be the cached ontes until we force rebuilding it
    cache_error_messages = True


    _logger = logging.getLogger(__name__)

    @staticmethod
    def _setupStreamHandler(stream):
        if _COLOR_LOGGING:
            stream_handler = RainbowLoggingHandler(
                stream,
                #  Customizing each column's color
                color_name=('blue', 'black', True),
                color_pathname=('black', 'red', False),
                color_module=('yellow', None, False),
                color_funcName=('blue', 'black', False),
                color_lineno=('green', None, False),
                color_asctime=('cyan', 'black', False),
                color_message_debug    = ('white'  , None , False),
                color_message_info     = ('green' , None , False),
                color_message_warning  = ('yellow', None , False),
                color_message_error    = ('red'   , None , True),
                color_message_critical = ('white' , 'red', True))
        else:
            stream_handler = logging.StreamHandler(stream)

        stream_handler.formatter = logging.Formatter(Config.log_format)
        logging.root.addHandler(stream_handler)
        logging.root.setLevel(Config.log_level)

    @staticmethod
    def _setupToolchain():
        Config.log_level = logging.DEBUG
        Config._logger.info("Setup for toolchain")
        Config.is_toolchain = True

    @staticmethod
    def _setupStandalone():
        Config._logger.info("Setup for standalone")
        Config.is_toolchain = False

    @staticmethod
    def setupBuild():
        if Config.is_toolchain is not None:
            return
        logging.getLogger("requests").setLevel(logging.WARNING)
        try:
            import vim
            Config._setupToolchain()
        except ImportError:
            if 'VIM' in os.environ.keys():
                Config._setupToolchain()
            else:
                Config._setupStandalone()

    @staticmethod
    def updateFromArgparse(args):
        for k, v in args._get_kwargs():
            if k in ('is_toolchain', ):
                raise RuntimeError("Can't redefine %s" % k)

            if k == 'thread_limit' and v is None:
                continue

            setattr(Config, k, v)

        _msg = ["Configuration update"]
        for k, v in Config.getCurrentConfig().iteritems():
            _msg += ["%s = %s" % (str(k), str(v))]

        Config._logger.info("\n".join(_msg))

    @staticmethod
    def getCurrentConfig():
        r = {}
        for k, v in Config.__dict__.iteritems():
            if k.startswith('_'):
                continue
            if k.startswith('__') and k.startswith('__'):
                continue
            if type(v) is staticmethod:
                continue
            r[k] = v
        return r

