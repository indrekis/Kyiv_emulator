// ISA-07 D12-A: real Kyiv_t IO24 current-code observations, NOT hardware oracle.
// Link src/main.cpp; do not link src/asm_disasm.cpp (owns another main).
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
    const std::string permitted =
        "|full|single|track1|zone2|multiline|missing|empty|short|"
        "malformed|bad-first|suffix|negative|negative-zero|over32|"
        "word41|double-space|outside-physical|alternate|crlf|track-missing|";
    if (permitted.find("|" + mode + "|") == std::string::npos) return 2;
    try {
        Kyiv_t m;
        constexpr addr_t pc = 0100;
        const addr_t target = mode == "alternate" ? 0130 : 0120;
        const addr_t a1 = mode == "single" ? 0201 :
            mode == "outside-physical" ? 02000 : 0200;
        const addr_t a2 = (mode == "single" || mode == "outside-physical") ? a1 : 0202;
        const word_t first = instr(024, static_cast<unsigned>(a1),
                                    static_cast<unsigned>(a2),
                                    static_cast<unsigned>(target));
        const word_t next = instr(017, 0700, 0701, 0702);
        m.kmem.write_memory(pc, first);
        m.kmem.write_memory(pc + 1, instr(033, 0, 0, 0));
        m.kmem.write_memory(target, next);
        m.kmem.write_memory(0700, 5);
        m.kmem.write_memory(0701, 3);
        m.kmem.write_memory(0702, 0);
        m.C_reg = pc;
        m.K_reg = 0;
        m.drum_num_read = mode == "track1" ? 1 :
                          mode == "track-missing" ? 2 : 0;
        m.drum_zone_read = mode == "zone2" ? 2 : 0;
        m.drum_num_write = 4;
        m.drum_zone_write = 6;
        const auto oldA = m.A_reg;
        const auto oldP = m.P_reg;
        const auto oldLoop = m.Loop_reg;
        const auto oldT = m.T_reg;
        const auto oldH = m.h;
        const auto oldTrack = m.drum_num_read;
        const auto oldZone = m.drum_zone_read;
        const auto oldWriteTrack = m.drum_num_write;
        const auto oldWriteZone = m.drum_zone_write;
        std::vector<word_t> before;
        before.reserve(02001);
        for (addr_t a = 0; a <= 02000; ++a)
            before.push_back(m.kmem.read_memory(a));
        bool succeeded = false;
        bool run1 = false;
        std::string error = "NONE";
        try {
            run1 = m.execute_opcode();
            succeeded = true;
        } catch (const std::exception& e) {
            error = std::string(e.what()).empty() ? "UNKNOWN" : "STD_EXCEPTION";
        } catch (...) {
            error = "OTHER_EXCEPTION";
        }
        const addr_t pc1 = m.C_reg;
        const word_t k1 = m.K_reg;
        unsigned changed = 0;
        bool outside = false;
        for (addr_t a = 0; a <= 02000; ++a) {
            if (m.kmem.read_memory(a) == before[static_cast<std::size_t>(a)])
                continue;
            ++changed;
            if (a < a1 || a > a2) outside = true;
        }
        const bool stable = m.A_reg == oldA && m.P_reg == oldP &&
            m.Loop_reg == oldLoop && m.T_reg == oldT && m.h == oldH &&
            m.drum_num_read == oldTrack && m.drum_zone_read == oldZone &&
            m.drum_num_write == oldWriteTrack &&
            m.drum_zone_write == oldWriteZone;
        bool run2 = false;
        if (succeeded) run2 = m.execute_opcode(); // genuine XOR at a3
        std::cout << std::oct
                  << "D12A-OBS mode=" << mode
                  << " status=" << (succeeded ? "OK" : "THROW")
                  << " pc1=" << pc1 << " pc2=" << m.C_reg
                  << std::dec
                  << " k1=" << (k1 == (succeeded ? next : first))
                  << " k2=" << (succeeded ? m.K_reg == next : m.K_reg == first)
                  << " changed=" << changed
                  << " outside=" << outside
                  << " stable=" << stable
                  << " ram=" << m.kmem.read_memory(0200) << '/'
                  << m.kmem.read_memory(0201) << '/'
                  << m.kmem.read_memory(0202)
                  << " unmapped=" << m.kmem.read_memory(02000)
                  << " xor=" << m.kmem.read_memory(0702)
                  << " run=" << run1 << '/' << run2
                  << " error=" << error
                  << " steps=" << (succeeded ? 2 : 1)
                  << " HOST_OBSERVATION=1 HARDWARE_ORACLE=0\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D12A-PROBE-ERROR mode=" << mode << " reason=" << e.what() << '\n';
        return 3;
    }
}
