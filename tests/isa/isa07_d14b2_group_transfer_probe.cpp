// D14-B2 genuine standalone group API, no Kyiv_t and no opcode decoder.
// The Python controller independently predicts all responses and whole image.
#include "kyiv_drum_group_transfer.h"
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace kyiv_drum_media;

namespace {
std::string perform(logical_media& media, const std::string& line) {
    std::istringstream input(line);
    std::string op;
    input >> op;
    try {
        if (op == "COUNT") {
            if (input >> op) return "BAD_PROTOCOL";
            return "COUNT " + std::to_string(media.written_count());
        }
        if (op == "CAP") {
            if (input >> op) return "BAD_PROTOCOL";
            return "CAP " + std::to_string(media.capacity());
        }
        if (op == "WRITE" || op == "READ" || op == "GET" || op == "ERASE") {
            std::size_t d, t, s;
            if (!(input >> d >> t >> s)) return "BAD_PROTOCOL";
            const coordinate at{d, t, s};
            if (op == "GET") {
                if (input >> op) return "BAD_PROTOCOL";
                auto c = media.inspect(at);
                return c.written ? ("CELL " + std::to_string(c.word)) : "UNWRITTEN";
            }
            if (op == "ERASE") {
                if (input >> op) return "BAD_PROTOCOL";
                media.erase(at);
                return "OK";
            }
            std::size_t count;
            if (!(input >> count)) return "BAD_PROTOCOL";
            if (op == "READ") {
                if (input >> op) return "BAD_PROTOCOL";
                const auto values = read_group(media, at, count);
                std::ostringstream result;
                result << "WORDS";
                for (auto value : values) result << ' ' << value;
                return result.str();
            }
            // Requesting arbitrarily many words cannot allocate unbounded
            // memory in the test protocol. The API receives only parsed data.
            if (count > media.capacity()) return "BAD_PROTOCOL";
            std::vector<raw_word_t> words;
            words.reserve(count);
            for (std::size_t i = 0; i < count; ++i) {
                raw_word_t w;
                if (!(input >> w)) return "BAD_PROTOCOL";
                words.push_back(w);
            }
            if (input >> op) return "BAD_PROTOCOL";
            const auto span = write_group(media, at, words);
            return "OK " + std::to_string(span.last.drum) + " " +
                std::to_string(span.last.track) + " " +
                std::to_string(span.last.slot);
        }
        return "BAD_PROTOCOL";
    } catch (const media_error& e) {
        return std::string("ERROR ") + e.what();
    }
}
} // namespace

int main(int argc, char** argv) {
    if (argc != 5) return 2;
    try {
        // Sandboxed ASCII profile names, no Windows-Unicode argv conversion.
        geometry g{argv[1], static_cast<std::size_t>(std::stoull(argv[2])),
                   static_cast<std::size_t>(std::stoull(argv[3])),
                   static_cast<std::size_t>(std::stoull(argv[4]))};
        logical_media media(g);
        std::cout << "D14B2-INIT " << media.capacity() << '\n';
        std::string line;
        std::size_t n = 0;
        while (std::getline(std::cin, line)) {
            std::cout << "D14B2-RESULT " << n << ' ' << perform(media, line)
                      << '\n';
            ++n;
        }
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D14B2-PROBE-ERROR " << e.what() << '\n';
        return 3;
    }
}
