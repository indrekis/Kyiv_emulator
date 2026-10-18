// ISA-07 D10-F2: standalone hypothetical converter; no Kyiv_t, no CPU writes.
// CLI: ten hexadecimal BCD nibbles (or deliberately invalid BCD), sign 0|1.
#include "kyiv_decimal_trunc.h"
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <string>

namespace {
bool decode(const char* str, std::uint64_t& value) {
    const std::string s(str);
    if (s.empty() || s.size() > 16) return false;
    value = 0;
    for (const char c: s) {
        unsigned v = 0;
        if (c >= '0' && c <= '9') v = static_cast<unsigned>(c - '0');
        else if (c >= 'a' && c <= 'f') v = static_cast<unsigned>(c - 'a' + 10);
        else if (c >= 'A' && c <= 'F') v = static_cast<unsigned>(c - 'A' + 10);
        else return false;
        value = (value << 4) | v;
    }
    return true;
}
const char* name(kyiv_decimal_trunc::status s) {
    using kyiv_decimal_trunc::status;
    switch (s) {
    case status::exact: return "EXACT";
    case status::truncated: return "TRUNCATED";
    case status::invalid_bcd: return "INVALID_BCD";
    }
    return "UNKNOWN";
}
}
int main(int argc, char** argv) {
    if (argc != 3 || (std::string(argv[2]) != "0" && std::string(argv[2]) != "1"))
        return 2;
    std::uint64_t packed=0;
    if (!decode(argv[1], packed)) return 2;
    const auto r=kyiv_decimal_trunc::convert_bcd10(packed, argv[2][0]=='1');
    std::cout << "D10F2-CONVERT status=" << name(r.state)
              << " word=" << std::oct << std::setfill('0') << std::setw(14) << r.word
              << " remainder=" << std::dec << r.remainder
              << " STAGED_ONLY=1 CPU_MUTATION=0\n";
    return 0;
}
