// ISA-07 D7: one CPU opcode, source-vs-emulator observations only.
// Build with src/main.cpp, NOT src/asm_disasm.cpp (own main).
// All documents about historical behaviour belong to the D7 evidence ledger.
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
        std::cerr << "usage: isa07_d7_io_documented_boundaries_probe "
                     "<20-range|20-decimal|21-range|22-range|23-range|24-range|25-next>\n";
        return 2;
    }
    const std::string mode(argv[1]);
    unsigned op = 0, a1 = 0200, a2 = 0202, a3 = 0;
    if      (mode == "20-range") op = 020;
    else if (mode == "20-decimal") { op = 020; a2 = 0201; }
    else if (mode == "21-range") op = 021;
    else if (mode == "22-range") { op = 022; a3 = 0120; }
    else if (mode == "23-range") { op = 023; a3 = 0120; }
    else if (mode == "24-range") { op = 024; a3 = 0120; }
    else if (mode == "25-next") { op = 025; a1 = 0; a2 = 0003; a3 = 0007; }
    else return 2;

    try {
        Kyiv_t m;
        constexpr addr_t pc = 0100;
        m.kmem.write_memory(pc, instruction(op, a1, a2, a3));
        m.kmem.write_memory(0200, 0);
        m.kmem.write_memory(0201, 0);
        m.kmem.write_memory(0202, 0);
        m.C_reg = pc;
        m.h = 0;
        m.perfo_num = 0;
        m.drum_num_read = 0;
        m.drum_zone_read = 0;
        // For output, distinct consecutive machine words help inspect contents;
        // we still count output fields in the isolated runner rather than decode
        // the formatter's host-dependent real-number representation.
        if (mode == "22-range" || mode == "23-range") {
            m.kmem.write_memory(0200, 1);
            m.kmem.write_memory(0201, 2);
            m.kmem.write_memory(0202, 3);
        }
        const bool running = m.execute_opcode();  // EXACTLY ONE CPU STEP
        std::cout << std::oct
                  << "D7-OBS mode=" << mode << " op=" << op
                  << " start_pc=" << pc << " next_pc=" << m.C_reg
                  << std::dec
                  << " mem0=" << m.kmem.read_memory(0200)
                  << " mem1=" << m.kmem.read_memory(0201)
                  << " mem2=" << m.kmem.read_memory(0202)
                  << " h=" << m.h
                  << " running=" << (running ? 1 : 0) << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D7-EXCEPTION mode=" << mode << " reason=" << e.what() << '\n';
        return 3;
    } catch (...) {
        std::cerr << "D7-EXCEPTION mode=" << mode << " reason=unknown\n";
        return 3;
    }
}
