typedef unsigned char u8 ;
typedef unsigned short u16;
typedef unsigned int u32;
typedef long long unsigned int u64;

typedef char i8;
typedef short i16;
typedef int i32;
typedef long long int i64;

typedef u32 u32x8 __attribute__ ((vector_size (4 * 8)));

#define PRINT  *((volatile unsigned char*)(0x110000))



void print_int(u32 num){
    u8 s[11];
    u8 i = 0;
    do{
        s[i++] = num%10 + '0';
        num /= 10;
    }while(num);
    
    while(i--)  PRINT = s[i];
}

void print_hex(u32 num){
    u8 s[11];
    u8 i = 0;
    do{
        u8 n = num % 16;
        s[i++] = n < 10 ? n + '0' : n - 10 + 'a';
        num /= 16;
    }while(num);
    
    while(i--)  PRINT = s[i];
}

void print_str(char *s){
    while(*s) PRINT = *s++;
}



void test_vector(){
    u32x8 v = {1,2,3,4,5,6,7,8};
    u32x8 w = {1,2,3,4,5,6,7,8};
    u32x8 r;

    print_str("v: ");
    for(int i = 0; i < 8; i++){
        print_int(v[i]);
        PRINT = ' ';
    }
    PRINT = '\n';

    print_str("w: ");
    for(int i = 0; i < 8; i++){
        print_int(w[i]);
        PRINT = ' ';
    }
    PRINT = '\n';

    print_str("v + w: ");
    r = v + w;
    for(int i = 0; i < 8; i++){
        print_int(r[i]);
        PRINT = ' ';
    }
    PRINT = '\n';

    print_str("v - w: ");
    r = v - w;
    for(int i = 0; i < 8; i++){
        print_int(r[i]);
        PRINT = ' ';
    }
    PRINT = '\n';

    print_str("v * w: ");
    r = v * w;
    for(int i = 0; i < 8; i++){
        print_int(r[i]);
        PRINT = ' ';
    }
    PRINT = '\n';

    print_str("v / w: ");
    r = v / w;
    for(int i = 0; i < 8; i++){
        print_int(r[i]);
        PRINT = ' ';
    }
    PRINT = '\n';

}

u32 volatile cycle(){
	u32 c;
	asm volatile ("rdcycle %0" : "=r" (c));
	return c;
}


u32 volatile time(){
	u32 c;
	asm volatile ("rdtime %0" : "=r" (c));
	return c;
}


void hexdump(u32 start, u32 size){
    for(int i = 0; i < size; i+=16){
        print_hex(start + i);
        PRINT = ' ';
        PRINT = ' ';
        for(int j = 0; j < 16; j++){
            u8 val = *(u8*)(start + i + j);
            print_hex(val >> 4);
            print_hex(val & 0xf);
            PRINT = ' ';
            if(j == 7) PRINT = ' ';
        }
        PRINT = '|';
        for(int j = 0; j < 16; j++){
            u8 c = *(u8*)(start + i + j);
            if (c < 32 || c > 127)
                PRINT = '.';
            else
                PRINT = c;
        }
        PRINT = '|';
        PRINT = '\n';
        PRINT = '\r';
    }
}


int main(){
    print_str("- Hexdump data segment (0x10000-0x10080):\n");
    hexdump(0x10000, 0x80);

    PRINT = '\n';
    print_str("- Test vector:\n");
    test_vector();

    PRINT = '\n';
    print_str("- Test CSR:\n");
    print_str("cycle: ");
    print_int(cycle());
    PRINT = '\n';
    print_str("time: ");
    print_int(time());
    PRINT = '\n';
    for(;;);
}

__attribute__((section(".init")))
void init(void){
	asm volatile("li sp, 0x100000"); // Stack pointer
	asm volatile("call main");
	for(;;);
}
