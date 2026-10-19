// D13-B stand-alone host-plan test. No Kyiv CPU stub and no physical-drum oracle.
#include "kyiv_drum_output_plan.h"
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc, char** argv) {
    if (argc < 2) return 2;
    const std::string mode(argv[1]);
    if (mode != "plan" && mode != "commit") return 2;
    if (mode == "commit" && argc < 4) return 2;
    std::vector<std::uint64_t> words;
    const int first = mode == "plan" ? 2 : 3;
    try {
        for (int i = first; i < argc; ++i) {
            const std::string s(argv[i]);
            if (s.empty() || s[0] == '-' || s[0] == '+') return 2;
            std::size_t end = 0;
            const std::uint64_t w = std::stoull(s, &end, 10);
            if (end != s.size()) return 2;
            words.push_back(w);
        }
        const auto plan = kyiv_drum_output_plan::prepare(words);
        if (mode == "commit" && plan.state == kyiv_drum_output_plan::status::exact) {
            const auto st = kyiv_drum_output_plan::commit(argv[2], plan.bytes);
            std::cout << "D13B-PLAN state=" << kyiv_drum_output_plan::status_text(st)
                      << " bytes=" << plan.bytes.size() << '\n';
        } else {
            std::cout << "D13B-PLAN state=" << kyiv_drum_output_plan::status_text(plan.state)
                      << " bytes=" << plan.bytes.size() << " hex=";
            constexpr char digits[] = "0123456789abcdef";
            for (unsigned char c : plan.bytes)
                std::cout << digits[c >> 4] << digits[c & 15];
            std::cout << '\n';
        }
    } catch (const std::exception& err) {
        std::cerr << "D13B-PLAN-EXCEPTION " << err.what() << '\n';
        return 3;
    }
    return 0;
}
