// ISA-07 D9-B: TWO genuine CPU steps, IO25 then IO23 or IO24.
// Compile with src/main.cpp only; asm_disasm.cpp defines its own main().
// Host files are process-isolated by Python; not physical device oracles.
#include "kyiv.h"
#include <cstdint>
#include <exception>
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
    const bool writing = mode.rfind("write-", 0) == 0;
    const bool reading = mode.rfind("read-", 0) == 0;
    if (mode != "write-basic" && mode != "write-single" &&
        mode != "write-offset" && mode != "write-alt" &&
        mode != "read-basic" && mode != "read-single" &&
        mode != "read-trackzone" && mode != "read-missing") return 2;
    if (!writing && !reading) return 2;
    try {
        Kyiv_t m;
        constexpr addr_t pc = 0100;
        const addr_t target = (mode == "write-alt") ? 0130 : 0120;
        const unsigned a1 = (mode == "write-single" || mode == "read-single" ||
                             mode == "write-offset") ? 0201 : 0200;
        const unsigned a2 = (mode == "write-single" || mode == "read-single") ? 0201 :
                            (mode == "write-offset") ? 0203 : 0202;
        // IO25 I=1 selects write registers; I=0 selects read registers.
        const unsigned setup_i = writing ? 1 : 0;
        const unsigned track = (mode == "read-trackzone") ? 1 :
                               (mode == "write-alt") ? 3 :
                               writing ? 2 : 0;
        const unsigned zone = (mode == "read-trackzone") ? 2 :
                              (mode == "write-alt") ? 5 :
                              writing ? 4 : 0;
        const word_t next_command = instr(writing ? 023 : 024, a1, a2, target);
        const word_t target_command = instr(033, 0, 0, 0);
        m.kmem.write_memory(pc, instr(025, setup_i, track, zone));
        m.kmem.write_memory(pc+1, next_command); // ACTUAL SECOND INSTRUCTION
        m.kmem.write_memory(target, target_command);
        for (addr_t a = 0200; a <= 0203; ++a)
            m.kmem.write_memory(a, writing ? (5 + (a-0200)*2) : 0);
        m.C_reg = pc;
        m.K_reg = 0;
        m.drum_num_read = 6;
        m.drum_zone_read = 7;
        m.drum_num_write = 8;
        m.drum_zone_write = 9;
        const bool running1 = m.execute_opcode(); // CPU STEP 1: IO25
        const addr_t pc1 = m.C_reg;
        const word_t k1 = m.K_reg;
        const int r1 = m.drum_num_read, z1 = m.drum_zone_read;
        const int w1 = m.drum_num_write, wz1 = m.drum_zone_write;
        const bool memory_unchanged1 =
            (m.kmem.read_memory(0200) == (writing ? 5U : 0U)) &&
            (m.kmem.read_memory(0201) == (writing ? 7U : 0U)) &&
            (m.kmem.read_memory(0202) == (writing ? 9U : 0U)) &&
            (m.kmem.read_memory(0203) == (writing ? 11U : 0U));
        const bool running2 = m.execute_opcode(); // CPU STEP 2: IO23/24
        const addr_t pc2 = m.C_reg;
        const word_t k2 = m.K_reg;
        std::cout << std::oct
                  << "D9B-OBS mode=" << mode
                  << " pc0=" << pc << " pc1=" << pc1 << " pc2=" << pc2
                  << std::dec
                  << " k1_match=" << (k1 == next_command)
                  << " k2_match=" << (k2 == target_command)
                  << " params=" << r1 << '/' << z1 << '/' << w1 << '/' << wz1
                  << " params_post=" << m.drum_num_read << '/' << m.drum_zone_read
                  << '/' << m.drum_num_write << '/' << m.drum_zone_write
                  << " memory_pre=" << memory_unchanged1
                  << " memory=" << m.kmem.read_memory(0200) << '/'
                  << m.kmem.read_memory(0201) << '/'
                  << m.kmem.read_memory(0202) << '/'
                  << m.kmem.read_memory(0203)
                  << " running=" << running1 << '/' << running2
                  << " steps=2" << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D9B-EXCEPTION mode=" << mode << " reason=" << e.what() << '\n';
        return 3;
    } catch (...) {
        std::cerr << "D9B-EXCEPTION mode=" << mode << " reason=unknown\n";
        return 3;
    }
}
