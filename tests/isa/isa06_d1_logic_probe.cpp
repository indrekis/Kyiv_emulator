// ISA-06 D1: logical instructions 013, 014, 015, 017.
// GY62, printed p. 12; DPS64, printed pp. 18-19.
// H3 regression: opcode 17 is 41-bit XNOR (DPS1964 p.18); OBS remain unqualified.
// Build from repository root:
// g++ -std=c++17 -O0 -g -Iinc src/main.cpp tests/isa/isa06_d1_logic_probe.cpp -o tempkyiv/isa06_d1_logic_probe.exe
#include <cstdint>
#include <exception>
#include <iostream>
#include <sstream>
#include <string>
#include <utility>
#include <vector>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
constexpr uint64_t SIGN = uint64_t{1} << 40;
constexpr uint64_t MASK41 = (SIGN << 1) - 1;
constexpr uint64_t PC = 0100;
constexpr uint64_t MOD = 04000;
int strict_total = 0, strict_pass = 0, obs_total = 0;

std::string oct(uint64_t x) {
    std::ostringstream out;
    out << std::oct << x;
    return out.str();
}
uint64_t instruction(unsigned op, uint64_t a1, uint64_t a2, uint64_t a3) {
    return (uint64_t(op) << 36) | ((a1 & 07777) << 24)
         | ((a2 & 07777) << 12) | (a3 & 07777);
}
struct Silence {
    std::ostringstream sink;
    std::streambuf* saved;
    Silence() : saved(std::cout.rdbuf(sink.rdbuf())) {}
    ~Silence() { std::cout.rdbuf(saved); }
    Silence(const Silence&) = delete;
    Silence& operator=(const Silence&) = delete;
};
bool step(Kyiv_t& m) {
    Silence silent;
    return m.execute_opcode();
}
struct Case {
    const char* name;
    unsigned op;
    uint64_t a1, a2, a3;
    uint64_t initial_A;
    std::vector<std::pair<uint64_t, uint64_t>> initial;
    uint64_t inspected_address, expected_value;
    // Optional extra postcondition: usually preservation of a source cell.
    uint64_t extra_address = 0, extra_expected = 0;
    bool check_extra = false;
};

void strict(const Case& tc) {
    ++strict_total;
    try {
        Kyiv_t m;
        m.A_reg = tc.initial_A;
        for (const auto& entry : tc.initial)
            m.kmem.write_memory(entry.first, entry.second);
        m.kmem.write_memory(PC, instruction(tc.op, tc.a1, tc.a2, tc.a3));
        m.C_reg = PC;
        const bool running = step(m);
        const uint64_t got = m.kmem.read_memory(tc.inspected_address);
        const bool extra = !tc.check_extra ||
            m.kmem.read_memory(tc.extra_address) == tc.extra_expected;
        const bool pass = running && !m.T_reg && m.C_reg == PC + 1 &&
                          got == tc.expected_value && extra;
        strict_pass += pass;
        std::cout << (pass ? "STRICT-PASS " : "DOC-MISMATCH ") << tc.name
                  << " | op=" << oct(tc.op)
                  << " got=" << oct(got) << " expected=" << oct(tc.expected_value)
                  << " C=" << oct(m.C_reg) << " A=" << oct(m.A_reg)
                  << " running=" << running << " stop=" << m.T_reg
                  << " extra=" << extra << '\n';
    } catch (const std::exception& e) {
        std::cout << "DOC-MISMATCH " << tc.name << " | exception: " << e.what() << '\n';
    } catch (...) {
        std::cout << "DOC-MISMATCH " << tc.name << " | unknown exception\n";
    }
}
void observe(const char* name, unsigned op, uint64_t a1, uint64_t a2,
             uint64_t a3, uint64_t initial_A,
             const std::vector<std::pair<uint64_t, uint64_t>>& data,
             uint64_t inspected) {
    ++obs_total;
    try {
        Kyiv_t m;
        m.A_reg = initial_A;
        for (const auto& e : data) m.kmem.write_memory(e.first, e.second);
        m.kmem.write_memory(PC, instruction(op, a1, a2, a3));
        m.C_reg = PC;
        const bool running = step(m);
        std::cout << "OBS " << name << " | value=" << oct(m.kmem.read_memory(inspected))
                  << " C=" << oct(m.C_reg) << " running=" << running
                  << " stop=" << m.T_reg << " [not historical oracle]\n";
    } catch (const std::exception& e) {
        std::cout << "OBS " << name << " | exception: " << e.what()
                  << " [not historical oracle]\n";
    } catch (...) {
        std::cout << "OBS " << name << " | unknown exception [not historical oracle]\n";
    }
}
} // namespace

