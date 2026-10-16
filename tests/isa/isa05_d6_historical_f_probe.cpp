#include <cstdint>
#include <iostream>
#include <sstream>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&,
                const addr3_t&) { return 0; }

static uint64_t cmd(unsigned op, uint64_t a1 = 0,
                    uint64_t a2 = 0, uint64_t a3 = 0) {
    return (uint64_t(op) << 36)
         | ((a1 & 07777) << 24)
         | ((a2 & 07777) << 12)
         | (a3 & 07777);
}

static bool step(Kyiv_t& m) {
    std::ostringstream sink;
    auto* old = std::cout.rdbuf(sink.rdbuf());
    try {
        bool result = m.execute_opcode();
        std::cout.rdbuf(old);
        return result;
    } catch (...) {
        std::cout.rdbuf(old);
        throw;
    }
}

static void prepare(Kyiv_t& m) {
    // GY1962, Appendix 2, printed pp. 165-166.
    m.kmem.write_memory(0207, 1);
    m.kmem.write_memory(0210, 2);
    m.kmem.write_memory(0211, 3);

    // Prepared fixture data, not independently transcribed
    // original contents at these two addresses.
    m.kmem.write_memory(01525, 1);
    m.kmem.write_memory(01252, 2);

    m.kmem.write_memory(0212, cmd(0, 0, 01525, 0));
    m.kmem.write_memory(0213, cmd(0, 0, 01252, 0));
    m.kmem.write_memory(0214, cmd(0, 0, 0211, 0));

    m.kmem.write_memory(0127, cmd(034, 0212, 0, 0215));
    m.kmem.write_memory(0130, cmd(016, 0215, 0207, 0132));
    m.kmem.write_memory(0131, cmd(033));
    m.kmem.write_memory(0132, cmd(034, 0213, 0, 0215));
    m.kmem.write_memory(0133, cmd(016, 0215, 0210, 0135));
    m.kmem.write_memory(0134, cmd(033));
    m.kmem.write_memory(0135, cmd(034, 0214, 0, 0215));
    m.kmem.write_memory(0136, cmd(016, 0215, 0211, 0140));
    m.kmem.write_memory(0137, cmd(033));
}

int main() {
    int passed = 0, failed = 0;

    Kyiv_t m;
    prepare(m);
    m.C_reg = 0127;

    struct Expected {
        uint64_t pc, a, result;
    };
    const Expected expected[] = {
        {0130, 01525, 1},
        {0132, 01525, 1},
        {0133, 01252, 2},
        {0135, 01252, 2},
        {0136, 0211,  3},
        {0140, 0211,  3}
    };

    for (const auto& e : expected) {
        bool running = false;
        try {
            running = step(m);
        } catch (const std::exception& ex) {
            std::cout << "FAIL exception: " << ex.what() << '\n';
            ++failed;
            break;
        }

        bool ok = running && !m.T_reg
               && m.C_reg == e.pc
               && m.A_reg == e.a
               && m.kmem.read_memory(0215) == e.result;

        std::cout << (ok ? "PASS " : "FAIL ")
                  << "historical_F_step C=" << std::oct << m.C_reg
                  << " A=" << m.A_reg
                  << " result=" << m.kmem.read_memory(0215)
                  << '\n';
        if (ok) ++passed;
        else { ++failed; break; }
    }


    // Synthetic mismatch: historical failure branch to 0131 (STOP).
    {
        Kyiv_t bad;
        prepare(bad);
        bad.kmem.write_memory(0207, 7);
        bad.C_reg = 0127;

        const bool first = step(bad);
        const bool compare = step(bad);
        const bool branched =
            first && compare && !bad.T_reg && bad.C_reg == 0131;

        const bool stop_result = step(bad);
        const bool stopped =
            !stop_result && bad.T_reg && bad.C_reg == 0132;

        const bool ok = branched && stopped;
        std::cout << (ok ? "PASS " : "FAIL ")
                  << "historical_F_failure_branch"
                  << " branched=" << branched
                  << " stopped=" << stopped << '\n';
        if (!ok) return 2;
    }

    // Research only: distinguish 10-bit and 11-bit interpretations.
    Kyiv_t probe;
    probe.kmem.write_memory(01010, 012345);
    probe.kmem.write_rom(03010, 065432);
    probe.kmem.write_memory(2, cmd(0, 0, 03010, 0));
    probe.kmem.write_memory(0100, cmd(034, 2, 0, 4));
    probe.C_reg = 0100;

    try {
        const bool running = step(probe);
        std::cout << "OBS F_3010_vs_1010"
                  << " A=" << std::oct << probe.A_reg
                  << " result=" << probe.kmem.read_memory(4)
                  << " running=" << running
                  << " [no historical assertion]\n";
    } catch (const std::exception& ex) {
        std::cout << "OBS F_3010_vs_1010 exception: "
                  << ex.what() << '\n';
    }

    std::cout << std::dec
              << "ISA-05 D6 HISTORICAL PASS=" << passed
              << "/6 FAIL=" << failed << " OBS=1\n";
    return (passed == 6 && failed == 0) ? 0 : 1;
}
