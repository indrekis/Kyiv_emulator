// ISA-07 D14-C1e: genuine Kyiv_t observations of a seven-step excerpt
// from the published magnetic-drum test. No opcode 23/24/25 is executed.
// Build with src/main.cpp, NOT a mock CPU. HARDWARE_ORACLE=0.
#include "kyiv.h"
#include <cstdint>
#include <exception>
#include <iostream>
#include <sstream>
#include <string>

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
constexpr word_t ins(unsigned op, unsigned a, unsigned b, unsigned c) {
    return (word_t(op) << 36) | (word_t(a) << 24) |
           (word_t(b) << 12) | word_t(c);
}

void step(Kyiv_t& m, const std::string& label, const char* phase,
          unsigned pc) {
    m.C_reg = pc;  // Deliberate isolated step, NOT an uninterrupted run.
    bool returned = false;
    std::string error = "NONE";
    try {
        returned = m.execute_opcode();
    } catch (const std::exception& e) {
        error = e.what();
    } catch (...) {
        error = "UNKNOWN";
    }
    std::cout << "D14C1E-STEP"
              << " id=" << label
              << " phase=" << phase
              << " ret=" << (returned ? 1 : 0)
              << " pc=" << pc
              << " C=" << m.C_reg
              << " K=" << m.K_reg
              << " v60=" << m.kmem.read_memory(0060)
              << " w24=" << m.kmem.read_memory(0024)
              << " w26=" << m.kmem.read_memory(0026)
              << " A=" << m.A_reg
              << " T=" << (m.T_reg ? 1 : 0)
              << " error=" << (error == "NONE" ? "NONE" : "EXCEPTION")
              << '\n';
}
}  // namespace

int main() {
    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream input(line);
        std::string id, mode, extra;
        unsigned n = 0, drum = 0, start = 0, modifier = 0;
        if (!(input >> id >> n >> drum >> start >> mode >> modifier) ||
            (input >> extra) || id.empty() || n > 500 ||
            drum < 1 || drum > 2 || start > 03777 ||
            (mode != "cabinet" && mode != "panel") || modifier > 03777) {
            std::cerr << "D14C1E-BAD_PROTOCOL\n";
            return 2;
        }
        try {
            Kyiv_t m;
            m.A_reg = modifier;
            m.kmem.write_memory(0052, ins(025, 1, 0, 0));
            m.kmem.write_memory(0054, ins(025, 0, 0, 0));
            // Original GY62 octal commands, deliberately replayed as
            // seven independent CPU steps in causal order.
            m.kmem.write_memory(0003, ins(001, 0052, 0000, 0024));
            m.kmem.write_memory(0005, ins(001, 0054, 0000, 0026));
            m.kmem.write_memory(0011, ins(010, 03000, 03040, 0060));
            m.kmem.write_memory(0016, ins(003, 03002, 0024, 0024));
            m.kmem.write_memory(0017, ins(003, 03002, 0026, 0026));
            m.kmem.write_memory(0035, ins(003, 0060, 0024, 0024));
            m.kmem.write_memory(0036, ins(003, 0060, 0026, 0026));
            m.kmem.write_memory(0060, 0777); // detect missing multiplication
            // 3040 is the documented +2^-12 fixed-point constant.
            m.kmem.write_rom(03040, word_t{1} << 28);
            const word_t raw_n = word_t(n) << 24;
            const word_t raw_selection = (word_t(drum) << 18) | start;
            if (mode == "cabinet") {
                m.kmem.write_rom(03000, raw_n);
                m.kmem.write_rom(03002, raw_selection);
            } else {
                // An independently exercised, explicit NK source selector.
                m.kmem.write_rom(03000, 0); // cabinet decoys
                m.kmem.write_rom(03002, 0);
                m.kmem.set_panel_nk_word(03000, raw_n);
                m.kmem.set_panel_nk_word(03002, raw_selection);
                m.kmem.select_panel_nk(03000, true);
                m.kmem.select_panel_nk(03002, true);
            }
            std::cout << "D14C1E-BEGIN id=" << id
                      << " nk0=" << m.kmem.read_memory(03000)
                      << " nk2=" << m.kmem.read_memory(03002)
                      << " rom3040=" << m.kmem.read_memory(03040)
                      << '\n';
            step(m, id, "copy-write", 0003);
            step(m, id, "copy-read", 0005);
            step(m, id, "multiply", 0011);
            step(m, id, "select-write", 0016);
            step(m, id, "select-read", 0017);
            step(m, id, "advance-write", 0035);
            step(m, id, "advance-read", 0036);
        } catch (const std::exception& e) {
            std::cerr << "D14C1E-FATAL id=" << id << " error=" << e.what() << '\n';
            return 3;
        } catch (...) {
            std::cerr << "D14C1E-FATAL id=" << id << " error=UNKNOWN\n";
            return 3;
        }
    }
    return 0;
}
