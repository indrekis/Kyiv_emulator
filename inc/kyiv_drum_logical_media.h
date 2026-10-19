#ifndef KYIVEMU_D14B1_LOGICAL_MEDIA_H
#define KYIVEMU_D14B1_LOGICAL_MEDIA_H

// ISA-07 D14-B1. Logical, host-defined media storage; NOT a physical drum image.
// No dependency on Kyiv_t or any physical opcode-field encoding.
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace kyiv_drum_media {

using raw_word_t = std::uint64_t;
constexpr raw_word_t word_mask = (raw_word_t{1} << 41) - 1;
constexpr raw_word_t sign_bit = raw_word_t{1} << 40;

struct geometry {
    std::string profile_id; // MANDATORY host experiment identifier, never implicit.
    std::size_t drums;
    std::size_t tracks_per_drum;
    std::size_t slots_per_track;
};

// All indices are ZERO BASED within this host API. This is not an encoding
// of 25's raw a2/a3 fields or the historical numbering of physical tracks.
struct coordinate {
    std::size_t drum;
    std::size_t track;
    std::size_t slot;
};

struct cell {
    bool written = false;
    raw_word_t word = 0; // irrelevant unless written==true
};

class media_error : public std::runtime_error {
public:
    explicit media_error(const char* code) : std::runtime_error(code) {}
};

class logical_media {
public:
    explicit logical_media(geometry g)
        : geometry_(std::move(g)), cells_(validated_total(geometry_)) {}

    const geometry& profile() const noexcept { return geometry_; }
    std::size_t capacity() const noexcept { return cells_.size(); }
    std::size_t written_count() const noexcept { return written_count_; }

    // Distinguish the UNWRITTEN slot from a WRITTEN raw +0. No policy for
    // the historical read of unwritten media is selected at this layer.
    cell inspect(coordinate at) const { return cells_[offset(at)]; }

    // Each individual change either completes or leaves this object unchanged.
    // Atomic MULTI-word transfers are the responsibility of D14-B2.
    void store(coordinate at, raw_word_t raw) {
        const std::size_t i = offset(at);
        if ((raw & ~word_mask) != 0)
            throw media_error("INVALID_WORD");
        if (!cells_[i].written) ++written_count_;
        cells_[i] = {true, raw};
    }

    void erase(coordinate at) {
        const std::size_t i = offset(at);
        if (cells_[i].written) --written_count_;
        cells_[i] = {};
    }

private:
    // HOST_POLICY safety limit. Tested profiles 3x24x137 and 3x24x511 fit.
    static constexpr std::size_t max_host_slots = 1000000;

    static std::size_t validated_total(const geometry& g) {
        if (g.profile_id.empty() || g.profile_id.size() > 64)
            throw media_error("INVALID_PROFILE");
        for (unsigned char c : g.profile_id) {
            if (!((c >= 'a' && c <= 'z') ||
                  (c >= 'A' && c <= 'Z') ||
                  (c >= '0' && c <= '9') ||
                  c == '_' || c == '-' || c == '.'))
                throw media_error("INVALID_PROFILE");
        }
        if (!g.drums || !g.tracks_per_drum || !g.slots_per_track)
            throw media_error("INVALID_GEOMETRY");
        constexpr std::size_t max = std::numeric_limits<std::size_t>::max();
        if (g.drums > max / g.tracks_per_drum)
            throw media_error("GEOMETRY_OVERFLOW");
        const std::size_t dt = g.drums * g.tracks_per_drum;
        if (dt > max / g.slots_per_track)
            throw media_error("GEOMETRY_OVERFLOW");
        const std::size_t total = dt * g.slots_per_track;
        if (total > max_host_slots)
            throw media_error("HOST_CAPACITY_LIMIT");
        return total;
    }

    std::size_t offset(coordinate a) const {
        if (a.drum >= geometry_.drums)
            throw media_error("INVALID_DRUM");
        if (a.track >= geometry_.tracks_per_drum)
            throw media_error("INVALID_TRACK");
        if (a.slot >= geometry_.slots_per_track)
            throw media_error("INVALID_SLOT");
        // Arithmetic cannot overflow: validated_total checked the full product.
        return ((a.drum * geometry_.tracks_per_drum) + a.track) *
                   geometry_.slots_per_track + a.slot;
    }

    geometry geometry_;
    std::vector<cell> cells_;
    std::size_t written_count_ = 0;
};

} // namespace kyiv_drum_media

#endif // KYIVEMU_D14B1_LOGICAL_MEDIA_H
