// ISA-06 D2: logical instruction sequencing, aliasing, and fetched-K behavior.
// GY62, printed pp. 10, 12, 163-164; DPS64, pp. 18-19, 160-163.
// H3: opcode 17 expected as masked XNOR; no electrical-level timing claim.
// g++ -std=c++17 -O0 -g -Iinc src/main.cpp tests/isa/isa06_d2_logic_sequence_probe.cpp -o tempkyiv/isa06_d2_logic_sequence_probe.exe
#include <cstdint>
#include <exception>
#include <functional>
#include <iostream>
#include <sstream>
#include <string>
#include <utility>
#include <vector>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
using W = uint64_t;
constexpr W SIGN = W{1} << 40;
constexpr W MASK41 = (SIGN << 1) - 1;
constexpr W PC = 0100;
constexpr W MOD = 04000;
constexpr W SAVED_P = 0137;
constexpr W SAVED_CY = 0765;
int total = 0, passed = 0;

W inst(unsigned op, W a, W b, W c) {
    return (W(op) << 36) | ((a & 07777) << 24) |
           ((b & 07777) << 12) | (c & 07777);
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
    Silence silence;
    return m.execute_opcode();
}
void fill(Kyiv_t& m, const std::vector<std::pair<W,W>>& data) {
    for (const auto& d : data) m.kmem.write_memory(d.first, d.second);
}
bool regs(const Kyiv_t& m, W initial_A) {
    return m.P_reg == SAVED_P && m.Loop_reg == SAVED_CY && m.A_reg == initial_A;
}
void strict(const char* name, const std::function<bool(Kyiv_t&)>& run) {
    ++total;
    try {
        Kyiv_t m;
        m.P_reg = SAVED_P;
        m.Loop_reg = SAVED_CY;
        const bool good = run(m);
        passed += good;
        std::cout << (good ? "STRICT-PASS " : "DOC-MISMATCH ") << name
                  << " | C=" << std::oct << m.C_reg
                  << " K=" << m.K_reg << " A=" << m.A_reg
                  << " P=" << m.P_reg << " Cy=" << m.Loop_reg
                  << std::dec << " stop=" << m.T_reg << '\n';
    } catch (const std::exception& e) {
        std::cout << "DOC-MISMATCH " << name << " | exception: " << e.what() << '\n';
    } catch (...) {
        std::cout << "DOC-MISMATCH " << name << " | unknown exception\n";
    }
}
void single(const char* name, unsigned op, W a, W b, W c, W initial_A,
            const std::vector<std::pair<W,W>>& data, W dest, W expected) {
    strict(name, [=](Kyiv_t& m) {
        m.A_reg = initial_A;
        fill(m, data);
        const W fetched = inst(op, a, b, c);
        m.kmem.write_memory(PC, fetched);
        m.C_reg = PC;
        const bool running = step(m);
        return running && !m.T_reg && m.C_reg == PC + 1 &&
               m.K_reg == fetched && m.kmem.read_memory(dest) == expected &&
               regs(m, initial_A);
    });
}
} // namespace

