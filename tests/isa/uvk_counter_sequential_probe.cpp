// H25/H18 - SOURCE-CONFIRMED UVK low-ten sequential advance.
// Native regression of the actual candidate Kyiv_t; never a hardware oracle.
#include <cstdint>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include "kyiv.h"
#include "asm_disasm.h"
int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&){return 0;}
namespace {
using U=uint64_t;
constexpr U NEGZERO=U{1}<<40;
U inst(unsigned op,U a1=0,U a2=0,U a3=0){
 return (U(op)<<36)|(a1<<24)|(a2<<12)|a3;
}
void req(bool ok,const char* msg){if(!ok)throw std::runtime_error(msg);}
bool exec(Kyiv_t& t){std::ostringstream sink;auto* o=std::cout.rdbuf(sink.rdbuf());
 try{bool r=t.execute_opcode();std::cout.rdbuf(o);return r;}
 catch(...){std::cout.rdbuf(o);throw;}}
Kyiv_t fresh(){return Kyiv_t(Kyiv_t::rom_boot_mode::deferred);}
void nop_low(){auto t=fresh();t.C_reg=01776;t.kmem.write_memory(01776,0);t.kmem.write_memory(01777,0);
 req(exec(t)&&t.C_reg==01777,"NOP_LOW_STEP");
 req(exec(t)&&t.C_reg==0000&&t.K_reg==0,"NOP_LOW_WRAP");
 req(t.kmem.read_memory(0000)==0,"ZERO_CELL_HARDWIRED");}
void nop_high(){auto t=fresh();t.C_reg=03776;t.kmem.write_rom(03776,0);t.kmem.write_rom(03777,0);
 req(exec(t)&&t.C_reg==03777,"NOP_HIGH_STEP");
 req(exec(t)&&t.C_reg==02000,"NOP_HIGH_WRAP_PRESERVE_BIT11");
 // Do not FETCH 02000: its historical physical accessibility is unresolved.
}
void compare_false(){auto t=fresh();t.kmem.write_memory(0001,0);t.kmem.write_memory(0002,1);
 t.kmem.write_memory(01777,inst(016,0001,0002,02007));t.C_reg=01777;
 req(exec(t)&&t.C_reg==0000,"COMPARE_FALSE_SEQUENTIAL_WRAP");}
void compare_true(){auto t=fresh();t.kmem.write_memory(0001,0);t.kmem.write_memory(0002,0);
 t.kmem.write_memory(01777,inst(016,0001,0002,02007));t.C_reg=01777;
 req(exec(t)&&t.C_reg==02007,"COMPARE_TRUE_FULL11_BRANCH");}
void call_full11(){auto t=fresh();t.kmem.write_memory(0001,NEGZERO);
 t.kmem.write_memory(01777,inst(030,0001,02001,02007));t.C_reg=01777;
 req(exec(t)&&t.C_reg==02007&&t.P_reg==02001,"CALL_LOADS_11_BIT_C_AND_P");}
void call_not_taken(){auto t=fresh();t.kmem.write_memory(0001,0);
 t.kmem.write_memory(01777,inst(030,0001,02001,02007));t.C_reg=01777;
 req(exec(t)&&t.C_reg==0000&&t.P_reg==0,"CALL_NOT_TAKEN_SEQ10");}
void return_full11(){auto t=fresh();t.kmem.write_memory(01777,inst(032));
 t.C_reg=01777;t.P_reg=02007;
 req(exec(t)&&t.C_reg==02007&&t.P_reg==0,"RETURN_FULL11_P_RESET");}
void conditional_dispatch(){auto t=fresh();t.kmem.write_memory(0001,0);
 t.kmem.write_memory(01777,inst(031,0001,02007,0007));t.C_reg=01777;
 req(exec(t)&&t.C_reg==02007,"FORK_POSITIVE_FULL11");}
void group_start(){auto t=fresh();t.kmem.write_memory(01777,inst(026,0002,0001,02007));t.C_reg=01777;
 req(exec(t)&&t.C_reg==0000&&t.A_reg==0001&&t.Loop_reg==0002,"GROUP_UNEQUAL_SEQ10");}
void arithmetic(){auto t=fresh();t.kmem.write_memory(01777,inst(001,0000,0000,0003));t.C_reg=01777;
 req(exec(t)&&t.C_reg==0000,"ARITH_SEQ10");}
void drum_legacy(){auto t=fresh();t.kmem.write_memory(01777,inst(025,0000,0001,0002));t.C_reg=01777;
 req(exec(t)&&t.C_reg==0000&&t.K_reg==0,"IO25_LEGACY_SEQ10_PREFETCH");}
void stop_policy(){auto t=fresh();t.kmem.write_memory(01777,inst(033));t.C_reg=01777;
 req(!exec(t)&&t.T_reg&&t.C_reg==0000,"STOP_HOST_PC_SEQUENTIAL_POLICY");
 // C after STOP is NOT claimed as historical behavior.
}
} // namespace
int main(){
 try{
  nop_low();nop_high();compare_false();compare_true();call_full11();call_not_taken();
  return_full11();conditional_dispatch();group_start();arithmetic();drum_legacy();stop_policy();
  std::cout<<"H25_H18_UVK_NATIVE=PASS; CASES=12/12; LOW10_WRAP=PASS; BIT11_PRESERVE=PASS;"
              " DIRECT_FULL11=PASS; IO25_LEGACY_PREFETCH=PASS; HARDWARE_ORACLE=0\n";
  return 0;
 }catch(const std::exception&e){std::cerr<<"H25_H18_UVK_NATIVE=FAIL "<<e.what()<<'\n';return 1;}
}
