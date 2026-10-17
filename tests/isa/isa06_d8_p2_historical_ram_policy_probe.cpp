// ISA-06 D8-P2: ORIGINAL fourth RAM diagnostic words + controlled memory.
// GY62 (1962), printed pp. 170-171; original words reused verbatim from D5.
// All signed-zero-copy expectations are emulator POLICY, not historical STRICT.
// ROM 3012/3026/3042 and RAM initial conditions are explicit test fixtures.
#include <cstdint>
#include <exception>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
using W=uint64_t;
constexpr W SIGN=W{1} << 40;
constexpr W UPPER_MAG=W{1} << 39;
constexpr W RET=0371;
constexpr W SENTINEL=077;

struct HistoricalWord { W pc, word; };
// Direct 14-octal-digit transcription at original locations (GY62 p. 171).
// Do not use an emulator-produced assembler output as the original record.
constexpr HistoricalWord HIST[] = {
    {0122, 0'26'0000'0200'0000ULL},
    {0123, 0'01'0021'0000'0020ULL},
    {0124, 0'31'0014'0126'0125ULL},
    {0125, 0'01'3036'0020'0020ULL},
    {0126, 0'01'0020'0000'4000ULL},
    {0127, 0'16'0021'3042'0133ULL},
    {0130, 0'16'0021'3026'0135ULL},
    {0131, 0'13'3012'0021'0021ULL},
    {0132, 0'05'0000'0000'0136ULL},
    {0133, 0'01'3026'0000'0021ULL},
    {0134, 0'05'0000'0000'0136ULL},
    {0135, 0'01'3012'0000'0021ULL},
    {0136, 0'27'4001'0123'0137ULL},
    {0140, 0'26'0000'0200'0000ULL},
    {0141, 0'01'0021'0000'0020ULL},
    {0142, 0'31'0014'0144'0143ULL},
    {0143, 0'01'3036'0020'0020ULL},
    {0144, 0'16'4000'0020'0146ULL},
    {0145, 0'33'0000'0004'0000ULL},
    {0146, 0'16'0021'3042'0152ULL},
    {0147, 0'16'0021'3026'0154ULL},
    {0150, 0'13'3012'0021'0021ULL},
    {0151, 0'05'0000'0000'0155ULL},
    {0152, 0'01'3026'0000'0021ULL},
    {0153, 0'05'0000'0000'0155ULL},
    {0154, 0'01'3012'0000'0021ULL},
    {0155, 0'27'4001'0141'0156ULL},
};

W original_word(W pc) {
    for (auto item : HIST) if (item.pc == pc) return item.word;
    throw std::logic_error("untranscribed original PC");
}
struct Silence {
    std::ostringstream sink;
    std::streambuf* previous;
    Silence():previous(std::cout.rdbuf(sink.rdbuf())){}
    ~Silence(){ std::cout.rdbuf(previous); }
};
bool step(Kyiv_t& cpu) { Silence s; return cpu.execute_opcode(); }
struct Transition { W pc,next; };

// First original write loop copies (-0), walks its sign-specific path,
// updates the traveling pattern to +1, then returns to 0123.
const std::vector<Transition> WRITE_NEG_ZERO={
    {0122,0123},{0123,0124},{0124,0126},{0126,0127},
    {0127,0130},{0130,0135},{0135,0136},{0136,0123}
};
// Second original write loop stores positive 1, then shifts 0021 to 2.
// Its 0132 opcode 05 equality branch is separately POLICY (ISA-05).
const std::vector<Transition> WRITE_POS_ONE={
    {0123,0124},{0124,0126},{0126,0127},{0127,0130},
    {0130,0131},{0131,0132},{0132,0136},{0136,0123}
};
const std::vector<Transition> READ_NEG_ZERO={
    {0140,0141},{0141,0142},{0142,0144},{0144,0146},
    {0146,0147},{0147,0154},{0154,0155},{0155,0141}
};
const std::vector<Transition> READ_POS_ONE={
    {0141,0142},{0142,0144},{0144,0146},{0146,0147},
    {0147,0150},{0150,0151},{0151,0155},{0155,0141}
};

