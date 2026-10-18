// ISA-07 D8-B: one CPU output opcode with a deterministic memory fixture.
// Build with src/main.cpp ONLY (src/asm_disasm.cpp defines another main).
// This probes digital address interval and host files; NOT a physical device.
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
    unsigned op = 0;
    if (mode.rfind("22-", 0) == 0) op = 022;
    else if (mode.rfind("23-", 0) == 0) op = 023;
    else return 2;
    const std::string kind = mode.substr(3);
    unsigned a1 = 0, a2 = 0;
    if (kind == "range") { a1 = 0200; a2 = 0202; }
    else if (kind == "single") { a1 = 0201; a2 = 0201; }
    else if (kind == "offset") { a1 = 0201; a2 = 0203; }
    else if (kind == "legacy") { a1 = 0001; a2 = 0002; }
    else if (kind == "fromzero") { a1 = 0000; a2 = 0002; }
    else return 2;
    try {
        Kyiv_t machine;
        constexpr addr_t pc = 0100;
        constexpr addr_t next = 0120;
        // Memory cell 0000 is hardwired to zero in Kyiv_memory_t.
        // It cannot be seeded with a nonzero fixture value.
        machine.kmem.write_memory(0001, 5);
        machine.kmem.write_memory(0002, 7);
        machine.kmem.write_memory(0200, 5);
        machine.kmem.write_memory(0201, 7);
        machine.kmem.write_memory(0202, 9);
        machine.kmem.write_memory(0203, 11);
        machine.kmem.write_memory(0204, 13); // Adjacent sentinel: must NOT be sent.
        machine.kmem.write_memory(pc, instruction(op, a1, a2, next));
        machine.C_reg = pc;
        const bool running = machine.execute_opcode(); // ONE_STEP_ONLY
        std::cout << std::oct
                  << "D8B-OBS mode=" << mode << " op=" << op
                  << " start_pc=" << pc << " next_pc=" << machine.C_reg
                  << std::dec
                  << " running=" << (running ? 1 : 0) << '\n';
        return 0;
    } catch (const std::exception& err) {
        std::cerr << "D8B-EXCEPTION mode=" << mode << " reason=" << err.what() << '\n';
        return 3;
    } catch (...) {
        std::cerr << "D8B-EXCEPTION mode=" << mode << " reason=unknown\n";
        return 3;
    }
}
