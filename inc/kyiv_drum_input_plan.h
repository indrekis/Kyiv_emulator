#ifndef KYIV_DRUM_INPUT_PLAN_H
#define KYIV_DRUM_INPUT_PLAN_H

// ISA-07 D12-B HOST_POLICY: decimal text framing, NOT physical drum encoding.
// Machine words are 40 magnitude bits and a distinct sign bit (including -0).
#include <cstddef>
#include <cstdint>
#include <istream>
#include <limits>
#include <string>
#include <utility>
#include <vector>

namespace kyiv_drum_input_plan {
constexpr std::uint64_t sign_bit = std::uint64_t{1} << 40;
constexpr std::uint64_t max_magnitude = sign_bit - 1;
constexpr std::size_t max_words = 02000;

enum class status {
    exact, unavailable_stream, invalid_count, invalid_selection,
    missing_track, invalid_zone, short_input, empty_record, invalid_token
};
struct plan { status state; std::vector<std::uint64_t> words; };

inline const char* status_text(status s) {
    switch (s) {
    case status::exact: return "EXACT";
    case status::unavailable_stream: return "UNAVAILABLE_STREAM";
    case status::invalid_count: return "INVALID_COUNT";
    case status::invalid_selection: return "INVALID_SELECTION";
    case status::missing_track: return "MISSING_TRACK";
    case status::invalid_zone: return "INVALID_ZONE";
    case status::short_input: return "SHORT_INPUT";
    case status::empty_record: return "EMPTY_RECORD";
    case status::invalid_token: return "INVALID_TOKEN";
    }
    return "UNKNOWN";
}

inline status parse_decimal(const std::string& token, std::uint64_t& result) {
    if (token.empty()) return status::empty_record;
    std::size_t i = 0;
    const bool negative = token[0] == '-';
    if (negative || token[0] == '+') i = 1;
    if (i == token.size()) return status::invalid_token;
    std::uint64_t magnitude = 0;
    for (; i < token.size(); ++i) {
        const unsigned char c = static_cast<unsigned char>(token[i]);
        if (c < '0' || c > '9') return status::invalid_token;
        const std::uint64_t digit = static_cast<std::uint64_t>(c - '0');
        if (magnitude > (max_magnitude - digit) / 10)
            return status::invalid_token;
        magnitude = 10 * magnitude + digit;
    }
    result = magnitude | (negative ? sign_bit : 0);
    return status::exact;
}

inline plan collect(std::istream& input, std::size_t track,
                    std::size_t byte_offset, std::size_t count) {
    if (count == 0 || count > max_words) return {status::invalid_count, {}};
    if (track > (std::numeric_limits<std::size_t>::max)() - count)
        return {status::invalid_selection, {}};
    if (!input) return {status::unavailable_stream, {}};
    std::string line;
    for (std::size_t i = 0; i <= track; ++i)
        if (!std::getline(input, line)) return {status::missing_track, {}};
    // The offset is a byte offset into the first selected line, not a token index.
    // A final CR is only accepted as the CRLF line terminator.
    if (!line.empty() && line.back() == '\r') line.pop_back();
    if (byte_offset > line.size()) return {status::invalid_zone, {}};
    line.erase(0, byte_offset);
    std::vector<std::uint64_t> staged;
    staged.reserve(count);
    bool first = true;
    while (staged.size() < count) {
        if (!first) {
            if (!std::getline(input, line)) return {status::short_input, {}};
            if (!line.empty() && line.back() == '\r') line.pop_back();
        }
        first = false;
        // Whitespace delimiting is limited to ASCII space and tab.
        // Unexpected CR/NUL and other separators are never silently consumed.
        const auto begin = line.find_first_not_of(" \t");
        if (begin == std::string::npos) return {status::empty_record, {}};
        std::size_t pos = begin;
        while (pos < line.size() && staged.size() < count) {
            while (pos < line.size() && (line[pos] == ' ' || line[pos] == '\t')) ++pos;
            if (pos == line.size()) break;
            const std::size_t token_start = pos;
            while (pos < line.size() && line[pos] != ' ' && line[pos] != '\t') ++pos;
            const std::string token = line.substr(token_start, pos - token_start);
            std::uint64_t word = 0;
            const auto parsed = parse_decimal(token, word);
            if (parsed != status::exact) return {parsed, {}};
            staged.push_back(word);
        }
    }
    return {status::exact, std::move(staged)};
}
} // namespace kyiv_drum_input_plan
#endif
