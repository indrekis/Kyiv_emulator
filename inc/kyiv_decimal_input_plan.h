#ifndef KYIV_DECIMAL_INPUT_PLAN_H
#define KYIV_DECIMAL_INPUT_PLAN_H

// ISA-07 D10-E2: side-effect-free host text planner for future IO20.
// All line/zone/framing/error rules are HOST_POLICY, never punched-card facts.
// Does not touch Kyiv_t, memory, registers, or physical device semantics.
#include "kyiv_decimal_ascii.h"
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <istream>
#include <string>
#include <utility>
#include <vector>

namespace kyiv_decimal_input_plan {

enum class status {
    exact, invalid_count, unavailable_stream, missing_start_line,
    invalid_first_offset, empty_record, invalid_token, nonexact,
    short_input, read_error, truncated
};

struct result {
    status state;
    std::vector<std::uint64_t> words;
};

// HOST_POLICY framing contract:
// * start_line is a zero-based PHYSICAL line number; earlier lines are skipped.
// * first_offset is a zero-based BYTE offset into only the selected first line.
// * subsequent lines are consumed whole; LF and CRLF accepted.
// * every consumed record is validated in its entirety (even beyond count).
// * no blank consumed records and no skipping bad records.
// * exactly 'count' output words, at most the 1024-word RAM capacity.
// * extra valid tokens on the last consumed record are ignored.
// * errors discard ALL staged words; 'exact' and 'truncated' are commit-ready.
// * 'truncated' applies only to STORED words, not surplus validated tokens.
// Not a historical assertion about a3, card zones, punch framing or errors.
inline result collect(std::istream& stream, std::size_t start_line,
                      std::size_t first_offset, std::size_t count) {
    if (count == 0 || count > 02000u)
        return {status::invalid_count, {}};
    if (!stream)
        return {status::unavailable_stream, {}};

    std::string line;
    for (std::size_t row = 0; row < start_line; ++row) {
        if (!std::getline(stream, line))
            return {stream.bad() ? status::read_error : status::missing_start_line, {}};
    }

    std::vector<std::uint64_t> staged;
    staged.reserve(count);
    bool any_truncated = false;
    bool first = true;
    while (staged.size() < count) {
        if (!std::getline(stream, line)) {
            return {stream.bad() ? status::read_error :
                    (first ? status::missing_start_line : status::short_input), {}};
        }
        // Portable normalization for std::getline on LF or CRLF text files.
        // CR anywhere else must be rejected by the strict ASCII parser.
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (first) {
            if (first_offset > line.size())
                return {status::invalid_first_offset, {}};
            line.erase(0, first_offset);
            first = false;
        }
        const auto parsed = kyiv_decimal_ascii::parse_record(line);
        if (parsed.state == kyiv_decimal_ascii::record_status::empty)
            return {status::empty_record, {}};
        if (parsed.state == kyiv_decimal_ascii::record_status::invalid_token)
            return {status::invalid_token, {}};
        if (parsed.state == kyiv_decimal_ascii::record_status::nonexact)
            return {status::nonexact, {}};
        const auto n = std::min(count - staged.size(), parsed.values.size());
        for (std::size_t i = 0; i < n; ++i) {
            any_truncated |= parsed.values[i].state == kyiv_decimal_ascii::status::truncated;
            staged.push_back(parsed.values[i].word);
        }
    }
    return {any_truncated ? status::truncated : status::exact,
            std::move(staged)};
}

} // namespace kyiv_decimal_input_plan

#endif // KYIV_DECIMAL_INPUT_PLAN_H
