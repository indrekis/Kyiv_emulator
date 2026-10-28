// ISA-04 D1: CPU arithmetic characterization (no source modifications).
// Build from repository root (MSYS2):
// g++ -std=c++17 -O0 -g -Iinc src/main.cpp tests/isa/isa04_characterization.cpp -o tempkyiv/isa04_characterization.exe
// ./tempkyiv/isa04_characterization.exe
// Exit status reflects STRICT tests only. OBS entries are not historical oracles.
#include <boost/multiprecision/cpp_int.hpp>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
constexpr uint64_t SIGN = uint64_t{1} << 40;
constexpr uint64_t MAG = SIGN - 1;
constexpr uint64_t PC = 0100;
using boost::multiprecision::uint128_t;
unsigned strict_total = 0, strict_failed = 0, obs_total = 0;

uint64_t inst(unsigned op, uint64_t a1=0002, uint64_t a2=0003, uint64_t a3=0004) {
    return (uint64_t(op) << 36) | (a1 << 24) | (a2 << 12) | a3;
}
void setup(Kyiv_t& m, unsigned op, uint64_t a1=0002, uint64_t a2=0003, uint64_t a3=0004) {
    m.C_reg = PC;
    m.kmem.write_memory(PC, inst(op, a1, a2, a3));
}
class Mute {
    std::ostringstream sink;
    std::streambuf* previous;
public:
    Mute(): previous(std::cout.rdbuf(sink.rdbuf())) {}
    ~Mute(){std::cout.rdbuf(previous);}
    Mute(const Mute&) = delete;
    Mute& operator=(const Mute&) = delete;
};
bool step(Kyiv_t& cpu) {
    Mute silence;
    return cpu.execute_opcode();
}
std::string oct(uint64_t x) {
    std::ostringstream o; o << std::oct << x; return o.str();
}
uint64_t rounded_mul(uint64_t a, uint64_t b, bool round) {
    const uint128_t product = uint128_t(a & MAG) * uint128_t(b & MAG)
        + (round ? (uint128_t(1) << 39) : uint128_t(0));
    uint64_t magnitude = static_cast<uint64_t>(product >> 40) & MAG;
    if (magnitude && bool(a & SIGN) != bool(b & SIGN)) magnitude |= SIGN;
    return magnitude;
}
void strict(const char* name, bool ok, const std::string& detail = {}) {
    ++strict_total; strict_failed += !ok;
    std::cout << (ok ? "PASS " : "FAIL ") << name;
    if (!detail.empty()) std::cout << " | " << detail;
    std::cout << '\n';
}
void observe(const char* name, const std::string& detail) {
    ++obs_total;
    std::cout << "OBS  " << name << " | " << detail << " [no historical assertion]" << '\n';
}
// Run a one-instruction program and fetch the raw destination code.
std::pair<uint64_t,bool> run(unsigned op, uint64_t a, uint64_t b) {
    Kyiv_t m;
    m.kmem.write_memory(0002, a);
    m.kmem.write_memory(0003, b);
    setup(m,op);
    bool go=step(m);
    if (m.C_reg != 0101 || m.T_reg) throw std::runtime_error("unexpected C or T in run()");
    return {m.kmem.read_memory(0004), go};
}
template<typename F> void strict_case(const char* name, F&& f) {
    try { const auto [pass, detail] = f(); strict(name, pass, detail); }
    catch(const std::exception& ex) { strict(name,false,std::string("exception: ")+ex.what()); }
    catch(...) { strict(name,false,"unknown exception"); }
}
template<typename F> void observation(const char* name, F&& f) {
    try {observe(name,f());}
    catch(const std::exception& ex) {observe(name,std::string("exception: ")+ex.what());}
    catch(...) {observe(name,"unknown exception");}
}
}

