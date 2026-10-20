#ifndef KYIVEMU_D14C2H1_HOST_ADDRESS_V1_H
#define KYIVEMU_D14C2H1_HOST_ADDRESS_V1_H

// ISA-07 D14-C2-H1: opt-in HOST_POLICY for limited integration experiments.
// NOT a historical interpretation of drum track/slot registers.
// C1b's qualified selector is accepted ONLY when raw a2 is exactly 0100,
// 0200 or 0300 octal. All other raw a2 values are rejected explicitly.
// Raw a3 is an EXPERIMENTAL zero-based LINEAR slot within that drum.
// No hidden historical geometry or implicit address policy.
#include "kyiv_drum_prepare_decode.h"
#include "kyiv_drum_logical_media.h"
#include <cstddef>
#include <cstdint>

namespace kyiv_drum_host_address {

enum class policy : unsigned { a3_linear_v1 = 1 };

struct prepared_address {
    kyiv_drum_prepare::direction requested;
    kyiv_drum_media::coordinate first;
    std::uint16_t raw_a2;
    std::uint16_t raw_a3;
};

// Does not mutate media or CPU; caller must explicitly select HOST policy.
// Throws media_error codes for HOST_POLICY failures; C1b checks raw opcode,
// direction and qualified numeric drum selector separately.
inline prepared_address resolve(const kyiv_drum_media::logical_media& media,
                                const kyiv_drum_prepare::decoded_prepare& d,
                                policy selected, unsigned pinned_drum_number) {
    using kyiv_drum_media::media_error;
    if (selected != policy::a3_linear_v1)
        throw media_error("UNSUPPORTED_HOST_POLICY");
    const auto& g = media.profile();
    if (g.drums != 3)
        throw media_error("HOST_REQUIRES_THREE_DRUMS");
    if (d.modify_a1 || d.modify_a2 || d.modify_a3)
        throw media_error("UNQUALIFIED_MODIFICATION_MARK");
    if (d.raw_a1 > 1 || d.drum_number < 1 || d.drum_number > 3 ||
        d.raw_a2 != (d.drum_number << 6))
        throw media_error("UNQUALIFIED_TRACK_MAPPING");

    // Caller locks the intended drum outside the ambiguous command word.
    // Example: original 0100 + 0100 collides with initial 0200.
    if (pinned_drum_number < 1 || pinned_drum_number > 3)
        throw media_error("HOST_INVALID_DRUM_LOCK");
    if (d.drum_number != pinned_drum_number)
        throw media_error("HOST_DRUM_LOCK_MISMATCH");

    // B1 validated the product g.tracks_per_drum * g.slots_per_track.
    const std::size_t size_per_drum = g.tracks_per_drum * g.slots_per_track;
    const std::size_t linear = d.raw_a3;
    if (linear >= size_per_drum)
        throw media_error("HOST_POSITION_OUT_OF_RANGE");

    return {
        d.requested,
        {static_cast<std::size_t>(d.drum_number - 1),
         linear / g.slots_per_track,
         linear % g.slots_per_track},
        d.raw_a2, d.raw_a3
    };
}

} // namespace kyiv_drum_host_address
#endif // KYIVEMU_D14C2H1_HOST_ADDRESS_V1_H
