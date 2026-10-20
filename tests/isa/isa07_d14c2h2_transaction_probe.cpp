// Standalone actual C++ session: no fake CPU and no src/main.cpp linkage.
// Protocol is intentionally ASCII only; all machine words are decimal raw bits.
#include "kyiv_drum_transaction_v1.h"
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using kyiv_drum_media::geometry;
using kyiv_drum_transaction_v1::session;

static std::string mode(kyiv_drum_prepare::direction d) {
    return d == kyiv_drum_prepare::direction::read ? "R" : "W";
}

static void execute(session& s, const std::string& line) {
    std::istringstream in(line);
    std::string cmd, trailing;
    in >> cmd;
    if (cmd == "P") {
        std::uint64_t word = 0;
        if (!(in >> word) || (in >> trailing)) { std::cout << "ERR PROTOCOL\n"; return; }
        const auto value = s.prepare(word);
        std::cout << "P " << mode(value.requested) << ' '
                  << value.first.drum << ' ' << value.first.track
                  << ' ' << value.first.slot << '\n';
    } else if (cmd == "W") {
        std::size_t n = 0;
        if (!(in >> n) || n > 1000000) { std::cout << "ERR PROTOCOL\n"; return; }
        std::vector<std::uint64_t> words;
        words.reserve(n);
        for (std::size_t i=0; i<n; ++i) {
            std::uint64_t word = 0;
            if (!(in >> word)) { std::cout << "ERR PROTOCOL\n"; return; }
            words.push_back(word);
        }
        if (in >> trailing) { std::cout << "ERR PROTOCOL\n"; return; }
        const auto span = s.write_words(words);
        std::cout << "W " << span.last.track << ' ' << span.last.slot << '\n';
    } else if (cmd == "R") {
        std::size_t n = 0;
        if (!(in >> n) || (in >> trailing)) { std::cout << "ERR PROTOCOL\n"; return; }
        const auto data = s.read_words(n);
        std::cout << "R " << data.size();
        for (auto w : data) std::cout << ' ' << w;
        std::cout << '\n';
    } else if (cmd == "I") {
        std::size_t d=0, t=0, p=0;
        if (!(in >> d >> t >> p) || (in >> trailing)) { std::cout << "ERR PROTOCOL\n"; return; }
        const auto v = s.snapshot().inspect({d,t,p});
        std::cout << "I " << v.written << ' ' << v.word << '\n';
    } else if (cmd == "S") {
        if (in >> trailing) { std::cout << "ERR PROTOCOL\n"; return; }
        std::cout << "S " << s.snapshot().written_count() << ' '
                  << s.read_prepared() << ' ' << s.write_prepared() << '\n';
    } else if (cmd == "X") {
        // TEST ONLY: temporarily replace target path by a directory, then
        // attempt a write. Must restore original image even if a test fails.
        std::size_t n=0;
        if (!(in >> n) || n != 1) { std::cout << "ERR PROTOCOL\n"; return; }
        std::uint64_t word=0;
        if (!(in >> word) || (in >> trailing)) { std::cout << "ERR PROTOCOL\n"; return; }
        const auto old_file=s.image_path();
        const auto backup=fs::path(old_file.string()+".probe-backup");
        if (fs::exists(backup)) throw std::runtime_error("BACKUP_EXISTS");
        fs::rename(old_file,backup);
        try {
            fs::create_directory(old_file);
            try {
                s.write_words({word});
                std::cout << "ERR EXPECTED_RENAME_FAILURE\n";
            } catch (const kyiv_drum_media::media_error& e) {
                std::cout << "ERR " << e.what() << '\n';
            }
            fs::remove(old_file);
            fs::rename(backup,old_file);
        } catch (...) {
            std::error_code ec;
            fs::remove(old_file,ec);
            fs::rename(backup,old_file,ec);
            throw;
        }
    } else {
        std::cout << "ERR PROTOCOL\n";
    }
}

int main(int argc, char** argv) {
    if (argc != 6) return 2;
    try {
        const auto g = geometry{argv[2],3u,static_cast<std::size_t>(std::stoull(argv[3])),
                               static_cast<std::size_t>(std::stoull(argv[4]))};
        session s(argv[1],g,kyiv_drum_host_address::policy::a3_linear_v1,
                  static_cast<unsigned>(std::stoul(argv[5])));
        std::cout << "INIT OK\n";
        std::string line;
        while (std::getline(std::cin,line)) {
            try { execute(s,line); }
            catch (const std::exception& e) { std::cout << "ERR " << e.what() << '\n'; }
        }
    } catch (const std::exception& e) {
        std::cout << "INIT ERR " << e.what() << '\n';
    }
}
