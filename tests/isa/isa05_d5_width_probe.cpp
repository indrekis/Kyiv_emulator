// ISA-05 D5: characterize 10-bit A/Cy against 11-bit address fields.
// GY62, printed pp. 9, 13-14, 54, 57, 59-60.
// STRICT = documented cases; POLICY = existing disputed interpretation;
// OBS = output ONLY, never historical correctness assertion.
#include <cstdint>
#include <exception>
#include <iostream>
#include <sstream>
#include <string>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }
namespace {
constexpr uint64_t SIGN = uint64_t{1} << 40;
constexpr uint64_t PC = 0100;
constexpr uint64_t TARGET = 0250;
constexpr uint64_t OTHER = 0240;
constexpr uint64_t MODIFY = 04000;
int strict_pass=0, policy_pass=0, failures=0, observations=0;
std::string oct(uint64_t x) { std::ostringstream o; o<<std::oct<<x; return o.str(); }
uint64_t cmd(unsigned op,uint64_t a1=0,uint64_t a2=0,uint64_t a3=0) {
    return (uint64_t(op)<<36) | ((a1 & 07777)<<24)
         | ((a2 & 07777)<<12) | (a3 & 07777);
}
struct Quiet {
    std::ostringstream sink;
    std::streambuf* prior;
    Quiet():prior(std::cout.rdbuf(sink.rdbuf())){}
    ~Quiet(){std::cout.rdbuf(prior);}
};
bool at(Kyiv_t& m, unsigned op,uint64_t a1=0,uint64_t a2=0,uint64_t a3=0) {
    m.kmem.write_memory(PC,cmd(op,a1,a2,a3)); m.C_reg=PC;
    Quiet q; return m.execute_opcode();
}
bool next(Kyiv_t& m) {Quiet q;return m.execute_opcode();}
std::string regs(const Kyiv_t& m,bool go) {
    return "C="+oct(m.C_reg)+" P="+oct(m.P_reg)
       +" Cy="+oct(m.Loop_reg)+" A="+oct(m.A_reg)
       +" go="+std::to_string(go)+" stop="+std::to_string(m.T_reg);
}
void check(const char* label,bool pass,bool policy,const std::string& detail) {
    if (!pass) ++failures;
    else if(policy)++policy_pass;
    else ++strict_pass;
    std::cout<<(pass?(policy?"POLICY-PASS ":"PASS "):"FAIL ")
        <<label<<" | "<<detail<<'\n';
}
void obs(const char* label,const std::string& detail) {
    ++observations;
    std::cout<<"OBS "<<label<<" | "<<detail<<" [not historical oracle]\n";
}
template<class F> void case_run(const char* label,F&& f,bool observational=false) {
    try{f();}catch(const std::exception& e){
        if(observational)obs(label,std::string("exception: ")+e.what());
        else check(label,false,false,std::string("exception: ")+e.what());
    }catch(...){
        if(observational)obs(label,"non-standard exception");
        else check(label,false,false,"non-standard exception");
    }
}
}
int main(){
    // STRICT: all address fields fit the documented A-register width.
    case_run("26_max_10bit_raw",[]{
        Kyiv_t m;bool go=at(m,026,01777,01776,TARGET);
        check("26_max_10bit_raw",go&&!m.T_reg&&m.Loop_reg==01777
             &&m.A_reg==01776&&m.C_reg==PC+1,false,regs(m,go));
    });
    case_run("26_equal_max_10bit_branch",[]{
        Kyiv_t m;bool go=at(m,026,01777,01777,TARGET);
        check("26_equal_max_10bit_branch",go&&!m.T_reg&&m.Loop_reg==01777
             &&m.A_reg==01777&&m.C_reg==TARGET,false,regs(m,go));
    });
    case_run("27_wrap_1777_plus_one",[]{
        Kyiv_t m;m.A_reg=01777;m.Loop_reg=0;
        bool go=at(m,027,1,OTHER,TARGET);
        check("27_wrap_1777_plus_one",go&&!m.T_reg&&m.A_reg==0
             &&m.C_reg==TARGET,false,regs(m,go));
    });
    case_run("27_wrap_nonmatching_limit",[]{
        Kyiv_t m;m.A_reg=01777;m.Loop_reg=2;
        bool go=at(m,027,1,OTHER,TARGET);
        check("27_wrap_nonmatching_limit",go&&!m.T_reg&&m.A_reg==0
             &&m.C_reg==OTHER,false,regs(m,go));
    });
    case_run("27_wrap_larger_step",[]{
        Kyiv_t m;m.A_reg=01775;m.Loop_reg=2;
        bool go=at(m,027,5,OTHER,TARGET);
        check("27_wrap_larger_step",go&&!m.T_reg&&m.A_reg==2
             &&m.C_reg==TARGET,false,regs(m,go));
    });
    case_run("30_plain_negative_call",[]{
        Kyiv_t m;m.kmem.write_memory(2,SIGN);
        bool go=at(m,030,2,OTHER,TARGET);
        check("30_plain_negative_call",go&&!m.T_reg&&m.P_reg==OTHER
             &&m.C_reg==TARGET,false,regs(m,go));
    });
    case_run("30_then_32_clears_return",[]{
        Kyiv_t m;m.kmem.write_memory(2,SIGN);
        m.kmem.write_memory(PC,cmd(030,2,OTHER,TARGET));
        m.kmem.write_memory(TARGET,cmd(032));m.C_reg=PC;
        bool call=next(m);const bool reached=(m.C_reg==TARGET && m.P_reg==OTHER);
        bool ret=next(m);
        check("30_then_32_clears_return",call&&ret&&reached&&!m.T_reg
             &&m.C_reg==OTHER&&m.P_reg==0,false,regs(m,ret));
    });
    case_run("34_field_1777_supported",[]{
        Kyiv_t m; m.kmem.write_memory(2,cmd(0,0,01777,0));
        m.kmem.write_memory(01777,012345);
        bool go=at(m,034,2,0,4);
        check("34_field_1777_supported",go&&!m.T_reg&&m.A_reg==01777
             &&m.kmem.read_memory(4)==012345&&m.C_reg==PC+1,false,
              regs(m,go)+" dst="+oct(m.kmem.read_memory(4)));
    });
    case_run("34_modified_destination_old_A",[]{
        Kyiv_t m;m.A_reg=1;
        m.kmem.write_memory(2,cmd(0,0,5,0));
        m.kmem.write_memory(5,012345);
        bool go=at(m,034,2,0,MODIFY|3);
        check("34_modified_destination_old_A",go&&!m.T_reg&&m.A_reg==5
             &&m.kmem.read_memory(4)==012345&&m.C_reg==PC+1,false,
             regs(m,go)+" dst4="+oct(m.kmem.read_memory(4)));
    });

    // POLICY: GY62 p. 57 allows modified return field; p. 13 contradicts it.
    case_run("30_modified_second_current_policy",[]{
        Kyiv_t m;m.A_reg=1;m.kmem.write_memory(2,SIGN);
        bool go=at(m,030,2,MODIFY|OTHER,TARGET);
        check("30_modified_second_current_policy",go&&!m.T_reg
            &&m.C_reg==TARGET&&m.P_reg==OTHER+1,true,regs(m,go)
            +" alternate_p13_P="+oct(OTHER));
    });

    // OBS: historical behavior is not established for the high field bit.
    case_run("30_modified_return_crosses_10bits",[]{
        Kyiv_t m;m.A_reg=1;m.kmem.write_memory(2,SIGN);
        bool go=at(m,030,2,MODIFY|01777,TARGET);
        obs("30_modified_return_crosses_10bits",regs(m,go)
            +" unmodified_P=1777, formal_p57_P=2000");
    },true);
    case_run("26_high_first_field_to_Cy",[]{
        Kyiv_t m;bool go=at(m,026,02003,3,TARGET);
        obs("26_high_first_field_to_Cy",regs(m,go)
            +" possible_ten_bit_Cy=3");
    },true);
    case_run("26_high_second_field_to_A",[]{
        Kyiv_t m;bool go=at(m,026,3,02004,TARGET);
        obs("26_high_second_field_to_A",regs(m,go)
            +" possible_ten_bit_A=4");
    },true);
    case_run("26_high_bit_can_change_equality",[]{
        Kyiv_t m;bool go=at(m,026,02003,3,TARGET);
        obs("26_high_bit_can_change_equality",regs(m,go)
            +" if_Cy_truncated_then_equal_and_C=250");
    },true);
    case_run("26_then_27_after_high_A",[]{
        Kyiv_t m;bool g1=at(m,026,6,02004,TARGET);
        const uint64_t initial_A=m.A_reg;
        bool g2=at(m,027,1,OTHER,TARGET);
        obs("26_then_27_after_high_A", "initial_A="+oct(initial_A)
            +" -> "+regs(m,g1&&g2));
    },true);
    case_run("27_high_Cy_limit_unreachable",[]{
        Kyiv_t m;m.A_reg=01777;m.Loop_reg=02003;
        bool go=at(m,027,4,OTHER,TARGET);
        obs("27_high_Cy_limit_unreachable",regs(m,go)
            +" if_Cy_truncated_then_C=250");
    },true);
    case_run("34_fetched_II_2005",[]{
        Kyiv_t m;m.kmem.write_memory(2,cmd(0,0,02005,0));
        m.kmem.write_memory(5,012345);
        bool go=at(m,034,2,0,4);
        obs("34_fetched_II_2005",regs(m,go)
            +" dst="+oct(m.kmem.read_memory(4))
            +" lower_10bits_source_0005="+oct(m.kmem.read_memory(5)));
    },true);
    std::cout<<"ISA-05 D5 STRICT="<<strict_pass<<"/9 POLICY="<<policy_pass
             <<"/1 OBS="<<observations<<" FAIL="<<failures<<'\n';
    return (failures || strict_pass!=9 || policy_pass!=1 || observations!=7) ? 1 : 0;
}
