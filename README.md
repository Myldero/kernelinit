# `kernelinit`
A tool for automating setup of kernel pwn challenges.

## Installation
```sh
python3 -m pip install kernelinit
```

## Usage
Just run `kernelinit` in the directory of the challenge. It should hopefully automatically locate the relevant files and create the setup.

Your exploit code is placed in `exploit-src`  
Compile and run QEMU with `make`  
`make debug` is just an alias for `gdb -x debug.gdb`  
To become root inside QEMU, run `/makeroot`, which is a setuid binary that gives you root.  
In some challenges, setuid binaries are stripped. In this case, try uncommenting line 20 in the Makefile.

If you want to modify the exploit template, type `kernelinit -h` to get the path to the templates directory. If you change it, 
be wary that changes will be overwritten when you update this package. 
Instead, it's recommended to replace `exploit-src` with a symlink to your template.

## Unintended solves
The tool may be able to find unintended solutions when the challenge author has let critical files or directories be writable to the user.
A list of tricks for these cases can be seen [here](tricks.md)

## Example
```
$ ls
bzImage  rootfs.cpio  run.sh
$ kernelinit
[INFO] No SMEP
[INFO] No KASLR
[INFO] Can leak info using kernel panics
[INFO] Running unintended checks...
[INFO] Extracting vmlinux...
[INFO] Finished unintended checks
[INFO] Successfully extracted vmlinux
$ ls
bzImage  debug.gdb  example.ko	exploit-src  Makefile  makeroot  my-run.sh  rootfs.cpio  run.sh  vmlinux
```