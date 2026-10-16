// ISA-04 D4: signed-zero normalization and observe cyclic-carry discrepancies.
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) {return 0;}
namespace {
constexpr uint64_t M = uint64_t{1} << 40;
constexpr uint64_t HALF = M / 2;
constexpr uint64_t QUARTER = M / 4;
constexpr uint64_t MAX = M - 1;
constexpr uint64_t PC = 0100;
int strict_count = 0, obs_count = 0, failures = 0;
struct Quiet {
    std::ostringstream sink;
    std::streambuf* orig;
    Quiet() : orig(std::cout.rdbuf(sink.rdbuf())) {}
    ~Quiet() { std::cout.rdbuf(orig); }
};
std::string oct(uint64_t v) {std::ostringstream s;s<<std::oct<<v;return s.str();}
uint64_t command(unsigned op,unsigned a1=2,unsigned a2=3,unsigned a3=4) {
    return (uint64_t(op)<<36)|(uint64_t(a1)<<24)|(uint64_t(a2)<<12)|uint64_t(a3);
}
struct Outcome {uint64_t order=0, dest=0, pc=0;bool cont=false,stop=false;};
Outcome run(unsigned op, uint64_t first,uint64_t second=0,
            unsigned a1=2,unsigned a2=3,unsigned a3=4) {
    Kyiv_t m;
    m.kmem.write_memory(a1,first);
    if(a2!=a1) m.kmem.write_memory(a2,second);
    m.kmem.write_memory(PC,command(op,a1,a2,a3));
    m.C_reg=PC;
    bool cont;
    {Quiet q;cont=m.execute_opcode();}
    return {m.kmem.read_memory(a2),m.kmem.read_memory(a3),m.C_reg,cont,m.T_reg};
}
void norm(const char* name,const Outcome& v,uint64_t order,uint64_t result) {
    ++strict_count;
    bool ok=v.order==order && v.dest==result && v.pc==PC+1 && v.cont && !v.stop;
    failures += !ok;
    std::cout<<(ok?"PASS ":"FAIL ")<<name<<" | order="<<oct(v.order)
             <<", mantissa="<<oct(v.dest)<<", expected_order="<<oct(order)
             <<", expected_mantissa="<<oct(result)<<"\n";
}
void value(const char* name,const Outcome& v,uint64_t expected) {
    ++strict_count;
    bool ok=v.dest==expected && v.pc==PC+1 && v.cont && !v.stop;
    failures += !ok;
    std::cout<<(ok?"PASS ":"FAIL ")<<name<<" | actual="<<oct(v.dest)
             <<", expected="<<oct(expected)<<"\n";
}
void observation(const char* name,const Outcome& v,bool known,uint64_t dps) {
    ++obs_count;
    std::cout<<"OBS  "<<name<<" | raw="<<oct(v.dest);
    if(known)std::cout<<", DPS64_scaled_formula="<<oct(dps)
                      <<", delta_LSB="<<int64_t(v.dest & MAX)-int64_t(dps & MAX);
    else std::cout<<", DPS64_exact_one_boundary=undefined";
    std::cout<<", continue="<<v.cont<<" [not historical oracle]\n";
}
}
int main() {
    norm("35_positive_zero",run(035,0),0,0);
    norm("35_negative_zero",run(035,M),0,M);
    norm("35_negative_quarter",run(035,M|QUARTER),1,M|HALF);
    // DPS64 p.153: mantissa output follows order output.
    value("35_minus_zero_second_third_alias",run(035,M,0,2,3,3),M);
    norm("35_minus_zero_first_second_alias",run(035,M,0,2,2,4),0,M);
    value("07_no_carry_control",run(007,QUARTER,QUARTER),HALF);
    // Real-number correction from DPS64 p.102; ±1 are undefined there.
    observation("07_exact_plus_one",run(007,HALF,HALF),false,0);
    observation("07_exact_minus_one",run(007,M|HALF,M|HALF),false,0);
    observation("07_plus_one_plus_LSB",run(007,HALF,HALF+1),true,1);
    observation("07_minus_one_minus_LSB",run(007,M|HALF,M|(HALF+1)),true,M|1);
    observation("07_two_maximums",run(007,MAX,MAX),true,M-2);
    std::cout<<"ISA-04 D4 STRICT="<<strict_count<<", OBS="<<obs_count
             <<", FAIL="<<failures<<"\n";
    return failures ? 1 : 0;
}
