#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <setjmp.h>
#define BUFFER_SIZE 4096u
static uint8_t expected[BUFFER_SIZE] __attribute__((aligned(64)));
static uint8_t src[BUFFER_SIZE] __attribute__((aligned(64)));
static uint8_t dst[BUFFER_SIZE] __attribute__((aligned(64)));
static jmp_buf recovery;
static unsigned seen_hart,seen_job,seen_index;
static uint64_t seen_got,seen_wanted;
static void fail(const char *why,unsigned hart,unsigned job,unsigned index,uint64_t got,uint64_t wanted) __attribute__((noreturn));
static void fail(const char *why,unsigned hart,unsigned job,unsigned index,uint64_t got,uint64_t wanted) {
 (void)why;seen_hart=hart;seen_job=job;seen_index=index;seen_got=got;seen_wanted=wanted;longjmp(recovery,1);
}
#include "helpers.inc"
static unsigned pattern(unsigned i) {return (i*73u+11u)&255u;}
static void require(int ok) {if(!ok){fputs("FAIL helper equivalence\n",stderr);exit(1);}}
int main(void) {
 initialize_buffers(src,dst);
 for(unsigned i=0;i<BUFFER_SIZE;++i)require(src[i]==0x3c && dst[i]==0xa5 && expected[i]==0xa5);
 for(unsigned i=0;i<BUFFER_SIZE;++i)dst[i]=expected[i]=(uint8_t)pattern(i);
 if(setjmp(recovery))require(0);else check_buffer("probe",1,17,dst);
 for(volatile unsigned index=0;index<BUFFER_SIZE;++index){
  unsigned i=index;uint8_t mask=(uint8_t)(1u<<(i%8u));dst[i]^=mask;
  if(!setjmp(recovery)){check_buffer("probe",1,17,dst);require(0);}
  require(seen_hart==1 && seen_job==17 && seen_index==index && seen_got==(pattern(index)^(1u<<(index%8u))) && seen_wanted==pattern(index));
  dst[index]=(uint8_t)pattern(index);
 }
 dst[127]^=0x80;dst[128]^=0x40;dst[4095]^=1;
 if(!setjmp(recovery)){check_buffer("probe",1,17,dst);require(0);}require(seen_index==127);
 puts("PASS helper equivalence: all 4096 poison bytes; identical buffers; every mismatch index/bit position; first of multiple mismatches");
 return 0;
}
