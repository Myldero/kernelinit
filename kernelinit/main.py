#!/usr/bin/env python3


import argparse
try:
    from importlib.metadata import version as _version
    version = _version('kernelinit')
except ImportError:
    version = None
from .runfile import RunFile
from .files import create_files, cleanup_files
from .unintended import do_unintended_checks
from .utils import TEMPLATES_DIR, debug


def main() -> None:
    parser = argparse.ArgumentParser(description='A tool for automating setup of kernel pwn challenges.'
                                                f' Template directory: {TEMPLATES_DIR}',
                                     add_help=False, allow_abbrev=False)
    parser.add_argument('-h', '--help', action='help', help="Show this help message")
    if version:
        parser.add_argument('-V', '--version', action='version', help="Show version", version=f'%(prog)s {version}')
    parser.add_argument('-v', '--verbose', action="store_true", help="Enable verbose output")
    parser.add_argument('--no-files', action="store_true", help="Only run checks. Do not create files")
    parser.add_argument('--no-vmlinux', action="store_true", help="Do not extract vmlinux")
    parser.add_argument('--clean', action="store_true", help="Clean up previously generated files and exit")
    parser.add_argument('--bzImage', type=str, help="Specify bzImage file")
    parser.add_argument('--cpio', type=str, help="Specify cpio file")
    parser.add_argument('--runfile', type=str, help="Specify run script")

    args = parser.parse_args()
    debug.verbose = args.verbose

    if args.clean:
        cleanup_files()
        return

    runfile = RunFile(args.runfile, args.cpio, args.bzImage)
    runfile.check_args()
    create_files(runfile, args)
    do_unintended_checks(runfile)


if __name__ == '__main__':
    main()
