// ISA-03 incremental regression: run with src/main.cpp only.
// Tests that rely on emulator policy are explicitly marked as such.
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
constexpr uint64_t sign = uint64_t{1} << 40;
constexpr uint64_t magnitude_mask = sign - 1;
constexpr uint64_t origin = 0100;
uint64_t instruction(unsigned op, uint64_t a, uint64_t b, uint64_t d) {
    return (uint64_t(op) << 36) | (a << 24) | (b << 12) | d;
}
void setup(Kyiv_t& machine, unsigned op, uint64_t a=0002, uint64_t b=0003, uint64_t d=0004) {
    machine.C_reg = origin;
    machine.kmem.write_memory(origin, instruction(op,a,b,d));
}
bool step(Kyiv_t& m) {
    std::ostringstream output;
    auto* previous = std::cout.rdbuf(output.rdbuf());
    try {
        bool result=m.execute_opcode();
        std::cout.rdbuf(previous);
        return result;
    } catch (...) { std::cout.rdbuf(previous); throw; }
}
template <class F> bool check(const char* name, F&& run) {
    try {
        bool pass=run();
        std::cout << (pass?"PASS ":"FAIL ") << name << '\n';
        return pass;
    } catch(const std::exception& e) {
        std::cout << "FAIL " << name << " exception=" << e.what() << '\n'; return false;
    }
}
}
int main() {
    int failures=0;
    failures+=!check("00_with_nonzero_address_fields_is_noop", [] {
        Kyiv_t m;setup(m, 000, 0002, 0003, 0004);
        m.kmem.write_memory(0004, 012345);
        return step(m) && m.C_reg == 0101 && !m.T_reg && m.kmem.read_memory(0004)==012345;
    });
    failures+=!check("12_normal_half_divided_by_three_quarters", [] {
        Kyiv_t m;m.kmem.write_memory(0002, sign/2);m.kmem.write_memory(0003, 3*sign/4);
        setup(m, 012);return step(m) && !m.T_reg && m.C_reg == 0101
            && m.kmem.read_memory(0004) == (uint64_t((static_cast<__uint128_t>(sign/2) << 40) / (3*sign/4)));
    });
    failures+=!check("12_quotient_exactly_one_stops", [] {
        Kyiv_t m;m.kmem.write_memory(0002, sign/2);m.kmem.write_memory(0003,sign/2);
        m.kmem.write_memory(0004,077);setup(m,012);
        return !step(m) && m.T_reg && m.C_reg==0101 && m.kmem.read_memory(0004)==077;
    });
    failures+=!check("12_blocked_quotient_one_skips_and_truncates", [] {
        Kyiv_t m;m.emergency_stop_blocked=true;m.kmem.write_memory(0002,sign/2);m.kmem.write_memory(0003,sign/2);
        setup(m,012);return step(m)&&!m.T_reg&&m.C_reg==0102&&m.kmem.read_memory(0004)==0;
    });
    failures+=!check("12_blocked_quotient_one_and_half_truncates", [] {
        Kyiv_t m;m.emergency_stop_blocked=true;m.kmem.write_memory(0002,3*sign/4);m.kmem.write_memory(0003,sign/2);
        setup(m,012);return step(m)&&!m.T_reg&&m.C_reg==0102&&m.kmem.read_memory(0004)==sign/2;
    });
    failures+=!check("12_blocked_negative_quotient_one_retains_negative_zero", [] {
        Kyiv_t m;m.emergency_stop_blocked=true;m.kmem.write_memory(0002,sign | sign/2);m.kmem.write_memory(0003,sign/2);
        setup(m,012);return step(m)&&!m.T_reg&&m.C_reg==0102&&m.kmem.read_memory(0004)==sign;
    });
    failures+=!check("12_division_by_zero_stops_even_when_blocked_emulator_policy", [] {
        Kyiv_t m;m.emergency_stop_blocked=true;m.kmem.write_memory(0002,sign/2);
        m.kmem.write_memory(0003,0);setup(m,012);
        return !step(m)&&m.T_reg&&m.C_reg==0101;
    });
    failures+=!check("01_new_block_flag_skips_on_overflow", [] {
        Kyiv_t m;m.emergency_stop_blocked=true;m.kmem.write_memory(0002,magnitude_mask);
        m.kmem.write_memory(0003,1);setup(m,001);
        return step(m)&&!m.T_reg&&m.C_reg==0102&&m.kmem.read_memory(0004)==0;
    });
    failures+=!check("02_new_block_flag_skips_on_overflow", [] {
        Kyiv_t m;m.emergency_stop_blocked=true;m.kmem.write_memory(0002,sign | magnitude_mask);
        m.kmem.write_memory(0003,1);setup(m,002);
        return step(m)&&!m.T_reg&&m.C_reg==0102&&m.kmem.read_memory(0004)==sign;
    });
    failures+=!check("03_new_block_flag_skips_on_overflow", [] {
        Kyiv_t m;m.emergency_stop_blocked=true;m.kmem.write_memory(0002,magnitude_mask);
        m.kmem.write_memory(0003,1);setup(m,003);
        return step(m)&&!m.T_reg&&m.C_reg==0102&&m.kmem.read_memory(0004)==0;
    });
    failures+=!check("33_stop_not_blocked_by_overflow_switch", [] {
        Kyiv_t m;m.emergency_stop_blocked=true;setup(m,033,0,0,0);
        return !step(m)&&m.T_reg;
    });
    std::cout << "ISA-03: " << (11-failures) << "/11 pass\n";
    return failures==0?0:1;
}
