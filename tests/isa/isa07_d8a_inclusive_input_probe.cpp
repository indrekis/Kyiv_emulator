// ISA-07 D8-A: GY62 inclusive a1..a2 memory interval for IO20, IO21, IO24.
// Exactly one CPU opcode execution; not a physical peripheral oracle.
// Build with src/main.cpp ONLY: src/asm_disasm.cpp has its own main().
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
    if (mode.rfind("20-", 0) == 0) op = 020;
    else if (mode.rfind("21-", 0) == 0) op = 021;
    else if (mode.rfind("24-", 0) == 0) op = 024;
    else return 2;
    if (mode != "20-range" && mode != "20-single" && mode != "20-offset" &&
        mode != "20-short" && mode != "21-range" && mode != "21-single" &&
        mode != "21-offset" && mode != "21-h1" && mode != "24-range" &&
        mode != "24-single" && mode != "24-offset" && mode != "24-short") return 2;
    const unsigned a1 = (mode.find("-single") != std::string::npos ||
                         mode.find("-offset") != std::string::npos) ? 0201 : 0200;
    const unsigned a2 = (mode.find("-single") != std::string::npos) ? 0201 :
                        (mode.find("-offset") != std::string::npos) ? 0203 : 0202;
    try {
        Kyiv_t machine;
        constexpr addr_t pc = 0100;
        machine.kmem.write_memory(pc, instruction(op,a1,a2,0));
        for (addr_t addr = 0200; addr <= 0203; ++addr)
            machine.kmem.write_memory(addr,0);
        machine.C_reg = pc;
        machine.perfo_num = 0;
        machine.drum_num_read = 0;
        machine.drum_zone_read = 0;
        machine.h = (mode == "21-h1") ? 1 : 0;
        const bool running = machine.execute_opcode(); // ONE_STEP_ONLY
        std::cout << std::oct
                  << "D8A-OBS mode=" << mode << " op=" << op
                  << " start_pc=" << pc << " next_pc=" << machine.C_reg
                  << std::dec
                  << " mem0=" << machine.kmem.read_memory(0200)
                  << " mem1=" << machine.kmem.read_memory(0201)
                  << " mem2=" << machine.kmem.read_memory(0202)
                  << " mem3=" << machine.kmem.read_memory(0203)
                  << " h=" << machine.h
                  << " running=" << (running ? 1 : 0) << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D8A-EXCEPTION mode=" << mode << " reason=" << e.what() << '\n';
        return 3;
    } catch (...) {
        std::cerr << "D8A-EXCEPTION mode=" << mode << " reason=unknown\n";
        return 3;
    }
}
