#ifndef KYIVEMU_H115_FP_CLI_V2_H
#define KYIVEMU_H115_FP_CLI_V2_H
// H115-B22 R2: a HOST launch adapter, not an FP arithmetic implementation.
// Any SHA-pinned, well-formed interchangeable-ROM image may be selected.
// CPU memory reads/operations are governed solely by Kyiv_t, NOT a hidden
// per-program HOST allowlist. Test-specific oracles live outside this header.
#include "kyiv.h"
#include "kyiv_host_image_v1.h"
#include "kyiv_rom_boot_v1.h"
#include "kyiv_sha256_v1.h"
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <streambuf>
#include <string>
#include <utility>
#include <vector>

namespace kyiv_fp_cli_v2 {
using W = std::uint64_t;
struct failure : std::runtime_error { using std::runtime_error::runtime_error; };
inline void require(bool ok, const std::string& why) {
    if (!ok) throw failure(why);
}
inline std::string oct(W n, int width) {
    std::ostringstream os;
    os << std::oct << std::setfill('0') << std::setw(width) << n;
    return os.str();
}
inline std::vector<unsigned char> read_bytes(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    require(bool(in), "FP_FILE_OPEN_FAILED");
    std::vector<unsigned char> result;
    for (char buffer[4096]; in;) {
        in.read(buffer, sizeof(buffer));
        const auto n = in.gcount();
        for (std::streamsize i=0; i<n; ++i) {
            require(result.size()<1048576, "FP_FILE_TOO_LARGE");
            result.push_back(static_cast<unsigned char>(buffer[i]));
        }
    }
    require(in.eof(), "FP_FILE_READ_FAILED");
    return result;
}
inline W parse_addr(const char* arg) {
    return kyiv_host_image_v1::parse_octal(arg, 4);
}
struct selection {
    std::string program, rom, rom_sha;
    W entry=0, end=0;
    bool has_end=false, verbose_cpu=false, trace_steps=false;
    std::size_t limit=0;
    std::vector<W> watches;
};
inline selection parse(int argc, char** argv) {
    require(argc>=8 && argv,
      "FP_USAGE: fp-image PROGRAM.k41 ENTRY_OCTAL MAX_STEPS_DECIMAL "
      "--fp-rom ROM.k41 --fp-sha256 HEX [--end-pointer OCTAL] "
      "[--watch OCTAL] [--trace-steps] [--verbose-cpu]");
    selection s;
    require(argv[2] && argv[3] && argv[4], "FP_MISSING_POSITIONAL");
    s.program=argv[2];
    require(!s.program.empty() && s.program.substr(0,2)!="--", "FP_PROGRAM_PATH");
    s.entry=parse_addr(argv[3]);
    require(s.entry>=0001 && s.entry<02000, "FP_ENTRY_NOT_RAM");
    s.limit=kyiv_host_image_v1::parse_limit(argv[4]);
    bool got_rom=false, got_sha=false;
    std::set<W> seen_watches;
    for (int i=5;i<argc;++i) {
        require(argv[i]!=nullptr, "FP_NULL_ARGUMENT");
        const std::string option=argv[i];
        if(option=="--fp-rom") {
            require(!got_rom && i+1<argc && argv[i+1], "FP_ROM_OPTION");
            s.rom=argv[++i];
            require(!s.rom.empty() && s.rom.substr(0,2)!="--", "FP_ROM_PATH");
            got_rom=true;
        } else if(option=="--fp-sha256") {
            require(!got_sha && i+1<argc && argv[i+1], "FP_SHA_OPTION");
            s.rom_sha=kyiv_rom_boot_v1::normalize_sha(argv[++i]);
            got_sha=true;
        } else if(option=="--end-pointer") {
            require(!s.has_end && i+1<argc && argv[i+1], "FP_END_OPTION");
            s.end=parse_addr(argv[++i]);
            require(s.end>=0001 && s.end<02000, "FP_END_NOT_RAM");
            s.has_end=true;
        } else if(option=="--watch") {
            require(i+1<argc && argv[i+1], "FP_WATCH_MISSING");
            const W addr=parse_addr(argv[++i]);
            require(addr<02000 || (addr>=03000 && addr<04000), "FP_WATCH_ADDRESS");
            require(seen_watches.insert(addr).second, "FP_WATCH_DUPLICATE");
            s.watches.push_back(addr);
        } else if(option=="--trace-steps") {
            require(!s.trace_steps, "FP_TRACE_DUPLICATE");
            s.trace_steps=true;
        } else if(option=="--verbose-cpu") {
            require(!s.verbose_cpu, "FP_VERBOSE_DUPLICATE");
            s.verbose_cpu=true;
        } else throw failure("FP_UNKNOWN_OPTION:"+option);
    }
    require(got_rom && got_sha, "FP_ROM_AND_SHA_REQUIRED");
    return s;
}
struct discard_buffer : std::streambuf {
    int overflow(int c) override {return traits_type::not_eof(c);}
};
class silence_stdout {
    std::streambuf* saved=nullptr;
    discard_buffer sink;
public:
    explicit silence_stdout(bool muted) {
        if(muted) saved=std::cout.rdbuf(&sink);
    }
    ~silence_stdout(){ if(saved) std::cout.rdbuf(saved); }
    silence_stdout(const silence_stdout&)=delete;
    silence_stdout& operator=(const silence_stdout&)=delete;
};
inline int execute(int argc, char** argv) {
    const selection cfg=parse(argc,argv);
    const auto rom_raw=read_bytes(cfg.rom);
    require(kyiv_sha256_v1::digest(rom_raw)==cfg.rom_sha, "FP_ROM_SHA256_MISMATCH");
    const auto fp_rom=kyiv_host_image_v1::load_file(cfg.rom,true);
    require(!fp_rom.empty() && fp_rom.size()<=320, "FP_ROM_WORD_COUNT");
    std::set<W> rom_addresses;
    for(const auto& word:fp_rom) {
        require(word.first>=03300 && word.first<04000, "FP_ROM_OUTSIDE_REPLACEABLE_RANGE");
        require(rom_addresses.insert(word.first).second, "FP_ROM_DUPLICATE");
    }
    const auto program=kyiv_host_image_v1::load_file(cfg.program,false);
    std::set<W> program_addresses;
    for (const auto& word:program) {
        require(word.first>=0001 && word.first<02000, "FP_PROGRAM_NOT_RAM");
        require(program_addresses.insert(word.first).second, "FP_PROGRAM_DUPLICATE");
    }
    require(program_addresses.count(cfg.entry), "FP_ENTRY_NOT_IN_IMAGE");
    if(cfg.has_end) require(program_addresses.count(cfg.end), "FP_END_NOT_IN_IMAGE");
    const auto program_sha=kyiv_sha256_v1::digest(read_bytes(cfg.program));
    const auto fixed=kyiv_rom_boot_v1::read(kyiv_rom_boot_v1::arguments{}, argv[0]);
    require(fixed.source_is_default && fixed.sha_pinned, "FP_FIXED_ROM_NOT_PINNED");
    require(fixed.sha256==kyiv_rom_boot_v1::pinned_default_sha256, "FP_FIXED_ROM_SHA_DRIFT");
    // All files and address ranges validated before constructing/mutating CPU.
    Kyiv_t cpu(Kyiv_t::rom_boot_mode::deferred);
    kyiv_rom_boot_v1::install(cpu,fixed);
    for(const auto& word:fp_rom) cpu.kmem.write_rom(word.first,word.second);
    for(const auto& word:program) cpu.kmem.write_memory(word.first,word.second);
    // The historical FP interpreter fetches a user-program pointer via NK 3000.
    // This panel word is a startup input, not a runtime HOST-side PC override.
    cpu.kmem.set_panel_nk_word(03000,W(cfg.entry)<<12);
    cpu.kmem.select_panel_nk(03000,true);
    cpu.emergency_stop_blocked=true;
    cpu.C_reg=03300;
    std::cout << "H115-FP-BOOT STATUS=PASS ROM=EXPLICIT_SHA256 SHA256=" << cfg.rom_sha
              << " ROM_WORDS="<<fp_rom.size()<<" PROGRAM_SHA256="<<program_sha
              << " ENTRY="<<oct(cfg.entry,4)
              << " END="<<(cfg.has_end?oct(cfg.end,4):"NONE")<<'\n';
    std::size_t steps=0, dispatches=0;
    bool ended=false, cpu_stopped=false;
    while(steps<cfg.limit) {
        const W pc=cpu.C_reg;
        const W pointer=(cpu.kmem.read_memory(0014)>>12)&07777ULL;
        if(pc==03305) {
            ++dispatches;
            if(cfg.has_end && pointer==cfg.end) { ended=true; break; }
        }
        // No HOST opcode/read allowlist: an ordinary machine program may
        // access panel words 3000..3007, fixed ROM, RAM and legal IO.
        // The real production CPU decides instruction semantics.
        bool proceed=false;
        {
            silence_stdout quiet(!cfg.verbose_cpu);
            proceed=cpu.execute_opcode();
        }
        ++steps;
        if(cfg.trace_steps)
            std::cout << "H115-FP-TRACE STEP="<<steps<<" PC="<<oct(pc,4)
                      <<" C_AFTER="<<oct(cpu.C_reg,4)
                      <<" PTR_BEFORE="<<oct(pointer,4)<<'\n';
        if(!proceed) { cpu_stopped=true; break; }
    }
    const char* status=ended?"END_POINTER":(cpu_stopped?"CPU_STOP":"LIMIT");
    std::cout << "H115-FP-RUN STATUS="<<status<<" STEPS="<<steps
              <<" DISPATCHES="<<dispatches<<" C="<<oct(cpu.C_reg,4)
              <<" POINTER="<<oct((cpu.kmem.read_memory(0014)>>12)&07777ULL,4)
              <<" HISTORICAL_ROM_AUTHENTICATED=NO\n";
    for(W addr:cfg.watches) {
        std::cout<<"H115-FP-WATCH ADDR="<<oct(addr,4)
                 <<" RAW="<<oct(cpu.kmem.read_memory(addr),14)<<'\n';
    }
    if(!ended && !cpu_stopped) {
        std::cerr<<"H115-FP-HOLD FP_STEP_LIMIT\n";
        return 5;
    }
    return 0;
}
inline int run(int argc,char**argv) {
    try {return execute(argc,argv);}
    catch(const std::exception& ex) {
        std::cerr<<"H115-FP-HOLD "<<ex.what()<<'\n';
        return 4;
    }
}
} // namespace kyiv_fp_cli_v2
#endif
