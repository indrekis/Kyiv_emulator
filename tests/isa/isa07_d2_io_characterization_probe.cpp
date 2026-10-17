// ISA-07 D2: one instruction in a temporary I/O sandbox, not a hardware oracle.
// Compile with src/main.cpp ONLY.  asm_disasm.cpp contains its own main().
#include "kyiv.h"
#include <cstdint>
#include <cstdlib>
#include <exception>
#include <iomanip>
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
        std::cerr << "usage: isa07_d2_io_characterization_probe.exe <20|21-h1|21-h0|22|23|24|25-read|25-write>\n";
        return 2;
    }
    const std::string mode(argv[1]);
    try {
        Kyiv_t m;
        unsigned op = 0, a1 = 0, a2 = 0, a3 = 0;
        if (mode == "20") {
            op = 020; a1 = 0200; a2 = 0202; a3 = 0;
            m.perfo_num = 0;
        } else if (mode == "21-h1" || mode == "21-h0") {
            op = 021; a1 = 0200; a2 = 0202; a3 = 0;
            m.h = mode == "21-h1" ? 1 : 0;
        } else if (mode == "22" || mode == "23") {
            op = mode == "22" ? 022 : 023;
            // I=0001 and II=0002 bound output to three machine words.
            // No writes to address zero and no real device side effects.
            a1 = 0001; a2 = 0002; a3 = 0120;
            m.kmem.write_memory(0001, 0005);
            m.kmem.write_memory(0002, 0007);
            m.kmem.write_memory(0003, 0011);
        } else if (mode == "24") {
            op = 024; a1 = 0200; a2 = 0202; a3 = 0;
            m.drum_num_read = 0;
            m.drum_zone_read = 0;
        } else if (mode == "25-read" || mode == "25-write") {
            op = 025; a1 = mode == "25-read" ? 0 : 1;
            a2 = 0003; a3 = 0007;
        } else {
            std::cerr << "unsupported mode: " << mode << '\n';
            return 2;
        }
        constexpr addr_t pc = 0100;
        m.kmem.write_memory(pc, instruction(op, a1, a2, a3));
        m.C_reg = pc;
        const bool running = m.execute_opcode(); // Exactly ONE CPU step.
        // Discarding this one-step machine immediately avoids repeated-PC loops.
        std::cout << std::oct
                  << "IO-OBS mode=" << mode << " op=" << op
                  << " start_pc=" << pc << " next_pc=" << m.C_reg
                  << " mem0200=" << m.kmem.read_memory(0200)
                  << " mem0201=" << m.kmem.read_memory(0201)
                  << " h=" << m.h
                  << " drum_read=" << m.drum_num_read
                  << " zone_read=" << m.drum_zone_read
                  << " drum_write=" << m.drum_num_write
                  << " zone_write=" << m.drum_zone_write
                  << std::dec << " running=" << (running ? 1 : 0) << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "IO-OBS-EXCEPTION mode=" << mode << " reason=" << e.what() << '\n';
        return 3;
    } catch (...) {
        std::cerr << "IO-OBS-EXCEPTION mode=" << mode << " reason=unknown\n";
        return 3;
    }
}
