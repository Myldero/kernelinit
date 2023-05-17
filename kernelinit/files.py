import os
import re
import shutil
import subprocess

import argparse
import threading

import libarchive
from typing import Optional

from .utils import get_file, info, error, debug, unparameterize, TEMPLATES_DIR
from .runfile import RunFile


def get_ko_file(cpio: str) -> Optional[str]:
    """
    Extract .ko file from CPIO file if necessary
    """
    ko_file = get_file('*.ko')
    if ko_file:
        return ko_file

    with libarchive.Archive(cpio) as a:
        for entry in a:
            if entry.pathname.endswith(".ko") and not re.match(r'lib/modules/[^/]+/kernel/', entry.pathname):
                filename = os.path.basename(entry.pathname)
                with open(filename, 'wb') as f:
                    f.write(a.read(entry.size))
                return f"./{filename}"


def create_files(runfile: RunFile, args: argparse.Namespace):
    """
    Create template files
    """
    if args.no_files:
        return

    with open('./my-run.sh', 'w') as f:
        print("#!/bin/sh", file=f)
        print("# Generated by kernelinit", file=f)
        print(unparameterize(runfile.create_debug_run(), pretty=True), file=f)
    os.chmod('./my-run.sh', 0o775)

    if runfile.initrd_gzipped:
        subprocess.check_output(["gunzip", "-fk", "--", runfile.args.initrd])

    with open('./debug.gdb', 'w') as f:
        print("# Generated by kernelinit", file=f)
        print("target remote :1234", file=f)
        if not args.no_vmlinux:
            print('add-symbol-file vmlinux', file=f)
        print('add-symbol-file exploit', file=f)
        ko_file = get_ko_file(runfile.args.initrd)
        if ko_file:
            print(f"add-symbol-file {ko_file} 0xffffffffc0000000", file=f)

    with open(os.path.join(TEMPLATES_DIR, 'Makefile'), 'r') as f:
        makefile = f.read().replace("CPIOFILE", runfile.args.initrd.replace(".gz", ""))
        if runfile.initrd_gzipped:
            makefile = makefile.replace("#gzip", "gzip")
    with open('./Makefile', 'w') as f:
        f.write(makefile)

    try:
        shutil.copytree(os.path.join(TEMPLATES_DIR, 'exploit-src'), './exploit-src')
    except OSError:
        error("'exploit-src' already exists. Skipping...")

    try:
        shutil.copy(os.path.join(TEMPLATES_DIR, 'makeroot'), './makeroot')
    except OSError:
        pass

    if not args.no_vmlinux:
        threading.Thread(target=extract_vmlinux, args=(runfile,)).start()


def extract_vmlinux(runfile: RunFile):
    """
    Run vmlinux-to-elf to extract vmlinux with symbols
    This takes time, so run in separate thread.
    """
    if os.path.exists("vmlinux"):
        shutil.move("vmlinux", "vmlinux - backup")

    info("Extracting vmlinux...")
    out = b''
    try:
        out = subprocess.run(['vmlinux-to-elf', '--', runfile.args.kernel, 'vmlinux'],
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
    except FileNotFoundError:
        error("Missing vmlinux-to-elf in PATH")

    if b'Successfully wrote the new ELF kernel' in out:
        info('Successfully extracted vmlinux')
    else:
        error('Failed extracting vmlinux using vmlinux-to-elf')
        if out:
            debug("vmlinux-to-elf output:\n" + out.decode())
        out = subprocess.check_output([os.path.join(TEMPLATES_DIR, "..", "extract-vmlinux"), runfile.args.kernel])
        with open('vmlinux', 'wb') as f:
            f.write(out)
        info("Successfully extracted vmlinux using extract-vmlinux")

def cleanup_files():
    """
    Remove files that were previously generated by kernelinit
    """
    def try_remove(filename):
        try:
            os.remove(filename)
        except OSError as e:
            debug(f'Failed to remove {repr(filename)}: {e.strerror}')

    def delete_safe(filename):
        if not os.path.isfile(filename):
            return
        with open(filename, 'r') as f:
            s = f.read()
        if 'Generated by kernelinit' in s:
            try_remove(filename)
        else:
            debug(f"Did not remove {repr(filename)}. Missing signature")

    try:
        subprocess.check_output(['make', 'clean'], stderr=subprocess.PIPE)
    except (OSError, subprocess.CalledProcessError):
        pass
    delete_safe('./my-run.sh')
    delete_safe('./Makefile')
    delete_safe('./debug.gdb')
    try_remove('./makeroot')

    if os.path.exists('./exploit-src'):
        try:
            subprocess.check_output(['diff', os.path.join(TEMPLATES_DIR, './exploit-src/'), 'exploit-src'], stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            try:
                line = input("exploit-src differs from template. Delete anyways? [y/N] ")
            except EOFError:
                return
            if not line.lower().startswith("y"):
                return
        shutil.rmtree('./exploit-src')
