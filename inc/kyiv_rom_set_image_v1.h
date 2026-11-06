#ifndef KYIVEMU_H116_ROM_SET_IMAGE_V1_H
#define KYIVEMU_H116_ROM_SET_IMAGE_V1_H
// H116-C1b: generic, opt-in, SHA-pinned ROM-set overlay on a DEFERRED CPU.
// The C1a Python catalog validates JSON manifests and exports a sparse
// KYIV41-OCT1 image. This C++ loader validates the exact bytes it installs.
// It never changes the production CPU or assigns values to unknown addresses.
#include "kyiv.h"
#include "kyiv_sha256_v1.h"
#include <cstdint>
#include <fstream>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace kyiv_rom_set_image_v1 {
struct arguments {
    std::vector<const char*> forwarded;
    bool selected = false;
    std::string filename;
    std::string expected_sha256;
};

inline std::string normalize_sha(const std::string& value) {
    if (value.size()!=64) throw std::runtime_error("H116_SET_SHA256_FORMAT");
    std::string out;
    out.reserve(64);
    for (unsigned char c:value) {
        if (c>='0' && c<='9') out.push_back(static_cast<char>(c));
        else if (c>='a' && c<='f') out.push_back(static_cast<char>(c));
        else if (c>='A' && c<='F') out.push_back(static_cast<char>(c-'A'+'a'));
        else throw std::runtime_error("H116_SET_SHA256_FORMAT");
    }
    return out;
}

inline arguments extract(int argc,const char* const* argv) {
    if (argc<1 || !argv) throw std::runtime_error("H116_SET_ARGUMENTS");
    arguments result;
    bool got_file=false,got_sha=false;
    for(int i=0;i<argc;++i) {
        if (!argv[i]) throw std::runtime_error("H116_SET_ARGUMENTS");
        const std::string opt=argv[i];
        if(i && (opt=="--rom-set-image" || opt=="--rom-set-sha256")) {
            if(i+1>=argc || !argv[i+1] || !argv[i+1][0] ||
               std::string(argv[i+1]).compare(0,2,"--")==0)
                throw std::runtime_error("H116_SET_OPTION_VALUE");
            const std::string value=argv[++i];
            if(opt=="--rom-set-image") {
                if(got_file) throw std::runtime_error("H116_SET_DUPLICATE_IMAGE");
                result.filename=value;got_file=true;
            } else {
                if(got_sha) throw std::runtime_error("H116_SET_DUPLICATE_SHA");
                result.expected_sha256=normalize_sha(value);got_sha=true;
            }
        } else result.forwarded.push_back(argv[i]);
    }
    if(got_file!=got_sha) throw std::runtime_error("H116_SET_IMAGE_AND_SHA_REQUIRED");
    result.selected=got_file;
    return result;
}

struct image {
    std::vector<std::pair<addr_t,word_t>> words;
    std::string sha256;
};
inline std::uint64_t parse_octal(const std::string& s,std::size_t width) {
    if(s.size()!=width) throw std::runtime_error("H116_SET_OCTAL_WIDTH");
    std::uint64_t v=0;
    for(unsigned char c:s) {
        if(c<'0'||c>'7') throw std::runtime_error("H116_SET_OCTAL_DIGIT");
        v=(v<<3)|(c-'0');
    }
    return v;
}
inline image read(const arguments& args) {
    if(!args.selected) throw std::runtime_error("H116_SET_NOT_SELECTED");
    std::ifstream in(args.filename,std::ios::binary);
    if(!in) throw std::runtime_error("H116_SET_FILE_OPEN");
    std::vector<unsigned char> raw;
    for(char block[4096];in;) {
        in.read(block,sizeof(block));
        for(std::streamsize i=0,n=in.gcount();i<n;++i) {
            if(raw.size()>=32768) throw std::runtime_error("H116_SET_FILE_TOO_LARGE");
            raw.push_back(static_cast<unsigned char>(block[i]));
        }
    }
    if(!in.eof()) throw std::runtime_error("H116_SET_FILE_READ");
    image result;
    result.sha256=kyiv_sha256_v1::digest(raw);
    if(result.sha256!=args.expected_sha256)
        throw std::runtime_error("H116_SET_SHA256_MISMATCH");
    std::string line;
    bool header=false;
    addr_t previous=0;
    auto consume=[&]() {
        if(!line.empty() && line.back()=='\r') line.pop_back();
        if(!header) {
            if(line!="KYIV41-OCT1") throw std::runtime_error("H116_SET_HEADER");
            header=true;
            return;
        }
        if(line.size()!=19 || line[4]!=' ')
            throw std::runtime_error("H116_SET_RECORD_FORMAT");
        const auto address=parse_octal(line.substr(0,4),4);
        const auto value=parse_octal(line.substr(5,14),14);
        if(address<03300 || address>=04000)
            throw std::runtime_error("H116_SET_OUT_OF_SLOTS");
        if(value >= (word_t{1}<<41))
            throw std::runtime_error("H116_SET_OVERWIDE_41");
        if(!result.words.empty() && address<=previous)
            throw std::runtime_error("H116_SET_UNSORTED_OR_DUPLICATE");
        previous=address;
        if(result.words.size()>=320) throw std::runtime_error("H116_SET_TOO_MANY_WORDS");
        result.words.emplace_back(address,value);
    };
    for(unsigned char c:raw) {
        if(c=='\n') {consume();line.clear();}
        else {if(c>127 || c==0) throw std::runtime_error("H116_SET_NON_ASCII");
              line.push_back(static_cast<char>(c));
              if(line.size()>64) throw std::runtime_error("H116_SET_LINE_TOO_LONG");}
    }
    if(!line.empty()) consume();
    if(!header || result.words.empty()) throw std::runtime_error("H116_SET_EMPTY");
    return result;
}
inline void install_at_init(Kyiv_t& cpu,const image& staged) {
    if(staged.words.empty() || staged.words.size()>320)
        throw std::runtime_error("H116_SET_INVALID_STAGE");
    // Invoked on a private, newly-created deferred CPU after ALL parsing,
    // hashes and conflicting launcher choices have been checked.
    for(const auto& w:staged.words) {
        if(w.first<03300 || w.first>=04000 || w.second>=(word_t{1}<<41))
            throw std::runtime_error("H116_SET_INVALID_WORD");
    }
    for(const auto& w:staged.words) cpu.kmem.write_rom(w.first,w.second);
}
} // namespace kyiv_rom_set_image_v1
#endif
