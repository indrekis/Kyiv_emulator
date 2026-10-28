#ifndef KYIV_SERIAL_DIVISION_H
#define KYIV_SERIAL_DIVISION_H

// Kyiv arithmetic unit, opcode 12: functional reconstruction of sequential
// fixed-point division (D-P-S 1964, printed pp. 141, 150-151).
// P2 shifts right in a 45-position register; discarded low bits are lost.
// This is not a recovered gate-level timing model or a hardware oracle.
#include <cassert>
#include <cstdint>

namespace kyiv_serial_division {

// Precondition: 0 <= dividend < divisor < 2^40. The CPU retains its existing
// zero-divisor, unrepresentable quotient, stop/skip and sign policies.
inline std::uint64_t quotient_magnitude(std::uint64_t dividend,
                                         std::uint64_t divisor) noexcept {
    constexpr std::uint64_t one = std::uint64_t{1} << 40;
    constexpr unsigned guard_bits = 5;
    assert(divisor != 0 && dividend < divisor && divisor < one);
    std::uint64_t p2 = divisor << guard_bits;
    std::int64_t remainder = (static_cast<std::int64_t>(dividend) -
                               static_cast<std::int64_t>(divisor)) * (1LL << guard_bits);
    // Initial subtraction includes the low-bit two's-complement correction.
    // It is equivalent to (dividend-divisor)<<5, NOT the diagnostic -1 variant.
    std::uint64_t quotient = 0;
    for (unsigned cycle = 0; cycle != 40; ++cycle) {
        p2 >>= 1;  // Each discarded low bit is irrevocably lost.
        const auto term = static_cast<std::int64_t>(p2);
        remainder = remainder < 0 ? remainder + term : remainder - term;
        quotient = (quotient << 1) | static_cast<std::uint64_t>(remainder >= 0);
    }
    return quotient;
}

} // namespace kyiv_serial_division
#endif // KYIV_SERIAL_DIVISION_H
