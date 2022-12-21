CC = musl-gcc
CFLAGS = -Wall -Wextra -O0 -static -ggdb -masm=intel

SOURCES = $(wildcard exploit-src/*.c)
OBJECTS = $(SOURCES:.c=.o)
LIBS = -lpthread

debug:
	gdb -x debug.gdb

run: cpio
	./my-run.sh

cpio: exploit
	cp CPIOFILE my-rootfs.cpio
	chmod u+s makeroot
	find exploit makeroot | cpio -A -F my-rootfs.cpio -o -H newc --owner=0.0
	chmod u-s makeroot
	#sed -i 's/cttyhack setuidgid 1000/cttyhack setuidgid    0/g' my-rootfs.cpio

build: exploit

exploit: $(OBJECTS)
	$(CC) $(CFLAGS) $^ $(LIBS) -o $@

clean:
	rm -f exploit my-rootfs.cpio $(OBJECTS)

.PHONY: run debug clean
.DEFAULT_GOAL := run