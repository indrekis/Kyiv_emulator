#ifndef KYIVEMU_H57_ROM_MODULE1_V1_H
#define KYIVEMU_H57_ROM_MODULE1_V1_H
// H57: explicit HOST-only replaceable ROM module 1 during image-mode startup.
// GY62 printed pp.8-9,93-95; no hardware hot swapping, no historical numerical contract.
// Staged parsing and SHA verification finish before mutating any CPU ROM cells.
#include "kyiv.h"
#include "kyiv_sha256_v1.h"
#include <cctype>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace kyiv_rom_module1_v1 {
constexpr const char* qualified_source_sha256 =
    "9c659521d263fe78c2d6356cb28bfeaac374c1e71d723e35cc60be19ad3e1e84";
constexpr addr_t first_address = 03300;
constexpr addr_t last_address = 03377;
constexpr std::size_t expected_words = 64;
constexpr word_t mask41 = (word_t{1} << 41) - 1;

struct arguments {
    std::vector<const char*> forwarded;
    bool selected = false;
    std::string filename;
    std::string expected_sha256;
};
inline std::string digest_option(const std::string& s) {
    if (s.size() != 64) throw std::runtime_error("H57_SHA256_FORMAT");
    std::string norm;
    for (unsigned char c : s) {
        if (!std::isxdigit(c)) throw std::runtime_error("H57_SHA256_FORMAT");
        norm.push_back(static_cast<char>(std::tolower(c)));
    }
    return norm;
}
inline arguments extract(int argc, const char* const argv[]) {
    if (argc < 1 || !argv) throw std::runtime_error("H57_ARGUMENTS");
    arguments result;
    bool path_seen = false, sha_seen = false;
    for (int i=0; i<argc; ++i) {
        if (!argv[i]) throw std::runtime_error("H57_ARGUMENTS");
        std::string arg(argv[i]);
        if (i && (arg == "--rom-module1" || arg == "--rom-module1-sha256")) {
            if (i+1 >= argc || !argv[i+1]) throw std::runtime_error("H57_MISSING_VALUE");
            const std::string val(argv[++i]);
            if (val.empty() || val.compare(0,2,"--")==0)
                throw std::runtime_error("H57_MISSING_VALUE");
            if (arg == "--rom-module1") {
                if (path_seen) throw std::runtime_error("H57_DUPLICATE_FILE");
                path_seen = true;
                result.filename = val;
            } else {
                if (sha_seen) throw std::runtime_error("H57_DUPLICATE_SHA256");
                sha_seen = true;
                result.expected_sha256 = digest_option(val);
            }
        } else result.forwarded.push_back(argv[i]);
    }
    if (path_seen != sha_seen) throw std::runtime_error("H57_FILE_AND_SHA_REQUIRED");
    result.selected = path_seen;
    return result;
}

struct image {
    std::vector<std::pair<addr_t,word_t>> words;
    std::string sha256;
    bool source_qualified = false;
};
inline std::uint64_t octal(const std::string& s, std::size_t width) {
    if (s.size()!=width) throw std::runtime_error("H57_OCTAL_WIDTH");
    std::uint64_t v = 0;
    for (unsigned char c : s) {
        if (c<'0' || c>'7') throw std::runtime_error("H57_OCTAL_DIGIT");
        v = (v<<3)|(c-'0');
    }
    return v;
}
inline image read(const arguments& args) {
    if (!args.selected) throw std::runtime_error("H57_NOT_SELECTED");
    std::ifstream f(std::filesystem::u8path(args.filename),std::ios::binary);
    if (!f) throw std::runtime_error("H57_FILE_OPEN");
    std::vector<unsigned char> raw;
    for (char block[4096]; f;) {
        f.read(block,sizeof(block));
        for (std::streamsize i=0,n=f.gcount();i<n;++i) {
            if (raw.size() >= 16384) throw std::runtime_error("H57_FILE_TOO_LARGE");
            raw.push_back(static_cast<unsigned char>(block[i]));
        }
    }
    if (!f.eof()) throw std::runtime_error("H57_FILE_READ");
    image staged;
    staged.sha256=kyiv_sha256_v1::digest(raw);
    if (staged.sha256!=args.expected_sha256)
        throw std::runtime_error("H57_SHA256_MISMATCH");
    staged.source_qualified=(staged.sha256==qualified_source_sha256);
    std::map<addr_t,word_t> parsed;
    bool header_seen=false;
    std::string line;
    auto consume=[&]() {
        if (!line.empty() && line.back()=='\r') line.pop_back();
        for (unsigned char c:line) if (c>127) throw std::runtime_error("H57_NON_ASCII");
        if (!header_seen) {
            if (line!="KYIV41-OCT1") throw std::runtime_error("H57_HEADER");
            header_seen=true; return;
        }
        if (line.empty()) throw std::runtime_error("H57_EMPTY_LINE");
        const auto space=line.find(' ');
        if (space==std::string::npos || line.find(' ',space+1)!=std::string::npos)
            throw std::runtime_error("H57_FIELDS");
        auto addr=octal(line.substr(0,space),4);
        auto word=octal(line.substr(space+1),14);
        if (addr<first_address || addr>last_address)
            throw std::runtime_error("H57_OUT_OF_SLOT");
        if (word>mask41) throw std::runtime_error("H57_OVERWIDE_41");
        if (!parsed.emplace(addr,word).second)
            throw std::runtime_error("H57_DUPLICATE_ADDRESS");
    };
    for (unsigned char c:raw) {
        if (c=='\n') {consume();line.clear();}
        else line.push_back(static_cast<char>(c));
    }
    if (!line.empty()) consume();
    if (!header_seen || parsed.size()!=expected_words)
        throw std::runtime_error("H57_INCOMPLETE_MODULE");
    for (addr_t a=first_address;a<=last_address;++a)
        if (!parsed.count(a)) throw std::runtime_error("H57_MISSING_ADDRESS");
    staged.words.assign(parsed.begin(),parsed.end());
    return staged;
}
// Preflight explicitly rejects overrides of the selected slot in the *image*.
// The source image remains a separate, independently validated object.
inline void reject_image_overlap(const std::vector<std::pair<addr_t,word_t>>& source) {
    for (const auto& x:source) {
        if (x.first>=first_address && x.first<=last_address)
            throw std::runtime_error("H57_IMAGE_MODULE_OVERLAP");
    }
}
// Initializing an empty deferred CPU, after validation of all inputs, is the
// only supported installation phase. No reset/hot-swap API is exposed.
inline void install_at_init(Kyiv_t& cpu, const image& staged) {
    if (staged.words.size()!=expected_words)
        throw std::runtime_error("H57_INVALID_STAGED_MODULE");
    for (const auto& w:staged.words) cpu.kmem.write_rom(w.first,w.second);
}
} // namespace kyiv_rom_module1_v1
#endif
