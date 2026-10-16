// Supplemental characterization tests for ISA-02.
// This file lives under tempkyiv/; no repository test files are overwritten.
#include <cstdint>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include "kyiv.h"
#include "asm_disasm.h"

// CPU-only standalone test: do not link src/asm_disasm.cpp, which contains main().
int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
constexpr uint64_t kSign = uint64_t{1} << 40;
constexpr uint64_t kMagnitudeMask = kSign - 1;
constexpr uint64_t kStart = 0100;

uint64_t instruction(unsigned op, uint64_t a1, uint64_t a2, uint64_t a3) {
    return (uint64_t(op) << 36) | (a1 << 24) | (a2 << 12) | a3;
}
void load(Kyiv_t& cpu, unsigned op, uint64_t a1, uint64_t a2, uint64_t a3) {
    cpu.C_reg = kStart;
    cpu.kmem.write_memory(kStart, instruction(op, a1, a2, a3));
}
bool step(Kyiv_t& cpu) {
    std::ostringstream discard;
    std::streambuf* previous = std::cout.rdbuf(discard.rdbuf());
    try {
        bool result = cpu.execute_opcode();
        std::cout.rdbuf(previous);
        return result;
    } catch (...) {
        std::cout.rdbuf(previous);
        throw;
    }
}
template<class F>
bool check(const char* name, F&& fn) {
    try {
        const bool ok = fn();
        std::cout << (ok ? "PASS " : "FAIL ") << name << '\n';
        return ok;
    } catch (const std::exception& e) {
        std::cout << "FAIL " << name << " | exception: " << e.what() << '\n';
        return false;
    }
}
} // namespace

int main() {
    unsigned failed = 0;
    failed += !check("03_sign_preserved_when_destination_aliases_source2", [] {
        Kyiv_t cpu;
        cpu.kmem.write_memory(0002, 5);
        cpu.kmem.write_memory(0003, kSign | 2);
        load(cpu, 003, 0002, 0003, 0003);
        return step(cpu) && cpu.kmem.read_memory(0003) == (kSign | 7);
    });
    failed += !check("03_negative_intermediate_destination_aliases_source1", [] {
        Kyiv_t cpu;
        cpu.kmem.write_memory(0002, kSign | 5);
        cpu.kmem.write_memory(0003, 2);
        load(cpu, 003, 0002, 0003, 0002);
        return step(cpu) && cpu.kmem.read_memory(0002) == 3;
    });
    failed += !check("03_preserves_negative_zero_sign_of_source2", [] {
        Kyiv_t cpu;
        cpu.kmem.write_memory(0002, 0);
        cpu.kmem.write_memory(0003, kSign);
        load(cpu, 003, 0002, 0003, 0004);
        return step(cpu) && cpu.kmem.read_memory(0004) == kSign;
    });
    failed += !check("03_overflow_stop_blocked_skips_one_instruction", [] {
        Kyiv_t cpu;
        cpu.B_tumb = 1;
        cpu.kmem.write_memory(0002, kMagnitudeMask);
        cpu.kmem.write_memory(0003, 1);
        load(cpu, 003, 0002, 0003, 0004);
        const bool cont = step(cpu);
        return cont && !cpu.T_reg && cpu.C_reg == 0102
            && cpu.kmem.read_memory(0004) == 0;
    });
    failed += !check("01_writing_to_0000_discards_result", [] {
        Kyiv_t cpu;
        cpu.kmem.write_memory(0002, 3);
        cpu.kmem.write_memory(0003, 4);
        load(cpu, 001, 0002, 0003, 0000);
        return step(cpu) && cpu.kmem.read_memory(0000) == 0;
    });
    std::cout << "ISA-02 supplement: " << (5 - failed) << "/5 pass\n";
    return failed == 0 ? 0 : 1;
}
