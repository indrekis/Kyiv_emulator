// D15/A2: A1 standalone driver now shares parser and bounded runner
// with production CLI image mode. The real Kyiv_t executes CPU instructions.
#include "kyiv_host_image_v1.h"
#include <cstdint>
#include <iostream>
#include <stdexcept>

// Standalone A1 does not link the production CLI disassembler.
int disassembly(const std::uint64_t&, Kyiv_memory_t&, const addr3_t&) {
    return 0;
}

int main(int argc, char** argv) {
    try {
        const auto cfg = kyiv_host_image_v1::parse(argc, argv);
        const auto image = kyiv_host_image_v1::load_file(cfg.filename,
                                                         cfg.allow_rom);
        Kyiv_t cpu;
        return kyiv_host_image_v1::execute(cpu, cfg, image, "D15A1");
    } catch (const std::exception& e) {
        std::cerr << "D15A1-ERROR " << e.what() << '\n';
        return 2;
    } catch (...) {
        std::cerr << "D15A1-ERROR UNKNOWN_EXCEPTION\n";
        return 2;
    }
}
