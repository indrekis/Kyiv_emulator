// A6/H29: native Ky iv opcode 013, seven verbatim GY62 test instructions.
// Values in source cases and expected outputs are immutable; no hardware oracle.
#include <cstdint>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <map>
#include <vector>
#include "kyiv.h"
#include "asm_disasm.h"
int disassembly(const std::uint64_t&, Kyiv_memory_t&, const addr3_t&) {return 0;}
namespace {
using W=std::uint64_t;
constexpr W S=W{1}<<40;
std::map<W,W> load_program(const std::string& path) {
    std::ifstream f(path);
    if (!f) throw std::runtime_error("missing pinned GY62 .k41: "+path);
    std::string magic;
    std::getline(f,magic);
    if (magic!="KYIV41-OCT1") throw std::runtime_error("GY62 bad header");
    std::map<W,W> out;
    std::string row;
    while(std::getline(f,row)){
        if(row.empty())continue;
        std::istringstream ss(row);
        std::string a,w,extra;
        if(!(ss>>a>>w) || ss>>extra || a.find_first_not_of("01234567")!=std::string::npos ||
           w.find_first_not_of("01234567")!=std::string::npos || w.size()!=14)
            throw std::runtime_error("GY62 bad row: "+row);
        W addr=std::stoull(a,nullptr,8), word=std::stoull(w,nullptr,8);
        if (!out.emplace(addr,word).second) throw std::runtime_error("GY62 duplicate address");
    }
    return out;
}
std::string oct14(W w){std::ostringstream s;s<<std::oct<<std::setfill('0')<<std::setw(14)<<w;return s.str();}
struct Silence {std::ostringstream os; std::streambuf* old;
    Silence():old(std::cout.rdbuf(os.rdbuf())){} ~Silence(){std::cout.rdbuf(old);} };
struct Case { W pc,shift_const,operand,expected,command; };
}
int main(int argc,char**argv) {
 try {
    if(argc!=2)throw std::runtime_error("usage: native_probe path/to/au1_batch38_0300_0345.k41");
    auto source=load_program(argv[1]);
    const Case cases[]={
      {0307,00000000000014ULL,00000000000000ULL,00000000000000ULL,013033700000347ULL},
      {0312,00000000000014ULL,020000000000000ULL,00000000000000ULL,013033730260347ULL},
      {0315,020000000000014ULL,020000000000000ULL,00002000000000ULL,013034030260347ULL},
      {0320,00000000000050ULL,020000000000001ULL,020000000000000ULL,013034131770347ULL},
      {0323,020000000000050ULL,020000000000001ULL,00000000000001ULL,013034231770347ULL},
      {0326,020000000000100ULL,025252525252525ULL,020000000000000ULL,013034400030347ULL},
      {0331,020000000000101ULL,025252525252525ULL,00000000000000ULL,013034500030347ULL},
    };
    // Exact commands/constants verified against pinned source text, not invented test instructions.
    unsigned total=0,pass=0;
    for(const auto& c:cases){
       const auto it=source.find(c.pc);
       if(it==source.end() || it->second!=c.command)throw std::runtime_error("GY62 source command differs at pc "+oct14(c.pc));
       Kyiv_t cpu(Kyiv_t::rom_boot_mode::deferred);
       cpu.kmem.write_rom(03026,S); // pinned mem/ROM.txt 3026 = -0
       cpu.kmem.write_rom(03177,S|1); // pinned mem/ROM.txt 3177 = -2^-40
       cpu.kmem.write_memory(0003,025252525252525ULL); // GY62 p.174 test operand
       for(W addr=0337; addr<=0345; ++addr){
          auto pos=source.find(addr);
          if(pos==source.end()) throw std::runtime_error("GY62 missing constant");
          cpu.kmem.write_memory(addr,pos->second);
       }
       cpu.kmem.write_memory(c.pc,c.command);
       cpu.C_reg=c.pc; cpu.A_reg=0017; cpu.P_reg=0137; cpu.Loop_reg=0765;
       const W first=cpu.kmem.read_memory((c.command>>24)&07777);
       const W second=cpu.kmem.read_memory((c.command>>12)&07777);
       if(first!=c.shift_const || second!=c.operand)
           throw std::runtime_error("source fixture mismatched at pc "+oct14(c.pc));
       bool running=false;
       {Silence quiet; running=cpu.execute_opcode();}
       const W got=cpu.kmem.read_memory(0347);
       const bool ok=running && !cpu.T_reg && cpu.K_reg==c.command &&
           cpu.C_reg==c.pc+1 && got==c.expected &&
           cpu.A_reg==0017 && cpu.P_reg==0137 && cpu.Loop_reg==0765;
       pass+=ok; ++total;
       std::cout << (ok?"STRICT-PASS":"DOC-MISMATCH") << " PC=" <<std::oct<<c.pc
                 <<" K="<<oct14(cpu.K_reg)<<" got="<<oct14(got)
                 <<" expected="<<oct14(c.expected)<<std::dec<<"\n";
    }
    std::cout << "H29_NATIVE_GY62="<<pass<<"/"<<total
              <<"; SOURCE=PINNED; CPU=PRODUCTION; HARDWARE_ORACLE=NO\n";
    return total==7 && pass==7?0:1;
 }catch(const std::exception& e){std::cerr<<"H29_NATIVE_FAIL="<<e.what()<<"\n";return 2;}
}
