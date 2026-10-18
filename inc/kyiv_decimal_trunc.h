#ifndef KYIV_DECIMAL_TRUNC_H
#define KYIV_DECIMAL_TRUNC_H

// ISA-07 D10-F2: standalone ten-digit BCD -> signed 40-bit binary fraction.
// Truncation toward zero is INFERRED/PROVISIONAL (NOT a historical oracle).
// No changes to D10-C, D10-D, D10-E2 or executable Kyiv_t CPU semantics.
// GY62 printed pp. 10-11, 17, 117-118; DPS64 printed pp. 120-122.
#include "kyiv_decimal_exact.h"
#include <cstdint>
#include <limits>

namespace kyiv_decimal_trunc {

enum class status { exact, truncated, invalid_bcd };
struct result {
    status state;
    std::uint64_t word;       // 41-bit sign/magnitude word, zero on error
    std::uint64_t remainder;  // numerator modulo 5^10; mathematical only
};

// x=N/10^10, |x|<1; floor(|x|*2^40)=floor(N*2^30/5^10).
// The largest numerator fits uint64_t: (10^10-1)*2^30 < 2^64.
constexpr std::uint64_t shift_factor = std::uint64_t{1} << 30;
static_assert((kyiv_decimal_exact::decimal_scale - 1) <=
              std::numeric_limits<std::uint64_t>::max() / shift_factor,
              "BCD conversion numerator must fit uint64_t");

constexpr result convert_bcd10(std::uint64_t packed_bcd, bool negative) noexcept {
    using namespace kyiv_decimal_exact;
    if ((packed_bcd & ~bcd_bits_mask) != 0)
        return {status::invalid_bcd, 0, 0};

    std::uint64_t digits = 0;
    for (unsigned nibble = 0; nibble < 10; ++nibble) {
        const unsigned digit = static_cast<unsigned>((packed_bcd >> (36 - 4*nibble)) & 0xFULL);
        if (digit > 9)
            return {status::invalid_bcd, 0, 0};
        digits = digits * 10 + digit;
    }
    const std::uint64_t scaled = digits * shift_factor;
    const std::uint64_t quotient = scaled / exact_divisor;
    const std::uint64_t remainder = scaled % exact_divisor;
    // PROVISIONAL IO20 truncation, NOT proven hardware rounding:
    // DPS64 (1964), pp. 120-122: shift/add conversion, no stated round-up.
    // GY62 (1962), pp. 10-11: multiplication 10 vs rounded 11;
    // p. 17: digit extraction to precision; pp. 117-118: software FP.
    // Microcode constants/low bits remain OPEN; see D10-F2 decision record.
    return {remainder == 0 ? status::exact : status::truncated,
            quotient | (negative ? sign_bit : 0), remainder};
}

} // namespace kyiv_decimal_trunc
#endif // KYIV_DECIMAL_TRUNC_H
