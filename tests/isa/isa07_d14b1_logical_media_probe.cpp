// ISA-07 D14-B1: standalone instrument; NO Kyiv_t or src/main.cpp.
// The Python sandbox supplies independent commands and expected observations.
#include "kyiv_drum_logical_media.h"
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <limits>
#include <memory>
#include <sstream>
#include <string>

using kyiv_drum_media::coordinate;
using kyiv_drum_media::geometry;
using kyiv_drum_media::logical_media;
using kyiv_drum_media::media_error;

namespace {
// The Windows narrow argv conversion can drop non-ASCII code points.
// This probe-only ASCII transport carries exact UTF-8 bytes to the real
// logical_media validator. It is not a production API or image format.
int hex_nibble(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    throw media_error("INVALID_PROFILE");
}
std::string decode_profile_hex(const std::string& hex) {
    if (hex.size() % 2 != 0) throw media_error("INVALID_PROFILE");
    std::string decoded;
    decoded.reserve(hex.size() / 2);
    for (std::size_t i = 0; i < hex.size(); i += 2)
        decoded.push_back(static_cast<char>(
            (hex_nibble(hex[i]) << 4) | hex_nibble(hex[i + 1])));
    return decoded;
}
std::string run(logical_media& image, std::unique_ptr<logical_media>& snapshot,
                const std::string& command) {
    std::istringstream in(command);
    std::string op;
    in >> op;
    try {
        std::size_t d = 0, t = 0, s = 0;
        std::uint64_t raw = 0;
        if (op == "COUNT") return "COUNT " + std::to_string(image.written_count());
        if (op == "CAP") return "CAP " + std::to_string(image.capacity());
        if (op == "SNAP") {
            snapshot = std::make_unique<logical_media>(image);
            return "SNAP " + std::to_string(snapshot->written_count());
        }
        if (op == "COUNTSNAP") {
            if (!snapshot) return "ERROR NO_SNAPSHOT";
            return "COUNTSNAP " + std::to_string(snapshot->written_count());
        }
        if (op == "GETSNAP" || op == "GET" || op == "PUTSNAP" ||
            op == "PUT" || op == "ERASE" || op == "ERASESNAP") {
            if (!(in >> d >> t >> s)) return "ERROR BAD_PROTOCOL";
            coordinate at{d, t, s};
            logical_media* ptr = &image;
            if (op == "GETSNAP" || op == "PUTSNAP" || op == "ERASESNAP") {
                if (!snapshot) return "ERROR NO_SNAPSHOT";
                ptr = snapshot.get();
            }
            if (op == "PUT" || op == "PUTSNAP") {
                if (!(in >> raw)) return "ERROR BAD_PROTOCOL";
                std::string remainder;
                if (in >> remainder) return "ERROR BAD_PROTOCOL";
                ptr->store(at, raw);
                return "PUT OK";
            }
            std::string remainder;
            if (in >> remainder) return "ERROR BAD_PROTOCOL";
            if (op == "ERASE" || op == "ERASESNAP") {
                ptr->erase(at);
                return "ERASE OK";
            }
            const auto cell = ptr->inspect(at);
            if (!cell.written) return "CELL UNWRITTEN";
            return "CELL WRITTEN " + std::to_string(cell.word);
        }
        return "ERROR BAD_PROTOCOL";
    } catch (const media_error& e) {
        return std::string("ERROR ") + e.what();
    }
}
} // namespace

int main(int argc, char** argv) {
    if (argc != 5 && argc != 6) return 2;
    const bool hex_profile = argc == 6;
    if (hex_profile && std::string(argv[1]) != "--profile-hex") return 2;
    const int i = hex_profile ? 3 : 2;
    try {
        const auto drums = static_cast<std::size_t>(std::stoull(argv[i]));
        const auto tracks = static_cast<std::size_t>(std::stoull(argv[i + 1]));
        const auto slots = static_cast<std::size_t>(std::stoull(argv[i + 2]));
        try {
            const std::string profile = hex_profile ?
                decode_profile_hex(argv[2]) : std::string(argv[1]);
            logical_media image(geometry{profile, drums, tracks, slots});
            std::cout << "D14B1-INIT OK " << image.capacity() << '\n';
            std::unique_ptr<logical_media> snapshot;
            std::string line;
            for (std::size_t n = 0; std::getline(std::cin, line); ++n)
                std::cout << "D14B1-RESULT " << n << ' '
                          << run(image, snapshot, line) << '\n';
        } catch (const media_error& e) {
            std::cout << "D14B1-INIT ERROR " << e.what() << '\n';
        }
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D14B1-PROTOCOL-ERROR " << e.what() << '\n';
        return 3;
    }
}
