// Pure HOST_POLICY decimal drum text adapter, no CPU or hardware oracle.
#include "kyiv_drum_input_plan.h"
#include <iostream>
#include <limits>
#include <string>

int main(int argc, char** argv) {
    if (argc != 4) return 2;
    try {
        const std::string tag(argv[1]);
        const std::size_t track = static_cast<std::size_t>(std::stoull(argv[2]));
        const std::size_t zone = static_cast<std::size_t>(std::stoull(argv[3]));
        // The unit protocol fixes count to 3 for normal cases, 1 for tag ONE,
        // and 0 for ZERO_COUNT; other counts via suffix '#N'.
        std::size_t count = 3;
        if (tag == "ONE") count = 1;
        if (tag == "ZERO_COUNT") count = 0;
        if (tag == "missing") std::cin.setstate(std::ios::badbit);
        const auto result = kyiv_drum_input_plan::collect(std::cin, track, zone, count);
        std::cout << "D12B-PLAN tag=" << tag << " status="
                  << kyiv_drum_input_plan::status_text(result.state)
                  << " count=" << result.words.size() << " values=";
        for (auto word : result.words) std::cout << std::oct << word << ',';
        std::cout << std::dec << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D12B-PLAN-ERROR " << e.what() << '\n';
        return 3;
    }
}
