// Standalone test instrument, without Kyiv_t or logical_media.
#include "kyiv_drum_prepare_decode.h"
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>

int main() {
    std::string line;

    while (std::getline(std::cin, line)) {
        std::istringstream input(line);
        std::uint64_t word = 0;
        std::uint64_t modifier = 0;
        std::string extra;

        if (!(input >> word >> modifier) || (input >> extra)) {
            std::cout << "ERR BAD_PROTOCOL\n";
            continue;
        }

        // Deliberately ignored: decode must use raw fields.
        (void)modifier;

        try {
            const auto d = kyiv_drum_prepare::decode(word);

            std::cout
                << "OK "
                << static_cast<unsigned>(d.requested) << ' '
                << d.drum_number << ' '
                << d.raw_a2 << ' '
                << d.raw_a3 << ' '
                << d.unresolved_ii_bits << ' '
                << d.modify_a1 << ' '
                << d.modify_a2 << ' '
                << d.modify_a3 << '\n';

        } catch (const kyiv_drum_prepare::decode_error& e) {
            std::cout << "ERR " << e.what() << '\n';
        }
    }
}
