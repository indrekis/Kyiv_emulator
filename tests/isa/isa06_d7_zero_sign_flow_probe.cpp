// ISA-06 D7: zero-result sign propagation into exact compare and sign branch.
// GY62 (1962), printed pp. 11, 13, 170-171; DPS64 (1964), pp. 94-103, 144-146.
// The sign of zero produced by opcode 01 is OBS, not a historical STRICT oracle.
// The continuation after historical 0123/0141 is an instrumented probe, NOT
// an original part of the historical RAM-test program.
#include <cstdint>
#include <exception>
#include <iostream>
#include <sstream>
#include <string>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
using W = uint64_t;
constexpr W SIGN = W{1} << 40;
constexpr W PC = 0100;
constexpr W RETURN = 0137;
constexpr W LOOP = 0765;
constexpr W POS_TARGET = 0150;
constexpr W NEG_TARGET = 0160;
constexpr W CMP_TARGET = 0200;
constexpr W HIST_K = 0'01'0021'0000'0020ULL;
int strict_total = 0, strict_pass = 0, obs_total = 0;

W inst(W opcode, W a, W b, W c) {
    return (opcode << 36) | ((a & 07777) << 24)
         | ((b & 07777) << 12) | (c & 07777);
}
std::string oct(W value) {
    std::ostringstream out;
    out << std::oct << value;
    return out.str();
}
struct Silence {
    std::ostringstream ignored;
    std::streambuf* old;
    Silence() : old(std::cout.rdbuf(ignored.rdbuf())) {}
    ~Silence() { std::cout.rdbuf(old); }
};
bool tick(Kyiv_t& cpu) { Silence s; return cpu.execute_opcode(); }

void init(Kyiv_t& cpu) {
    cpu.P_reg = RETURN;
    cpu.Loop_reg = LOOP;
    cpu.A_reg = 0;
    cpu.T_reg = false;
    cpu.kmem.write_rom(03026, SIGN); // Explicit diagnostic fixture, not authenticated ROM.
}

// STRICT: code-exact compare of independently injected +0/-0, opcode 016.
void exact_compare(const char* label, W left, W right, bool branch) {
    ++strict_total;
    try {
        Kyiv_t m;
        init(m);
        m.kmem.write_memory(0002, left);
        m.kmem.write_memory(0003, right);
        const W k = inst(016, 0002, 0003, CMP_TARGET);
        m.kmem.write_memory(PC, k);
        m.C_reg = PC;
        const bool running = tick(m);
        const W expected_pc = branch ? CMP_TARGET : PC + 1;
        const bool ok = running && !m.T_reg && m.K_reg == k &&
                        m.C_reg == expected_pc && m.P_reg == RETURN &&
                        m.A_reg == 0 && m.Loop_reg == LOOP &&
                        m.kmem.read_memory(0002) == left &&
                        m.kmem.read_memory(0003) == right;
        strict_pass += ok;
        std::cout << (ok ? "STRICT-PASS " : "DOC-MISMATCH ") << label
                  << " | 016 a=" << oct(left) << " b=" << oct(right)
                  << " C=" << oct(m.C_reg) << " expected_C=" << oct(expected_pc)
                  << " K=" << oct(m.K_reg) << " stop=" << m.T_reg << '\n';
    } catch (const std::exception& e) {
        std::cout << "DOC-MISMATCH " << label << " | exception=" << e.what() << '\n';
    }
}

// STRICT: branching on the sign bit of a preloaded +0/-0, opcode 031.
void sign_branch(const char* label, W value, bool negative) {
    ++strict_total;
    try {
        Kyiv_t m;
        init(m);
        m.kmem.write_memory(0002, value);
        const W k = inst(031, 0002, POS_TARGET, NEG_TARGET);
        m.kmem.write_memory(PC, k);
        m.C_reg = PC;
        const bool running = tick(m);
        const W expected_pc = negative ? NEG_TARGET : POS_TARGET;
        const bool ok = running && !m.T_reg && m.K_reg == k &&
                        m.C_reg == expected_pc && m.P_reg == RETURN &&
                        m.A_reg == 0 && m.Loop_reg == LOOP &&
                        m.kmem.read_memory(0002) == value;
        strict_pass += ok;
        std::cout << (ok ? "STRICT-PASS " : "DOC-MISMATCH ") << label
                  << " | 031 sign=" << (negative ? "negative" : "positive")
                  << " C=" << oct(m.C_reg) << " expected_C=" << oct(expected_pc)
                  << " stop=" << m.T_reg << '\n';
    } catch (const std::exception& e) {
        std::cout << "DOC-MISMATCH " << label << " | exception=" << e.what() << '\n';
    }
}

