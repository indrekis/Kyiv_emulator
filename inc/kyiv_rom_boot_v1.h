#ifndef KYIVEMU_D15A3P3_ROM_BOOT_H
#define KYIVEMU_D15A3P3_ROM_BOOT_H
// D15/A3-P3: checked, explicit HOST ROM bootstrap for image mode only.
// This does NOT claim the reconstructed ROM is a historical hardware oracle.
#include "kyiv.h"
#include "kyiv_sha256_v1.h"
#include <algorithm>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _WIN32
#include <windows.h>
#endif

namespace kyiv_rom_boot_v1 {
namespace fs = std::filesystem;
constexpr const char* pinned_default_sha256 =
    "a1d9c28e969fa1d74966a78fdbb1bf85b4c45354a764cb8665a73b0a62bdab38";

struct arguments {
    std::vector<const char*> forwarded;
    bool explicit_rom = false;
    std::string rom_filename;
    std::string expected_sha256;
};

inline std::string normalize_sha(const std::string& s) {
    if (s.size() != 64) throw std::runtime_error("ROM_INVALID_SHA256");
    std::string out;
    out.reserve(64);
    for (unsigned char ch : s) {
        if (!std::isxdigit(ch)) throw std::runtime_error("ROM_INVALID_SHA256");
        out.push_back(static_cast<char>(std::tolower(ch)));
    }
    return out;
}

// Strip only ROM-specific image-mode options, preserving the previously
// qualified A2 image parser and argument-order semantics.
inline arguments extract(int argc, const char* const argv[]) {
    if (argc < 1 || !argv) throw std::runtime_error("ROM_INVALID_ARGUMENTS");
    arguments out;
    bool got_path = false, got_sha = false;
    for (int i=0;i<argc;++i) {
        if (!argv[i]) throw std::runtime_error("ROM_INVALID_ARGUMENTS");
        const std::string arg = argv[i];
        if (i > 0 && (arg == "--rom-file" || arg == "--rom-sha256")) {
            if (i+1 >= argc || !argv[i+1])
                throw std::runtime_error("ROM_MISSING_OPTION_VALUE");
            const std::string value = argv[++i];
            if (arg == "--rom-file") {
                if (got_path) throw std::runtime_error("ROM_DUPLICATE_PATH");
                if (value.empty() || value.substr(0, 2) == "--")
                    throw std::runtime_error("ROM_INVALID_PATH");
                got_path = true;
                out.rom_filename = value;
            } else {
                if (got_sha) throw std::runtime_error("ROM_DUPLICATE_SHA256");
                got_sha = true;
                out.expected_sha256 = normalize_sha(value);
            }
        } else {
            out.forwarded.push_back(argv[i]);
        }
    }
    if (got_sha && !got_path) throw std::runtime_error("ROM_SHA_REQUIRES_FILE");
    out.explicit_rom = got_path;
    return out;
}

inline fs::path executable_path(const char* argv0) {
#ifdef _WIN32
    (void)argv0;
    std::wstring name(32768, L'\0');
    const auto n = GetModuleFileNameW(nullptr, &name[0], static_cast<DWORD>(name.size()));
    if (n == 0 || n >= name.size()) throw std::runtime_error("ROM_EXE_PATH_FAILED");
    name.resize(n);
    return fs::path(name);
#elif defined(__linux__)
    std::error_code ec;
    auto p = fs::read_symlink("/proc/self/exe", ec);
    if (!ec) return p;
    if (!argv0 || !*argv0) throw std::runtime_error("ROM_EXE_PATH_FAILED");
    return fs::canonical(argv0);
#else
    if (!argv0 || !*argv0) throw std::runtime_error("ROM_EXE_PATH_FAILED");
    return fs::canonical(argv0);
#endif
}

inline fs::path choose_default_rom(const char* argv0) {
    const fs::path dir = executable_path(argv0).parent_path();
    const fs::path paths[] = {dir / "mem" / "ROM.txt", dir / ".." / "mem" / "ROM.txt"};
    fs::path found;
    for (const auto& p : paths) {
        std::error_code ec;
        if (!fs::is_regular_file(p, ec)) continue;
        const fs::path absolute = fs::canonical(p, ec);
        if (ec) throw std::runtime_error("ROM_DEFAULT_PATH_FAILED");
        if (!found.empty() && found != absolute)
            throw std::runtime_error("ROM_DEFAULT_AMBIGUOUS");
        found = absolute;
    }
    if (found.empty()) throw std::runtime_error("ROM_DEFAULT_NOT_FOUND");
    return found;
}

struct image {
    std::vector<std::pair<addr_t,word_t>> words;
    std::string sha256;
    bool unknown_3200 = false;
    bool source_is_default = false;
    bool sha_pinned = false;
};

inline image read(const arguments& args, const char* argv0) {
    const auto source = args.explicit_rom ? fs::u8path(args.rom_filename) : choose_default_rom(argv0);
    const auto expected = args.explicit_rom ? args.expected_sha256 : std::string(pinned_default_sha256);
    std::ifstream in(source, std::ios::binary);
    if (!in) throw std::runtime_error("ROM_OPEN_FAILED");
    std::vector<unsigned char> bytes;
    char block[4096];
    while (in) {
        in.read(block, sizeof(block));
        const auto n = in.gcount();
        for (std::streamsize i=0;i<n;++i) {
            if (bytes.size() >= 1048576) throw std::runtime_error("ROM_TOO_LARGE");
            bytes.push_back(static_cast<unsigned char>(block[i]));
        }
    }
    if (!in.eof()) throw std::runtime_error("ROM_READ_FAILED");
    image result;
    result.sha256 = kyiv_sha256_v1::digest(bytes);
    result.sha_pinned = !expected.empty();
    if (result.sha_pinned && result.sha256 != expected)
        throw std::runtime_error("ROM_SHA256_MISMATCH");
    result.source_is_default = !args.explicit_rom;
    std::map<addr_t,word_t> values;
    std::string line;
    // Parse bytes, not a text-mode stream: SHA covers exact CRLF/LF bytes.
    auto parse_line = [&]() {
        if (line.empty()) return;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty()) throw std::runtime_error("ROM_INVALID_RECORD");
        for (unsigned char c: line)
            if (c > 127) throw std::runtime_error("ROM_NON_ASCII");
        std::istringstream iss(line);
        std::string address, code, a1, a2, a3, extra;
        if (!(iss >> address >> code >> a1 >> a2 >> a3) || (iss >> extra))
            throw std::runtime_error("ROM_INVALID_RECORD");
        const auto oct = [](const std::string& s, unsigned n) -> std::uint64_t {
            if (s.size() != n) throw std::runtime_error("ROM_INVALID_OCTAL_WIDTH");
            std::uint64_t v = 0;
            for (unsigned char c : s) {
                if (c < '0' || c > '7') throw std::runtime_error("ROM_INVALID_OCTAL_DIGIT");
                v = (v << 3) | (c - '0');
            }
            return v;
        };
        const auto addr = oct(address,4);
        if (addr < 03010 || addr > 03277)
            throw std::runtime_error("ROM_ADDRESS_OUTSIDE_FIXED_RANGE");
        const auto word = (oct(code,2) << 36) | (oct(a1,4) << 24) |
                          (oct(a2,4) << 12) | oct(a3,4);
        if (word >= (std::uint64_t{1} << 41))
            throw std::runtime_error("ROM_OVERWIDE_WORD");
        if (!values.emplace(addr,word).second)
            throw std::runtime_error("ROM_DUPLICATE_ADDRESS");
    };
    for (unsigned char c: bytes) {
        if (c == '\n') { parse_line(); line.clear(); }
        else line.push_back(static_cast<char>(c));
    }
    if (!line.empty()) parse_line();
    result.unknown_3200 = !values.count(03200);
    if (values.size() != (result.unknown_3200 ? 183u : 184u))
        throw std::runtime_error("ROM_MISSING_REQUIRED_WORD");
    for (addr_t addr=03010; addr<=03277; ++addr) {
        if (addr == 03200 && result.unknown_3200) continue;
        if (!values.count(addr)) throw std::runtime_error("ROM_MISSING_REQUIRED_WORD");
    }
    result.words.assign(values.begin(), values.end());
    return result;
}

inline void install(Kyiv_t& cpu, const image& rom) {
    for (const auto& item: rom.words) cpu.kmem.write_rom(item.first,item.second);
}
} // namespace kyiv_rom_boot_v1
#endif
