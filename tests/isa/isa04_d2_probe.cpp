// ISA-04 D2. Source-backed STRICT, current emulator POLICY, unresolved OBS.
// Compile and run with src/main.cpp, using the same stub strategy as D1.
#include <boost/multiprecision/cpp_int.hpp>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
constexpr uint64_t M = uint64_t{1} << 40;
constexpr uint64_t MAG = M - 1;
constexpr uint64_t PC = 0100;
using boost::multiprecision::uint128_t;
int failures = 0;
int strict_count = 0, policy_count = 0, observation_count = 0;

struct Quiet {
    std::ostringstream buffer;
    std::streambuf* saved;
    Quiet(): saved(std::cout.rdbuf(buffer.rdbuf())) {}
    ~Quiet() { std::cout.rdbuf(saved); }
};
std::string oct(uint64_t value) {
    std::ostringstream o;
    o << std::oct << value;
    return o.str();
}
uint64_t command(unsigned opcode, uint64_t a1=2, uint64_t a2=3, uint64_t a3=4) {
    return (uint64_t(opcode) << 36) | (a1 << 24) | (a2 << 12) | a3;
}
bool step(Kyiv_t& machine) {
    Quiet q;
    return machine.execute_opcode();
}
struct Outcome { uint64_t dest, pc; bool continuation, stopped; };
Outcome run(unsigned opcode, uint64_t lhs, uint64_t rhs,
            uint64_t a1=2, uint64_t a2=3, uint64_t a3=4) {
    Kyiv_t m;
    m.kmem.write_memory(a1,lhs);
    m.kmem.write_memory(a2,rhs);
    m.C_reg = PC;
    m.kmem.write_memory(PC,command(opcode,a1,a2,a3));
    const bool ongoing = step(m);
    return {m.kmem.read_memory(a3),m.C_reg,ongoing,m.T_reg};
}
void check(const char* label, bool ok, bool policy, const std::string& detail={}) {
    failures += !ok;
    (policy ? policy_count : strict_count)++;
    std::cout << (ok ? (policy ? "POLICY-PASS " : "PASS ") : "FAIL ") << label;
    if (!detail.empty()) std::cout << " | " << detail;
    std::cout << '\n';
}
void obs(const char* label,const std::string& detail) {
    ++observation_count;
    std::cout << "OBS " << label << " | " << detail << " [unresolved; no oracle]\n";
}
uint64_t multiplication(uint64_t lhs,uint64_t rhs,bool rounded) {
    const uint128_t magnitude = (uint128_t(lhs & MAG) * uint128_t(rhs & MAG)
        + (rounded ? (uint128_t(1) << 39) : uint128_t(0))) >> 40;
    const uint64_t low = uint64_t(magnitude) & MAG;
    return low | (low && bool(lhs & M) != bool(rhs & M) ? M : 0);
}
uint64_t cyclic_policy(uint64_t a, uint64_t b) {
    const int64_t signed_a = (a & M) ? -int64_t(a & MAG) : int64_t(a & MAG);
    const int64_t signed_b = (b & M) ? -int64_t(b & MAG) : int64_t(b & MAG);
    const int64_t sum = signed_a + signed_b;
    const bool negative = sum < 0;
    const uint64_t magnitude = uint64_t(negative ? -sum : sum);
    return ((magnitude + (magnitude >= M ? 1ULL : 0ULL)) & MAG)
        | (negative ? M : 0ULL);
}
void verify(unsigned op, uint64_t a, uint64_t b, uint64_t expected,
            const char* label, bool policy=false) {
    try {
        const Outcome o=run(op,a,b);
        check(label,o.dest==expected && o.pc==PC+1 && o.continuation && !o.stopped,
              policy,"actual="+oct(o.dest)+", expected="+oct(expected));
    } catch(const std::exception& e) {check(label,false,policy,std::string("exception: ")+e.what());}
}
}

int main() {
    // Strict: sums within representable magnitude avoid the disputed carry.
    verify(007,M/4,M/8,3*M/8,"07_positive_no_carry");
    verify(007,M|M/4,M|M/8,M|(3*M/8),"07_negative_no_carry");
    verify(007,M/2,M|(M/4),M/4,"07_different_signs_no_carry");
    // Policy-only: these checks preserve what the existing emulator does;
    // they do NOT assert which LSB actual Kyiv hardware would produce.
    verify(007,M/2,M/2,cyclic_policy(M/2,M/2),"07_positive_exact_one",true);
    verify(007,M|M/2,M|M/2,cyclic_policy(M|M/2,M|M/2),"07_negative_exact_minus_one",true);
    verify(007,M/2,M/2+1,cyclic_policy(M/2,M/2+1),"07_positive_over_one",true);
    verify(007,M|M/2,M|(M/2+1),cyclic_policy(M|M/2,M|(M/2+1)),"07_negative_under_minus_one",true);
    verify(007,MAG,MAG,cyclic_policy(MAG,MAG),"07_near_max_both",true);

    // For a nonzero rounded/truncated result, sign is determined by operands.
    verify(010,M|M/2,M/2,multiplication(M|M/2,M/2,false),"10_nonzero_negative_product");
    verify(011,M|M/2,M/2,multiplication(M|M/2,M/2,true),"11_nonzero_negative_rounded_product");
    verify(010,1,M/2,0,"10_discard_half_lsb");
    verify(011,1,M/2,1,"11_round_half_lsb_up");
    verify(011,1,M/2-1,0,"11_below_rounding_threshold");

    // Sign-magnitude negative nonzero input to normalization.
    try {
        Kyiv_t m;
        m.kmem.write_memory(2,M|(M/4));
        m.C_reg=PC;
        m.kmem.write_memory(PC,command(035));
        bool go=step(m);
        const auto p=m.kmem.read_memory(3),mant=m.kmem.read_memory(4);
        check("35_negative_quarter",go && !m.T_reg && m.C_reg==PC+1
          && p==1 && mant==(M|(M/2)),false,"order="+oct(p)+", mantissa="+oct(mant));
    } catch(const std::exception& e) {check("35_negative_quarter",false,false,e.what());}

    // Observations only: source texts do not establish these exact outputs.
    for (unsigned op : {010U,011U}) {
        auto o=run(op,M,M/2);
        obs(op==010 ? "10_negative_zero_times_half" : "11_negative_zero_times_half",
            "raw="+oct(o.dest));
    }
    for (uint64_t z : {uint64_t{0},M}) {
        Kyiv_t m;
        m.kmem.write_memory(2,z);
        m.C_reg=PC;m.kmem.write_memory(PC,command(035));
        bool go=step(m);
        obs(z==0 ? "35_positive_zero" : "35_negative_zero",
            "order="+oct(m.kmem.read_memory(3))+", mantissa="+oct(m.kmem.read_memory(4))+
            ", continues="+std::to_string(go));
    }
    // Destination/source2 overlap: observe memory-write ordering, not an ISA oracle.
    {
        auto o=run(035,M/4,0,2,3,3);
        obs("35_order_destination_alias", "final_address3="+oct(o.dest));
    }
    std::cout << "ISA-04 D2: STRICT="<<strict_count<<", POLICY="<<policy_count
       <<", OBS="<<observation_count<<", FAIL="<<failures<<'\n';
    return failures ? 1 : 0;
}
