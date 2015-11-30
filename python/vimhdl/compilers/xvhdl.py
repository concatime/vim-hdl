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
"Xilinx xhvdl builder implementation"

import os
import re
import subprocess
from vimhdl.compilers.base_compiler import BaseCompiler
from vimhdl import exceptions

class XVHDL(BaseCompiler):
    """Implementation of the xvhdl compiler"""

    # Implementation of abstract class properties
    __builder_name__ = 'xvhdl'

    # XVHDL specific class properties
    _BuilderStdoutMessageScanner = re.compile(
        r"^(?P<error_type>[EW])\w+:\s*"
        r"\[(?P<error_number>[^\]]+)\]\s*"
        r"(?P<error_message>[^\[]+)\s*\["
        r"(?P<filename>[^:]+):"
        r"(?P<line_number>\d+)", flags=re.I)

    _BuilderStdoutIgnoreLines = re.compile(r"^(?!(ERROR|WARNING):).*")

    def __init__(self, target_folder):
        self._version = ''
        super(XVHDL, self).__init__(target_folder)
        # FIXME: Built-in libraries should not be statically defined
        # like this. Review this at some point
        self.builtin_libraries = ['ieee', 'std', 'unisim', 'xilinxcorelib', \
                'synplify', 'synopsis', 'maxii', 'family_support']
        self._xvhdlini = 'xvhdl.init'
        self._built_libs = []

    def _makeMessageRecord(self, line):
        line_number = None
        column = ''
        filename = None
        error_number = None
        error_type = None
        error_message = None

        scan = self._BuilderStdoutMessageScanner.scanner(line)

        while True:
            match = scan.match()
            if not match:
                break

            _dict = match.groupdict()

            line_number = _dict['line_number']
            filename = _dict['filename']
            error_number = _dict['error_number']
            error_type = _dict['error_type']
            error_message = _dict['error_message']

        return {
            'checker'        : 'xvhdl',
            'line_number'    : line_number,
            'column'         : column,
            'filename'       : filename,
            'error_number'   : error_number,
            'error_type'     : error_type,
            'error_message'  : error_message,
        }

    def checkEnvironment(self):
        try:
            version = subprocess.check_output(\
                ['xvhdl', '--nolog', '--version'], \
                stderr=subprocess.STDOUT)
            self._version = \
                    re.findall(r"^Vivado Simulator\s+([\d\.]+)", version)[0]
            self._logger.info("xvhdl version string: '%s'. " + \
                    "Version number is '%s'", \
                    version[:-1], self._version)
        except Exception as exc:
            self._logger.fatal("Sanity check failed")
            raise exceptions.SanityCheckError(str(exc))

    def _createLibrary(self, source):
        if source.library in self._built_libs:
            return

        self._built_libs += [source.library]
        open(self._xvhdlini, 'w').write('\n'.join(\
                ["%s=%s" % (x, os.path.join(self._target_folder, x)) \
                for x in self._built_libs]))

    def _doBuild(self, source, flags=None):
        cmd = ['xvhdl',
               '--nolog',
               '--verbose', '0',
               '--initfile', self._xvhdlini,
               '--work', source.library]
        cmd += flags
        cmd += [source.filename]

        self._logger.debug(" ".join(cmd))

        try:
            stdout = list(subprocess.check_output(cmd, \
                    stderr=subprocess.STDOUT).split("\n"))
        except subprocess.CalledProcessError as exc:
            stdout = list(exc.output.split("\n"))

        rebuilds = []
        records = []

        for line in stdout:
            if self._BuilderStdoutIgnoreLines.match(line):
                continue
            record = self._makeMessageRecord(line)
            assert None not in record.values(), \
                    "File: %s ==> Error at %s\n%s" % \
                    (source.filename, repr(line), repr(record))
            records.append(record)
            self._logger.info(line)
            self._logger.info(record)

        return records, rebuilds

