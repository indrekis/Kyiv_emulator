// Standalone probe; uses genuine C1b/B1/B2 components, NEVER Kyiv_t.
#include "kyiv_drum_host_address_v1.h"
#include "kyiv_drum_group_transfer.h"
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

int main() {
    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream input(line);
        std::uint64_t word = 0;
        std::size_t pinned = 0, drums = 0, tracks = 0, slots = 0, count = 0;
        unsigned mode = 0;
        std::string extra;
        if (!(input >> word >> pinned >> drums >> tracks >> slots >> count >> mode) ||
            (input >> extra)) {
            std::cout << "ERR BAD_PROTOCOL\n";
            continue;
        }
        try {
            const auto d = kyiv_drum_prepare::decode(word);
            kyiv_drum_media::logical_media media(
                {"host-c2h1-explicit", drums, tracks, slots});
            const auto p = kyiv_drum_host_address::resolve(
                media, d, mode == 3
                    ? static_cast<kyiv_drum_host_address::policy>(99)
                    : kyiv_drum_host_address::policy::a3_linear_v1,
                static_cast<unsigned>(pinned));
            if (mode == 0 || mode == 3) {
                std::cout << "OK " << static_cast<unsigned>(p.requested)
                          << ' ' << p.first.drum << ' ' << p.first.track
                          << ' ' << p.first.slot << '\n';
            } else if (mode == 1 || mode == 4) {
                std::vector<kyiv_drum_media::raw_word_t> words(count);
                for (std::size_t i = 0; i < count; ++i)
                    words[i] = (i % 2 == 0)
                        ? kyiv_drum_media::sign_bit
                        : static_cast<kyiv_drum_media::raw_word_t>(i);
                if (mode == 4 && !words.empty())
                    words.back() = kyiv_drum_media::word_mask + 1;
                try {
                    const auto span = kyiv_drum_media::write_group(
                        media, p.first, words);
                    const auto readback = kyiv_drum_media::read_group(
                        media, p.first, count);
                    if (readback != words || media.written_count() != count)
                        throw std::logic_error("ROUNDTRIP_BROKEN");
                    std::cout << "OK " << static_cast<unsigned>(p.requested)
                              << ' ' << p.first.drum << ' ' << p.first.track
                              << ' ' << p.first.slot << ' ' << span.last.track
                              << ' ' << span.last.slot << ' ' << count << '\n';
                } catch (const kyiv_drum_media::media_error& e) {
                    if (media.written_count() != 0)
                        throw std::logic_error("NONATOMIC_WRITE");
                    std::cout << "ERR " << e.what() << " UNCHANGED=1\n";
                }
            } else if (mode == 2) {
                try {
                    (void)kyiv_drum_media::read_group(media, p.first, count);
                    std::cout << "ERR UNEXPECTED_READ_SUCCESS\n";
                } catch (const kyiv_drum_media::media_error& e) {
                    if (media.written_count() != 0)
                        throw std::logic_error("READ_CHANGED_MEDIA");
                    std::cout << "ERR " << e.what() << " UNCHANGED=1\n";
                }
            } else {
                std::cout << "ERR BAD_MODE\n";
            }
        } catch (const kyiv_drum_prepare::decode_error& e) {
            std::cout << "ERR " << e.what() << '\n';
        } catch (const kyiv_drum_media::media_error& e) {
            std::cout << "ERR " << e.what() << '\n';
        }
    }
}
