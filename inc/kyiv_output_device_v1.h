#ifndef KYIV_H24_H10_OUTPUT_DEVICE_V1_H
#define KYIV_H24_H10_OUTPUT_DEVICE_V1_H
// H24/H10 opt-in candidate: side-effect-free HOST representations of 41-bit words.
// Opt-in candidate will be wired into opcode22; NOT an historical printer driver.
// Octal 14-digit shape and BCD 10-digit shape come from GY1962 pp.6-8,16.
// ASCII sign/spacing, record separation and error signaling are HOST_POLICY.
#include <cstdint>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace kyiv_h10_output {
constexpr std::uint64_t sign_bit = std::uint64_t{1} << 40;
constexpr std::uint64_t magnitude_mask = sign_bit - 1;
constexpr std::uint64_t max_word = (sign_bit << 1) - 1;
enum class profile { legacy_decimal_file, octal_14_preview, bcd_10_preview, punch_unknown };
struct selection {
    profile mode = profile::legacy_decimal_file;
};
class device_adapter {
    selection external_{};
public:
    void operator_select(selection next) noexcept { external_ = next; }
    selection current() const noexcept { return external_; }
    std::vector<std::string> render_tokens(const std::vector<std::uint64_t>& words) const {
        // Validate complete transaction, then render. Never writes to filesystem.
        std::vector<std::string> tokens;
        tokens.reserve(words.size());
        for (const auto w : words) {
            if (w > max_word) throw std::runtime_error("H10_WORD_NOT_41_BITS");
            if (external_.mode == profile::punch_unknown)
                throw std::runtime_error("H10_PUNCH_ENCODING_UNKNOWN");
            if (external_.mode == profile::legacy_decimal_file) {
                const std::uint64_t magnitude = w & magnitude_mask;
                tokens.push_back(((w & sign_bit) && magnitude != 0 ? "-" : "")
                                 + std::to_string(magnitude));
            } else if (external_.mode == profile::octal_14_preview) {
                std::ostringstream s;
                s << std::oct << std::setfill('0') << std::setw(14) << w;
                tokens.push_back(s.str());
            } else if (external_.mode == profile::bcd_10_preview) {
                std::string s;
                s.reserve(11);
                s.push_back((w & sign_bit) ? '-' : '+');
                for (int nib=9; nib>=0; --nib) {
                    const auto digit = (w >> (4*nib)) & 0xFULL;
                    if (digit >= 10) throw std::runtime_error("H10_INVALID_BCD_DIGIT");
                    s.push_back(static_cast<char>('0' + digit));
                }
                tokens.push_back(s);
            } else {
                throw std::runtime_error("H10_UNKNOWN_PROFILE");
            }
        }
        return tokens;
    }
    std::string host_preview_bytes(const std::vector<std::uint64_t>& words) const {
        const auto tokens = render_tokens(words);
        std::string bytes;
        for (const auto& token : tokens) {
            bytes += token;
            bytes += (external_.mode == profile::legacy_decimal_file ? " " : "\n");
        }
        return bytes;
    }
};
} // namespace kyiv_h10_output
#endif
