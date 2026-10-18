// ISA-07 D10-E3: real Kyiv_t::execute_opcode() witness, two CPU steps on success.
// Build with src/main.cpp ONLY (src/asm_disasm.cpp owns its own main()).
// User fixture files are isolated by the Python runner; this probe never
// implements a substitute CPU or input conversion.
#include "kyiv.h"
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
constexpr word_t instr(unsigned op, unsigned a1, unsigned a2, unsigned a3) {
    return (word_t(op) << 36) | (word_t(a1) << 24) |
           (word_t(a2) << 12) | word_t(a3);
}
std::string octal(word_t v) {
    std::ostringstream o;
    o << std::oct << std::setfill('0') << std::setw(14) << v;
    return o.str();
}
std::string octaddr(addr_t a) {
    std::ostringstream o;
    o << std::oct << a;
    return o.str();
}
unsigned address(const char* s) {
    const auto val = std::stoul(s, nullptr, 0);
    if (val > 07777u) throw std::runtime_error("bad-argument-address");
    return static_cast<unsigned>(val);
}
}

int main(int argc, char** argv) {
    if (argc != 7) return 2;
    const std::string mode(argv[1]);
    try {
        const auto a1 = address(argv[2]);
        const auto a2 = address(argv[3]);
        const auto a3 = address(argv[4]);
        const int selected_line = std::stoi(argv[5]);
        const auto a_reg = address(argv[6]);
        constexpr addr_t pc = 0100, nxt = 0101;
        constexpr addr_t lhs = 0700, rhs = 0701, dst = 0702;
        constexpr word_t sentinel = 01234567012345ULL;
        constexpr word_t follow = instr(017, lhs, rhs, dst);
        const word_t first = instr(020, a1, a2, a3);
        Kyiv_t m;
        for (addr_t a = 1; a < 02000; ++a)
            m.kmem.write_memory(a, sentinel);
        m.kmem.write_memory(pc, first);
        m.kmem.write_memory(nxt, follow);
        m.kmem.write_memory(lhs, 5);
        m.kmem.write_memory(rhs, 3);
        m.kmem.write_memory(dst, sentinel);
        m.C_reg = pc;
        m.K_reg = 0;
        m.A_reg = a_reg;
        m.perfo_num = selected_line;
        const auto prior_k = m.K_reg;
        const auto prior_p = m.P_reg;
        const auto prior_loop = m.Loop_reg;
        const auto prior_h = m.h;
        const auto prior_t = m.T_reg;
        std::vector<word_t> before;
        before.reserve(02000);
        for (addr_t a = 0; a < 02000; ++a)
            before.push_back(m.kmem.read_memory(a));

        // Independent test-side address oracle: raw 12-bit instruction
        // fields, modifier flag 04000 and effective 11-bit address 03777.
        // Do not call CPU address-decoding helpers from this translation unit.
        const addr_t target_first = ((a1 & 03777u) +
            ((a1 & 04000u) ? a_reg : 0u)) & 03777u;
        const addr_t target_last = ((a2 & 03777u) +
            ((a2 & 04000u) ? a_reg : 0u)) & 03777u;
        try {
            const bool run1 = m.execute_opcode(); // ACTUAL CPU STEP #1
            const auto pc1 = m.C_reg;
            const auto k1 = m.K_reg;
            bool guard = true;
            for (addr_t a = 0; a < 02000; ++a) {
                const bool writable_target =
                    target_first <= target_last &&
                    a >= target_first && a <= target_last;
                if (!writable_target && m.kmem.read_memory(a) != before[a])
                    guard = false;
            }
            std::string words;
            if (target_first <= target_last && target_last < 02000) {
                for (addr_t a = target_first; a <= target_last; ++a) {
                    if (!words.empty()) words += '/';
                    words += octal(m.kmem.read_memory(a));
                }
            }
            if (words.empty()) words = "NONE";
            const bool stable = m.A_reg == a_reg &&
                m.perfo_num == selected_line && m.h == prior_h &&
                m.P_reg == prior_p && m.Loop_reg == prior_loop &&
                m.T_reg == prior_t;
            const bool run2 = m.execute_opcode(); // ACTUAL CPU STEP #2: XOR
            std::cout << "D10E3-CPU mode=" << mode << " status=OK"
                      << " pc1=" << octaddr(pc1)
                      << " pc2=" << octaddr(m.C_reg)
                      << " k1=" << (k1 == follow)
                      << " k2=" << (m.K_reg == follow)
                      << " guard=" << guard
                      << " regs=" << stable
                      << " xor=" << m.kmem.read_memory(dst)
                      << " run=" << run1 << '/' << run2
                      << " words=" << words << " steps=2\n";
        } catch (const std::runtime_error& e) {
            bool memory_unchanged = true;
            for (addr_t a = 0; a < 02000; ++a)
                if (m.kmem.read_memory(a) != before[a]) memory_unchanged = false;
            const bool stable = m.A_reg == a_reg &&
                m.perfo_num == selected_line && m.h == prior_h &&
                m.P_reg == prior_p && m.Loop_reg == prior_loop &&
                m.T_reg == prior_t;
            // The initial fetch intentionally changed K from prior_k.
            const bool prefetched_current = m.K_reg == first && prior_k == 0;
            std::string reason = e.what();
            if (reason.rfind("IO20: ", 0) == 0) reason.erase(0, 6);
            else reason = "UNEXPECTED_EXCEPTION";
            std::cout << "D10E3-CPU mode=" << mode << " status=ERROR"
                      << " reason=" << reason << " pc=" << octaddr(m.C_reg)
                      << " k=" << prefetched_current
                      << " unchanged=" << memory_unchanged
                      << " regs=" << stable << " steps=1\n";
        }
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D10E3-HARNESS-ERROR mode=" << mode
                  << " reason=" << e.what() << '\n';
        return 3;
    }
}
