#ifndef KYIVEMU_D14C2H3A1_CLI_V1_H
#define KYIVEMU_D14C2H3A1_CLI_V1_H

// D14-C2-H3/A1: PURE CLI suffix parser, opt-in HOST_POLICY, NOT historical.
// Accepted suffix: [--experimental-drum PATH PROFILE TRACKS SLOTS PIN]
//                  [--block-overflow-stop]
// The two suffixes have a strict order, preserving existing legacy positionals.
// This parser NEVER opens, creates, attaches, or mutates an image or CPU.
#include "kyiv_drum_logical_media.h"
#include <cstddef>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>

namespace kyiv_drum_cli_v1 {

class cli_error : public std::runtime_error {
public:
    explicit cli_error(const char* code) : std::runtime_error(code) {}
};

struct configuration {
    std::string existing_image;
    kyiv_drum_media::geometry expected_geometry;
    unsigned pinned_drum = 0;
};

struct parsed_suffix {
    int legacy_argc = 0;
    bool block_overflow_stop = false;
    std::optional<configuration> drum;
};

// Decimal-only integers. Reject signed forms, whitespace, overflow, and junk.
inline std::size_t decimal(const std::string& text) {
    if (text.empty()) throw cli_error("CLI_INVALID_DECIMAL");
    std::size_t result = 0;
    for (const unsigned char ch : text) {
        if (ch < '0' || ch > '9') throw cli_error("CLI_INVALID_DECIMAL");
        const auto d = static_cast<std::size_t>(ch - '0');
        if (result > (std::numeric_limits<std::size_t>::max() - d) / 10)
            throw cli_error("CLI_INVALID_DECIMAL");
        result = result * 10 + d;
    }
    if (!result) throw cli_error("CLI_ZERO_VALUE");
    return result;
}

inline parsed_suffix parse(int argc, const char* const argv[]) {
    if (argc < 1 || !argv) throw cli_error("CLI_INVALID_ARGV");
    for (int i = 0; i < argc; ++i)
        if (!argv[i]) throw cli_error("CLI_INVALID_ARGV");
    parsed_suffix out;
    int end = argc;
    if (end > 1 && std::string(argv[end - 1]) == "--block-overflow-stop") {
        out.block_overflow_stop = true;
        --end;
    }
    // The marker and its five arguments must occupy the FINAL six positions.
    if (end >= 7 && std::string(argv[end - 6]) == "--experimental-drum") {
        const std::string path = argv[end - 5];
        const std::string profile = argv[end - 4];
        if (path.empty() || path == "--experimental-drum" ||
            path == "--block-overflow-stop")
            throw cli_error("CLI_INVALID_IMAGE_PATH");
        const std::size_t tracks = decimal(argv[end - 3]);
        const std::size_t slots = decimal(argv[end - 2]);
        const std::size_t pin = decimal(argv[end - 1]);
        if (pin > 3) throw cli_error("CLI_INVALID_DRUM_LOCK");
        // Delegate profile/geometry validation to existing B1; it also enforces
        // the 1,000,000-slot HOST cap. Never invent a historical default.
        kyiv_drum_media::geometry g{profile, 3, tracks, slots};
        const kyiv_drum_media::logical_media validation(g);
        (void)validation;
        out.drum = configuration{path, std::move(g),
                                 static_cast<unsigned>(pin)};
        end -= 6;
    }
    // Reject any marker in the remaining argv, including incomplete suffixes.
    for (int i = 1; i < end; ++i) {
        if (std::string(argv[i]) == "--experimental-drum")
            throw cli_error("CLI_INCOMPLETE_EXPERIMENTAL_DRUM");
        if (std::string(argv[i]) == "--block-overflow-stop")
            throw cli_error("CLI_MISPLACED_OVERFLOW_FLAG");
    }
    out.legacy_argc = end;
    return out;
}

} // namespace kyiv_drum_cli_v1
#endif
