// D10-C: standalone exact ten-digit BCD -> 41-bit word probe.
// Build WITHOUT src/main.cpp; this is NOT an IO20 CPU test.
#include "kyiv_decimal_exact.h"
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
using kyiv_decimal_exact::convert_bcd10;
using kyiv_decimal_exact::status;

std::uint64_t pack_decimal_digits(std::uint64_t n) {
    if (n >= kyiv_decimal_exact::decimal_scale)
        throw std::invalid_argument("decimal digit magnitude out of range");
    std::uint64_t packed = 0;
    std::uint64_t place = 1;
    for (unsigned i = 0; i < 10; ++i) {
        packed |= (n % 10) * place;
        n /= 10;
        place <<= 4;
    }
    return packed;
}

const char* name(status s) {
    switch (s) {
        case status::exact: return "EXACT";
        case status::nonexact: return "NONEXACT";
        case status::invalid_bcd: return "INVALID_BCD";
    }
    return "UNKNOWN";
}

int sweep() {
    unsigned passed = 0;
    for (std::uint64_t magnitude = 0; magnitude < 1024; ++magnitude) {
        const std::uint64_t packed = pack_decimal_digits(
            (magnitude * kyiv_decimal_exact::decimal_scale) / 1024);
        for (int sign = 0; sign != 2; ++sign) {
            const auto r = convert_bcd10(packed, sign != 0);
            const std::uint64_t want = (magnitude << 30) |
                (sign ? kyiv_decimal_exact::sign_bit : 0);
            if (r.state != status::exact || r.word != want) {
                std::cerr << "D10C-SWEEP-FAIL magnitude=" << magnitude
                          << " negative=" << sign << '\n';
                return 1;
            }
            ++passed;
        }
    }
    std::cout << "D10C-SWEEP PASS=" << passed << "/2048"
              << " MAGNITUDES=1024 SIGNS=2 ZERO_SIGN_PRESERVED=1"
              << " NO_FLOATING_POINT=1\n";
    return 0;
}
} // namespace

int main(int argc, char** argv) {
    if (argc == 2 && std::string(argv[1]) == "--sweep")
        return sweep();
    if (argc != 3) {
        std::cerr << "usage: probe <ten-nibble-hex> <+|-> | --sweep\n";
        return 2;
    }
    try {
        const std::string bcd_string(argv[1]);
        const std::string sign(argv[2]);
        if (sign != "+" && sign != "-") return 2;
        std::size_t parsed = 0;
        const std::uint64_t bcd = std::stoull(bcd_string, &parsed, 16);
        if (parsed != bcd_string.size()) return 2;
        const auto r = kyiv_decimal_exact::convert_bcd10(bcd, sign == "-");
        std::cout << "D10C-CONVERT bcd=" << bcd_string
                  << " sign=" << sign << " status=" << name(r.state)
                  << " oct41=" << std::oct << std::setfill('0')
                  << std::setw(14) << r.word << std::dec
                  << " host_code_only=1\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D10C-ARGS-FAIL " << e.what() << '\n';
        return 2;
    }
}
