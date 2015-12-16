#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

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

import os
import logging
import time
import argparse
from prettytable import PrettyTable
try:
    import argcomplete
    _HAS_ARGCOMPLETE = True
except ImportError:
    _HAS_ARGCOMPLETE = False

try:
    import cProfile as profile
except ImportError:
    import profile

def _pathSetup():
    import sys
    path_to_this_file = os.path.realpath(__file__).split(os.path.sep)[:-2]
    vimhdl_path = os.path.sep.join(path_to_this_file)
    if vimhdl_path not in sys.path:
        sys.path.insert(0, vimhdl_path)

if __name__ == '__main__':
    _pathSetup()

from vimhdl.config import Config
from vimhdl.project_builder import ProjectBuilder

def _fileExtentensionCompleter(extension):
    def _completer(**kwargs):
        prefix = kwargs['prefix']
        if prefix == '':
            prefix = os.curdir

        result = []
        for line in os.listdir(prefix):
            if line.lower().endswith('.' + extension):
                result.append(line)
            elif os.path.isdir(line):
                result.append("./" + line)

        return result
    return _completer


def parseArguments():
    parser = argparse.ArgumentParser()
    # pylint: disable=bad-whitespace

    # Options
    parser.add_argument('--verbose', '-v', action='append_const', const=1,
                        help="""Increases verbose level. Use multiple times to
                                increase more""")

    parser.add_argument('--clean', '-c', action='store_true',
                        help="Cleans the project before building")

    parser.add_argument('--build', '-b', action='store_true',
                        help="Builds the project given by <project_file>")

    parser.add_argument('--sources', '-s', action='append', nargs='*',
                        help="""Source(s) file(s) to build individually""") \
                            .completer = _fileExtentensionCompleter('vhd')

    parser.add_argument('--debug-print-sources', action='store_true')
    parser.add_argument('--debug-print-compile-order', action='store_true')
    parser.add_argument('--debug-parse-source-file', action='store_true')
    parser.add_argument('--debug-run-static-check', action='store_true')
    parser.add_argument('--debug-profiling', action='store', nargs='?',
                        metavar='OUTPUT_FILENAME', const='vimhdl.pstats')

    # Mandatory arguments
    parser.add_argument('project_file', action='store', nargs=1,
                        help="""Configuration file that defines what should be
                        built (lists sources, libraries, build flags and so on""")

    # pylint: enable=bad-whitespace

    if _HAS_ARGCOMPLETE:
        argcomplete.autocomplete(parser)

    args = parser.parse_args()

    args.project_file = args.project_file[0]

    args.log_level = logging.FATAL
    if args.verbose:
        if len(args.verbose) == 0:
            args.log_level = logging.FATAL
        elif len(args.verbose) == 1:
            args.log_level = logging.WARNING
        elif len(args.verbose) == 2:
            args.log_level = logging.INFO
        elif len(args.verbose) >= 3:
            args.log_level = logging.DEBUG

    # Planify source list if supplied
    if args.sources:
        args.sources = [source for sublist in args.sources for source in sublist]

    Config.log_level = args.log_level
    Config.setupBuild()

    return args

def runStandaloneSourceFileParse(fname):
    """Standalone source_file.VhdlSourceFile run"""
    from vimhdl.source_file import VhdlSourceFile
    source = VhdlSourceFile(fname)
    print "Source: %s" % source
    design_units = source.getDesignUnits()
    if design_units:
        print " - Design_units:"
        for unit in design_units:
            print " -- %s" % str(unit)
    dependencies = source.getDependencies()
    if dependencies:
        print " - Dependencies:"
        for dependency in dependencies:
            print " -- %s.%s" % (dependency['library'], dependency['unit'])

def runStandaloneStaticCheck(fname):
    """Standalone source_file.VhdlSourceFile run"""
    from vimhdl.static_check import vhdStaticCheck

    for record in vhdStaticCheck(open(fname, 'r').read().split('\n')):
        print record

def main(args):
    "Main runner command processing"

    # FIXME: Find a better way to insert a header to the log file
    _logger.info("#"*(197 - 32))
    _logger.info("Creating project object")

    if args.clean:
        _logger.info("Cleaning up")
        ProjectBuilder.clean(args.project_file)

    if args.debug_print_sources or args.debug_print_compile_order or args.build:
        project = ProjectBuilder(project_file=args.project_file)
        project.readConfigFile()

    if args.debug_print_sources:
        sources = PrettyTable(['Filename', 'Library', 'Flags'])
        sources.align['Filename'] = 'l'
        sources.sortby = 'Library'
        for source in project.sources.values():
            sources.add_row([source.filename, source.library, " ".join(source.flags)])
        print sources

    if args.debug_print_compile_order:
        for source in project.getCompilationOrder():
            print "{lang} {library} {path} {flags}".format(
                lang='vhdl', library=source.library, path=source.filename,
                flags=' '.join(source.flags))
            assert not set(['-93', '-2008']).issubset(source.flags)

    if args.build:
        if not args.sources:
            project.buildByDependency()
        else:
            for source in args.sources:
                try:
                    _logger.info("Building source '%s'", source)
                    for record in project.buildByPath(source):
                        print "[{error_type}-{error_number}] @ " \
                              "({line_number},{column}): {error_message}"\
                                .format(**record)
                except RuntimeError as exception:
                    _logger.error("Unable to build '%s': '%s'", source,
                                  str(exception))
                    continue

    if args.debug_parse_source_file:
        for source in args.sources:
            runStandaloneSourceFileParse(source)

    if args.debug_run_static_check:
        for source in args.sources:
            runStandaloneStaticCheck(source)

    if args.debug_print_sources or args.debug_print_compile_order or args.build:
        project.saveCache()


if __name__ == '__main__':
    start = time.time()
    runner_args = parseArguments()
    _logger = logging.getLogger(__name__)
    if runner_args.debug_profiling:
        profile.run('main(runner_args)', runner_args.debug_profiling)
    else:
        main(runner_args)
    end = time.time()
    _logger.info("Process took %.2fs", (end - start))


