// ISA-04 D5: reproducible comparisons for opcode 007 (cyclic addition).
// STRICT: documented nonoverflow cases and no emergency stop/skip on overflow.
// POLICY: recorded implementation, NOT hardware-certified.
// OBS: final result vs DPS64 printed-p102 *candidate*, not a historical oracle.
#include <cstdint>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
constexpr std::uint64_t M = std::uint64_t{1} << 40;
constexpr std::uint64_t MAG = M - 1;
constexpr std::uint64_t H = M / 2;
constexpr std::uint64_t Q = M / 4;
constexpr std::uint64_t PC = 0100;
int strict_count = 0, policy_count = 0, observations = 0, failures = 0;

struct Silence {
    std::ostringstream sink;
    std::streambuf* previous;
    Silence() : previous(std::cout.rdbuf(sink.rdbuf())) {}
    ~Silence() { std::cout.rdbuf(previous); }
};
std::string oct(std::uint64_t v) {
    std::ostringstream ss;
    ss << std::oct << v;
    return ss.str();
}
std::uint64_t instruction() {
    return (std::uint64_t{007} << 36) | (std::uint64_t{2} << 24)
           | (std::uint64_t{3} << 12) | 4;
}
struct Outcome {
    std::uint64_t result;
    std::uint64_t pc;
    bool continues;
    bool stop;
};
Outcome run(std::uint64_t left, std::uint64_t right, bool block_overflow=false) {
    Kyiv_t m;
    m.kmem.write_memory(2, left);
    m.kmem.write_memory(3, right);
    m.kmem.write_memory(PC, instruction());
    m.C_reg = PC;
    m.emergency_stop_blocked = block_overflow;
    bool continues = false;
    { Silence silence; continues = m.execute_opcode(); }
    return {m.kmem.read_memory(4), m.C_reg, continues, m.T_reg};
}
bool step_ok(const Outcome& o) {
    return o.continues && !o.stop && o.pc == PC + 1;
}
void check(const char* title, const Outcome& o, std::uint64_t want, bool policy=false) {
    const bool ok = step_ok(o) && o.result == want;
    ++(policy ? policy_count : strict_count);
    failures += !ok;
    std::cout << (ok ? (policy ? "POLICY-PASS " : "PASS ") : "FAIL ")
              << title << " | actual=" << oct(o.result)
              << " expected=" << oct(want) << " pc=" << oct(o.pc) << '\n';
}
void only_control(const char* title, const Outcome& o) {
    const bool ok = step_ok(o);
    ++strict_count;
    failures += !ok;
    std::cout << (ok ? "PASS " : "FAIL ") << title
              << " | output=" << oct(o.result) << " pc=" << oct(o.pc)
              << " [numeric result NOT asserted]\n";
}
// A candidate reading of DPS64 p.102 for |a+b|>1, not a machine-level oracle.
// Taking scaled signed sums allows exact integer arithmetic with no float rounding.
void compare_candidate(const char* title, std::uint64_t left, std::uint64_t right) {
    const auto o = run(left, right);
    const auto magnitude = [](std::uint64_t word)->std::int64_t {
        const auto val = static_cast<std::int64_t>(word & MAG);
        return (word & M) ? -val : val;
    };
    const std::int64_t sum = magnitude(left) + magnitude(right);
    const bool outside = (sum > static_cast<std::int64_t>(M) ||
                          sum < -static_cast<std::int64_t>(M));
    ++observations;
    std::cout << "OBS " << title << " | actual=" << oct(o.result)
              << " sum_scaled=" << sum << " DPS64_candidate=";
    if (outside) {
        const std::int64_t adjusted = sum > 0 ? sum - static_cast<std::int64_t>(M)
                                               : sum + static_cast<std::int64_t>(M);
        const bool negative = adjusted < 0;
        const auto mag = static_cast<std::uint64_t>(negative ? -adjusted : adjusted);
        const std::uint64_t candidate = (negative ? M : 0ULL) | (mag & MAG);
        std::cout << oct(candidate) << " delta_LSB="
                  << static_cast<std::int64_t>(o.result & MAG)
                     - static_cast<std::int64_t>(candidate & MAG);
    } else {
        std::cout << "not specified at exact boundary or no overflow";
    }
    std::cout << " continues=" << o.continues << " [not an oracle]\n";
}
void observe_zero(const char* title, std::uint64_t left, std::uint64_t right) {
    const auto o = run(left, right);
    ++observations;
    std::cout << "OBS " << title << " | raw=" << oct(o.result)
              << " [signed-zero convention unresolved]\n";
}
}

int main() {
    // Source-supported arithmetic with no carry and nonzero outcomes.
    check("07_positive_no_carry", run(Q, Q), H);
    check("07_negative_no_carry", run(M | Q, M | Q), M | H);
    check("07_mixed_sign_no_carry", run(H, M | Q), Q);
    check("07_mixed_sign_negative", run(Q, M | H), M | Q);
    // GY62 p.11: cyclic addition does NOT raise an overflow stop. The output
    // word remains an unresolved hardware issue, so verify control only.
    only_control("07_overflow_does_not_stop", run(H, H+1));
    only_control("07_overflow_block_flag_does_not_skip", run(H, H+1, true));
    only_control("07_negative_overflow_does_not_stop", run(M | H, M | (H+1)));

    // Snapshot POLICY: exact values of existing implementation, NOT a truth oracle.
    check("07_policy_exact_plus_one", run(H, H), 1, true);
    check("07_policy_exact_minus_one", run(M | H, M | H), M | 1, true);
    check("07_policy_plus_one_lsb", run(H, H+1), 2, true);
    check("07_policy_minus_one_lsb", run(M | H, M | (H+1)), M | 2, true);
    check("07_policy_near_two", run(MAG, MAG), MAG, true);

    // DPS64 p.102 candidate; exact +/-1 boundary is explicitly NOT asserted.
    compare_candidate("07_exact_plus_one", H, H);
    compare_candidate("07_exact_minus_one", M | H, M | H);
    compare_candidate("07_plus_one_plus_lsb", H, H+1);
    compare_candidate("07_minus_one_minus_lsb", M | H, M | (H+1));
    compare_candidate("07_two_maximal_operands", MAG, MAG);
    observe_zero("07_cancel_to_zero", H, M | H);
    observe_zero("07_negative_zero_plus_negative_zero", M, M);

    std::cout << "ISA-04 D5 STRICT=" << strict_count
              << " POLICY=" << policy_count
              << " OBS=" << observations
              << " FAIL=" << failures << '\n';
    return failures ? 1 : 0;
}
