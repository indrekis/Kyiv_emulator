// D14-C2-H3/C1: test-only injection of a failed B3 replacement.
// Never use on an actual user image. The independent runner creates a private
// temporary directory and a marker required by this executable.
#include "kyiv_drum_transaction_v1.h"
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
namespace drum = kyiv_drum_media;
namespace txn = kyiv_drum_transaction_v1;

static void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}

int main(int argc, char* argv[]) {
    try {
        if (argc == 2 && std::string(argv[1]) == "--self-test") {
            require((std::uint64_t{025} << 36) < (std::uint64_t{1} << 41),
                    "OPCODE_ENCODING");
            std::cout << "D14C2H3C1-PROBE-SELFTEST PASS\n";
            return 0;
        }
        if (argc != 2) throw std::runtime_error("USAGE: probe IMAGE");
        const fs::path image = fs::absolute(fs::path(argv[1]));
        const fs::path parent = image.parent_path();
        const fs::path marker = parent / ".h3c1-isolated-sandbox";
        {
            std::ifstream in(marker, std::ios::binary);
            std::string line;
            require(bool(in) && bool(std::getline(in, line)) &&
                    line == "H3C1-PRIVATE-TEST-ONLY", "ISOLATION_MARKER_REQUIRED");
        }
        require(fs::is_regular_file(image) && !fs::is_symlink(image),
                "IMAGE_NOT_REGULAR");
        const fs::path backup = parent / (image.filename().string() + ".h3c1-backup");
        require(!fs::exists(backup), "BACKUP_PATH_OCCUPIED");

        txn::session session(image, drum::geometry{"h3c1-recovery", 3, 2, 8},
                             kyiv_drum_host_address::policy::a3_linear_v1, 1);
        const auto original = session.read_prepared();
        const std::size_t old_count = session.snapshot().written_count();
        const auto old0 = session.snapshot().inspect({0, 0, 3});
        const auto old1 = session.snapshot().inspect({0, 0, 4});
        const auto old2 = session.snapshot().inspect({0, 0, 5});
        require(old_count == 3 && old0.written && old1.written && old2.written,
                "BASELINE_IMAGE_UNEXPECTED");
        const std::uint64_t command =
            (std::uint64_t{025} << 36) | (std::uint64_t{1} << 24) |
            (std::uint64_t{0100} << 12) | 3;
        session.prepare(command);
        require(session.write_prepared() && session.read_prepared() == original,
                "PREPARATION_FAILED");

        // Inject OS rename failure deterministically: retain the good target
        // at a sibling backup name and occupy the destination with a directory.
        // This is strictly confined to the marked, private test directory.
        fs::rename(image, backup);
        bool occupied = false;
        std::string observed;
        try {
            require(fs::create_directory(image), "INJECT_DIRECTORY_FAILED");
            occupied = true;
            try {
                session.write_words({drum::sign_bit, 0, 0x22334});
                observed = "UNEXPECTED_WRITE_SUCCESS";
            } catch (const drum::media_error& e) {
                observed = e.what();
            }
        } catch (...) {
            if (occupied) {
                std::error_code ignored;
                fs::remove(image, ignored);
            }
            std::error_code ignored;
            fs::rename(backup, image, ignored);
            throw;
        }
        // Restore before any further assertions, even when the injected
        // operation did not fail as expected.
        require(fs::remove(image), "INJECT_DIRECTORY_NOT_EMPTY");
        fs::rename(backup, image);

        require(observed == "REPLACE_FAILED", "EXPECTED_REPLACE_FAILED");
        require(session.snapshot().written_count() == old_count,
                "SESSION_WRITTEN_COUNT_CHANGED");
        const auto same = [&](drum::coordinate c, drum::cell before) {
            const auto after = session.snapshot().inspect(c);
            return after.written == before.written && after.word == before.word;
        };
        require(same({0, 0, 3}, old0) && same({0, 0, 4}, old1) &&
                same({0, 0, 5}, old2), "SESSION_SNAPSHOT_CHANGED");
        require(session.write_prepared(), "WRITE_PREPARATION_CHANGED");
        // Reopen through the real B3 decoder, not the in-memory session.
        const auto recovered = kyiv_drum_persistence::load(image);
        require(recovered.written_count() == old_count &&
                recovered.inspect({0, 0, 3}).word == old0.word &&
                recovered.inspect({0, 0, 4}).word == old1.word &&
                recovered.inspect({0, 0, 5}).word == old2.word,
                "REOPENED_IMAGE_CHANGED");
        std::cout << "D14C2H3C1-FAULT PASS REPLACE_FAILED=1 "
                     "SESSION_ROLLBACK=1 RESTORED_FILE_REOPENED=1\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D14C2H3C1-FAULT ERROR=" << e.what() << "\n";
        return 1;
    }
}
