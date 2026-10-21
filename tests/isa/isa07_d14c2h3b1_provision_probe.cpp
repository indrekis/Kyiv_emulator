// Independent native readback of a provisioned image, including empty cells.
#include "kyiv_drum_persistence.h"
#include "kyiv_drum_cli_v1.h"
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
int main(int argc, char** argv) {
    try {
        if (argc != 6 || std::string(argv[1]) != "inspect")
            throw std::runtime_error("PROBE_USAGE");
        const kyiv_drum_media::geometry g{
            argv[3], 3, kyiv_drum_cli_v1::decimal(argv[4]),
            kyiv_drum_cli_v1::decimal(argv[5])};
        const auto disk = kyiv_drum_persistence::load(argv[2]);
        if (!kyiv_drum_persistence::same_geometry(g,disk.profile()))
            throw std::runtime_error("GEOMETRY_MISMATCH");
        if (disk.written_count()) throw std::runtime_error("NOT_EMPTY");
        for (std::size_t d=0; d<3; ++d)
            for (std::size_t t=0; t<g.tracks_per_drum; ++t)
                for (std::size_t s=0; s<g.slots_per_track; ++s)
                    if (disk.inspect({d,t,s}).written)
                        throw std::runtime_error("WRITTEN_CELL");
        std::cout << "D14C2H3B1-INSPECT PASS SLOTS=" << disk.capacity()
                  << " WRITTEN=0 GEOMETRY_EXACT=1\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "D14C2H3B1-INSPECT ERROR=" << ex.what() << '\n';
        return 2;
    }
}
