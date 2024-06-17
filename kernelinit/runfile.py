import os
import subprocess
import argparse
from typing import Tuple, Dict, List, Union, Optional

from .utils import get_file, parameterize, info, important, fatal, debug, error


class RunFile:
    def __init__(self, filename: str = None, cpio: str = None, bzImage: str = None):
        if filename is not None and not os.path.isfile(filename):
            fatal(f"Runfile {repr(filename)} does not exist")
        self.filename = filename or get_file('run*.sh') or get_file(r'start*.sh')
        if self.filename is None:
            fatal("No runfile found")
        with open(self.filename, 'r') as f:
            s = f.read()
        self.cmd, *runfile_args = parameterize(s[s.find("qemu-system"):])
        self.arch = self.cmd[12:]

        self.args = parse_qemu_arguments(runfile_args)

        self.args.initrd = get_cpio(cpio or self.args.initrd)
        self.initrd_gzipped = self.args.initrd.endswith(".gz")
        self.args.kernel = bzImage or self.args.kernel
        if not os.path.isfile(self.args.kernel):
            self.args.kernel = get_file('bzImage')
            if self.args.kernel is None:
                fatal("No bzImage file found")

    def check_args(self) -> None:
        """
        Run simple checks on runfile arguments
        """
        cpu_args = self.args.cpu.split(',') if self.args.cpu else []
        vm_args = self.args.append.split() if self.args.append else []

        if self.args.monitor is None or self.args.serial == 'mon:stdio':
            important("Unintended using QEMU Monitor")

        if not any(i in cpu_args for i in ('smep', '+smep')):
            info("No SMEP")

        if not any(i in cpu_args for i in ('smap', '+smap')):
            info("No SMAP")

        if self.args.smp:
            if self.args.smp.isdigit():
                cpu_count = int(self.args.smp)
            else:
                cpu_count = int(get_vm_arg(self.args.smp.split(","), 'cores', '1'))
            if cpu_count > 1:
                info("Multiple CPUs. Maybe race condition?")

        if get_vm_arg(vm_args, 'nokaslr'):
            info("No KASLR")

        if (get_vm_arg(vm_args, 'pti') == 'on' and self.arch == 'x86_64') or \
           (get_vm_arg(vm_args, 'kpti') == '1' and self.arch == 'aarch64'):
            info("Page Table Isolation (pti) enabled")

        if get_vm_arg(vm_args, 'oops') != 'panic':
            info("Kernel panics will not crash qemu")

    def create_release_run(self, cpio: Optional[str] = None, kernel_args: List[Tuple[str, str]] = ()) -> List[str]:
        l = [self.cmd]

        for key, value in self.args._get_kwargs():
            key = "-" + key.replace("_", "-")
            if value is None:
                continue
            elif isinstance(value, str):
                if key == '-initrd' and cpio:
                    value = cpio
                if key == '-append' and kernel_args:
                    value = value.split()
                    for a, b in kernel_args:
                        set_vm_arg(value, a, b)
                    value = " ".join(value)
                l += [key, value]
            elif isinstance(value, list):
                for i in value:
                    l += [key, i]
            elif value is True:
                l += [key]
        return l

    def create_debug_run(self, cpio=None) -> List[str]:
        l = self.create_release_run(cpio=cpio, kernel_args=[('loglevel', 'loglevel=7'),
                                                       ("panic", "panic=0"),
                                                       ("kaslr", "nokaslr")])
        l += ['-s']
        return l


def get_vm_arg(vm_args: List[str], arg: str, default=None):
    """
    Get argument from argument list
    """
    for i in vm_args:
        key, *value = i.split("=", 1)
        if key == arg:
            return value[0] if value else True
    return default


def set_vm_arg(vm_args: List[str], target_key: str, target_value: str) -> None:
    """
    Replace specific key with value. Used for updating kernel args in debug runfile
    """
    for i, arg in enumerate(vm_args):
        key, *_ = arg.split("=", 1)
        if key == target_key:
            vm_args[i] = target_value
            return
    vm_args.append(target_value)


def get_cpio(cpio: Optional[str]) -> str:
    if not os.path.isfile(cpio):
        cpio = get_file('*.cpio')
        if cpio:
            return cpio
        cpio = get_file('*.cpio.gz')
        if not cpio:
            fatal("No cpio file found")
    return cpio


def parse_qemu_arguments(runfile_args: List[str]) -> argparse.Namespace:
    """
    Parse the qemu-system command arguments
    """
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)

    errors = []
    def _error(msg):
        errors.append(msg)
    parser.error = _error

    parser.add_argument("-nographic", action="store_true")
    parser.add_argument("-no-reboot", action="store_true")
    parser.add_argument("-no-shutdown", action="store_true")
    parser.add_argument("-enable-kvm", action="store_true")
    parser.add_argument("-snapshot", action="store_true")
    parser.add_argument("-monitor")
    parser.add_argument("-display")
    parser.add_argument("-kernel")
    parser.add_argument("-initrd")
    parser.add_argument("-append")
    parser.add_argument("-m")
    parser.add_argument("-cpu")
    parser.add_argument("-smp")
    parser.add_argument("-serial")
    parser.add_argument("-machine")
    parser.add_argument("-accel")
    parser.add_argument("-boot")
    parser.add_argument("-L")
    parser.add_argument("-hda")
    parser.add_argument("-hdb")
    parser.add_argument("-hdc")
    parser.add_argument("-hdd")
    parser.add_argument("-cdrom")
    parser.add_argument("-net", action="append")
    parser.add_argument("-netdev", action="append")
    parser.add_argument("-fsdev", action="append")
    parser.add_argument("-drive", action="append")
    parser.add_argument("-chardev", action="append")
    parser.add_argument("-blockdev", action="append")
    parser.add_argument("-tpmdev", action="append")
    parser.add_argument("-numa", action="append")
    parser.add_argument("-global", action="append")
    parser.add_argument("-device", action="append")
    parser.add_argument("-object", action="append")
    parser.add_argument("-virtfs", action="append")

    args, ignored = parser.parse_known_args(runfile_args)
    if args is None:
        fatal(f"Runfile contains invalid command:" + "* \n".join(errors))
    elif errors:
        error(f"Non-fatal errors when parsing runfile:\n- " + "* \n".join(errors))

    if ignored:
        debug("The following runfile arguments were ignored:", *ignored)
    return args