int main() {
    // GY62 p.12: I contains a *memory address* of a shift constant.
    // Its six low bits give the amount. Its sign gives the direction.
    // The entire 41-bit operand, including sign, is logically shifted.
    const std::vector<Case> cases = {
        {"13_positive_zero_amount_preserves_negative_zero", 013, 2, 3, 4, 0,
            {{2, 0}, {3, SIGN}}, 4, SIGN},
        {"13_negative_zero_amount_preserves_code", 013, 2, 3, 4, 0,
            {{2, SIGN}, {3, SIGN | 025}}, 4, SIGN | 025},
        {"13_left_one_discards_sign", 013, 2, 3, 4, 0,
            {{2, 1}, {3, SIGN | 1}}, 4, 2, 3, SIGN | 1, true},
        {"13_right_one_moves_sign_into_magnitude", 013, 2, 3, 4, 0,
            {{2, SIGN | 1}, {3, SIGN}}, 4, SIGN >> 1},
        {"13_left_39", 013, 2, 3, 4, 0,
            {{2, 39}, {3, 1}}, 4, uint64_t{1} << 39},
        {"13_right_39", 013, 2, 3, 4, 0,
            {{2, SIGN | 39}, {3, SIGN}}, 4, 2},
        {"13_left_40_lsb_becomes_negative_zero", 013, 2, 3, 4, 0,
            {{2, 40}, {3, 1}}, 4, SIGN},
        {"13_right_40_sign_becomes_lsb", 013, 2, 3, 4, 0,
            {{2, SIGN | 40}, {3, SIGN}}, 4, 1},
        {"13_left_41_all_bits_zero", 013, 2, 3, 4, 0,
            {{2, 41}, {3, MASK41}}, 4, 0},
        {"13_right_41_all_bits_zero", 013, 2, 3, 4, 0,
            {{2, SIGN | 41}, {3, MASK41}}, 4, 0},
        {"13_left_63_all_bits_zero", 013, 2, 3, 4, 0,
            {{2, 63}, {3, MASK41}}, 4, 0},
        {"13_right_63_all_bits_zero", 013, 2, 3, 4, 0,
            {{2, SIGN | 63}, {3, MASK41}}, 4, 0},
        {"13_high_magnitude_bits_of_constant_ignored", 013, 2, 3, 4, 0,
            {{2, (uint64_t{1} << 32) | 2}, {3, 1}}, 4, 4},
        {"13_negative_high_magnitude_bits_ignored", 013, 2, 3, 4, 0,
            {{2, SIGN | (uint64_t{1} << 30) | 1}, {3, SIGN}}, 4, SIGN >> 1},
        {"13_shift_negative_zero_left_one", 013, 2, 3, 4, 0,
            {{2, 1}, {3, SIGN}}, 4, 0},
        {"13_shift_negative_zero_right_one", 013, 2, 3, 4, 0,
            {{2, SIGN | 1}, {3, SIGN}}, 4, SIGN >> 1},
        {"13_destination_equals_operand", 013, 2, 3, 3, 0,
            {{2, 1}, {3, 1}}, 3, 2, 2, 1, true},
        {"13_destination_equals_constant", 013, 2, 3, 2, 0,
            {{2, SIGN | 1}, {3, SIGN}}, 2, SIGN >> 1, 3, SIGN, true},
        {"13_all_three_addresses_modified", 013, MOD | 1, MOD | 2, MOD | 3, 1,
            {{2, 1}, {3, 1}}, 4, 2, 2, 1, true},
        {"13_destination_zero_discard", 013, 2, 3, 0, 0,
            {{2, 1}, {3, 1}}, 0, 0, 3, 1, true},

        // GY62 p.12 / DPS64 pp.18-19: bitwise operations use all 41 bits.
        {"14_or_mixed_bits_and_sign", 014, 2, 3, 4, 0,
            {{2, SIGN | 025}, {3, 042}}, 4, SIGN | 067},
        {"14_or_positive_and_negative_zero", 014, 2, 3, 4, 0,
            {{2, 0}, {3, SIGN}}, 4, SIGN},
        {"15_and_mixed_bits_and_sign", 015, 2, 3, 4, 0,
            {{2, SIGN | 074}, {3, SIGN | 012}}, 4, SIGN | 010},
        {"15_and_positive_and_negative_zero", 015, 2, 3, 4, 0,
            {{2, 0}, {3, SIGN}}, 4, 0},
        {"17_xnor_cancels_two_sign_bits", 017, 2, 3, 4, 0,
            {{2, SIGN | 074}, {3, SIGN | 012}}, 4, (MASK41 ^ 066)},
        {"17_xnor_negative_zero_and_positive_zero", 017, 2, 3, 4, 0,
            {{2, SIGN}, {3, 0}}, 4, (MASK41 ^ SIGN)},
        {"17_xnor_two_negative_zeros", 017, 2, 3, 4, 0,
            {{2, SIGN}, {3, SIGN}}, 4, MASK41},
        {"14_or_destination_equals_first_source", 014, 2, 3, 2, 0,
            {{2, 025}, {3, 042}}, 2, 067, 3, 042, true},
        {"15_and_destination_equals_second_source", 015, 2, 3, 3, 0,
            {{2, 074}, {3, 012}}, 3, 010, 2, 074, true},
        {"17_xnor_same_source_dest_all", 017, 2, 2, 2, 0,
            {{2, SIGN | 012}}, 2, MASK41},
        {"14_or_all_three_addresses_modified", 014, MOD | 1, MOD | 2, MOD | 3, 1,
            {{2, SIGN | 025}, {3, 042}}, 4, SIGN | 067},
        {"15_and_modifier_on_first_address_only", 015, MOD | 1, 3, 4, 1,
            {{2, SIGN | 074}, {3, SIGN | 012}}, 4, SIGN | 010},
        {"17_xnor_modifier_on_second_address_only", 017, 2, MOD | 2, 4, 1,
            {{2, SIGN | 074}, {3, SIGN | 012}}, 4, (MASK41 ^ 066)},
        {"14_or_destination_zero_discard", 014, 2, 3, 0, 0,
            {{2, SIGN}, {3, 1}}, 0, 0, 2, SIGN, true},
        {"15_and_destination_zero_discard", 015, 2, 3, 0, 0,
            {{2, SIGN | 7}, {3, SIGN | 1}}, 0, 0},
        {"17_xnor_destination_zero_discard", 017, 2, 3, 0, 0,
            {{2, SIGN}, {3, SIGN}}, 0, 0},
        {"14_or_modified_address_wraps_to_zero", 014, 2, MOD | 03777, 4, 1,
            {{2, SIGN | 025}}, 4, SIGN | 025},
        {"17_xnor_modified_destination_wraps_to_zero", 017, 2, 3, MOD | 03777, 1,
            {{2, SIGN}, {3, 1}}, 0, 0}
    };
    for (const auto& tc : cases) strict(tc);

    // These cases deliberately fall outside the documented RAM address range
    // (GY62 pp. 8-9) or use a ROM destination. They do not have a historical oracle.
    observe("14_write_to_ROM_destination", 014, 2, 3, 03010, 0,
            {{2, SIGN}, {3, 1}}, 03010);
    observe("13_modified_source_enters_undocumented_2000", 013,
            2, MOD | 01777, 4, 1, {{2, 1}}, 4);

    std::cout << "ISA-06 D1 STRICT=" << strict_pass << '/' << strict_total
              << " DOC-MISMATCH=" << (strict_total - strict_pass)
              << " POLICY=0 OBS=" << obs_total << '\n';
    return strict_total == strict_pass ? 0 : 1;
}
