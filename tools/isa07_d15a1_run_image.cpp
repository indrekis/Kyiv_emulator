// D15/A1: bounded execution of a HOST octal image using the real Kyiv_t.
// Standalone qualification tool; not a historical image-file format.
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

// This standalone executable does not need the CLI disassembler.
// CPU arithmetic, registers and memory remain the production implementation.
int disassembly(const std::uint64_t&, Kyiv_memory_t&,
                const addr3_t&) {
    return 0;
}

namespace {

using record = std::pair<addr_t, word_t>;
constexpr word_t word_mask = (word_t{1} << 41) - 1;

std::uint64_t parse_octal(const std::string& s, std::size_t width) {
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

bool usable_address(addr_t a) {
    return (a >= 0001 && a < 02000) ||
           (a >= 03000 && a < 04000);
}

std::size_t parse_limit(const std::string& s) {
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

std::vector<record> load_file(const std::string& filename,
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

void print_word(word_t w) {
    std::cout << std::oct << std::setfill('0')
              << std::setw(14) << w << std::dec;
}

void print_addr(addr_t a) {
    std::cout << std::oct << std::setfill('0')
              << std::setw(4) << a << std::dec;
}

} // namespace

int main(int argc, char** argv) {
    try {
        if (argc < 4)
            throw std::runtime_error(
                "USAGE: image.k41 START_OCTAL MAX_STEPS_DECIMAL "
                "[--allow-rom] [--watch ADDR_OCTAL]...");

        const addr_t start = parse_octal(argv[2], 4);
        if (!usable_address(start))
            throw std::runtime_error("INVALID_START_ADDRESS");

        const std::size_t limit = parse_limit(argv[3]);

        bool allow_rom = false;
        std::vector<addr_t> watched;

        for (int i = 4; i < argc; ++i) {
            const std::string arg = argv[i];

            if (arg == "--allow-rom") {
                if (allow_rom)
                    throw std::runtime_error("DUPLICATE_ALLOW_ROM");
                allow_rom = true;
            } else if (arg == "--watch" && i + 1 < argc) {
                const addr_t address = parse_octal(argv[++i], 4);
                if (!usable_address(address))
                    throw std::runtime_error("INVALID_WATCH_ADDRESS");
                watched.push_back(address);
            } else {
                throw std::runtime_error("INVALID_ARGUMENT");
            }
        }

        // Parse and validate the complete image before touching memory.
        const auto image = load_file(argv[1], allow_rom);

        Kyiv_t cpu;
        for (const auto& item : image) {
            if (item.first >= 03000)
                cpu.kmem.write_rom(item.first, item.second);
            else
                cpu.kmem.write_memory(item.first, item.second);
        }
        cpu.C_reg = start;

        std::cout << "D15A1-LOAD PASS WORDS=" << image.size()
                  << " ROM_OPT_IN=" << (allow_rom ? 1 : 0) << '\n';

        std::size_t steps = 0;
        bool stopped = false;

        while (steps < limit) {
            const bool keep_running = cpu.execute_opcode();
            ++steps;
            if (!keep_running) {
                stopped = true;
                break;
            }
        }

        std::cout << "D15A1-RUN STATUS="
                  << (stopped ? "CPU_STOP" : "LIMIT")
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

        for (addr_t a : watched) {
            std::cout << "D15A1-WATCH ADDR=";
            print_addr(a);
            std::cout << " RAW=";
            print_word(cpu.kmem.read_memory(a));
            std::cout << '\n';
        }

        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D15A1-ERROR " << e.what() << '\n';
        return 2;
    } catch (...) {
        std::cerr << "D15A1-ERROR UNKNOWN_EXCEPTION\n";
        return 2;
    }
}
