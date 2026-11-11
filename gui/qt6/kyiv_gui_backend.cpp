// Kyiv demonstration control bridge: persistent CPU, bounded stepping, in-process checkpoint.
// Build links unchanged src/main.cpp and src/asm_disasm.cpp (main renamed in the latter).
// Protocol: exactly one tab-separated response line per request; no writes to repository.
#include "kyiv.h"
#include "kyiv_host_image_v1.h"
#include "kyiv_rom_boot_v1.h"
#include "kyiv_rom_set_image_v1.h"

#include <cctype>
#include <algorithm>
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {
struct Snapshot {
    Kyiv_memory_t memory;
    std::uint64_t C, K, P, Loop, A, B;
    bool T, emergency_stop;
    std::size_t h;
    int perfo, drum_nr, drum_zr, drum_nw, drum_zw;
    kyiv_h10_output::profile output_mode;
    std::uint64_t executed;
};

Snapshot save(const Kyiv_t& c, std::uint64_t steps) {
    if (c.has_experimental_drum()) throw std::runtime_error("DRUM_CHECKPOINT_UNSUPPORTED");
    return {c.kmem, c.C_reg, c.K_reg, c.P_reg, c.Loop_reg, c.A_reg,
            c.B_tumb, c.T_reg, c.emergency_stop_blocked, c.h, c.perfo_num,
            c.drum_num_read, c.drum_zone_read, c.drum_num_write,
            c.drum_zone_write, c.io22_output_mode, steps};
}
void restore(Kyiv_t& c, const Snapshot& s) {
    if (c.has_experimental_drum()) throw std::runtime_error("DRUM_CHECKPOINT_UNSUPPORTED");
    c.kmem = s.memory;
    c.C_reg=s.C; c.K_reg=s.K; c.P_reg=s.P; c.Loop_reg=s.Loop;
    c.A_reg=s.A; c.B_tumb=s.B; c.T_reg=s.T;
    c.emergency_stop_blocked=s.emergency_stop; c.h=s.h;
    c.perfo_num=s.perfo; c.drum_num_read=s.drum_nr;
    c.drum_zone_read=s.drum_zr; c.drum_num_write=s.drum_nw;
    c.drum_zone_write=s.drum_zw; c.io22_output_mode=s.output_mode;
}

std::string oct(std::uint64_t value, unsigned width) {
    std::ostringstream s;
    s << std::oct << std::setw(width) << std::setfill('0') << value;
    return s.str();
}
std::uint64_t parse_octal(const std::string& s, unsigned width,
                          std::uint64_t maximum) {
    if (s.size()!=width) throw std::runtime_error("INVALID_OCTAL_WIDTH");
    std::uint64_t out=0;
    for (char c : s) {
        if (c<'0'||c>'7') throw std::runtime_error("INVALID_OCTAL_DIGIT");
        out=(out<<3)+static_cast<unsigned>(c-'0');
    }
    if (out>maximum) throw std::runtime_error("OCTAL_OUT_OF_RANGE");
    return out;
}
unsigned parse_count(const std::string& s, unsigned max) {
    if (s.empty() || s.size()>5) throw std::runtime_error("INVALID_COUNT");
    unsigned out=0;
    for (char c : s) {
        if (c<'0'||c>'9') throw std::runtime_error("INVALID_DECIMAL_COUNT");
        out=10*out+static_cast<unsigned>(c-'0');
    }
    if (out==0 || out>max) throw std::runtime_error("COUNT_OUT_OF_RANGE");
    return out;
}
std::vector<std::string> fields(const std::string& line) {
    std::vector<std::string> parts;
    std::size_t from=0;
    while (true) {
        const auto at=line.find('\t',from);
        if (at==std::string::npos) {parts.emplace_back(line.substr(from));break;}
        parts.emplace_back(line.substr(from,at-from));
        from=at+1;
    }
    return parts;
}
void require_args(const std::vector<std::string>& v,std::size_t size) {
    if (v.size()!=size) throw std::runtime_error("WRONG_ARGUMENT_COUNT");
}
std::string state(const Kyiv_t& c,std::uint64_t steps) {
    return "C="+oct(c.C_reg,4)+"\tK="+oct(c.K_reg,14)+
           "\tA="+oct(c.A_reg,4)+"\tP="+oct(c.P_reg,4)+
           "\tLOOP="+oct(c.Loop_reg,4)+"\tT="+(c.T_reg?"1":"0")+
           "\tSTEPS="+std::to_string(steps);
}
// Keeps the historical CPU's verbose diagnostics off the line protocol.
class Silence {
    std::ostringstream suppressed_;
    std::streambuf* previous_;
public:
    Silence() : previous_(std::cout.rdbuf(suppressed_.rdbuf())) {}
    ~Silence() {std::cout.rdbuf(previous_);}
    Silence(const Silence&)=delete;
    Silence& operator=(const Silence&)=delete;
};

struct Server {
    kyiv_rom_boot_v1::image rom;
    std::optional<kyiv_rom_set_image_v1::image> rom_set;
    std::unique_ptr<Kyiv_t> cpu;
    std::optional<Snapshot> checkpoint;
    std::uint64_t executed=0;
    bool fault=false;
    // HOST FP dispatcher boundary: not a machine STOP instruction.
    std::optional<std::uint64_t> fp_end_pointer;
    bool fp_done=false;
    bool saved_fp_done=false;
    // H118: same dispatcher counter as the H115 CLI (PC==3305, including
    // the final END_POINTER boundary); protocol-only, no CPU changes.
    std::uint64_t fp_dispatches=0, saved_fp_dispatches=0;

    bool at_fp_end(const Kyiv_t& m) const {
        return fp_end_pointer && m.C_reg==03305 &&
               ((m.kmem.read_memory(00014)>>12)&07777ULL)==*fp_end_pointer;
    }
    std::string fp_status() const {
        if (!fp_end_pointer) return "";
        return "\tDISPATCHES="+std::to_string(fp_dispatches)+
               (fp_done ? "\tEND_POINTER=1" : "");
    }

    explicit Server(const std::string& rom_path,
                    const std::string& set_path,
                    const std::string& set_sha) {
        kyiv_rom_boot_v1::arguments args;
        args.explicit_rom=true;
        args.rom_filename=rom_path;
        args.expected_sha256=kyiv_rom_boot_v1::pinned_default_sha256;
        rom=kyiv_rom_boot_v1::read(args, "");
        if (!rom.sha_pinned || rom.sha256!=args.expected_sha256)
            throw std::runtime_error("ROM_SHA_UNPINNED");
        if (!set_path.empty()) {
            kyiv_rom_set_image_v1::arguments opt;
            opt.selected=true; opt.filename=set_path;
            opt.expected_sha256=kyiv_rom_set_image_v1::normalize_sha(set_sha);
            rom_set=kyiv_rom_set_image_v1::read(opt);
        }
    }
    Kyiv_t& get() {
        if (!cpu) throw std::runtime_error("LOAD_IMAGE_FIRST");
        return *cpu;
    }
    std::string handle(const std::vector<std::string>& a) {
        if (a.empty()) throw std::runtime_error("EMPTY_REQUEST");
        if (a[0]=="PING") {
            require_args(a,1);
            return "OK\tPING\tPROTOCOL=1\tROM_SHA256="+rom.sha256+
                   (rom_set ? "\tROMSET_SHA256="+rom_set->sha256 : "");
        }
        if (a[0]=="LOAD" || a[0]=="LOADFP") {
            const bool fp = a[0]=="LOADFP";
            require_args(a,fp ? 4 : 3);
            if (fp && !rom_set) throw std::runtime_error("FP_ROM_SET_REQUIRED");
            if (a[1].empty() || a[1].find('\n')!=std::string::npos ||
                a[1].find('\r')!=std::string::npos)
                throw std::runtime_error("INVALID_IMAGE_PATH");
            const auto start=parse_octal(a[2],4,03777);
            if (!kyiv_host_image_v1::usable_address(start))
                throw std::runtime_error("INVALID_START");
            const auto image=kyiv_host_image_v1::load_file(a[1],false);
            std::optional<std::uint64_t> end;
            if (fp) {
                if (start>=02000) throw std::runtime_error("FP_ENTRY_NOT_RAM");
                if (std::none_of(image.begin(),image.end(),[start](const auto& rec){
                        return rec.first==start;
                    })) throw std::runtime_error("FP_ENTRY_ABSENT");
                const auto value=parse_octal(a[3],4,01777);
                if (!kyiv_host_image_v1::usable_address(value) ||
                    std::none_of(image.begin(),image.end(),[value](const auto& rec){
                        return rec.first==value;
                    })) throw std::runtime_error("FP_END_POINTER_ABSENT");
                end=value;
            }
            auto next=std::make_unique<Kyiv_t>(Kyiv_t::rom_boot_mode::deferred);
            kyiv_rom_boot_v1::install(*next,rom);
            if (rom_set) kyiv_rom_set_image_v1::install_at_init(*next,*rom_set);
            for (const auto& rec:image) {
                if (rec.first>=03000) throw std::runtime_error("ROM_IMAGE_NOT_ALLOWED");
                next->kmem.write_memory(rec.first,rec.second);
            }
            if (fp) {
                // H115-B22: enter the ROM interpreter, never execute FP user opcodes as CPU opcodes.
                next->kmem.set_panel_nk_word(03000,start<<12);
                next->kmem.select_panel_nk(03000,true);
                next->emergency_stop_blocked=true;
                next->C_reg=03300;
            } else {
                next->C_reg=start;
            }
            cpu.swap(next); // No loss of old state if any input validation failed.
            checkpoint.reset(); executed=0; fault=false;
            fp_end_pointer=end; fp_done=false; saved_fp_done=false;
            fp_dispatches=0; saved_fp_dispatches=0;
            return std::string("OK\t")+(fp ? "LOADFP" : "LOAD")+
                   "\tWORDS="+std::to_string(image.size())+"\t"+state(*cpu,executed)+
                   (fp ? "\tFP_ENTRY="+oct(start,4)+"\tFP_END_POINTER="+oct(*end,4) : "");
        }
        if (a[0]=="STATE") {
            require_args(a,1);
            return "OK\tSTATE\t"+state(get(),executed)+fp_status();
        }
        if (a[0]=="STEP") {
            require_args(a,2);
            const auto n=parse_count(a[1],32);
            Kyiv_t& m=get();
            if (fault) throw std::runtime_error("CPU_FAULT_RELOAD_OR_RESTORE");
            if (m.T_reg || fp_done) return "OK\tSTEP\tEXECUTED=0\tPATH=-\t"+
                                            state(m,executed)+fp_status();
            std::string path;
            unsigned done=0;
            for (;done<n && !m.T_reg;++done) {
                // H115 counts every encounter with the dispatcher, including
                // final END_POINTER; save/restore must rewind this counter.
                if (fp_end_pointer && m.C_reg==03305) ++fp_dispatches;
                if (at_fp_end(m)) { fp_done=true; break; }
                if (!path.empty()) path+=',';
                path+=oct(m.C_reg,4);
                try {
                    bool cont=false;
                    {Silence quiet;cont=m.execute_opcode();}
                    ++executed;
                    if (!cont) break;
                } catch (...) {fault=true;throw;}
            }
            // Detect completion even when the last requested step reached the boundary.
            if (!fp_done && at_fp_end(m)) {
                // A STEP batch can stop precisely on the boundary; count it
                // now, once, even though the CPU does not execute this word.
                ++fp_dispatches;
                fp_done=true;
            }
            // 'done' excludes the last instruction when it stops the CPU.
            const unsigned actual=static_cast<unsigned>(std::count(path.begin(),path.end(),',')) + (path.empty()?0:1);
            return "OK\tSTEP\tEXECUTED="+std::to_string(actual)+
                   "\tPATH="+(path.empty()?"-":path)+"\t"+state(m,executed)+fp_status();
        }
        if (a[0]=="DUMP") {
            require_args(a,3);
            const auto address=parse_octal(a[1],4,03777);
            const unsigned n=parse_count(a[2],64);
            if (address+n>04000) throw std::runtime_error("DUMP_OUTSIDE_MEMORY");
            Kyiv_t& m=get();
            std::string payload;
            for (unsigned i=0;i<n;++i) {
                if (i) payload+=',';
                payload+=oct(m.kmem.read_memory(address+i),14);
            }
            return "OK\tDUMP\tSTART="+oct(address,4)+
                   "\tCOUNT="+std::to_string(n)+"\tDATA="+payload;
        }
        if (a[0]=="SAVE") {
            require_args(a,1);
            checkpoint=save(get(),executed);
            saved_fp_done=fp_done; saved_fp_dispatches=fp_dispatches;
            return "OK\tSAVE\t"+state(*cpu,executed)+fp_status();
        }
        if (a[0]=="RESTORE") {
            require_args(a,1);
            if (!checkpoint) throw std::runtime_error("NO_CHECKPOINT");
            restore(get(),*checkpoint);
            executed=checkpoint->executed;fault=false;
            fp_done=saved_fp_done; fp_dispatches=saved_fp_dispatches;
            return "OK\tRESTORE\t"+state(*cpu,executed)+fp_status();
        }
        if (a[0]=="SETNK") {
            require_args(a,3);
            const auto addr=parse_octal(a[1],4,03777);
            if (!Kyiv_NK_panel_t::is_selectable(addr))
                throw std::runtime_error("ONLY_NK3000_TO_3002");
            const auto word=parse_octal(a[2],14,(std::uint64_t{1}<<41)-1);
            Kyiv_t& m=get();
            m.kmem.set_panel_nk_word(addr,word);
            m.kmem.select_panel_nk(addr,true);
            return "OK\tSETNK\tADDR="+oct(addr,4)+"\tWORD="+oct(word,14);
        }
        if (a[0]=="CLEARNK") {
            require_args(a,2);
            const auto addr=parse_octal(a[1],4,03777);
            if (!Kyiv_NK_panel_t::is_selectable(addr))
                throw std::runtime_error("ONLY_NK3000_TO_3002");
            get().kmem.select_panel_nk(addr,false);
            return "OK\tCLEARNK\tADDR="+oct(addr,4);
        }
        if (a[0]=="QUIT") {require_args(a,1);return "OK\tQUIT";}
        throw std::runtime_error("UNKNOWN_COMMAND");
    }
};
}

int main(int argc,char** argv) {
    if ((argc!=2 && argc!=6) ||
        (argc==6 && (std::string(argv[2])!="--rom-set-image" ||
                      std::string(argv[4])!="--rom-set-sha256"))) {
        std::cerr << "Usage: kyiv_gui_backend.exe PATH_TO_ROM_TXT "
                     "[--rom-set-image IMAGE.k41 --rom-set-sha256 HEX]\n";
        return 2;
    }
    try {
        Server server(argv[1],argc==6 ? argv[3] : "",
                      argc==6 ? argv[5] : "");
        std::string line;
        while (std::getline(std::cin,line)) {
            try {
                const auto a=fields(line);
                const std::string out=server.handle(a);
                std::cout << out << std::endl;
                if (!a.empty() && a[0]=="QUIT") break;
            } catch (const std::exception& e) {
                std::string msg=e.what();
                for (char& c:msg) if (c=='\r'||c=='\n'||c=='\t') c=' ';
                std::cout << "ERR\t" << msg << std::endl;
            }
        }
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "GUI_BACKEND_INIT_FAIL: " << e.what() << '\n';
        return 1;
    }
}
