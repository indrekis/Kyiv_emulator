#ifndef KYIV_DRUM_OUTPUT_PLAN_H
#define KYIV_DRUM_OUTPUT_PLAN_H

// ISA-07 D13-B. HOST_POLICY: decimal textual drum output, NOT historical
// magnetic-drum encoding. Single-writer, single-process atomic replacement;
// neither fsync durability nor multi-writer synchronization is promised.
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <string>
#include <system_error>
#include <vector>

namespace kyiv_drum_output_plan {

enum class status {
    exact,
    invalid_count,
    invalid_word,
    temp_create_failed,
    temp_write_failed,
    replace_failed
};

inline const char* status_text(status s) {
    switch (s) {
    case status::exact:              return "EXACT";
    case status::invalid_count:      return "INVALID_COUNT";
    case status::invalid_word:       return "INVALID_WORD";
    case status::temp_create_failed: return "TEMP_CREATE_FAILED";
    case status::temp_write_failed:  return "TEMP_WRITE_FAILED";
    case status::replace_failed:     return "REPLACE_FAILED";
    }
    return "UNKNOWN";
}

struct plan {
    status state = status::invalid_count;
    std::string bytes;
};

// Sign-magnitude word: bit 40 is the sign, bits 0..39 the magnitude.
// Output tokens are unscaled signed decimal integers with a trailing space;
// this preserves existing positive-word formatting and additionally keeps -0.
inline plan prepare(const std::vector<std::uint64_t>& words) {
    constexpr std::uint64_t sign = (std::uint64_t{1} << 40);
    constexpr std::uint64_t valid_mask = (std::uint64_t{1} << 41) - 1;
    if (words.empty() || words.size() > 02000U)
        return {status::invalid_count, {}};
    std::string data;
    data.reserve(words.size() * 16);
    for (std::uint64_t w : words) {
        if ((w & ~valid_mask) != 0)
            return {status::invalid_word, {}};
        if ((w & sign) != 0)
            data.push_back('-');
        data += std::to_string(w & (sign - 1));
        data.push_back(' ');
    }
    return {status::exact, std::move(data)};
}

// Replace in the destination's directory to avoid cross-device rename.
// The temporary file is removed on EVERY unsuccessful return.
// A caller must serialize writers to the same destination (OPEN concurrency).
inline status commit(const std::filesystem::path& destination,
                     const std::string& data) {
    namespace fs = std::filesystem;
    std::error_code ec;
    fs::path temp;
    const auto nonce = std::chrono::steady_clock::now().time_since_epoch().count();
    // Host adapter works with a fixed relative path, but a suffix limits
    // accidental collisions across independent emulator invocations.
    for (unsigned attempt = 0; attempt < 64; ++attempt) {
        fs::path candidate = destination;
        candidate += ".d13b_tmp_" + std::to_string(nonce) + "_" +
                     std::to_string(attempt);
        ec.clear();
        const bool exists = fs::exists(candidate, ec);
        if (ec)
            return status::temp_create_failed;
        if (!exists) {
            temp = std::move(candidate);
            break;
        }
    }
    if (temp.empty())
        return status::temp_create_failed;

    struct temp_guard {
        fs::path path;
        ~temp_guard() {
            if (!path.empty()) {
                std::error_code ignored;
                fs::remove(path, ignored);
            }
        }
    } guard{temp};

    std::ofstream out(temp, std::ios::out | std::ios::binary | std::ios::trunc);
    if (!out.is_open())
        return status::temp_create_failed;
    out.write(data.data(), static_cast<std::streamsize>(data.size()));
    out.flush();
    const bool wrote = static_cast<bool>(out);
    out.close();
    if (!wrote || out.fail())
        return status::temp_write_failed;

    ec.clear();
    fs::rename(temp, destination, ec);
    if (ec)
        return status::replace_failed;
    guard.path.clear();
    return status::exact;
}

} // namespace kyiv_drum_output_plan
#endif
