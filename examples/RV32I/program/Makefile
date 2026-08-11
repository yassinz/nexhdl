
all: riscv

GCCARGS = -march=rv32i -mabi=ilp32 -Os -static -lm -nostartfiles --freestanding

# https://github.com/xpack-dev-tools/riscv-none-elf-gcc-xpack/releases
CC = riscv-none-elf

riscv:
	$(CC)-gcc $(GCCARGS) -T core.ld main.c -o main
	$(CC)-objcopy -O binary -j .code main code.bin
	$(CC)-objcopy -O binary -j .data main data.bin
	$(CC)-objcopy -O binary main program.bin
#	$(CC)-objdump -d main
