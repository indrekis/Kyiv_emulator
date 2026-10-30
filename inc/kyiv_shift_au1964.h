#pragma once
// Kyiv A6/H29: source-derived PRIMARY production reconstruction for opcode 013 (octal).
// Historical support: DPS 1964 pp. 151-152; 1962 pp. 12, 173-174.
// IMPORTANT: sign sampling before a possible simultaneous clear at IVA3 is
// selected based on source-test 0326. This is NOT a measured electrical timing.
// Do NOT mistake this physical proof of the IVA3 micro-timing.
#include <cstdint>
#include <stdexcept>

namespace kyiv_shift_au1964 {
constexpr std::uint64_t kMagnitudeMask = (std::uint64_t{1} << 40) - 1;
constexpr std::uint64_t kSignBit = std::uint64_t{1} << 40;
constexpr std::uint64_t kWordMask = (std::uint64_t{1} << 41) - 1;

struct ShiftResult {
    std::uint64_t word;
    std::uint64_t adder_magnitude;
    unsigned actual_shifts;
    bool z6;
    bool z40;
    bool p2_sign_before_output;
};

// Shift constant is a 41-bit sign+magnitude word; its sign selects direction.
// The magnitude is deliberately NOT masked to six low bits. The model uses
// the entire 40-bit one's complement in the adder's counter path.
inline ShiftResult shift013(std::uint64_t shift_constant, std::uint64_t operand) {
    if ((shift_constant & ~kWordMask) || (operand & ~kWordMask))
        throw std::invalid_argument("shift013: value not 41-bit");
    const bool right = (shift_constant & kSignBit) != 0;
    const std::uint64_t count = shift_constant & kMagnitudeMask;
    std::uint64_t counter = kMagnitudeMask ^ count;
    std::uint64_t p1 = right ? 0 : operand;
    std::uint64_t p2 = right ? operand : 0;
    unsigned shifts = 0;
    bool z6 = false, z40 = false;
    // The first increment takes place *before* any data shift.
    for (unsigned pulse = 0; pulse <= 64; ++pulse) {
        const std::uint64_t before = counter;
        const std::uint64_t wide = before + 1;
        z6 = (before & 63u) == 63u;
        z40 = wide > kMagnitudeMask;
        counter = wide & kMagnitudeMask;
        if (pulse != 0) {
            ++shifts;
            if (right) p2 >>= 1; // shifts sign as data; ISdv2 clears top bit
            else p1 = (p1 << 1) & kWordMask;
        }
        if (z6) break;
        if (pulse == 64) throw std::logic_error("shift013: missing z6");
    }
    std::uint64_t sum_magnitude = 0;
    if (z40) {
        sum_magnitude = (p1 | p2) & kMagnitudeMask;
        if ((p1 & kSignBit) != 0) p2 |= kSignBit; // I3 sign-copy
    }
    // Chosen H25/H28 selected source-compatible timing: IVA3 reads P2 before extra clear.
    const bool p2_sign = (p2 & kSignBit) != 0;
    return {(p2_sign ? kSignBit : 0) | sum_magnitude,
            sum_magnitude, shifts, z6, z40, p2_sign};
}
} // namespace kyiv_shift_au1964
