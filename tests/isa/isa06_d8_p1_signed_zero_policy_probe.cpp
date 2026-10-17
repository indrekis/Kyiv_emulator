// ISA-06 D8-P1: candidate signed-zero policy; NOT a hardware oracle.
// GY62 printed pp. 11,13,17,170-171; DPS64 printed pp. 96-101,144-146.
#include <cstdint>
#include <exception>
#include <iostream>
#include <sstream>
#include <string>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
using W=uint64_t;
constexpr W SIGN=W{1}<<40;
constexpr W PC=0100;
constexpr W RETURN=0137;
constexpr W LOOP=0765;
int policy_total=0,policy_pass=0,strict_total=0,strict_pass=0;
W inst(W op,W a,W b,W c) {
    return (op<<36) | ((a&07777)<<24) | ((b&07777)<<12) | (c&07777);
}
struct Silence {
    std::ostringstream ignored;
    std::streambuf* old;
    Silence():old(std::cout.rdbuf(ignored.rdbuf())){}
    ~Silence(){std::cout.rdbuf(old);}
};
bool tick(Kyiv_t& cpu){ Silence quiet; return cpu.execute_opcode(); }
void setup(Kyiv_t& m){
    m.P_reg=RETURN; m.Loop_reg=LOOP; m.A_reg=0; m.T_reg=false;
    m.kmem.write_rom(03026,SIGN); // TEST FIXTURE, not authenticated ROM
}
void probe(const char* name,W op,W a,W b,W expected,bool policy,
           bool historical=false,W pc=PC) {
    if(policy) ++policy_total; else ++strict_total;
    try {
        Kyiv_t m; setup(m);
        const W src1=historical?0021:0002;
        const W src2=historical?0000:0003;
        const W dst =historical?0020:0004;
        m.kmem.write_memory(src1,a);
        if(src2!=0) m.kmem.write_memory(src2,b);
        const W k=historical?0'01'0021'0000'0020ULL:inst(op,src1,src2,dst);
        m.kmem.write_memory(pc,k);
        m.C_reg=pc;
        const bool running=tick(m);
        const W got=m.kmem.read_memory(dst);
        const bool ok=running && !m.T_reg && m.K_reg==k &&
              m.C_reg==pc+1 && got==expected &&
              m.P_reg==RETURN && m.Loop_reg==LOOP && m.A_reg==0;
        if(policy)policy_pass+=ok;else strict_pass+=ok;
        std::cout<<(ok?(policy?"POLICY-PASS ":"STRICT-PASS "):
                             (policy?"POLICY-FAIL ":"DOC-MISMATCH "))
                 <<name<<" expected="<<std::oct<<expected
                 <<" actual="<<got<<" C="<<m.C_reg<<std::dec<<'\n';
    }catch(const std::exception& e){
        std::cout<<(policy?"POLICY-FAIL ":"DOC-MISMATCH ")<<name
                 <<" exception="<<e.what()<<'\n';
    }
}
}
int main(){
    // POLICY hypotheses: never count these as historical STRICT success.
    probe("01_+0_+0",001,0,0,0,true);
    probe("01_+0_-0",001,0,SIGN,SIGN,true);
    probe("01_-0_+0",001,SIGN,0,SIGN,true);
    probe("01_-0_-0",001,SIGN,SIGN,SIGN,true);
    probe("01_+5_-5",001,5,SIGN|5,SIGN,true);
    probe("01_-5_+5",001,SIGN|5,5,SIGN,true);
    // Genuine historical instruction words, but *injected* operand -0.
    // Not an end-to-end fourth-RAM-test historical oracle.
    probe("historical_0123_injected_-0",001,SIGN,0,SIGN,true,true,0123);
    probe("historical_0141_injected_-0",001,SIGN,0,SIGN,true,true,0141);
    // Existing documented arithmetic semantics, independent of zero-sum policy.
    probe("01_+7_+5",001,7,5,12,false);
    probe("01_-7_+5",001,SIGN|7,5,SIGN|2,false);
    probe("02_+7_minus_+7",002,7,7,SIGN,false);
    probe("02_-7_minus_-7",002,SIGN|7,SIGN|7,SIGN,false);
    const int strict_bad=strict_total-strict_pass;
    const int policy_bad=policy_total-policy_pass;
    std::cout<<"ISA-06 D8-P1 STRICT="<<strict_pass<<'/'<<strict_total
             <<" DOC-MISMATCH="<<strict_bad
             <<" POLICY="<<policy_pass<<'/'<<policy_total
             <<" POLICY-FAIL="<<policy_bad<<'\n';
    return (strict_bad||policy_bad)?1:0;
}
