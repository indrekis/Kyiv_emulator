// ISA-01 characterization probe for https://github.com/indrekis/Kyiv_emulator
// Source baseline: main @ 0e2a06f544712c48b53323492fcfdc578de90473.
// Deliberately not an assert-based CI test yet: failures are expected in the baseline.
// Build from the repo root:
// g++ -std=c++17 -O0 -g -Iinc src/main.cpp tests/isa/first_pass_probe.cpp -o isa_first_pass_probe
// ./isa_first_pass_probe                   # report only, exit 0
// ./isa_first_pass_probe --strict          # nonzero exit if any mismatch

#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "kyiv.h"
#include "asm_disasm.h"

// In the baseline, the real disassembler is in asm_disasm.cpp along with main().
// This harmless stub lets this CPU-only probe link without the CLI's main().
int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
constexpr uint64_t kSign = uint64_t{1} << 40;
constexpr uint64_t kMantissa = kSign - 1;
constexpr uint64_t kMod = 04000;  // 12th bit in each of the 12-bit address fields.
constexpr uint64_t kStart = 0100;

uint64_t command(unsigned opcode, uint64_t a1, uint64_t a2, uint64_t a3) {
    if (opcode > 037 || a1 > 07777 || a2 > 07777 || a3 > 07777)
        throw std::invalid_argument("instruction field exceeds defined width");
    return (uint64_t(opcode) << 36) | (a1 << 24) | (a2 << 12) | a3;
}

struct MuteOutput {
    std::ostringstream output;
    std::streambuf *prior;
    MuteOutput() : prior(std::cout.rdbuf(output.rdbuf())) {}
    ~MuteOutput() { std::cout.rdbuf(prior); }
    MuteOutput(const MuteOutput&) = delete;
    MuteOutput& operator=(const MuteOutput&) = delete;
};

struct Outcome { std::string name, observed, expected; bool ok; };
std::vector<Outcome> results;
void check(const std::string& name, bool ok,
           const std::string& observed, const std::string& expected) {
    results.push_back({name, observed, expected, ok});
}
std::string oct(uint64_t x) {
    std::ostringstream o; o << std::oct << x; return o.str();
}
void set_command(Kyiv_t& cpu, unsigned op, uint64_t a1, uint64_t a2, uint64_t a3) {
    cpu.C_reg = kStart;
    cpu.kmem.write_memory(kStart, command(op, a1, a2, a3));
}
// Execute one instruction without logging; permit exception propagation to the case.
bool step(Kyiv_t& cpu) {
    MuteOutput m;
    return cpu.execute_opcode();
}

template<class F>
void test(const std::string& name, const std::string& expected, F&& body) {
    try {
        const auto [ok, actual] = body();
        check(name, ok, actual, expected);
    } catch (const std::exception& e) {
        check(name, false, std::string("exception: ") + e.what(), expected);
    } catch (...) {
        check(name, false, "unknown exception", expected);
    }
}
} // namespace

