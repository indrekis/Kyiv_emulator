#ifndef KYIVEMU_D14C2H2_TRANSACTION_V1_H
#define KYIVEMU_D14C2H2_TRANSACTION_V1_H

// D14-C2-H2/P1. An opt-in HOST_POLICY *session*, not Kyiv_t integration.
// Source: the existing B1/B2/B3 storage/persistence and C1b/C2-H1 mapping.
// Both independent prepare states start INVALID. No implicit image creation.
// A write is staged in a private media copy, persisted, then committed to RAM
// using noexcept move assignment. No crash durability or concurrent writers.
#include "kyiv_drum_host_address_v1.h"
#include "kyiv_drum_group_transfer.h"
#include "kyiv_drum_persistence.h"
#include <cstdint>
#include <filesystem>
#include <type_traits>
#include <utility>
#include <vector>

namespace kyiv_drum_transaction_v1 {
namespace media = kyiv_drum_media;
namespace persist = kyiv_drum_persistence;
namespace host = kyiv_drum_host_address;
namespace prep = kyiv_drum_prepare;

class session {
public:
    session(std::filesystem::path existing_image,
            media::geometry expected_geometry, host::policy selected,
            unsigned pinned_drum)
        : file_(std::move(existing_image)),
          image_(persist::load(file_)),
          policy_(selected), pin_(pinned_drum) {
        if (!persist::same_geometry(image_.profile(), expected_geometry))
            throw media::media_error("GEOMETRY_MISMATCH");
        if (selected != host::policy::a3_linear_v1)
            throw media::media_error("UNSUPPORTED_HOST_POLICY");
        if (pinned_drum < 1 || pinned_drum > 3)
            throw media::media_error("HOST_INVALID_DRUM_LOCK");
        if (image_.profile().drums != 3)
            throw media::media_error("HOST_REQUIRES_THREE_DRUMS");
    }

    // Validation is complete before either selected state is changed.
    // Read and write preparation are distinct, persistent until replaced.
    host::prepared_address prepare(std::uint64_t raw_instruction) {
        const auto decoded = prep::decode(raw_instruction);
        const auto resolved = host::resolve(image_, decoded, policy_, pin_);
        if (resolved.requested == prep::direction::read)
            read_ = {true, resolved.first};
        else
            write_ = {true, resolved.first};
        return resolved;
    }

    bool read_prepared() const noexcept { return read_.valid; }
    bool write_prepared() const noexcept { return write_.valid; }
    const media::logical_media& snapshot() const noexcept { return image_; }
    const std::filesystem::path& image_path() const noexcept { return file_; }

    // Strong guarantee on all exceptions from B2 validation or B3 saving,
    // within a single process under the stated file system assumptions.
    media::transfer_span write_words(const std::vector<media::raw_word_t>& words) {
        if (!write_.valid) throw media::media_error("UNPREPARED_WRITE");
        // The B1 copy is an intentional transaction staging cost, not a
        // change to B2's allocation-free group commit on one media object.
        media::logical_media staged = image_;
        const auto span = media::write_group(staged, write_.first, words);
        persist::save_atomic(staged, file_);
        static_assert(std::is_nothrow_move_assignable<media::logical_media>::value,
                      "In-memory commit after successful rename must not throw");
        image_ = std::move(staged);
        return span;
    }

    // No read side effects; caller must prevalidate the whole RAM destination
    // and the eventual C/K branch before committing anything to Kyiv_t.
    std::vector<media::raw_word_t> read_words(std::size_t count) const {
        if (!read_.valid) throw media::media_error("UNPREPARED_READ");
        return media::read_group(image_, read_.first, count);
    }

private:
    struct prepared_state {
        bool valid = false;
        media::coordinate first{0, 0, 0};
    };
    std::filesystem::path file_;
    media::logical_media image_;
    host::policy policy_;
    unsigned pin_;
    prepared_state read_;
    prepared_state write_;
};
} // namespace kyiv_drum_transaction_v1
#endif
