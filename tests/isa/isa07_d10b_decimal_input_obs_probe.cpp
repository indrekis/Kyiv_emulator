// ISA-07 D10-B: one CPU step OBSERVATION of the current ASCII host adapter.
// NOT a historical card/tape oracle and NOT a CPU correctness test for numeric input.
// Build with src/main.cpp ONLY (src/asm_disasm.cpp defines its own main()).
#include "kyiv.h"
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <string>

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
constexpr word_t instr(unsigned op, unsigned a1, unsigned a2, unsigned a3) {
    return (word_t(op) << 36) | (word_t(a1) << 24) |
           (word_t(a2) << 12) | word_t(a3);
}
}

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const std::string mode(argv[1]);
    if (mode != "20-text10" && mode != "20-bcd625" &&
        mode != "20-dot625" && mode != "20-negzero" &&
        mode != "20-neg10" && mode != "20-text7" &&
        mode != "21-raw11") return 2;
    try {
        Kyiv_t m;
        constexpr addr_t pc = 0100;
        const bool is21 = mode == "21-raw11";
        const word_t next = instr(033, 0, 0, 0);
        m.kmem.write_memory(pc, instr(is21 ? 021 : 020, 0200, 0200, 0));
        m.kmem.write_memory(pc + 1, next);
        m.kmem.write_memory(0200, 0);
        m.C_reg = pc;
        m.perfo_num = 0;
        m.h = 0;
        const bool running = m.execute_opcode();  // ONE_STEP_ONLY; no second step.
        const word_t raw = m.kmem.read_memory(0200);
        std::cout << "D10B-HOST-OBS mode=" << mode << " raw=" << std::dec << raw
                  << " oct41=" << std::oct << std::setw(14) << std::setfill('0') << raw
                  << " pc=" << m.C_reg << std::dec
                  << " k_prefetch=" << (m.K_reg == next)
                  << " h=" << m.h
                  << " running=" << (running ? 1 : 0)
                  << " one_step=1\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "D10B-HOST-EXCEPTION mode=" << mode
                  << " reason=" << error.what() << '\n';
        return 3;
    } catch (...) {
        std::cerr << "D10B-HOST-EXCEPTION mode=" << mode << " unknown\n";
        return 3;
    }
}