// Instrumented three-step chain: arithmetic -> exact compare to -0 ->
// sign branch. The comparison's two possible fall-through destinations
// contain identical sign-branch words, ensuring three executed steps.
// The continuation is diagnostic, *even when pc is historical 0123/0141*.
void chain(const char* label, W op, W pc, W a, W b, bool strict,
           bool historical_word = false) {
    if (strict) ++strict_total; else ++obs_total;
    try {
        Kyiv_t m;
        init(m);
        const W src1 = historical_word ? 0021 : 0002;
        const W src2 = historical_word ? 0000 : 0003;
        const W dst  = historical_word ? 0020 : 0004;
        m.kmem.write_memory(src1, a);
        if (src2 != 0) m.kmem.write_memory(src2, b);
        const W k0 = historical_word ? HIST_K : inst(op, src1, src2, dst);
        const W compare = inst(016, dst, 03026, pc + 3);
        const W branch = inst(031, dst, POS_TARGET, NEG_TARGET);
        m.kmem.write_memory(pc, k0);
        m.kmem.write_memory(pc + 1, compare);
        m.kmem.write_memory(pc + 2, branch);
        m.kmem.write_memory(pc + 3, branch);
        m.C_reg = pc;

        const bool run0 = tick(m);
        const W fetched0 = m.K_reg;
        const W after0 = m.C_reg;
        const W result = m.kmem.read_memory(dst);
        const bool run1 = tick(m);
        const W fetched1 = m.K_reg;
        const W after1 = m.C_reg;
        const bool equals_neg_zero = (after1 == pc + 3);
        const bool run2 = tick(m);
        const W fetched2 = m.K_reg;
        const W after2 = m.C_reg;
        const bool result_negative = (result & SIGN) != 0;
        const bool no_stop = run0 && run1 && run2 && !m.T_reg;
        if (strict) {
            // GY62 p. 13 explicitly defines equal-operand subtraction as -0.
            // Then comparison 016 and sign branch 031 are historically specified.
            const bool ok = no_stop && k0 == inst(002, 0002, 0003, 0004) &&
                            fetched0 == k0 && fetched1 == compare &&
                            fetched2 == branch && after0 == pc + 1 &&
                            result == SIGN && after1 == pc + 3 && equals_neg_zero &&
                            after2 == NEG_TARGET && result_negative &&
                            m.P_reg == RETURN && m.A_reg == 0 && m.Loop_reg == LOOP;
            strict_pass += ok;
            std::cout << (ok ? "STRICT-PASS " : "DOC-MISMATCH ") << label;
        } else {
            std::cout << "OBS " << label;
        }
        std::cout << " | op=" << oct(op) << " K=" << oct(fetched0)
                  << " a=" << oct(a) << " b=" << oct(b)
                  << " result=" << oct(result)
                  << " result_sign=" << (result_negative ? "negative" : "positive")
                  << " C0=" << oct(after0)
                  << " compare_to_-0=" << (equals_neg_zero ? "equal" : "different")
                  << " C1=" << oct(after1)
                  << " branch_C=" << oct(after2)
                  << " stop=" << m.T_reg
                  << (strict ? "" : " [not a zero-sum sign oracle]") << '\n';
    } catch (const std::exception& e) {
        if (strict) std::cout << "DOC-MISMATCH " << label;
        else std::cout << "OBS " << label;
        std::cout << " | exception=" << e.what()
                  << (strict ? "" : " [not a historical oracle]") << '\n';
    }
}
} // namespace

int main() {
    exact_compare("16_plus_zero_equals_plus_zero", 0, 0, true);
    exact_compare("16_negative_zero_equals_negative_zero", SIGN, SIGN, true);
    exact_compare("16_plus_zero_not_negative_zero", 0, SIGN, false);
    exact_compare("16_negative_zero_not_plus_zero", SIGN, 0, false);
    sign_branch("31_plus_zero_positive_arm", 0, false);
    sign_branch("31_negative_zero_negative_arm", SIGN, true);
    chain("02_equal_positive_to_negative_zero_compare_branch", 002, PC, 5, 5, true);
    chain("02_equal_negative_to_negative_zero_compare_branch", 002, PC,
          SIGN | 5, SIGN | 5, true);

    chain("01_plus_zero_plus_zero", 001, PC, 0, 0, false);
    chain("01_plus_zero_plus_negative_zero", 001, PC, 0, SIGN, false);
    chain("01_negative_zero_plus_plus_zero", 001, PC, SIGN, 0, false);
    chain("01_negative_zero_plus_negative_zero", 001, PC, SIGN, SIGN, false);
    chain("01_positive_five_plus_negative_five", 001, PC, 5, SIGN | 5, false);
    chain("01_negative_five_plus_positive_five", 001, PC, SIGN | 5, 5, false);
    chain("historical_0123_with_probe_continuation", 001, 0123, SIGN, 0, false, true);
    chain("historical_0141_with_probe_continuation", 001, 0141, SIGN, 0, false, true);

    std::cout << "ISA-06 D7 STRICT=" << strict_pass << '/' << strict_total
              << " DOC-MISMATCH=" << (strict_total - strict_pass)
              << " POLICY=0 OBS=" << obs_total << '\n';
    return strict_pass == strict_total ? 0 : 1;
}