int main(int argc, char** argv) {
    const bool strict = argc > 1 && std::string(argv[1]) == "--strict";

    test("00_NOP_does_not_stop", "C=0101, T=0, continue=1", [] {
        Kyiv_t cpu;
        set_command(cpu, 000, 0000, 0000, 0000);
        bool go = step(cpu);
        bool ok = cpu.C_reg == 0101 && !cpu.T_reg && go;
        return std::pair{ok, "C=" + oct(cpu.C_reg) + ", T=" +
            std::to_string(cpu.T_reg) + ", continue=" + std::to_string(go)};
    });

    test("01_ADD_baseline", "dest=7, C=0101, continue=1", [] {
        Kyiv_t cpu;
        cpu.kmem.write_memory(0002, 3);
        cpu.kmem.write_memory(0003, 4);
        set_command(cpu, 001, 0002, 0003, 0004);
        bool go = step(cpu);
        uint64_t x=cpu.kmem.read_memory(0004);
        return std::pair{x == 7 && cpu.C_reg == 0101 && go,
            "dest=" + oct(x) + ", C=" + oct(cpu.C_reg) +
            ", continue=" + std::to_string(go)};
    });

    test("01_ADD_overflow", "T=1, continue=0, dest=77", [] {
        Kyiv_t cpu;
        cpu.kmem.write_memory(0002, kMantissa);
        cpu.kmem.write_memory(0003, 1);
        cpu.kmem.write_memory(0004, 077);
        set_command(cpu, 001, 0002, 0003, 0004);
        bool go = step(cpu);
        uint64_t x=cpu.kmem.read_memory(0004);
        return std::pair{cpu.T_reg && !go && x == 077,
            "T=" + std::to_string(cpu.T_reg) + ", continue=" +
            std::to_string(go) + ", dest=" + oct(x)};
    });

    test("02_SUB_equal_nonzero_yields_minus_zero", "dest=20000000000000 (octal)", [] {
        Kyiv_t cpu;
        cpu.kmem.write_memory(0002, 5);
        cpu.kmem.write_memory(0003, 5);
        set_command(cpu, 002, 0002, 0003, 0004);
        step(cpu);
        uint64_t x=cpu.kmem.read_memory(0004);
        return std::pair{x == kSign, "dest=" + oct(x)};
    });

    test("03_ADDCMD_positive_intermediate", "dest=negative 7", [] {
        Kyiv_t cpu;
        cpu.kmem.write_memory(0002, 5);
        cpu.kmem.write_memory(0003, kSign | 2);
        set_command(cpu, 003, 0002, 0003, 0004);
        step(cpu);
        uint64_t x=cpu.kmem.read_memory(0004);
        return std::pair{x == (kSign | 7), "dest=" + oct(x)};
    });

    test("03_ADDCMD_negative_intermediate", "dest=positive 3", [] {
        Kyiv_t cpu;
        cpu.kmem.write_memory(0002, kSign | 5);
        cpu.kmem.write_memory(0003, 2);
        set_command(cpu, 003, 0002, 0003, 0004);
        step(cpu);
        uint64_t x=cpu.kmem.read_memory(0004);
        return std::pair{x == 3, "dest=" + oct(x)};
    });

    test("03_ADDCMD_overflow_stop", "T=1, continue=0", [] {
        Kyiv_t cpu;
        cpu.kmem.write_memory(0002, kMantissa);
        cpu.kmem.write_memory(0003, 1);
        set_command(cpu, 003, 0002, 0003, 0004);
        bool go=step(cpu);
        return std::pair{cpu.T_reg && !go, "T="+std::to_string(cpu.T_reg)+
          ", continue="+std::to_string(go)};
    });

    test("06_SUBABS_sign", "dest=negative 2", [] {
        Kyiv_t cpu;
        cpu.kmem.write_memory(0002, kSign | 7);
        cpu.kmem.write_memory(0003, 9);
        set_command(cpu, 006, 0002, 0003, 0004);
        step(cpu);
        uint64_t x=cpu.kmem.read_memory(0004);
        return std::pair{x == (kSign | 2), "dest=" + oct(x)};
    });

    test("ADDR_modified_wrap_11_bits", "effective a1=0212, dest=12", [] {
        Kyiv_t cpu;
        cpu.A_reg = 01323;
        cpu.kmem.write_memory(0212, 9);
        cpu.kmem.write_memory(0002, 3);
        set_command(cpu, 001, kMod | 02667, 0002, 0004);
        step(cpu);
        uint64_t x=cpu.kmem.read_memory(0004);
        return std::pair{x == 12, "dest=" + oct(x)};
    });

    test("RAM_address_0000_immutable", "mem[0000]=0", [] {
        Kyiv_t cpu;
        try { cpu.kmem.write_memory(0000, 23); }
        catch (...) { /* A strict memory bus may reject writes; invariant still holds. */ }
        uint64_t x=cpu.kmem.read_memory(0000);
        return std::pair{x == 0, "mem[0000]=" + oct(x)};
    });

    test("14_logical_OR", "dest=017", [] {
        Kyiv_t cpu;
        cpu.kmem.write_memory(0002, 012);
        cpu.kmem.write_memory(0003, 005);
        set_command(cpu, 014, 0002, 0003, 0004);
        step(cpu);
        uint64_t x=cpu.kmem.read_memory(0004);
        return std::pair{x == 017, "dest=" + oct(x)};
    });

    test("15_logical_AND", "dest=000", [] {
        Kyiv_t cpu;
        cpu.kmem.write_memory(0002, 012);
        cpu.kmem.write_memory(0003, 005);
        set_command(cpu, 015, 0002, 0003, 0004);
        step(cpu);
        uint64_t x=cpu.kmem.read_memory(0004);
        return std::pair{x == 0, "dest=" + oct(x)};
    });

    unsigned failures=0;
    for (const auto& r: results) {
        std::cout << (r.ok ? "PASS " : "FAIL ") << r.name
                  << " | observed: " << r.observed
                  << " | expected: " << r.expected << '\n';
        failures += !r.ok;
    }
    std::cout << "SUMMARY " << (results.size()-failures) << "/"
              << results.size() << " pass; " << failures << " mismatch(es)\n";
    return strict && failures ? EXIT_FAILURE : EXIT_SUCCESS;
}
