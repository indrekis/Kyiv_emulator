#ifndef KYIVEMU_D15A2_HOST_IMAGE_V1_H
#define KYIVEMU_D15A2_HOST_IMAGE_V1_H

// D15/A2: shared HOST-only KYIV41-OCT1 file reader and bounded CPU runner.
// No historical media/ROM/time claims. The CPU and its semantics are unchanged.
#include "kyiv.h"
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace kyiv_host_image_v1 {
using record = std::pair<addr_t, word_t>;
constexpr word_t word_mask = (word_t{1} << 41) - 1;

inline std::uint64_t parse_octal(const std::string& s, std::size_t width) {
    if (s.size() != width)
        throw std::runtime_error("INVALID_OCTAL_WIDTH");
    std::uint64_t value = 0;
    for (char c : s) {
        if (c < '0' || c > '7')
            throw std::runtime_error("INVALID_OCTAL_DIGIT");
        value = (value << 3) | std::uint64_t(c - '0');
    }
    return value;
}

inline bool usable_address(addr_t a) {
    return (a >= 0001 && a < 02000) ||
           (a >= 03000 && a < 04000);
}

inline std::size_t parse_limit(const std::string& s) {
    if (s.empty())
        throw std::runtime_error("INVALID_STEP_LIMIT");
    std::size_t n = 0;
    for (char c : s) {
        if (c < '0' || c > '9')
            throw std::runtime_error("INVALID_STEP_LIMIT");
        const std::size_t digit = std::size_t(c - '0');
        if (n > (100000 - digit) / 10)
            throw std::runtime_error("STEP_LIMIT_TOO_LARGE");
        n = n * 10 + digit;
    }
    if (n == 0)
        throw std::runtime_error("INVALID_STEP_LIMIT");
    return n;
}

inline std::vector<record> load_file(const std::string& filename,
                              bool allow_rom) {
    std::ifstream in(filename);
    if (!in)
        throw std::runtime_error("IMAGE_OPEN_FAILED");

    std::vector<record> result;
    std::set<addr_t> seen;
    std::string line;
    bool header = false;

    while (std::getline(in, line)) {
        const auto comment = line.find('#');
        if (comment != std::string::npos)
            line.erase(comment);

        std::istringstream fields(line);
        std::string first, second, extra;
        if (!(fields >> first))
            continue;

        if (!header) {
            if (first != "KYIV41-OCT1" || (fields >> extra))
                throw std::runtime_error("INVALID_IMAGE_HEADER");
            header = true;
            continue;
        }

        if (!(fields >> second) || (fields >> extra))
            throw std::runtime_error("INVALID_IMAGE_RECORD");

        const addr_t address = parse_octal(first, 4);
        const word_t value = parse_octal(second, 14);

        if (!usable_address(address))
            throw std::runtime_error("INVALID_LOAD_ADDRESS");
        if (address >= 03000 && !allow_rom)
            throw std::runtime_error("ROM_LOAD_REQUIRES_OPT_IN");
        if (value > word_mask)
            throw std::runtime_error("OVERWIDE_41_BIT_WORD");
        if (!seen.insert(address).second)
            throw std::runtime_error("DUPLICATE_ADDRESS");

        result.emplace_back(address, value);
    }

    if (in.bad())
        throw std::runtime_error("IMAGE_READ_FAILED");
    if (!header || result.empty())
        throw std::runtime_error("EMPTY_IMAGE");

    return result;
}

inline void print_word(word_t w) {
    std::cout << std::oct << std::setfill('0')
              << std::setw(14) << w << std::dec;
}

inline void print_addr(addr_t a) {
    std::cout << std::oct << std::setfill('0')
              << std::setw(4) << a << std::dec;
}


struct options {
    std::string filename;
    addr_t start = 0;
    std::size_t limit = 0;
    bool allow_rom = false;
    std::vector<addr_t> watched;
};

inline options parse(int argc, const char* const argv[]) {
    if (argc < 4 || !argv)
        throw std::runtime_error(
            "USAGE: image.k41 START_OCTAL MAX_STEPS_DECIMAL "
            "[--allow-rom] [--watch ADDR_OCTAL]...");
    for (int i=0; i<argc; ++i)
        if (!argv[i]) throw std::runtime_error("INVALID_ARGUMENT");
    options cfg;
    cfg.filename = argv[1];
    cfg.start = parse_octal(argv[2], 4);
    if (!usable_address(cfg.start))
        throw std::runtime_error("INVALID_START_ADDRESS");
    cfg.limit = parse_limit(argv[3]);
    for (int i=4; i<argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--allow-rom") {
            if (cfg.allow_rom)
                throw std::runtime_error("DUPLICATE_ALLOW_ROM");
            cfg.allow_rom = true;
        } else if (arg == "--watch" && i+1<argc) {
            const addr_t address = parse_octal(argv[++i],4);
            if (!usable_address(address))
                throw std::runtime_error("INVALID_WATCH_ADDRESS");
            cfg.watched.push_back(address);
        } else {
            throw std::runtime_error("INVALID_ARGUMENT");
        }
    }
    return cfg;
}

inline int execute(Kyiv_t& cpu, const options& cfg,
                   const std::vector<record>& image,
                   const std::string& tag) {
    // All parsing and preflight are complete before any memory write.
    for (const auto& item : image) {
        if (item.first >= 03000)
            cpu.kmem.write_rom(item.first, item.second);
        else
            cpu.kmem.write_memory(item.first, item.second);
    }
    cpu.C_reg = cfg.start;
    std::cout << tag << "-LOAD PASS WORDS=" << image.size()
              << " ROM_OPT_IN=" << (cfg.allow_rom ? 1 : 0) << '\n';
    std::size_t steps = 0;
    bool stopped = false;
    while (steps < cfg.limit) {
        const bool keep_running = cpu.execute_opcode();
        ++steps;
        if (!keep_running) {
            stopped = true;
            break;
        }
    }
    std::cout << tag << "-RUN STATUS=" << (stopped ? "CPU_STOP" : "LIMIT")
              << " STEPS=" << steps << " C=";
    print_addr(cpu.C_reg);
    std::cout << " K=";
    print_word(cpu.K_reg);
    std::cout << " A=";
    print_addr(cpu.A_reg);
    std::cout << " P=";
    print_addr(cpu.P_reg);
    std::cout << " LOOP=";
    print_addr(cpu.Loop_reg);
    std::cout << " T=" << (cpu.T_reg ? 1 : 0) << '\n';
    for (addr_t a : cfg.watched) {
        std::cout << tag << "-WATCH ADDR=";
        print_addr(a);
        std::cout << " RAW=";
        print_word(cpu.kmem.read_memory(a));
        std::cout << '\n';
    }
    return 0;
}

} // namespace kyiv_host_image_v1
#endif
