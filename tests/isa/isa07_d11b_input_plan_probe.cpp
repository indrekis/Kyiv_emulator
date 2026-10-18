// D11-B parser/planner is a pure host-policy helper: no real paper tape claim.
#include "kyiv_binary_input_plan.h"
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>

int main(int argc, char** argv) {
    if (argc != 4) return 2;
    try {
        const std::string tag=argv[1];
        const auto start=static_cast<std::size_t>(std::stoull(argv[2]));
        const auto count=static_cast<std::size_t>(std::stoull(argv[3]));
        const auto result=kyiv_binary_input_plan::collect(std::cin,start,count);
        std::cout << "D11B-PLAN tag=" << tag
                  << " status=" << kyiv_binary_input_plan::status_text(result.state)
                  << " count=" << result.words.size() << " values=";
        for (auto w:result.words) std::cout << std::oct << w << ',';
        std::cout << std::dec << '\n';
    } catch (const std::exception& e) {
        std::cerr << "D11B-PLAN-ERROR " << e.what() << '\n';
        return 3;
    }
    return 0;
}
