
SECTIONS {
    . = 0x0000;

    .code : {
        *(.init)
        *(.text*);
    }
    . = 0x10000;
    .data : {
        *(.data*);
        *(.bss*);
        *(.rodata*);
    } 
}