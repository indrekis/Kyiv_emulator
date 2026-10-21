// Genuine C++17 HOST parser probe. NO CPU and NO filesystem operations.
#include "kyiv_drum_cli_v1.h"
#include <iostream>
#include <string>
int main(int argc, char** argv) {
    try {
        // Treat probe's argv exactly as main's argv: first arg is program name.
        const auto p = kyiv_drum_cli_v1::parse(argc, const_cast<const char* const*>(argv));
        std::cout << "OK|" << p.legacy_argc << '|' << (p.block_overflow_stop ? 1 : 0)
                  << '|' << (p.drum ? 1 : 0);
        if (p.drum) {
            const auto& d = *p.drum;
            std::cout << '|' << d.expected_geometry.profile_id
                      << '|' << d.expected_geometry.tracks_per_drum
                      << '|' << d.expected_geometry.slots_per_track
                      << '|' << d.pinned_drum << '|' << d.existing_image;
        }
        std::cout << '\n';
    } catch (const kyiv_drum_cli_v1::cli_error& e) {
        std::cout << "ERR|" << e.what() << '\n';
    } catch (const kyiv_drum_media::media_error& e) {
        std::cout << "ERR|" << e.what() << '\n';
    } catch (const std::exception& e) {
        std::cerr << "UNEXPECTED " << e.what() << '\n';
        return 2;
    }
    return 0;
}
