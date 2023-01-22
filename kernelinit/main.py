#!/usr/bin/env python3

import os
import shutil
import subprocess
import glob
from kernelinit.utils import parameterize, unparameterize, debug, info, important, error
import pexpect
import re
import libarchive
from typing import Tuple, Dict, List, Union


def get_file(expr: str):
    l = glob.glob(f"**/{expr}", recursive=True)
    if l:
        return l[0]
    return None


def get_cpio(cpio: str):
    if not os.path.exists(cpio):
        cpio = get_file('*.cpio')
        if cpio:
            return cpio
        cpio = get_file('*.cpio.gz')
        if not cpio:
            error("No cpio file found")
            exit()
    if cpio.endswith(".gz"):
        subprocess.check_output(["gunzip", "-k", "--", cpio])
        return cpio[:-3]
    return cpio


def parse_runfile() -> Tuple[str, Dict[str, Union[bool,str,List[str]]]]:
    runfile = get_file('run*.sh') or get_file(r'start*.sh')
    if runfile is None:
        error("No runfile found")
        exit(-1)
    with open(runfile, 'r') as f:
        s = f.read()
    out = s[s.find("qemu-system"):]
    cmd, *args = parameterize(out)
    d = {}
    for i in range(len(args)):
        if args[i].startswith("-"):
            if len(args) > i+1 and not args[i+1].startswith("-"):
                key, value = args[i][1:], args[i+1]
                if key == 'net':
                    if key not in d:
                        d[key] = []
                    d[key].append(value)
                else:
                    d[key] = value
            else:
                d[args[i][1:]] = True
    return cmd, d


def get_ko_file(cpio: str):
    ko_file = get_file('*.ko')
    if ko_file:
        return ko_file

    with libarchive.Archive(cpio) as a:
        for entry in a:
            if entry.pathname.endswith(".ko") and not entry.pathname.startswith("lib/modules"):
                filename = os.path.basename(entry.pathname)
                with open(filename, 'wb') as f:
                    f.write(a.read(entry.size))
                return f"./{filename}"


def get_vm_arg(vm_args: List[str], arg: str, default=None):
    for i in vm_args:
        key, *value = i.split("=", 1)
        if key == arg:
            return value[0] if value else True
    return default


def create_release_run(cmd, args, cpio='my-rootfs.cpio', append=None) -> List[str]:
    bzimage = args.get('kernel', '')
    if not os.path.exists(bzimage):
        bzimage = get_file('bzImage')
    l = [cmd, '-nographic', '-monitor', '/dev/null']
    l += ['-kernel', bzimage]
    l += ['-initrd', cpio]
    l += ['-m', args.get('m', '64')]
    l += ['-cpu', args.get('cpu', 'kvm64')]
    l += ['-smp', args.get('smp', '2')]
    l += ['-append', append or args['append']]
    for i in args.get('net', []):
        l += ['-net', i]
    return l


def create_debug_run(cmd, args, cpio='my-rootfs.cpio') -> List[str]:
    l = create_release_run(cmd, args, cpio=cpio, append="console=ttyS0 loglevel=3 oops=panic panic=0 nokaslr")
    l += ['-s']
    return l


def check_runfile_args():
    cmd, args = parse_runfile()

    cpu_args = args.get('cpu', '').split(',')
    vm_args = args.get('append', '').split()

    if 'monitor' not in args:
        important("No '-monitor' flag. Unintended using QEMU Monitor")

    if not any(i.endswith("smep") for i in cpu_args):
        info("No SMEP")

    if not any(i.endswith("smap") for i in cpu_args):
        info("No SMAP")

    if 'smp' in args:
        smp = args['smp']
        if smp.isdigit():
            cpu_count = int(smp)
        else:
            cpu_count = int(get_vm_arg(smp.split(","), 'cores', '4'))
        if cpu_count > 1:
            info("Multiple CPUs. Maybe race condition?")

    if get_vm_arg(vm_args, 'nokaslr'):
        info("No KASLR")

    if int(get_vm_arg(vm_args, 'loglevel', '7')) > 0:
        info("Can leak info using kernel panics")

    if get_vm_arg(vm_args, 'oops') != 'panic':
        info("Kernel panics will not crash qemu")


    if 'initrd' not in args:
        error("ERROR: Currently only .cpio files supported")
        exit()
    cpio = get_cpio(args['initrd'])
    return cmd, args, cpio