void initial(Kyiv_t& cpu) {
    // NOT authenticated historical ROM; never rely on CWD-based loader.
    cpu.kmem.write_rom(03012, 1);
    cpu.kmem.write_rom(03026, SIGN);
    cpu.kmem.write_rom(03042, UPPER_MAG);
    for (auto item : HIST) cpu.kmem.write_memory(item.pc,item.word);
    cpu.kmem.write_memory(0014,0);       // choose positive arm of original 31
    cpu.kmem.write_memory(0021,SIGN);    // injected initial -0
    cpu.kmem.write_memory(0020,SENTINEL);
    cpu.kmem.write_memory(0200,SENTINEL);
    cpu.kmem.write_memory(0201,SENTINEL);
    cpu.kmem.write_memory(01777,SENTINEL);
    cpu.P_reg=RET;
    cpu.A_reg=0;
    cpu.Loop_reg=077;
    cpu.T_reg=false;
}
void enter_read(Kyiv_t& cpu) {
    // Explicit test-harness phase transition, NOT the original 0137..0140 path.
    cpu.A_reg=0;
    cpu.Loop_reg=077;
    cpu.C_reg=0140;
    cpu.kmem.write_memory(0021,SIGN);
    cpu.kmem.write_memory(0020,SENTINEL);
}
struct Walk {
    bool ok=true;
    size_t steps=0;
    W first_bad=0;
    std::string detail;
};
void walk(Kyiv_t& cpu,const std::vector<Transition>& trace,Walk& out) {
    for (auto t : trace) {
        if (cpu.C_reg!=t.pc) {
            out.ok=false;out.first_bad=t.pc;out.detail="pre-PC mismatch";return;
        }
        const bool running=step(cpu);
        ++out.steps;
        if (!running || cpu.T_reg || cpu.K_reg!=original_word(t.pc)
             || cpu.C_reg!=t.next) {
            out.ok=false;out.first_bad=t.pc;out.detail="K/next-PC/stop mismatch";return;
        }
    }
}
int strict_n=0,strict_ok=0,policy_n=0,policy_ok=0;
void result(const char* type,const char* name,bool ok,Kyiv_t& cpu,
            const Walk& w) {
    if(std::string(type)=="STRICT") {++strict_n;strict_ok+=ok;}
    else {++policy_n;policy_ok+=ok;}
    std::cout<<(ok? (std::string(type)+"-PASS ")
                   : (std::string(type)=="STRICT" ? "DOC-MISMATCH ":"POLICY-FAIL "))
         <<name<<" | steps="<<w.steps<<" C="<<std::oct<<cpu.C_reg
         <<" A="<<cpu.A_reg<<" Cy="<<cpu.Loop_reg
         <<" mem20="<<cpu.kmem.read_memory(0020)
         <<" mem21="<<cpu.kmem.read_memory(0021)
         <<" mem200="<<cpu.kmem.read_memory(0200)
         <<" mem201="<<cpu.kmem.read_memory(0201)
         <<" stop="<<cpu.T_reg<<" bad_pc="<<w.first_bad
         <<std::dec<<" "<<w.detail<<"\n";
}
void policy_write_mixed() {
    try {
        Kyiv_t cpu;initial(cpu);cpu.C_reg=0122;
        Walk w;walk(cpu,WRITE_NEG_ZERO,w);walk(cpu,WRITE_POS_ONE,w);
        const bool ok=w.ok && w.steps==16 && cpu.C_reg==0123
          && cpu.A_reg==0202 && cpu.Loop_reg==0
          && cpu.kmem.read_memory(0200)==SIGN
          && cpu.kmem.read_memory(0201)==1
          && cpu.kmem.read_memory(0020)==1
          && cpu.kmem.read_memory(0021)==2
          && cpu.P_reg==RET;
        result("POLICY","write_minus_zero_then_plus_one",ok,cpu,w);
    } catch(const std::exception& e) {
        ++policy_n;std::cout<<"POLICY-FAIL write_minus_zero_then_plus_one exception="<<e.what()<<"\n";
    }
}
void policy_read_mixed() {
    try {
        Kyiv_t cpu;initial(cpu);
        cpu.kmem.write_memory(0200,SIGN);
        cpu.kmem.write_memory(0201,1);
        enter_read(cpu);
        Walk w;walk(cpu,READ_NEG_ZERO,w);walk(cpu,READ_POS_ONE,w);
        const bool ok=w.ok && w.steps==16 && cpu.C_reg==0141
          && cpu.A_reg==0202 && cpu.Loop_reg==0
          && cpu.kmem.read_memory(0200)==SIGN
          && cpu.kmem.read_memory(0201)==1
          && cpu.kmem.read_memory(0020)==1
          && cpu.kmem.read_memory(0021)==2
          && cpu.P_reg==RET;
        result("POLICY","read_minus_zero_then_plus_one",ok,cpu,w);
    } catch(const std::exception& e) {
        ++policy_n;std::cout<<"POLICY-FAIL read_minus_zero_then_plus_one exception="<<e.what()<<"\n";
    }
}
void policy_joined() {
    try {
        Kyiv_t cpu;initial(cpu);cpu.C_reg=0122;
        Walk w;walk(cpu,WRITE_NEG_ZERO,w);walk(cpu,WRITE_POS_ONE,w);
        const bool written=w.ok && w.steps==16 && cpu.C_reg==0123
          && cpu.kmem.read_memory(0200)==SIGN
          && cpu.kmem.read_memory(0201)==1;
        if(w.ok) {enter_read(cpu);walk(cpu,READ_NEG_ZERO,w);walk(cpu,READ_POS_ONE,w);}
        const bool ok=written && w.ok && w.steps==32
          && cpu.C_reg==0141 && cpu.A_reg==0202 && cpu.Loop_reg==0
          && cpu.kmem.read_memory(0200)==SIGN
          && cpu.kmem.read_memory(0201)==1
          && cpu.kmem.read_memory(0020)==1
          && cpu.kmem.read_memory(0021)==2
          && cpu.P_reg==RET;
        result("POLICY","write_then_read_with_explicit_phase_reset",ok,cpu,w);
    } catch(const std::exception& e) {
        ++policy_n;std::cout<<"POLICY-FAIL write_then_read_with_explicit_phase_reset exception="<<e.what()<<"\n";
    }
}
// Counterfactual experiment. The *harness*, NOT opcode 01, changes one bit of
// RAM[0020] AFTER the historical 0141 copy, before original exact compare 0144.
// Demonstrates that losing the -0 code would enter original STOP at 0145.
// The -0 produced by 0141 is still a POLICY; this whole chain is POLICY.
void policy_counterfactual_stop() {
    try {
        Kyiv_t cpu;initial(cpu);
        cpu.kmem.write_memory(0200,SIGN);
        enter_read(cpu);
        Walk w;
        const std::vector<Transition> prefix={{0140,0141},{0141,0142},{0142,0144}};
        walk(cpu,prefix,w);
        const bool before=w.ok && cpu.kmem.read_memory(0020)==SIGN;
        cpu.kmem.write_memory(0020,0); // explicitly injected M0-like +0
        bool compare_running=false;
        bool stop_running=true;
        if(w.ok) {
            compare_running=step(cpu);++w.steps;
            const bool cmp_ok=compare_running && !cpu.T_reg &&
              cpu.K_reg==original_word(0144) && cpu.C_reg==0145;
            if (!cmp_ok) {w.ok=false;w.first_bad=0144;w.detail="compare did not reject injected +0";}
        }
        if(w.ok) {
            stop_running=step(cpu);++w.steps;
            if(stop_running || !cpu.T_reg || cpu.K_reg!=original_word(0145)) {
                w.ok=false;w.first_bad=0145;w.detail="original STOP not taken";
            }
        }
        result("POLICY","counterfactual_plus_zero_after_0141_triggers_stop",
               before && w.ok && w.steps==5 && !stop_running,cpu,w);
    } catch(const std::exception& e) {
        ++policy_n;std::cout<<"POLICY-FAIL counterfactual_plus_zero_after_0141_triggers_stop exception="<<e.what()<<"\n";
    }
}
// Independently preloaded differing machine codes: documented exact compare
// (016) followed by the original STOP (033). No opcode 01 executed.
void strict_preloaded_mismatch() {
    try {
        Kyiv_t cpu;initial(cpu);
        cpu.kmem.write_memory(0200,SIGN);
        cpu.kmem.write_memory(0020,0);
        cpu.A_reg=0200;
        cpu.C_reg=0144;
        Walk w;
        const bool compare_running=step(cpu);++w.steps;
        bool ok=compare_running && !cpu.T_reg && cpu.K_reg==original_word(0144)
             && cpu.C_reg==0145;
        if(ok) {
            const bool stop_running=step(cpu);++w.steps;
            ok=!stop_running && cpu.T_reg && cpu.K_reg==original_word(0145);
        }
        result("STRICT","preloaded_code_mismatch_stops_original_0145",
               ok && w.steps==2,cpu,w);
    } catch(const std::exception& e) {
        ++strict_n;std::cout<<"DOC-MISMATCH preloaded_code_mismatch_stops_original_0145 exception="<<e.what()<<"\n";
    }
}
} // namespace

int main() {
    policy_write_mixed();
    policy_read_mixed();
    policy_joined();
    policy_counterfactual_stop();
    strict_preloaded_mismatch();
    std::cout<<"ISA-06 D8-P2 STRICT="<<strict_ok<<"/"<<strict_n
             <<" DOC-MISMATCH="<<(strict_n-strict_ok)
             <<" POLICY="<<policy_ok<<"/"<<policy_n
             <<" POLICY-FAIL="<<(policy_n-policy_ok)<<"\n";
    return (strict_ok==strict_n && policy_ok==policy_n) ? 0 : 1;
}
