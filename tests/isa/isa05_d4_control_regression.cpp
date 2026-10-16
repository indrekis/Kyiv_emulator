// ISA-05 D4: source-backed P register reset, NGO raw fields, OGO 10-bit wrap.
// Historical source: GY62, printed pp. 14, 54, 58-60.
#include <cstdint>
#include <exception>
#include <iostream>
#include <sstream>
#include <string>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }
namespace {
constexpr uint64_t PC = 0100;
constexpr uint64_t B = 0250;
constexpr uint64_t MOD = 04000;
constexpr uint64_t NEGZERO = uint64_t(1) << 40;
int passed = 0, failed = 0, observed = 0;
std::string oct(uint64_t v) { std::ostringstream s; s << std::oct << v; return s.str(); }
uint64_t instruction(unsigned op, uint64_t a1=0, uint64_t a2=0, uint64_t a3=0) {
    return (uint64_t(op) << 36) | (a1 << 24) | (a2 << 12) | a3;
}
struct Silence {
    std::ostringstream sink;
    std::streambuf* saved;
    Silence(): saved(std::cout.rdbuf(sink.rdbuf())) {}
    ~Silence() { std::cout.rdbuf(saved); }
};
bool run(Kyiv_t& m, unsigned op, uint64_t a1=0,uint64_t a2=0,uint64_t a3=0) {
    m.C_reg=PC;
    m.kmem.write_memory(PC,instruction(op,a1,a2,a3));
    Silence s;
    return m.execute_opcode();
}
void check(const char* name, bool good, const Kyiv_t& m) {
    (good ? passed : failed)++;
    std::cout<<(good ? "PASS " : "FAIL ")<<name
             <<" | C="<<oct(m.C_reg)<<" P="<<oct(m.P_reg)
             <<" Cy="<<oct(m.Loop_reg)<<" A="<<oct(m.A_reg)
             <<" stopped="<<m.T_reg<<'\n';
}
void obs(const char* name, const Kyiv_t& m) {
    observed++;
    std::cout<<"OBS "<<name<<" | Cy="<<oct(m.Loop_reg)
             <<" A="<<oct(m.A_reg)<<" [no historical assertion]\n";
}
}
int main() {
    try {
        {
            Kyiv_t m; m.P_reg=0350;
            bool go=run(m,032,017,023,025);
            check("32_transfer_then_clear_P",go&&!m.T_reg&&m.C_reg==0350&&m.P_reg==0,m);
        }
        {
            Kyiv_t m; m.P_reg=0;
            bool go=run(m,032,017,023,025);
            check("32_zero_return_remains_zero",go&&!m.T_reg&&m.C_reg==0&&m.P_reg==0,m);
        }
        {
            Kyiv_t m; m.P_reg=0350;
            m.kmem.write_memory(2,NEGZERO);
            m.kmem.write_memory(B,instruction(032,077,077,077));
            bool called=run(m,030,2,0240,B);
            // Follow the call with an actual return instruction.
            m.C_reg=B;
            bool returned;
            {Silence s; returned=m.execute_opcode();}
            check("30_then_32_roundtrip_and_P_clear",called&&returned&&!m.T_reg
              &&m.C_reg==0240&&m.P_reg==0,m);
        }
        {
            Kyiv_t m; m.A_reg=1;
            bool go=run(m,026,MOD|010,011,B);
            check("26_first_field_raw_with_modifier",go&&!m.T_reg&&m.C_reg==PC+1&&m.Loop_reg==010&&m.A_reg==011,m);
        }
        {
            Kyiv_t m; m.A_reg=1;
            bool go=run(m,026,010,MOD|011,B);
            check("26_second_field_raw_with_modifier",go&&!m.T_reg&&m.C_reg==PC+1&&m.Loop_reg==010&&m.A_reg==011,m);
        }
        {
            Kyiv_t m; m.A_reg=1;
            bool go=run(m,026,MOD|010,MOD|010,B);
            check("26_equal_raw_fields_branch",go&&!m.T_reg&&m.C_reg==B&&m.Loop_reg==010&&m.A_reg==010,m);
        }
        {
            Kyiv_t m; m.A_reg=01777;
            bool go=run(m,026,MOD|010,MOD|011,B);
            check("26_modifiers_not_applied_to_raw_fields",go&&!m.T_reg&&m.C_reg==PC+1&&m.Loop_reg==010&&m.A_reg==011,m);
        }
        {
            Kyiv_t m; m.A_reg=01777; m.Loop_reg=0;
            bool go=run(m,027,1,0240,B);
            check("27_ten_bit_wrap_and_exit",go&&!m.T_reg&&m.C_reg==B&&m.A_reg==0,m);
        }
        {
            Kyiv_t m; m.A_reg=01776; m.Loop_reg=3;
            bool go=run(m,027,3,0240,B);
            check("27_wrap_and_continue",go&&!m.T_reg&&m.C_reg==0240&&m.A_reg==1,m);
        }
        {
            Kyiv_t m; m.A_reg=5; m.Loop_reg=8;
            bool go=run(m,027,3,0240,B);
            check("27_baseline_no_wrap",go&&!m.T_reg&&m.C_reg==B&&m.A_reg==8,m);
        }
        {
            Kyiv_t m; m.A_reg=1; m.Loop_reg=2;
            bool go=run(m,027,MOD|1,0240,B);
            check("27_increment_ignores_modifier",go&&!m.T_reg&&m.C_reg==B&&m.A_reg==2,m);
        }
        {
            Kyiv_t m;
            bool go=run(m,026,02003,02004,B);
            (void)go;
            obs("26_eleven_bit_fields_to_ten_bit_registers",m);
        }
    } catch (const std::exception& e) {
        failed++;
        std::cerr<<"FAIL unhandled exception: "<<e.what()<<'\n';
    } catch (...) {
        failed++;
        std::cerr<<"FAIL unhandled non-standard exception\n";
    }
    std::cout<<"ISA-05 D4 STRICT="<<passed<<"/"<<(passed+failed)
             <<" OBS="<<observed<<" FAIL="<<failed<<'\n';
    return failed ? 1 : 0;
}
