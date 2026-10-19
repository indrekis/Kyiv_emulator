// ISA-07 D13-B: observe genuine Kyiv_t IO23, not a mock CPU.
// Link with src/main.cpp; NEVER with src/asm_disasm.cpp (another main).
#include "kyiv.h"
#include <cstdint>
#include <exception>
#include <iostream>
#include <string>
#include <vector>

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }
namespace {
constexpr word_t ins(unsigned op, unsigned a, unsigned b, unsigned c) {
    return (word_t(op) << 36) | (word_t(a) << 24) | (word_t(b) << 12) | word_t(c);
}
}
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const std::string name(argv[1]);
    constexpr word_t sign = 1ULL << 40;
    constexpr addr_t pc = 0100;
    const std::string cases =
        "|range|single|offset|fromzero|negative|negative-zero|sign-only|"
        "max-positive|max-negative|overwrite|altjump|modified|io25-setup|"
        "last-ram|zero-source|mixed|reversed|beyond-physical|rom-source|"
        "cross-physical|invalid-start|invalid-end|invalid-first|invalid-second|"
        "invalid-third|invalid-negative|invalid-last|output-is-dir|"
        "empty-out-is-dir|invalid-before-overwrite|";
    if (cases.find("|" + name + "|") == std::string::npos) return 2;
    try {
        Kyiv_t m;
        addr_t first = 0200, last = 0202;
        if (name == "single" || name == "negative-zero" || name == "sign-only" ||
            name == "max-positive" || name == "max-negative" ||
            name == "zero-source" || name == "last-ram" ||
            name == "invalid-first" || name == "invalid-last" ||
            name == "invalid-negative") first=last=0200;
        if (name == "single") first=last=0201;
        if (name == "offset") {first=0201;last=0203;}
        if (name == "fromzero") {first=0;last=0002;}
        if (name == "reversed") {first=0202;last=0200;}
        if (name == "beyond-physical" || name == "invalid-start") first=last=02000;
        if (name == "invalid-end") {first=0200;last=03000;}
        if (name == "rom-source") first=last=03010;
        if (name == "cross-physical") {first=01777;last=02000;}
        if (name == "modified") {first=0177;last=0201;m.A_reg=1;}
        if (name == "last-ram") first=last=01777;
        if (name == "zero-source") first=last=0;
        const addr_t target=name=="altjump" ? 0130 : 0120;
        word_t command=ins(023,static_cast<unsigned>(first),
                           static_cast<unsigned>(last),static_cast<unsigned>(target));
        if (name=="modified") command|=(1ULL<<35)|(1ULL<<23);
        const word_t xor_cmd=ins(017,0700,0701,0702);
        if (name=="io25-setup") {
            m.kmem.write_memory(pc,ins(025,1,6,9));
            m.kmem.write_memory(pc+1,command);
        } else {
            m.kmem.write_memory(pc,command);
            m.kmem.write_memory(pc+1,ins(033,0,0,0));
        }
        m.kmem.write_memory(target,xor_cmd);
        m.kmem.write_memory(0700,5);
        m.kmem.write_memory(0701,3);
        m.kmem.write_memory(0702,0);
        m.kmem.write_memory(0001,5);
        m.kmem.write_memory(0002,7);
        m.kmem.write_memory(0200,5);
        m.kmem.write_memory(0201,7);
        m.kmem.write_memory(0202,9);
        m.kmem.write_memory(0203,11);
        m.kmem.write_memory(01777,15);
        m.kmem.write_rom(03010,17);
        if (name=="negative") m.kmem.write_memory(0200,sign|5);
        if (name=="negative-zero" || name=="sign-only") m.kmem.write_memory(0200,sign);
        if (name=="max-positive") m.kmem.write_memory(0200,sign-1);
        if (name=="max-negative") m.kmem.write_memory(0200,sign|(sign-1));
        if (name=="mixed") {m.kmem.write_memory(0200,sign|5);
                             m.kmem.write_memory(0201,sign);
                             m.kmem.write_memory(0202,sign-1);}
        if (name=="invalid-first" || name=="invalid-before-overwrite" ||
            name=="invalid-negative") m.kmem.write_memory(0200,(1ULL<<45)|sign|5);
        if (name=="invalid-second") m.kmem.write_memory(0201,(1ULL<<45)|7);
        if (name=="invalid-third") m.kmem.write_memory(0202,(1ULL<<45)|9);
        if (name=="invalid-last") m.kmem.write_memory(0200,(1ULL<<45)|5);
        m.C_reg=pc;m.K_reg=0;m.h=7;
        m.drum_num_read=3;m.drum_zone_read=4;
        m.drum_num_write=5;m.drum_zone_write=8;
        const auto oldA=m.A_reg;
        const auto oldP=m.P_reg;
        const auto oldL=m.Loop_reg;
        const auto oldT=m.T_reg;
        const auto oldH=m.h;
        const auto oldR=m.drum_num_read;
        const auto oldRZ=m.drum_zone_read;
        std::vector<word_t> before;
        before.reserve(04000);
        for(addr_t i=0;i<04000;++i)before.push_back(m.kmem.read_memory(i));
        bool setup=true;
        if(name=="io25-setup") {
            setup=m.execute_opcode() && m.C_reg==pc+1 && m.K_reg==command &&
                  m.drum_num_write==6 && m.drum_zone_write==9;
        }
        const auto beforePC=m.C_reg;
        bool accepted=false;
        std::string reason="NONE";
        try {m.execute_opcode();accepted=true;}
        catch(const std::exception& e) {
            reason=e.what();
            if(reason.rfind("IO23: ",0)==0)reason.erase(0,6);
        } catch(...) {reason="UNKNOWN_EXCEPTION";}
        const auto pc1=m.C_reg;
        const auto k1=m.K_reg;
        bool whole_mem=true;
        for(addr_t i=0;i<04000;++i)
            if(before[static_cast<std::size_t>(i)]!=m.kmem.read_memory(i)) {
                whole_mem=false;break;
            }
        const bool stable=(m.A_reg==oldA && m.P_reg==oldP &&
            m.Loop_reg==oldL && m.T_reg==oldT && m.h==oldH &&
            m.drum_num_read==oldR && m.drum_zone_read==oldRZ &&
            m.drum_num_write==(name=="io25-setup"?6:5) &&
            m.drum_zone_write==(name=="io25-setup"?9:8));
        bool run2=false;
        if(accepted)run2=m.execute_opcode();
        std::cout << std::oct
                  << "D13B-OBS mode=" << name
                  << " status=" << (accepted?"OK":"ERROR")
                  << " pc0=" << beforePC << " pc1=" << pc1
                  << " pc2=" << m.C_reg
                  << std::dec
                  << " k1=" << (k1==(accepted?xor_cmd:command))
                  << " k2=" << (accepted?m.K_reg==xor_cmd:m.K_reg==command)
                  << " setup=" << setup
                  << " memory=" << whole_mem
                  << " stable=" << stable
                  << " xor=" << m.kmem.read_memory(0702)
                  << " run2=" << run2
                  << " steps=" << (name=="io25-setup"?(accepted?3:2):(accepted?2:1))
                  << " reason=" << reason
                  << " HARDWARE_ORACLE=0\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr << "D13B-PROBE-EXCEPTION " << e.what() << '\n';
        return 3;
    } catch(...) {
        std::cerr << "D13B-PROBE-EXCEPTION UNKNOWN\n";
        return 3;
    }
}
