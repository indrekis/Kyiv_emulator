// ISA-07 D10-D: standalone HOST_POLICY ASCII -> BCD -> D10-C exact word.
// Build WITHOUT src/main.cpp. No peripheral or CPU operation is executed.
#include "kyiv_decimal_ascii.h"
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

namespace {
const char* state_name(kyiv_decimal_ascii::status s) {
    using kyiv_decimal_ascii::status;
    switch (s) {
    case status::exact: return "EXACT";
    case status::nonexact: return "NONEXACT";
    case status::invalid_token: return "INVALID_TOKEN";
    }
    return "UNKNOWN";
}
const char* record_name(kyiv_decimal_ascii::record_status s) {
    using kyiv_decimal_ascii::record_status;
    switch (s) {
    case record_status::exact: return "EXACT";
    case record_status::empty: return "EMPTY";
    case record_status::nonexact: return "NONEXACT";
    case record_status::invalid_token: return "INVALID_TOKEN";
    }
    return "UNKNOWN";
}
std::string oct_word(std::uint64_t value) {
    std::ostringstream os;
    os << std::oct << std::setfill('0') << std::setw(14) << value;
    return os.str();
}
std::string bcd_hex(std::uint64_t value) {
    std::ostringstream os;
    os << std::hex << std::setfill('0') << std::setw(10) << value;
    return os.str();
}
std::string decimal_digits(std::uint64_t value) {
    std::ostringstream os;
    os << std::dec << std::setfill('0') << std::setw(10) << value;
    return os.str();
}
int line_end_edges() {
    using kyiv_decimal_ascii::status;
    using kyiv_decimal_ascii::record_status;
    const bool ok =
        kyiv_decimal_ascii::parse_token("6250000000\r").state == status::invalid_token &&
        kyiv_decimal_ascii::parse_token("6250000000\n").state == status::invalid_token &&
        kyiv_decimal_ascii::parse_record("0.6250000000\r").state == record_status::invalid_token &&
        kyiv_decimal_ascii::parse_record("0.6250000000\n").state == record_status::invalid_token;
    if (!ok) { std::cerr << "D10D-EDGES-FAIL\n"; return 1; }
    std::cout << "D10D-EDGES PASS=4/4 CR_LF=REJECTED IN_PROCESS=1\n";
    return 0;
}
int sweep() {
    unsigned passed = 0;
    for (std::uint64_t magnitude = 0; magnitude < 1024; ++magnitude) {
        const std::string digits = decimal_digits(magnitude * 9'765'625ULL);
        for (unsigned sign = 0; sign != 2; ++sign) {
            for (unsigned fmt = 0; fmt != 2; ++fmt) {
                const std::string token = std::string(sign ? "-" : "+") +
                    (fmt ? "0." : "") + digits;
                const auto actual = kyiv_decimal_ascii::parse_token(token);
                const std::uint64_t want = (magnitude << 30) |
                    (sign ? kyiv_decimal_exact::sign_bit : 0);
                if (actual.state != kyiv_decimal_ascii::status::exact ||
                    actual.word != want || actual.negative != (sign != 0)) {
                    std::cerr << "D10D-SWEEP-FAIL magnitude=" << magnitude
                              << " sign=" << sign << " fmt=" << fmt << '\n';
                    return 1;
                }
                ++passed;
            }
        }
    }
    std::cout << "D10D-SWEEP PASS=" << passed << "/4096"
              << " MAGNITUDES=1024 SIGNS=2 FORMATS=2 SIGNED_ZERO=1"
              << " CPU_MUTATION=0\n";
    return 0;
}
} // namespace

void print_token(const kyiv_decimal_ascii::result& r) {
    std::cout << "D10D-TOKEN status=" << state_name(r.state)
              << " bcd=" << bcd_hex(r.packed_bcd)
              << " negative=" << r.negative
              << " oct41=" << oct_word(r.word)
              << " HOST_POLICY=1\n";
}

int main(int argc, char** argv) {
    if (argc == 2 && std::string(argv[1]) == "--sweep") return sweep();
    if (argc == 2 && std::string(argv[1]) == "--edges") return line_end_edges();
    // Do NOT pass Unicode through Windows argv: best-fit ANSI conversion on some
    // toolchains changes fullwidth digit U+FF10 into ASCII '0' BEFORE parsing.
    // Construct the exact UTF-8 bytes INSIDE the C++ process instead.
    if (argc == 2 && std::string(argv[1]) == "--nonascii") {
        const std::string token = std::string("\xEF\xBC\x90") + ".6250000000";
        print_token(kyiv_decimal_ascii::parse_token(token));
        return 0;
    }
    if (argc == 2) {
        print_token(kyiv_decimal_ascii::parse_token(argv[1]));
        return 0;
    }
    if (argc == 3 && std::string(argv[1]) == "--record") {
        const auto r = kyiv_decimal_ascii::parse_record(argv[2]);
        std::cout << "D10D-RECORD status=" << record_name(r.state)
                  << " count=" << r.values.size() << " words=";
        if (r.values.empty()) std::cout << "NONE";
        for (std::size_t i = 0; i != r.values.size(); ++i) {
            if (i) std::cout << '/';
            std::cout << oct_word(r.values[i].word);
        }
        std::cout << " ATOMIC=1 HOST_POLICY=1\n";
        return 0;
    }
    std::cerr << "usage: probe <token> | --record <record> | --sweep | --edges\n";
    return 2;
}
