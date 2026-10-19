#ifndef KYIVEMU_D14C1B_PREPARE_DECODE_H
#define KYIVEMU_D14C1B_PREPARE_DECODE_H

// ISA-07 D14-C1b: partial HOST-independent decoder for opcode 025.
// GY62 pp. 15, 59, 124, 177-179.
// Not a completed physical address decoder; HARDWARE_ORACLE=0.
#include <cstdint>
#include <stdexcept>

namespace kyiv_drum_prepare {

enum class direction : unsigned {
    read = 0,
    write = 1
};

class decode_error : public std::runtime_error {
public:
    explicit decode_error(const char* s) : std::runtime_error(s) {}
};

struct decoded_prepare {
    direction requested;
    std::uint16_t raw_a1;
    std::uint16_t raw_a2;
    std::uint16_t raw_a3;
    unsigned drum_number;
    std::uint16_t unresolved_ii_bits;
    bool modify_a1;
    bool modify_a2;
    bool modify_a3;
};

inline decoded_prepare decode(std::uint64_t word) {
    constexpr std::uint64_t mask41 =
        (std::uint64_t{1} << 41) - 1;

    if ((word & ~mask41) != 0)
        throw decode_error("INVALID_WORD");

    if (((word >> 36) & 037u) != 025u)
        throw decode_error("INVALID_OPCODE");

    const unsigned a1 = (word >> 24) & 03777u;
    const unsigned a2 = (word >> 12) & 03777u;
    const unsigned a3 = word & 03777u;

    if (a1 > 1)
        throw decode_error("INVALID_DIRECTION");

    // SOURCE_DERIVED: third octal digit of the raw II address.
    const unsigned drum = (a2 >> 6) & 07u;

    if (drum < 1 || drum > 3)
        throw decode_error("INVALID_DRUM");

    // NOT a track number. The physical mapping is unresolved.
    const unsigned unresolved = a2 & 03077u;

    return {
        a1 == 0 ? direction::read : direction::write,
        static_cast<std::uint16_t>(a1),
        static_cast<std::uint16_t>(a2),
        static_cast<std::uint16_t>(a3),
        drum,
        static_cast<std::uint16_t>(unresolved),
        ((word >> 35) & 1u) != 0,
        ((word >> 23) & 1u) != 0,
        ((word >> 11) & 1u) != 0
    };
}

} // namespace kyiv_drum_prepare
#endif
