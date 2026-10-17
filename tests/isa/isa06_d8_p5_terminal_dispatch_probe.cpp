// ISA-06 D8-P5: bounded terminal dispatcher and isolated STOP entry characterization.
// GY62 (1962) Appendix 2, printed p.171, original machine words 0157,0161,0164..0166.
// ROM[3000], ROM[3042], RAM[0014/0017] and registers are injected fixtures.
// ALL behavioral scenarios are POLICY; targets 0022/0177 remain UNEXECUTED.
#include <cstdint>
#include <exception>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }
namespace {
using W=uint64_t;
constexpr W SIGN=W{1}<<40;
constexpr W TOP_MAG=W{1}<<39;
constexpr W WORD_0157=0'16'0017'3042'0161ULL;
constexpr W WORD_0161=0'31'0014'0162'0164ULL;
constexpr W WORD_0164=0'31'3000'0022'0177ULL;
constexpr W WORD_0165=0'33'0000'0001'0077ULL;
constexpr W WORD_0166=0'33'0000'0003'0177ULL;
struct Silence {
    std::ostringstream unused;
    std::streambuf* saved;
    Silence():saved(std::cout.rdbuf(unused.rdbuf())){}
    ~Silence(){std::cout.rdbuf(saved);}
};
bool tick(Kyiv_t& cpu){Silence s;return cpu.execute_opcode();}
std::string oct(W value){std::ostringstream s;s<<std::oct<<value;return s.str();}
void init(Kyiv_t& cpu, W rom3000){
    // Deliberately bypass the working-directory-dependent ROM loader.
    cpu.kmem.write_rom(03000,rom3000);
    cpu.kmem.write_rom(03042,TOP_MAG);
    cpu.kmem.write_memory(0157,WORD_0157);
    cpu.kmem.write_memory(0161,WORD_0161);
    cpu.kmem.write_memory(0164,WORD_0164);
    cpu.kmem.write_memory(0165,WORD_0165);
    cpu.kmem.write_memory(0166,WORD_0166);
    cpu.kmem.write_memory(0014,SIGN); // force the branch to original 0164
    cpu.kmem.write_memory(0017,TOP_MAG);
    cpu.C_reg=0157; cpu.A_reg=0; cpu.Loop_reg=077;
    cpu.P_reg=0371; cpu.T_reg=false; cpu.B_tumb=0;
}
struct Step {W pc,k,next;};

bool terminal_dispatch(const char* name,W rom3000,W destination){
    Kyiv_t cpu;init(cpu,rom3000);
    constexpr W PCS[]={0157,0161,0164};
    constexpr W WORDS[]={WORD_0157,WORD_0161,WORD_0164};
    const W NEXT[]={0161,0164,destination};
    W first_bad_pc=0, fetched_k=0;std::string why;
    size_t count=0;
    for(size_t i=0;i<3;++i){
        const W pc=cpu.C_reg;
        bool running=false;
        try {running=tick(cpu);}
        catch(const std::exception& e){first_bad_pc=pc;why=e.what();break;}
        ++count;
        if(pc!=PCS[i]||cpu.K_reg!=WORDS[i]||!running||cpu.T_reg||cpu.C_reg!=NEXT[i]){
            first_bad_pc=pc;fetched_k=cpu.K_reg;why="unexpected K, STOP or next PC";break;
        }
    }
    const bool ok=why.empty() && count==3 && cpu.C_reg==destination &&
        cpu.kmem.read_memory(03000)==rom3000 &&
        cpu.kmem.read_memory(0014)==SIGN &&
        cpu.kmem.read_memory(0017)==TOP_MAG &&
        cpu.P_reg==0371 && cpu.A_reg==0 && cpu.Loop_reg==077;
    std::cout<<(ok?"POLICY-PASS ":"POLICY-FAIL ")<<name
             <<" steps="<<count<<" rom3000="<<oct(rom3000)
             <<" next_pc="<<oct(cpu.C_reg)<<" expected="<<oct(destination)
             <<" first_bad_pc="<<oct(first_bad_pc)<<" fetched_K="<<oct(fetched_k)
             <<" reason="<<why<<" target_unexecuted=1\n";
    return ok;
}

bool direct_stop(const char* name,W pc,W word){
    Kyiv_t cpu;init(cpu,0);
    cpu.C_reg=pc;
    bool running=true;
    std::string why;
    try{running=tick(cpu);}catch(const std::exception& e){why=e.what();}
    // No claim that 0164 reaches 0165/0166; no claim about STOP code / PC increment.
    const bool ok=why.empty() && !running && cpu.T_reg && cpu.K_reg==word &&
                  cpu.P_reg==0371 && cpu.A_reg==0 && cpu.Loop_reg==077;
    std::cout<<(ok?"POLICY-PASS ":"POLICY-FAIL ")<<name
             <<" direct_entry_pc="<<oct(pc)<<" fetched_K="<<oct(cpu.K_reg)
             <<" stopped="<<cpu.T_reg<<" returned_running="<<running
             <<" observed_next_pc="<<oct(cpu.C_reg)
             <<" reachable_from_0164=OPEN reason="<<why<<'\n';
    return ok;
}
}

int main(){
    try {
        const bool a=terminal_dispatch("rom3000_plus_zero_routes_0022",0,0022);
        const bool b=terminal_dispatch("rom3000_minus_zero_routes_0177",SIGN,0177);
        const bool c=terminal_dispatch("rom3000_negative_one_routes_0177",SIGN|1,0177);
        const bool d=direct_stop("isolated_original_0165_STOP",0165,WORD_0165);
        const bool e=direct_stop("isolated_original_0166_STOP",0166,WORD_0166);
        const int pass=int(a)+int(b)+int(c)+int(d)+int(e);
        std::cout<<"ISA-06 D8-P5 STRICT=0/0 DOC-MISMATCH=0 POLICY="<<pass
                 <<"/5 POLICY-FAIL="<<(5-pass)<<" OBS=0\n";
        return pass==5?0:1;
    } catch(const std::exception& e){
        std::cerr<<"POLICY-FAIL unhandled exception="<<e.what()<<'\n';return 1;
    }
}
