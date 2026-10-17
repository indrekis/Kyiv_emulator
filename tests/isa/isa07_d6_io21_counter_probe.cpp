// ISA-07 D6: one/two bounded opcode-21 steps using disposable host tape.
// Code-model regression only, NOT a hardware tape reader oracle.
// Link src/main.cpp; do not link src/asm_disasm.cpp (it has a CLI main).
#include "kyiv.h"
#include <cstdint>
#include <exception>
#include <iostream>
#include <string>

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
constexpr word_t instruction(unsigned op, unsigned a1, unsigned a2, unsigned a3) {
    return (word_t(op) << 36) | (word_t(a1) << 24) |
           (word_t(a2) << 12) | word_t(a3);
}
}

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: isa07_d6_io21_counter_probe <h0|h1|h2|h4|seq>\n";
        return 2;
    }
    const std::string mode = argv[1];
    size_t start = 0;
    unsigned steps = 1;
    if      (mode == "h0") start = 0;
    else if (mode == "h1") start = 1;
    else if (mode == "h2") start = 2;
    else if (mode == "h4") start = 4;
    else if (mode == "seq") { start = 0; steps = 2; }
    else return 2;

    try {
        Kyiv_t machine;
        constexpr addr_t pc = 0100;
        machine.kmem.write_memory(pc, instruction(021, 0200, 0202, 0000));
        machine.C_reg = pc;
        machine.h = start;
        for (unsigned iteration = 0; iteration < steps; ++iteration) {
            const size_t previous_h = machine.h;
            const bool running = machine.execute_opcode();
            std::cout << std::oct
                      << "IO21-OBS mode=" << mode
                      << " iter=" << std::dec << iteration << std::oct
                      << " h_before=" << previous_h
                      << " h_after=" << machine.h
                      << " mem0200=" << machine.kmem.read_memory(0200)
                      << " mem0201=" << machine.kmem.read_memory(0201)
                      << " C=" << machine.C_reg
                      << std::dec << " running=" << (running ? 1 : 0)
                      << '\n';
            if (!running) return 4;
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "IO21-EXCEPTION mode=" << mode << " reason=" << error.what() << '\n';
        return 3;
    } catch (...) {
        std::cerr << "IO21-EXCEPTION mode=" << mode << " reason=unknown\n";
        return 3;
    }
}
