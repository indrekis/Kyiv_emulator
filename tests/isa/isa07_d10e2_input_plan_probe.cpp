// ISA-07 D10-E2: independent staging probe only (NOT a Kyiv_t CPU test).
// Input is raw bytes on stdin to avoid Windows argv Unicode normalization.
#include "kyiv_decimal_input_plan.h"
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

namespace {
const char* name(kyiv_decimal_input_plan::status s) {
    using kyiv_decimal_input_plan::status;
    switch (s) {
    case status::exact: return "EXACT";
    case status::invalid_count: return "INVALID_COUNT";
    case status::unavailable_stream: return "UNAVAILABLE_STREAM";
    case status::missing_start_line: return "MISSING_START_LINE";
    case status::invalid_first_offset: return "INVALID_FIRST_OFFSET";
    case status::empty_record: return "EMPTY_RECORD";
    case status::invalid_token: return "INVALID_TOKEN";
    case status::nonexact: return "NONEXACT";
    case status::short_input: return "SHORT_INPUT";
    case status::read_error: return "READ_ERROR";
    }
    return "UNKNOWN";
}
bool parse_size(const char* p, std::size_t& out) {
    // Deliberately restrict tool CLI arguments to ASCII digits and a modest range.
    if (!p || !*p) return false;
    std::size_t v = 0;
    for (const char* c = p; *c; ++c) {
        if (*c < '0' || *c > '9') return false;
        v = v * 10 + static_cast<unsigned>(*c - '0');
        if (v > 100000) return false;
    }
    out = v;
    return true;
}
}

int main(int argc, char** argv) {
    if (argc != 4) return 2;
    std::size_t start = 0, offset = 0, count = 0;
    if (!parse_size(argv[1], start) || !parse_size(argv[2], offset) ||
        !parse_size(argv[3], count)) return 2;
    auto r = kyiv_decimal_input_plan::collect(std::cin, start, offset, count);
    std::cout << "D10E2-PLAN status=" << name(r.state)
              << " count=" << r.words.size() << " words=";
    if (r.words.empty()) std::cout << "NONE";
    for (std::size_t i = 0; i < r.words.size(); ++i) {
        if (i) std::cout << '/';
        std::cout << std::oct << std::setfill('0') << std::setw(14) << r.words[i];
    }
    std::cout << " STAGED_ONLY=1 CPU_MUTATION=0\n";
    return 0;
}
