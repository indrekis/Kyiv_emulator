// Explicit standalone image provisioning. Not an implicit kyivemu attach path.
#include "kyiv_drum_provision_v1.h"
#include "kyiv_drum_cli_v1.h"
#include <exception>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    try {
        if (argc != 6 || std::string(argv[1]) != "create")
            throw kyiv_drum_media::media_error("PROVISION_USAGE");
        const auto tracks = kyiv_drum_cli_v1::decimal(argv[4]);
        const auto slots = kyiv_drum_cli_v1::decimal(argv[5]);
        const auto receipt = kyiv_drum_provision_v1::create_new(
            argv[2], {argv[3], 3, tracks, slots});
        std::cout << "D14C2H3B1-CREATE PASS SLOTS=" << receipt.slots
                  << " IMAGE_BYTES=" << receipt.image_bytes
                  << " WRITTEN=0 NO_CLOBBER=1 HARDWARE_ORACLE=0\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "D14C2H3B1-CREATE ERROR=" << ex.what() << '\n';
        return 2;
    }
}
