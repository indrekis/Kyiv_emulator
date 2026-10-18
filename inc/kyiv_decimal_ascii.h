#ifndef KYIV_DECIMAL_ASCII_H
#define KYIV_DECIMAL_ASCII_H

// ISA-07 D10-D HOST_POLICY: standalone ASCII presentation of ten fractional
// BCD digits and a separate sign. NOT a historical punched-card encoding.
// D10-F3: provisional truncation via D10-F2; text grammar is still HOST_POLICY.
#include "kyiv_decimal_trunc.h"
#include <cstdint>
#include <string_view>
#include <utility>
#include <vector>

namespace kyiv_decimal_ascii {

// Keep legacy nonexact enumerator for compatibility; valid decimals now use truncated.
enum class status { exact, nonexact, invalid_token, truncated };
struct result {
    status state;
    std::uint64_t packed_bcd;
    bool negative;
    std::uint64_t word;
};

// HOST_POLICY token grammar, ASCII only:
//   [+-]? ( [0-9]{10} | 0.[0-9]{10} )
// The ten digits are fractional positions (no integer decimal part).
// No whitespace inside a token, partial conversion, exponent or locale rules.
inline result parse_token(std::string_view token) noexcept {
    bool negative = false;
    if (!token.empty() && (token.front() == '+' || token.front() == '-')) {
        negative = token.front() == '-';
        token.remove_prefix(1);
    }
    if (token.size() == 12 && token[0] == '0' && token[1] == '.') {
        token.remove_prefix(2);
    } else if (token.size() != 10) {
        return {status::invalid_token, 0, false, 0};
    }
    std::uint64_t packed = 0;
    for (const char digit : token) {
        if (digit < '0' || digit > '9')
            return {status::invalid_token, 0, false, 0};
        packed = (packed << 4) | static_cast<unsigned>(digit - '0');
    }
    // D10-F2 mathematical truncation is PROVISIONAL, not a hardware oracle.
    const auto converted = kyiv_decimal_trunc::convert_bcd10(packed, negative);
    if (converted.state == kyiv_decimal_trunc::status::exact)
        return {status::exact, packed, negative, converted.word};
    if (converted.state == kyiv_decimal_trunc::status::truncated)
        return {status::truncated, packed, negative, converted.word};
    // Defensive: grammatical digits can never produce invalid BCD.
    return {status::invalid_token, 0, false, 0};
}

enum class record_status { exact, empty, invalid_token, nonexact, truncated };
struct record_result {
    record_status state;
    std::vector<result> values;
};

// HOST_POLICY record splitting ONLY: one already-extracted text record,
// SP and TAB separators, leading/trailing/repeated separators allowed.
// All-or-nothing: rejected records return NO values for a caller to store.
// LF/CRLF framing, historical card zones and source line selection are OPEN.
inline record_result parse_record(std::string_view record) {
    std::vector<result> values;
    bool any_truncated = false;
    std::size_t i = 0;
    while (i < record.size()) {
        while (i < record.size() && (record[i] == ' ' || record[i] == '\t'))
            ++i;
        if (i == record.size()) break;
        const std::size_t begin = i;
        while (i < record.size() && record[i] != ' ' && record[i] != '\t')
            ++i;
        const auto value = parse_token(record.substr(begin, i - begin));
        if (value.state == status::invalid_token)
            return {record_status::invalid_token, {}};
        if (value.state == status::nonexact)
            return {record_status::nonexact, {}};
        any_truncated |= value.state == status::truncated;
        values.push_back(value);
    }
    if (values.empty()) return {record_status::empty, {}};
    return {any_truncated ? record_status::truncated : record_status::exact,
            std::move(values)};
}

} // namespace kyiv_decimal_ascii

#endif // KYIV_DECIMAL_ASCII_H