def create_files(cmd: str, args, cpio: str):
    templates_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')

    with open('./my-run.sh', 'w') as f:
        print("#!/bin/sh", file=f)
        print(unparameterize(create_debug_run(cmd, args)), file=f)
    os.chmod('./my-run.sh', 0o775)

    with open('./debug.gdb', 'w') as f:
        print("target remote :1234", file=f)
        ko_file = get_ko_file(cpio)
        print('add-symbol-file vmlinux', file=f)
        print('add-symbol-file exploit', file=f)
        if ko_file:
            print(f"add-symbol-file {ko_file} 0xffffffffc0000000", file=f)

    with open(os.path.join(templates_dir, 'Makefile'), 'r') as f:
        makefile = f.read().replace("CPIOFILE", cpio)
    with open('./Makefile', 'w') as f:
        f.write(makefile)

    try:
        shutil.copytree(os.path.join(templates_dir, 'exploit-src'), './exploit-src')
    except OSError:
        error("'exploit-src' already exists. Skipping...")

    try:
        shutil.copy(os.path.join(templates_dir, 'makeroot'), './makeroot')
    except OSError:
        pass


def do_unintended_checks(cmd: str):
    info("Running unintended checks...")
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    def send_cmd(c):
        child.sendline(c); child.readline()
        child.expect_exact(b'$ ')
        return ansi_escape.sub('', child.before.decode())

    visited = set()
    def get_writable(dirname, message):
        if dirname in visited:
            return
        visited.add(dirname)
        debug(f"get_writable('{dirname}')")
        if dirname != '/':
            get_writable(os.path.dirname(dirname), message)

        out = send_cmd(f"ls -ld '{dirname}'").strip()
        if 'cannot access' in out:
            return
        elif f'{dirname} -> ' in out:
            new_name = re.findall(f'{dirname} -> (.*\S)', out)[0]
            get_writable(os.path.normpath(os.path.join(os.path.dirname(dirname), new_name)), message)
            return
        perms, _, fuid, *_ = out.split()
        if perms[-3:-1] == 'rw' or fuid in (uid, uidname):
            important(f"Write-access to '{dirname}'.", message)

    child = pexpect.spawn(cmd)
    child.expect_exact(b'$ ')
    my_id = send_cmd('id').strip().split()
    uid, *uidname = my_id[0][4:].split("(")
    uidname = uidname[0][:-1] if uidname else None
    debug("uid:", uid, uidname)
    get_writable('/sbin/modprobe', message='Unintended by hijacking /sbin/modprobe')
    get_writable('/etc/passwd', message='Unintended by overwriting /etc/passwd (If busybox is SUID)')
    child.sendeof()


def extract_vmlinux():
    bzimage = get_file('bzImage')
    if os.path.exists("vmlinux"):
        shutil.move("vmlinux", "vmlinux - backup")

    info("Extracting vmlinux...")
    out = subprocess.check_output(['vmlinux-to-elf', bzimage, 'vmlinux'])
    if b'Successfully wrote the new ELF kernel to vmlinux' in out:
        info('Successfully wrote the new ELF kernel to vmlinux')
    else:
        error('Failed extracting vmlinux')


def main() -> None:
    cmd, args, cpio = check_runfile_args()
    create_files(cmd, args, cpio)
    do_unintended_checks(unparameterize(create_release_run(cmd, args, cpio)))
    extract_vmlinux()


if __name__ == '__main__':
    main()
