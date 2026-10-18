#ifndef KYIV_DECIMAL_EXACT_H
#define KYIV_DECIMAL_EXACT_H

// ISA-07 D10-C: standalone DIGITAL conversion of ten BCD fractional digits.
// No hardware/card sign encoding, text grammar, rounding, or IO20 integration.
// Historical basis: GY62 (1962) pp. 7, 17; DPS64 (1964) pp. 15–16.
#include <cstdint>

namespace kyiv_decimal_exact {

constexpr std::uint64_t sign_bit = std::uint64_t{1} << 40;
constexpr std::uint64_t bcd_bits_mask = (std::uint64_t{1} << 40) - 1;
constexpr std::uint64_t decimal_scale = 10'000'000'000ULL;
constexpr std::uint64_t exact_divisor = 9'765'625ULL; // 5^10

// The sign is supplied SEPARATELY from the ten BCD nibbles.
// Signed zero here is a WORD-ENCODING property, not a punched input oracle.
enum class status { exact, nonexact, invalid_bcd };

struct result {
    status state;
    std::uint64_t word;
};

constexpr result convert_bcd10(std::uint64_t packed_bcd, bool negative) noexcept {
    // A BCD payload has EXACTLY ten nibbles; higher bits are not allowed.
    if ((packed_bcd & ~bcd_bits_mask) != 0)
        return {status::invalid_bcd, 0};

    std::uint64_t decimal_integer = 0;
    for (unsigned nibble = 0; nibble != 10; ++nibble) {
        const unsigned shift = 36u - 4u * nibble;
        const unsigned digit = static_cast<unsigned>((packed_bcd >> shift) & 0xFULL);
        if (digit > 9)
            return {status::invalid_bcd, 0};
        decimal_integer = 10 * decimal_integer + digit;
    }

    // x = decimal_integer / 10^10.
    // x * 2^40 = decimal_integer * 2^30 / 5^10.
    // Exact iff 5^10 divides decimal_integer; no floating-point/rounding.
    if (decimal_integer % exact_divisor != 0)
        return {status::nonexact, 0};

    const std::uint64_t magnitude = (decimal_integer / exact_divisor) << 30;
    return {status::exact, magnitude | (negative ? sign_bit : 0)};
}

} // namespace kyiv_decimal_exact

#endif // KYIV_DECIMAL_EXACT_H
