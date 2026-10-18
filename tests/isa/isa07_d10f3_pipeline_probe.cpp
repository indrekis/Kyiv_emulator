// ISA-07 D10-F3: standalone token/record/whole-command text planner probe.
// This is NOT a Kyiv_t CPU test. Byte input is stdin, not Windows argv.
#include "kyiv_decimal_input_plan.h"
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <sstream>
#include <string>
#include <vector>

namespace {
const char* name(kyiv_decimal_ascii::status s) {
    using S = kyiv_decimal_ascii::status;
    switch(s) {
    case S::exact: return "EXACT";
    case S::truncated: return "TRUNCATED";
    case S::nonexact: return "NONEXACT_LEGACY";
    case S::invalid_token: return "INVALID_TOKEN";
    }
    return "UNKNOWN";
}
const char* name(kyiv_decimal_ascii::record_status s) {
    using S = kyiv_decimal_ascii::record_status;
    switch(s) {
    case S::exact: return "EXACT";
    case S::truncated: return "TRUNCATED";
    case S::nonexact: return "NONEXACT_LEGACY";
    case S::empty: return "EMPTY_RECORD";
    case S::invalid_token: return "INVALID_TOKEN";
    }
    return "UNKNOWN";
}
const char* name(kyiv_decimal_input_plan::status s) {
    using S = kyiv_decimal_input_plan::status;
    switch(s) {
    case S::exact: return "EXACT";
    case S::truncated: return "TRUNCATED";
    case S::nonexact: return "NONEXACT_LEGACY";
    case S::invalid_count: return "INVALID_COUNT";
    case S::unavailable_stream: return "UNAVAILABLE_STREAM";
    case S::missing_start_line: return "MISSING_START_LINE";
    case S::invalid_first_offset: return "INVALID_FIRST_OFFSET";
    case S::empty_record: return "EMPTY_RECORD";
    case S::invalid_token: return "INVALID_TOKEN";
    case S::short_input: return "SHORT_INPUT";
    case S::read_error: return "READ_ERROR";
    }
    return "UNKNOWN";
}
void output(const std::string& mode, const char* state,
            const std::vector<std::uint64_t>& words) {
    std::cout << "D10F3-OBS mode=" << mode << " status=" << state
              << " count=" << std::dec << words.size() << " words=";
    if (words.empty()) std::cout << "NONE";
    for (std::size_t i = 0; i != words.size(); ++i) {
        if (i) std::cout << '/';
        std::cout << std::oct << std::setw(14) << std::setfill('0') << words[i];
    }
    std::cout << " CPU_MUTATION=0 TRUNCATION_PROVISIONAL=1\n";
}
bool size_arg(const char* s, std::size_t& value) {
    if (!s || !*s) return false;
    value = 0;
    for (const char* p = s; *p; ++p) {
        if (*p < '0' || *p > '9') return false;
        value = value * 10 + static_cast<unsigned>(*p - '0');
        if (value > 100000) return false;
    }
    return true;
}
}
int main(int argc, char** argv) {
    if (argc < 2) return 2;
    const std::string mode(argv[1]);
    if (mode == "token" || mode == "record") {
        if (argc != 2) return 2;
        const std::string text(std::istreambuf_iterator<char>{std::cin},
                               std::istreambuf_iterator<char>{});
        if (mode == "token") {
            const auto r = kyiv_decimal_ascii::parse_token(text);
            if (r.state == kyiv_decimal_ascii::status::invalid_token ||
                r.state == kyiv_decimal_ascii::status::nonexact)
                output(mode, name(r.state), {});
            else output(mode, name(r.state), {r.word});
        } else {
            const auto r = kyiv_decimal_ascii::parse_record(text);
            std::vector<std::uint64_t> words;
            for (const auto& v : r.values) words.push_back(v.word);
            output(mode, name(r.state), words);
        }
        return 0;
    }
    if (mode == "plan" && argc == 5) {
        std::size_t start=0, offset=0, count=0;
        if (!size_arg(argv[2],start) || !size_arg(argv[3],offset) ||
            !size_arg(argv[4],count)) return 2;
        auto r = kyiv_decimal_input_plan::collect(std::cin,start,offset,count);
        output(mode, name(r.state), r.words);
        return 0;
    }
    return 2;
}
