#ifndef KYIVEMU_D14C2H3B1_PROVISION_V1_H
#define KYIVEMU_D14C2H3B1_PROVISION_V1_H

// D14-C2-H3/B1: create-new-only HOST_POLICY for empty KYIVDRM1 images.
// Deliberately separate from CPU attachment and B3's replace-capable save_atomic.
// Atomic no-clobber publication uses filesystem::create_hard_link on a SAME-
// DIRECTORY pre-written file. Fails closed where hard links are unsupported.
// This is not a crash-durability, adversarial-path, or historical-drum oracle.
#include "kyiv_drum_persistence.h"
#include <array>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <random>
#include <string>
#include <system_error>
#include <utility>

namespace kyiv_drum_provision_v1 {
namespace fs = std::filesystem;
using kyiv_drum_media::geometry;
using kyiv_drum_media::logical_media;
using kyiv_drum_media::media_error;

struct creation_receipt {
    std::size_t slots = 0;
    std::size_t image_bytes = 0;
};

inline bool occupied(const fs::path& path) {
    std::error_code ec;
    const auto stat = fs::symlink_status(path, ec); // catches dangling symlinks
    if (!ec) return stat.type() != fs::file_type::not_found;
    if (ec == std::errc::no_such_file_or_directory) return false;
    throw media_error("IMAGE_PATH_STATUS_FAILED");
}

inline creation_receipt create_new(const fs::path& image, geometry explicit_geometry) {
    if (image.empty() || image.filename().empty() ||
        image.filename() == "." || image.filename() == "..")
        throw media_error("INVALID_IMAGE_PATH");

    // All validation and encoding precedes filesystem changes.
    const logical_media empty(std::move(explicit_geometry));
    const auto serialized = kyiv_drum_persistence::encode(empty);
    if (occupied(image)) throw media_error("IMAGE_EXISTS");

    const fs::path parent = image.has_parent_path() ? image.parent_path() : fs::path(".");
    std::error_code ec;
    if (!fs::is_directory(parent, ec) || ec)
        throw media_error("IMAGE_PARENT_INVALID");

    // A high-entropy, same-directory candidate; B3 writes to this name via
    // its existing save_atomic() routine. No pre-existing name may be reused.
    // Non-adversarial single-host operation only; hostile path races are OPEN.
    std::random_device entropy;
    std::string random_hex;
    constexpr char alphabet[] = "0123456789abcdef";
    for (int i = 0; i < 4; ++i) {
        const std::uint32_t raw = (std::uint32_t(entropy()) << 16) ^
                                  std::uint32_t(entropy());
        for (int j = 7; j >= 0; --j)
            random_hex.push_back(alphabet[(raw >> (4*j)) & 15]);
    }
    const auto stamp = std::chrono::steady_clock::now().time_since_epoch().count();
    fs::path temporary;
    bool saved = false;
    for (unsigned trial = 0; trial < 16; ++trial) {
        temporary = parent / (image.filename().string() + ".provision." +
                              random_hex + "." + std::to_string(stamp) +
                              "." + std::to_string(trial));
        if (!occupied(temporary)) { saved = true; break; }
    }
    if (!saved) throw media_error("PROVISION_TEMP_NAME_FAILED");

    try {
        kyiv_drum_persistence::save_atomic(empty, temporary);
        ec.clear();
        // POSIX link/Windows NTFS CreateHardLinkW: publication is atomic and
        // FAILS if the destination exists, even for a dangling symlink.
        fs::create_hard_link(temporary, image, ec);
        if (ec) {
            if (occupied(image)) throw media_error("IMAGE_EXISTS");
            throw media_error("ATOMIC_CREATE_UNAVAILABLE");
        }
    } catch (...) {
        std::error_code ignored;
        fs::remove(temporary, ignored);
        throw;
    }
    // Target now owns a hard link to the same bytes, independent of this name.
    std::error_code ignored;
    fs::remove(temporary, ignored); // best effort; never roll back a published image
    return {empty.capacity(), serialized.size()};
}
} // namespace kyiv_drum_provision_v1
#endif
