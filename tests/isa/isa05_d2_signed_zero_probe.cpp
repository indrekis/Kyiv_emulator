// ISA-05 D2: GY62 printed pp. 13 and 17, exact sign/magnitude comparison.
// Link with src/main.cpp (CPU only), not CLI src/asm_disasm.cpp.
#include <cstdint>
#include <exception>
#include <iostream>
#include <sstream>
#include <string>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
constexpr uint64_t SIGN = uint64_t{1} << 40;
constexpr uint64_t PC = 0100;
constexpr uint64_t TARGET = 0250;
int strict_ok = 0, policy_ok = 0, failed = 0;

std::string oct(uint64_t x) {
    std::ostringstream os;
    os << std::oct << x;
    return os.str();
}
struct Silence {
    std::ostringstream out;
    std::streambuf* saved;
    Silence(): saved(std::cout.rdbuf(out.rdbuf())) {}
    ~Silence() { std::cout.rdbuf(saved); }
};
uint64_t command(unsigned opcode, uint64_t a1=2, uint64_t a2=3, uint64_t a3=TARGET) {
    return (uint64_t(opcode)<<36) | (a1<<24) | (a2<<12) | a3;
}
struct Result { uint64_t pc; bool continues, stopped; };
Result run(unsigned opcode,uint64_t left,uint64_t right,
           uint64_t a1=2,uint64_t a2=3) {
    Kyiv_t m;
    m.kmem.write_memory(a1,left);
    if (a1 != a2) m.kmem.write_memory(a2,right);
    m.kmem.write_memory(PC,command(opcode,a1,a2));
    m.C_reg=PC;
    bool continues;
    {Silence silence; continues=m.execute_opcode();}
    return {m.C_reg,continues,m.T_reg};
}
void check(const char* name,unsigned opcode,uint64_t left,uint64_t right,
           bool should_branch,bool policy=false,uint64_t a1=2,uint64_t a2=3) {
    try {
        const Result r=run(opcode,left,right,a1,a2);
        const uint64_t wanted=should_branch?TARGET:PC+1;
        const bool ok=r.pc==wanted && r.continues && !r.stopped;
        if (ok) (policy?policy_ok:strict_ok)++;
        else failed++;
        std::cout<<(ok?(policy?"POLICY-PASS ":"PASS "):"FAIL ")<<name
                 <<" | C="<<oct(r.pc)<<", expected="<<oct(wanted)
                 <<", continue="<<r.continues<<", stop="<<r.stopped<<'\n';
    } catch (const std::exception& e) {
        ++failed;std::cout<<"FAIL "<<name<<" | exception: "<<e.what()<<'\n';
    } catch (...) {
        ++failed;std::cout<<"FAIL "<<name<<" | unknown exception\n";
    }
}
}
int main() {
    // GY62 p.17: -0 < +0. Retain <= for other equal numeric values as POLICY.
    check("04_negative_zero_below_positive_zero",004,SIGN,0,true);
    check("04_positive_zero_above_negative_zero",004,0,SIGN,false);
    check("04_negative_zero_below_positive_nonzero",004,SIGN,1,true);
    check("04_positive_zero_above_negative_nonzero",004,0,SIGN|1,false);
    check("04_negative_nonzero_below_negative_zero",004,SIGN|1,SIGN,true);
    check("04_negative_zero_above_negative_nonzero",004,SIGN,SIGN|1,false);
    check("04_positive_nonzero_above_positive_zero",004,1,0,false);
    check("04_positive_zero_below_positive_nonzero",004,0,1,true);

    // GY62 p.13: 16 requires exact magnitude AND sign, including both zeros.
    check("16_pluszero_vs_minuszero",016,0,SIGN,false);
    check("16_minuszero_vs_pluszero",016,SIGN,0,false);
    check("16_pluszero_equals_pluszero",016,0,0,true);
    check("16_minuszero_equals_minuszero",016,SIGN,SIGN,true);
    check("16_equal_positive_nonzero",016,7,7,true);
    check("16_equal_negative_nonzero",016,SIGN|7,SIGN|7,true);
    check("16_unequal_sign_nonzero",016,7,SIGN|7,false);
    check("16_unequal_magnitude",016,SIGN|7,SIGN|6,false);
    check("16_alias_same_cell_negative_zero",016,SIGN,0,true,false,2,2);

    // Current <= equality convention remains under historical review.
    check("04_equal_positive_zero",004,0,0,true,true);
    check("04_equal_negative_zero",004,SIGN,SIGN,true,true);
    check("04_equal_nonzero",004,7,7,true,true);
    check("05_abs_equal_with_opposite_zero_signs",005,0,SIGN,true,true);
    check("05_abs_equal_nonzero",005,SIGN|7,7,true,true);

    std::cout<<"ISA-05 D2 STRICT="<<strict_ok<<"/17 POLICY="<<policy_ok
             <<"/5 FAIL="<<failed<<'\n';
    return failed?1:0;
}
