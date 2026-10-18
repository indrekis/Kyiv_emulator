#ifndef KYIV_BINARY_INPUT_PLAN_H
#define KYIV_BINARY_INPUT_PLAN_H

// ISA-07 D11-B: strict HOST_POLICY for a textual raw 41-bit Kyiv word.
// Not a claim about the historical punched-tape encoding.
#include <cstddef>
#include <cstdint>
#include <istream>
#include <limits>
#include <string>
#include <vector>
#include <utility>

namespace kyiv_binary_input_plan {
constexpr std::uint64_t max_word = (std::uint64_t{1} << 41) - 1;
constexpr std::size_t max_words = 02000;

enum class status {
    exact, unavailable_stream, invalid_count, invalid_selection,
    missing_start_line, short_input, empty_record, invalid_token
};

struct plan {
    status state;
    std::vector<std::uint64_t> words;
};

inline const char* status_text(status s) {
    switch (s) {
    case status::exact: return "EXACT";
    case status::unavailable_stream: return "UNAVAILABLE_STREAM";
    case status::invalid_count: return "INVALID_COUNT";
    case status::invalid_selection: return "INVALID_SELECTION";
    case status::missing_start_line: return "MISSING_START_LINE";
    case status::short_input: return "SHORT_INPUT";
    case status::empty_record: return "EMPTY_RECORD";
    case status::invalid_token: return "INVALID_TOKEN";
    }
    return "UNKNOWN";
}

inline status parse_line(std::string line, std::uint64_t& value) {
    // A CR is accepted ONLY as the terminator of a CRLF record.
    if (!line.empty() && line.back() == '\r') line.pop_back();
    const auto start = line.find_first_not_of(" \t");
    if (start == std::string::npos) return status::empty_record;
    const auto last = line.find_last_not_of(" \t");
    const std::size_t length = last - start + 1;
    if (length > 14) return status::invalid_token;
    std::uint64_t parsed = 0;
    for (std::size_t j = start; j <= last; ++j) {
        const unsigned char c = static_cast<unsigned char>(line[j]);
        if (c < '0' || c > '7') return status::invalid_token;
        const std::uint64_t digit = c - '0';
        if (parsed > (max_word - digit) / 8) return status::invalid_token;
        parsed = parsed * 8 + digit;
    }
    value = parsed;
    return status::exact;
}

inline plan collect(std::istream& in, std::size_t first_line, std::size_t count) {
    if (!in) return {status::unavailable_stream, {}};
    if (count == 0 || count > max_words) return {status::invalid_count, {}};
    if (first_line > (std::numeric_limits<std::size_t>::max)() - count)
        return {status::invalid_selection, {}};
    std::string line;
    for (std::size_t i = 0; i < first_line; ++i)
        if (!std::getline(in, line)) return {status::missing_start_line, {}};
    std::vector<std::uint64_t> staged;
    staged.reserve(count);
    for (std::size_t i = 0; i < count; ++i) {
        if (!std::getline(in, line))
            return {i == 0 ? status::missing_start_line : status::short_input, {}};
        std::uint64_t word = 0;
        const status state = parse_line(line, word);
        if (state != status::exact) return {state, {}};
        staged.push_back(word);
    }
    return {status::exact, std::move(staged)};
}
} // namespace kyiv_binary_input_plan
#endif
