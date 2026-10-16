// ISA-06 D3: three real opcode 013 instructions, GY62 printed p. 171.
// Source words are authentic; operands are controlled test fixtures.
#include <cstdint>
#include <exception>
#include <fstream>
#include <iostream>
#include <sstream>
#include "kyiv.h"
#include "asm_disasm.h"
int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) {return 0;}
namespace {
using W=uint64_t;
constexpr W SIGN=W{1}<<40;
constexpr W MASK41=(SIGN<<1)-1;
constexpr W P=0137, CY=0765, A=0017;
W instr(unsigned op,W x,W y,W z){return (W(op)<<36)|(x<<24)|(y<<12)|z;}
struct Silence {std::ostringstream capture; std::streambuf* old;
    Silence():old(std::cout.rdbuf(capture.rdbuf())){}
    ~Silence(){std::cout.rdbuf(old);} };
bool step(Kyiv_t& m){Silence s;return m.execute_opcode();}
int strict_total=0,strict_pass=0,obs_total=0;
void historical(const char* name,W pc,W operand_addr,W input,W expected){
    ++strict_total;
    try {
       Kyiv_t m;
       // Controlled fixture: positive shift count 1, independent of ROM.txt.
       m.kmem.write_rom(03012,1);
       const W word=instr(013,03012,operand_addr,operand_addr);
       m.kmem.write_memory(pc,word);
       m.kmem.write_memory(operand_addr,input);
       m.C_reg=pc; m.A_reg=A; m.P_reg=P; m.Loop_reg=CY;
       const bool running=step(m);
       const bool ok=running && !m.T_reg && m.C_reg==pc+1 && m.K_reg==word &&
         m.kmem.read_memory(operand_addr)==expected &&
         m.A_reg==A && m.P_reg==P && m.Loop_reg==CY;
       strict_pass+=ok;
       std::cout<<(ok?"STRICT-PASS ":"DOC-MISMATCH ")<<name
                <<" | PC="<<std::oct<<pc<<" K="<<word
                <<" input="<<input<<" result="<<m.kmem.read_memory(operand_addr)
                <<" expected="<<expected<<" C="<<m.C_reg<<std::dec<<'\n';
    } catch (const std::exception& e) {
       std::cout<<"DOC-MISMATCH "<<name<<" | exception="<<e.what()<<'\n';
    }
}
}
int main(){
    // These are the three verbatim instruction words from GY62 p.171.
    historical("historical_0131_running_one", 0131,0021,1,2);
    historical("historical_0150_sign_bit_overflow",0150,0021,SIGN,0);
    historical("historical_0156_mixed_pattern",0156,0017,SIGN|03,06);
    ++obs_total;
    // The constructor reads ../mem/ROM.txt relative to the PROCESS working
    // directory. In our normal repository-root test invocation that path does
    // not designate mem/ROM.txt, so a default-constructed CPU can read zero
    // despite a nonzero transcribed ROM word. Report both independently.
    try {
       Kyiv_t m;
       std::ifstream ctor_path("../mem/ROM.txt");
       std::ifstream root_path("mem/ROM.txt");
       const bool ctor_file_open = ctor_path.is_open();
       const bool root_file_open = root_path.is_open();
       std::string source_word = "UNAVAILABLE";
       if (root_file_open) {
           std::string line;
           source_word = "MISSING";
           while (std::getline(root_path, line)) {
               std::istringstream fields(line);
               std::string address;
               if (!(fields >> address) || address != "3012") continue;
               std::string group, digits;
               while (fields >> group) digits += group;
               if (digits.size() != 14 ||
                   digits.find_first_not_of("01234567") != std::string::npos) {
                   source_word = "MALFORMED";
               } else {
                   std::ostringstream value;
                   value << std::oct << std::stoull(digits, nullptr, 8);
                   source_word = value.str();
               }
               break;
           }
       }
       std::cout << "OBS transcribed_ROM_3012 | constructor_value=" << std::oct
                 << m.kmem.read_memory(03012) << std::dec
                 << " constructor_input_path_open=" << ctor_file_open
                 << " repo_mem_file_open=" << root_file_open
                 << " repo_file_value=" << source_word
                 << " [working-directory-dependent; NOT a historical oracle]\n";
    } catch (const std::exception& e) {
       std::cout << "OBS transcribed_ROM_3012 | exception=" << e.what()
                 << " [NOT a historical oracle]\n";
    }
    std::cout<<"ISA-06 D3 STRICT="<<strict_pass<<'/'<<strict_total
             <<" DOC-MISMATCH="<<(strict_total-strict_pass)
             <<" POLICY=0 OBS="<<obs_total<<'\n';
    return strict_total==strict_pass ? 0:1;
}
