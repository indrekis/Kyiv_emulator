// ISA-07 D14-C2-H3/C2. TEST-ONLY B3 termination-window witness.
// Build ONLY against Python-generated private copies of transaction and
// persistence headers. Never run against an actual user-owned drum image.
#include "kyiv_drum_transaction_v1.h"
#ifndef KYIVEMU_D14C2H3C2_TEST_COPY
#error "H3C2 requires the test-only instrumented B3 header"
#endif
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
namespace media = kyiv_drum_media;
namespace session_api = kyiv_drum_transaction_v1;

static void require(bool ok, const char* code) {
    if (!ok) throw std::runtime_error(code);
}

int main(int argc, char** argv) {
    try {
        if (argc == 2 && std::string(argv[1]) == "--self-test") {
            require((std::uint64_t{025} << 36) < (std::uint64_t{1} << 41),
                    "OPCODE_ENCODING");
            std::cout << "D14C2H3C2-PROBE-SELFTEST PASS\n";
            return 0;
        }
        require(argc == 2, "USAGE: probe IMAGE");
        const fs::path image = fs::absolute(fs::path(argv[1]));
        require(image.filename() == "crash.kdr", "FIXTURE_NAME_REQUIRED");
        const fs::path guard = image.parent_path() / ".h3c2-private-sandbox";
        {
            std::ifstream in(guard, std::ios::binary);
            std::string line;
            require(bool(in) && bool(std::getline(in, line)) &&
                    line == "H3C2-PRIVATE-TEST-ONLY", "ISOLATION_MARKER_REQUIRED");
        }
        require(fs::is_regular_file(image) && !fs::is_symlink(image),
                "IMAGE_NOT_REGULAR");
        session_api::session s(image, media::geometry{"h3c2-kill", 3, 2, 8},
            kyiv_drum_host_address::policy::a3_linear_v1, 1);
        require(s.snapshot().written_count() == 3, "EXPECTED_INITIAL_WRITES");
        require(s.snapshot().inspect({0, 0, 3}).word == 0 &&
                s.snapshot().inspect({0, 0, 4}).word == media::sign_bit &&
                s.snapshot().inspect({0, 0, 5}).word == 0x111001,
                "UNEXPECTED_INITIAL_WORDS");
        const std::uint64_t prep = (std::uint64_t{025} << 36) |
            (std::uint64_t{1} << 24) | (std::uint64_t{0100} << 12) | 3;
        (void)s.prepare(prep);
        require(s.write_prepared(), "WRITE_PREPARATION_FAILED");
        // The Python runner must externally terminate the process at a test-only
        // pause inserted into a PRIVATE copy of the B3 persistence header.
        // Returning normally is ALWAYS a failure in the termination gate.
        s.write_words({media::sign_bit, 0, 0x22334});
        std::cerr << "D14C2H3C2-PROBE ERROR=WRITER_RETURNED_WITHOUT_KILL\n";
        return 2;
    } catch (const std::exception& e) {
        std::cerr << "D14C2H3C2-PROBE ERROR=" << e.what() << "\n";
        return 1;
    }
}
