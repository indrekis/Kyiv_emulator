// ISA-07 D13-A: current-code IO23 host observations on the genuine Kyiv_t.
// Link ONLY src/main.cpp (src/asm_disasm.cpp has its own main).
// This is NOT a physical magnetic-drum oracle.
#include "kyiv.h"
#include <cstdint>
#include <exception>
#include <iostream>
#include <string>
#include <vector>

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
    const std::string allowed =
        "|range|single|offset|legacy|fromzero|overwrite|open-error|"
        "negative|negative-zero|max-positive|max-negative|sign-only|"
        "reversed|beyond-physical|rom-source|drum-params|modified-addresses|"
        "alternate-branch|io25-setup|highbits-masked|";
    if (allowed.find("|" + mode + "|") == std::string::npos) return 2;
    try {
        Kyiv_t m;
        constexpr word_t sign = 1ULL << 40;
        constexpr word_t magnitude_mask = sign - 1;
        constexpr addr_t pc = 0100;
        const addr_t target = (mode == "alternate-branch") ? 0130 : 0120;
        addr_t a1 = 0200, a2 = 0202;
        if (mode == "single") a1 = a2 = 0201;
        if (mode == "offset") { a1 = 0201; a2 = 0203; }
        if (mode == "legacy") { a1 = 0001; a2 = 0002; }
        if (mode == "fromzero") { a1 = 0000; a2 = 0002; }
        if (mode == "reversed") { a1 = 0202; a2 = 0200; }
        if (mode == "beyond-physical") a1 = a2 = 02000;
        if (mode == "rom-source") a1 = a2 = 03010;
        if (mode == "sign-only") a1 = a2 = 0200;
        if (mode == "max-positive" || mode == "max-negative" ||
            mode == "highbits-masked") a1 = a2 = 0200;
        if (mode == "modified-addresses") { a1 = 0177; a2 = 0201; m.A_reg = 1; }

        word_t write_word = instr(023, static_cast<unsigned>(a1),
                                 static_cast<unsigned>(a2),
                                 static_cast<unsigned>(target));
        if (mode == "modified-addresses")
            write_word |= (1ULL << 35) | (1ULL << 23); // A1 and A2 selectors
        const word_t target_word = instr(017, 0700, 0701, 0702);
        if (mode == "io25-setup") {
            m.kmem.write_memory(pc, instr(025, 1, 6, 9));
            m.kmem.write_memory(pc + 1, write_word);
        } else {
            m.kmem.write_memory(pc, write_word);
            m.kmem.write_memory(pc + 1, instr(033, 0, 0, 0)); // wrong path witness
        }
        m.kmem.write_memory(target, target_word);
        m.kmem.write_memory(0700, 5);
        m.kmem.write_memory(0701, 3);
        m.kmem.write_memory(0702, 0);
        m.kmem.write_memory(0001, 5);
        m.kmem.write_memory(0002, 7);
        m.kmem.write_memory(0200, 5);
        m.kmem.write_memory(0201, 7);
        m.kmem.write_memory(0202, 9);
        m.kmem.write_memory(0203, 11);
        m.kmem.write_memory(02000, 13);  // Current HOST memory class, not physical Kyiv RAM
        m.kmem.write_rom(03010, 17);
        if (mode == "negative") m.kmem.write_memory(0200, sign | 5);
        if (mode == "negative-zero" || mode == "sign-only")
            m.kmem.write_memory(0200, sign);
        if (mode == "max-positive") m.kmem.write_memory(0200, magnitude_mask);
        if (mode == "max-negative") m.kmem.write_memory(0200, sign | magnitude_mask);
        if (mode == "highbits-masked") m.kmem.write_memory(0200, (1ULL << 45) | 5);

        m.C_reg = pc;
        m.K_reg = 0;
        m.h = 3;
        m.drum_num_read = 10;
        m.drum_zone_read = 11;
        m.drum_num_write = mode == "drum-params" ? 8 : 4;
        m.drum_zone_write = mode == "drum-params" ? 9 : 6;
        const auto initial_A = m.A_reg;
        const auto initial_P = m.P_reg;
        const auto initial_L = m.Loop_reg;
        const auto initial_T = m.T_reg;
        const auto initial_h = m.h;
        const auto initial_read = m.drum_num_read;
        const auto initial_read_zone = m.drum_zone_read;
        const int expected_write = mode == "io25-setup" ? 6 : m.drum_num_write;
        const int expected_write_zone = mode == "io25-setup" ? 9 : m.drum_zone_write;
        std::vector<word_t> memory_before;
        memory_before.reserve(04000);
        for (addr_t a = 0; a < 04000; ++a)
            memory_before.push_back(m.kmem.read_memory(a));

        bool setup_ok = true;
        bool run_setup = true;
        if (mode == "io25-setup") {
            run_setup = m.execute_opcode(); // real step 1: IO25
            setup_ok = run_setup && m.C_reg == pc + 1 && m.K_reg == write_word &&
                m.drum_num_write == 6 && m.drum_zone_write == 9;
        }
        const bool run1 = m.execute_opcode(); // IO23, first or second genuine step
        const addr_t pc1 = m.C_reg;
        const word_t k1 = m.K_reg;
        bool memory_unchanged = true;
        for (addr_t a = 0; a < 04000; ++a) {
            if (m.kmem.read_memory(a) != memory_before[static_cast<std::size_t>(a)]) {
                memory_unchanged = false;
                break;
            }
        }
        const bool stable = m.A_reg == initial_A && m.P_reg == initial_P &&
            m.Loop_reg == initial_L && m.T_reg == initial_T && m.h == initial_h &&
            m.drum_num_read == initial_read &&
            m.drum_zone_read == initial_read_zone &&
            m.drum_num_write == expected_write &&
            m.drum_zone_write == expected_write_zone;
        const bool run2 = m.execute_opcode(); // genuine target XOR
        std::cout << std::oct
                  << "D13A-OBS mode=" << mode
                  << " pc1=" << pc1 << " pc2=" << m.C_reg
                  << std::dec
                  << " k1=" << (k1 == target_word)
                  << " k2=" << (m.K_reg == target_word)
                  << " setup=" << setup_ok
                  << " memory=" << memory_unchanged
                  << " stable=" << stable
                  << " xor=" << m.kmem.read_memory(0702)
                  << " running=" << (run_setup && run1 && run2)
                  << " steps=" << (mode == "io25-setup" ? 3 : 2)
                  << " HOST_OBSERVATION=1 HARDWARE_ORACLE=0\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D13A-PROBE-ERROR mode=" << mode << " reason=" << e.what() << '\n';
        return 3;
    } catch (...) {
        std::cerr << "D13A-PROBE-ERROR mode=" << mode << " reason=unknown\n";
        return 3;
    }
}
