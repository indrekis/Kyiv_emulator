// ISA-07 D9-A: two actual CPU steps after IO24, not peripheral hardware.
// Compile with src/main.cpp ONLY (asm_disasm.cpp owns another main).
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
    if (argc != 2) return 2;
    const std::string mode(argv[1]);
    if (mode != "full" && mode != "short" && mode != "empty" &&
        mode != "missing" && mode != "track1" && mode != "single" &&
        mode != "altjump") return 2;
    try {
        Kyiv_t m;
        constexpr addr_t origin = 0100;
        const addr_t target = (mode == "altjump") ? 0130 : 0120;
        const addr_t a1 = (mode == "single") ? 0201 : 0200;
        const addr_t a2 = (mode == "single") ? 0201 : 0202;
        // Target is a real nonzero instruction, not a stub or a no-op.
        // (0204 XOR 0205) -> 0206 = 5 XOR 3 = 6.
        const word_t target_word = instruction(017, 0204, 0205, 0206);
        m.kmem.write_memory(origin, instruction(024, a1, a2, target));
        m.kmem.write_memory(origin + 1, instruction(033, 0, 0, 0)); // Wrong sequential path
        m.kmem.write_memory(target, target_word);
        m.kmem.write_memory(0204, 5);
        m.kmem.write_memory(0205, 3);
        for (addr_t addr = 0200; addr <= 0202; ++addr)
            m.kmem.write_memory(addr, 0);
        m.C_reg = origin;
        m.K_reg = 0;
        m.drum_num_read = (mode == "track1") ? 1 : 0;
        m.drum_zone_read = 0;
        m.drum_num_write = 2;
        m.drum_zone_write = 3;
        const int read_before = m.drum_num_read;
        const int zone_before = m.drum_zone_read;
        const int write_before = m.drum_num_write;
        const int write_zone_before = m.drum_zone_write;
        const bool running1 = m.execute_opcode(); // CPU STEP 1: IO24
        const addr_t pc1 = m.C_reg;
        const word_t k1 = m.K_reg;
        const word_t w0 = m.kmem.read_memory(0200);
        const word_t w1 = m.kmem.read_memory(0201);
        const word_t w2 = m.kmem.read_memory(0202);
        const bool running2 = m.execute_opcode(); // CPU STEP 2: target XOR
        const addr_t pc2 = m.C_reg;
        const word_t k2 = m.K_reg;
        const word_t xor_value = m.kmem.read_memory(0206);
        const bool params_unchanged =
            m.drum_num_read == read_before && m.drum_zone_read == zone_before &&
            m.drum_num_write == write_before && m.drum_zone_write == write_zone_before;
        std::cout << std::oct
                  << "D9A-OBS mode=" << mode
                  << " pc0=" << origin << " target=" << target
                  << " pc1=" << pc1 << " pc2=" << pc2
                  << std::dec
                  << " k1_match=" << (k1 == target_word)
                  << " k2_match=" << (k2 == target_word)
                  << " mem=" << w0 << '/' << w1 << '/' << w2
                  << " xor=" << xor_value
                  << " drum_unchanged=" << params_unchanged
                  << " running=" << running1 << '/' << running2
                  << " steps=2"
                  << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D9A-EXCEPTION mode=" << mode << " reason=" << e.what() << '\n';
        return 3;
    } catch (...) {
        std::cerr << "D9A-EXCEPTION mode=" << mode << " reason=unknown\n";
        return 3;
    }
}