int main() {
    // All aliases are within documented writable RAM and use 41-bit words.
    // GY62 pp. 10, 163-164: instruction is fetched to K before operand
    // selection and result write. GY62 p. 12: logical instructions are sequential.
    single("13_constant_is_operand_right", 013, 2, 2, 4, 0,
           {{2, SIGN | 1}}, 4, SIGN >> 1);
    single("13_constant_operand_destination_same_right", 013, 2, 2, 2, 0,
           {{2, SIGN | 1}}, 2, SIGN >> 1);
    single("13_constant_operand_destination_same_left", 013, 2, 2, 2, 0,
           {{2, 2}}, 2, 8);
    single("14_both_sources_same", 014, 2, 2, 4, 0,
           {{2, SIGN | 025}}, 4, SIGN | 025);
    single("15_all_three_same", 015, 2, 2, 2, 0,
           {{2, SIGN | 025}}, 2, SIGN | 025);
    single("17_all_three_same", 017, 2, 2, 2, 0,
           {{2, SIGN | 025}}, 2, MASK41);

    const W src1_pc = inst(014, PC, 3, 4);
    single("14_current_instruction_as_first_source", 014, PC, 3, 4, 0,
           {{3, SIGN | 05}}, 4, src1_pc | (SIGN | 05));
    const W src2_pc = inst(017, 3, PC, 4);
    single("17_current_instruction_as_second_source", 017, 3, PC, 4, 0,
           {{3, SIGN | 05}}, 4, (~(src2_pc ^ (SIGN | 05))) & MASK41);
    const W shifted_pc = inst(013, 2, PC, 4);
    single("13_current_instruction_as_shift_operand", 013, 2, PC, 4, 0,
           {{2, 1}}, 4, (shifted_pc << 1) & MASK41);

    // Write the currently executing instruction: K is already latched,
    // the result is stored at PC, but execution still advances to PC+1.
    const W replacement = inst(014, 5, 6, 7);
    single("14_overwrite_current_instruction", 014, 2, 3, PC, 0,
           {{2, replacement}, {3, 0}}, PC, replacement);
    single("17_overwrite_current_instruction", 017, 2, 3, PC, 0,
           {{2, replacement}, {3, 0}}, PC, (MASK41 ^ replacement));
    single("13_overwrite_current_instruction", 013, 2, 3, PC, 0,
           {{2, 0}, {3, replacement}}, PC, replacement);
    single("14_modified_destination_resolves_to_current_instruction", 014,
           2, 3, MOD | 077, 1, {{2, replacement}, {3, 0}}, PC, replacement);
    const W modsrc_pc = inst(014, MOD | 077, 3, 4);
    single("14_modified_source_resolves_to_current_instruction", 014,
           MOD | 077, 3, 4, 1, {{3, 020}}, 4, modsrc_pc | 020);
    const W srcdst_pc = inst(014, PC, 3, PC);
    single("14_current_instruction_source_and_destination", 014,
           PC, 3, PC, 0, {{3, 020}}, PC, srcdst_pc | 020);

    // A two-instruction CPU run: opcode 14 writes the full 41-bit word
    // that the very next fetch executes. This is not just a one-step
    // comparison against a memory postcondition.
    strict("14_construct_next_instruction_then_execute", [](Kyiv_t& m) {
        const W first = inst(014, 2, 3, PC + 1);
        const W second = inst(014, 5, 6, 7);
        fill(m, {{2, second}, {3, 0}, {5, SIGN | 05}, {6, 012}});
        m.kmem.write_memory(PC, first);
        m.C_reg = PC;
        const bool r1 = step(m);
        const bool intermediate = r1 && !m.T_reg && m.C_reg == PC + 1 &&
                                  m.K_reg == first && m.kmem.read_memory(PC + 1) == second;
        const bool r2 = step(m);
        return intermediate && r2 && !m.T_reg && m.C_reg == PC + 2 &&
               m.K_reg == second && m.kmem.read_memory(7) == (SIGN | 017) && regs(m, 0);
    });
    strict("13_shift_zero_copies_next_instruction_then_execute", [](Kyiv_t& m) {
        const W first = inst(013, 2, 3, PC + 1);
        const W second = inst(017, 5, 6, 7);
        fill(m, {{2, 0}, {3, second}, {5, SIGN | 025}, {6, SIGN | 012}});
        m.kmem.write_memory(PC, first);
        m.C_reg = PC;
        const bool r1 = step(m);
        const bool intermediate = r1 && !m.T_reg && m.C_reg == PC + 1 &&
                                  m.K_reg == first && m.kmem.read_memory(PC + 1) == second;
        const bool r2 = step(m);
        return intermediate && r2 && !m.T_reg && m.C_reg == PC + 2 &&
               m.K_reg == second && m.kmem.read_memory(7) == (MASK41 ^ 037) && regs(m, 0);
    });

    std::cout << "ISA-06 D2 STRICT=" << passed << '/' << total
              << " DOC-MISMATCH=" << (total - passed) << " POLICY=0 OBS=0\n";
    return total == passed ? 0 : 1;
}