int main(){
    // Seven-bit names in the console are intentional; operations are octal.
    strict_case("07_addcyc_no_carry_positive", [] {
        auto [v,go]=run(007,SIGN/4,SIGN/8);
        return std::pair{go && v == 3*SIGN/8,"result="+oct(v)+", expected="+oct(3*SIGN/8)};
    });
    strict_case("07_addcyc_no_carry_negative", [] {
        auto [v,go]=run(007,SIGN|SIGN/4,SIGN|SIGN/8);
        return std::pair{go && v == (SIGN|3*SIGN/8),"result="+oct(v)+", expected="+oct(SIGN|3*SIGN/8)};
    });
    strict_case("10_mul_half_half", [] {
        auto [v,go]=run(010,SIGN/2,SIGN/2);
        return std::pair{go && v==rounded_mul(SIGN/2,SIGN/2,false),"result="+oct(v)};
    });
    strict_case("10_mul_mixed_sign", [] {
        auto [v,go]=run(010,SIGN|(SIGN/2),SIGN/2);
        uint64_t want=rounded_mul(SIGN|(SIGN/2),SIGN/2,false);
        return std::pair{go && v==want,"result="+oct(v)+", expected="+oct(want)};
    });
    strict_case("10_mul_max_max_45bit_accumulator", [] {
        auto [v,go]=run(010,MAG,MAG);
        uint64_t want=017777777777774ULL; // H14 45-bit, 40-cycle model
        return std::pair{go && v==want,"result="+oct(v)+", expected="+oct(want)};
    });
    strict_case("10_mul_truncation_at_half_lsb", [] {
        auto [v,go]=run(010,1,SIGN/2);
        return std::pair{go && v==0,"result="+oct(v)+", expected=0"};
    });
    strict_case("11_rmul_half_half", [] {
        auto [v,go]=run(011,SIGN/2,SIGN/2);
        uint64_t want=rounded_mul(SIGN/2,SIGN/2,true);
        return std::pair{go && v==want,"result="+oct(v)+", expected="+oct(want)};
    });
    strict_case("11_rmul_tie_adds_one_lsb", [] {
        auto [v,go]=run(011,1,SIGN/2);
        return std::pair{go && v==1,"result="+oct(v)+", expected=1"};
    });
    strict_case("11_rmul_below_tie_no_increment", [] {
        auto [v,go]=run(011,1,SIGN/2-1);
        return std::pair{go && v==0,"result="+oct(v)+", expected=0"};
    });
    strict_case("11_rmul_max_max_45bit_accumulator", [] {
        auto [v,go]=run(011,MAG,MAG);
        uint64_t want=017777777777775ULL; // GY62 p.172, H14-C
        return std::pair{go && v==want,"result="+oct(v)+", expected="+oct(want)};
    });
    strict_case("35_norm_half_already_normal", [] {
        Kyiv_t m;m.kmem.write_memory(0002,SIGN/2);setup(m,035);
        bool go=step(m);
        uint64_t exp=m.kmem.read_memory(0003), val=m.kmem.read_memory(0004);
        return std::pair{go && m.C_reg==0101 && exp==SIGN && val==SIGN/2,
            "exp="+oct(exp)+", mantissa="+oct(val)};
    });
    strict_case("35_norm_quarter_left_shift_one", [] {
        Kyiv_t m;m.kmem.write_memory(0002,SIGN/4);setup(m,035);
        bool go=step(m);
        uint64_t exp=m.kmem.read_memory(0003), val=m.kmem.read_memory(0004);
        return std::pair{go && exp==(SIGN|1) && val==SIGN/2,"exp="+oct(exp)+", mantissa="+oct(val)};
    });
    strict_case("35_norm_smallest_positive_lsb", [] {
        Kyiv_t m;m.kmem.write_memory(0002,1);setup(m,035);
        bool go=step(m);
        uint64_t exp=m.kmem.read_memory(0003), val=m.kmem.read_memory(0004);
        return std::pair{go && exp==(SIGN|39) && val==SIGN/2,"exp="+oct(exp)+", mantissa="+oct(val)};
    });

    // The following are observations only, pending scheme-level source reconciliation.
    observation("07_positive_carry_at_one", [] {
        auto [v,go]=run(007,SIGN/2,SIGN/2);
        return "raw="+oct(v)+", expected mathematical cyclic remainder=0; continue="+std::to_string(go);
    });
    observation("07_negative_carry_at_minus_one", [] {
        auto [v,go]=run(007,SIGN|SIGN/2,SIGN|SIGN/2);
        return "raw="+oct(v)+", expected mathematical cyclic remainder=0; continue="+std::to_string(go);
    });
    observation("10_negative_zero_times_half", [] {
        auto [v,go]=run(010,SIGN,SIGN/2);
        return "raw="+oct(v)+", continue="+std::to_string(go);
    });
    observation("11_negative_zero_times_half", [] {
        auto [v,go]=run(011,SIGN,SIGN/2);
        return "raw="+oct(v)+", continue="+std::to_string(go);
    });
    observation("35_normalize_positive_zero", [] {
        Kyiv_t m;setup(m,035);bool go=step(m);
        return "exp="+oct(m.kmem.read_memory(0003)) + ", mantissa="+oct(m.kmem.read_memory(0004))+
            ", continue="+std::to_string(go);
    });
    observation("35_normalize_negative_zero", [] {
        Kyiv_t m;m.kmem.write_memory(0002,SIGN);setup(m,035);bool go=step(m);
        return "exp="+oct(m.kmem.read_memory(0003)) + ", mantissa="+oct(m.kmem.read_memory(0004))+
            ", continue="+std::to_string(go);
    });
    std::cout << "ISA-04 D1 STRICT: " << (strict_total-strict_failed) << '/' << strict_total
              << " pass; " << strict_failed << " mismatch(es); OBS " << obs_total << '\n';
    return strict_failed ? 1 : 0;
}
