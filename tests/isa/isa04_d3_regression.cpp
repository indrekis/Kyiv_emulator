// ISA-04 D3: source-backed signed-zero multiplication and positive-zero norm.
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) {return 0;}
namespace {
constexpr uint64_t SIGN = uint64_t(1) << 40;
constexpr uint64_t HALF = SIGN / 2;
constexpr uint64_t QUARTER = SIGN / 4;
constexpr uint64_t PC = 0100;
int strict_count = 0;
int observation_count = 0;
int failures = 0;
struct Silence {
    std::ostringstream sink;
    std::streambuf* old;
    Silence() : old(std::cout.rdbuf(sink.rdbuf())) {}
    ~Silence() { std::cout.rdbuf(old); }
};
std::string oct(uint64_t x) {
    std::ostringstream s; s << std::oct << x; return s.str();
}
uint64_t instruction(unsigned opcode, unsigned a1=2, unsigned a2=3,unsigned a3=4) {
    return (uint64_t(opcode)<<36) | (uint64_t(a1)<<24)
           | (uint64_t(a2)<<12) | uint64_t(a3);
}
struct Result {uint64_t dst=0;uint64_t second=0;uint64_t pc=0;bool cont=false;bool stop=false;};
Result run(unsigned op,uint64_t a,uint64_t b=0,unsigned a1=2,unsigned a2=3,unsigned a3=4) {
    Kyiv_t m;
    m.kmem.write_memory(a1,a);
    if (a1!=a2) m.kmem.write_memory(a2,b);
    m.kmem.write_memory(PC,instruction(op,a1,a2,a3));
    m.C_reg=PC;
    bool continuing;
    {Silence quiet;continuing=m.execute_opcode();}
    return {m.kmem.read_memory(a3),m.kmem.read_memory(a2),m.C_reg,continuing,m.T_reg};
}
void strict(const char* label,const Result& v,uint64_t expected) {
    ++strict_count;
    bool ok = v.dst==expected && v.pc==PC+1 && v.cont && !v.stop;
    failures += !ok;
    std::cout << (ok?"PASS ":"FAIL ") << label
              << " | actual="<<oct(v.dst)<<", expected="<<oct(expected)<<"\n";
}
void norm_strict(const char* label,uint64_t input,uint64_t expected_order,uint64_t expected_mantissa) {
    Result r=run(035,input);
    ++strict_count;
    bool ok = r.second==expected_order && r.dst==expected_mantissa
           && r.pc==PC+1 && r.cont && !r.stop;
    failures += !ok;
    std::cout<<(ok?"PASS ":"FAIL ")<<label<<" | order="<<oct(r.second)
             <<", mantissa="<<oct(r.dst)<<"\n";
}
void observe(const char* label,const Result& r) {
    ++observation_count;
    std::cout<<"OBS "<<label<<" | order="<<oct(r.second)
             <<", mantissa="<<oct(r.dst)<<" [no historical assertion]\n";
}
}
int main(){
    // DPS64 pp. 149-150: operand sign XOR, even if the product is zero.
    strict("10_negative_zero_times_half", run(010,SIGN,HALF), SIGN);
    strict("11_negative_zero_times_half", run(011,SIGN,HALF), SIGN);
    strict("10_positive_zero_times_negative_half",run(010,0,SIGN|HALF),SIGN);
    strict("11_positive_zero_times_negative_half",run(011,0,SIGN|HALF),SIGN);
    strict("10_negative_zero_times_negative_half",run(010,SIGN,SIGN|HALF),0);
    strict("11_negative_zero_times_negative_half",run(011,SIGN,SIGN|HALF),0);
    strict("10_negative_underflow_to_zero",run(010,SIGN|1,HALF),SIGN);
    strict("11_negative_below_rounding_threshold",run(011,SIGN|1,HALF-1),SIGN);
    strict("11_negative_round_half_lsb_up",run(011,SIGN|1,HALF),SIGN|1);
    strict("10_nonzero_negative_product",run(010,SIGN|HALF,HALF),SIGN|QUARTER);
    strict("11_nonzero_negative_product",run(011,SIGN|HALF,HALF),SIGN|QUARTER);
    // DPS64 p. 153: zero suppresses normalizing shifts and clears counter.
    norm_strict("35_positive_zero_no_shifts",0,SIGN,0);
    norm_strict("35_positive_quarter",QUARTER,SIGN|1,HALF);
    // DPS64 p. 153: order written first, mantissa second.
    strict("35_alias_second_third_final_mantissa",run(035,QUARTER,0,2,3,3),HALF);
    // Negative zero has a sign trigger and zero-detector ambiguity. Remain OBS.
    observe("35_negative_zero",run(035,SIGN));
    std::cout<<"ISA-04 D3 STRICT="<<strict_count<<", OBS="<<observation_count
             <<", FAIL="<<failures<<"\n";
    return failures ? 1 : 0;
}
