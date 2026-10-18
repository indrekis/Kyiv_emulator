// D11-B: REAL Kyiv_t, not a mock; disassembly printing is the only stub.
#include "kyiv.h"
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }
namespace {
constexpr word_t ins(unsigned op, unsigned a, unsigned b, unsigned c) {
    return (word_t(op)<<36) | (word_t(a)<<24) | (word_t(b)<<12) | word_t(c);
}
std::string octal(word_t w) {std::ostringstream s; s<<std::oct<<w;return s.str();}
}
int main(int argc, char** argv) {
    if (argc != 6) return 2;
    const std::string tag(argv[1]);
    try {
        const addr_t start=std::stoull(argv[2],nullptr,8);
        const addr_t end=std::stoull(argv[3],nullptr,8);
        const size_t cursor=std::stoull(argv[4]);
        const addr_t shift=std::stoull(argv[5],nullptr,8);
        constexpr addr_t pc=0100, lhs=0700, rhs=0701, dest=0702;
        constexpr word_t sentinel=01234567012345ULL;
        const word_t opcode=ins(021,static_cast<unsigned>(start),
                                static_cast<unsigned>(end),0120);
        const word_t next=ins(017,lhs,rhs,dest); // actual step 2: 5 XOR 3 => 6
        Kyiv_t m;
        for (addr_t a=1;a<02000;++a) m.kmem.write_memory(a,sentinel);
        m.kmem.write_memory(pc,opcode);
        m.kmem.write_memory(pc+1,next);
        m.kmem.write_memory(0120,ins(033,0,0,0));
        m.kmem.write_memory(lhs,5);
        m.kmem.write_memory(rhs,3);
        m.kmem.write_memory(dest,sentinel);
        m.C_reg=pc; m.K_reg=0; m.h=cursor;
        m.A_reg=shift; m.perfo_num=7;
        const auto wasA=m.A_reg;
        const auto wasP=m.P_reg;
        const auto wasL=m.Loop_reg;
        const auto wasT=m.T_reg;
        const auto wasH=m.h;
        std::vector<word_t> before;
        for(addr_t a=0;a<02000;++a) before.push_back(m.kmem.read_memory(a));
        bool accepted=false;
        std::string reason="NONE";
        try {m.execute_opcode(); accepted=true;}
        catch (const std::exception& e) {
            reason=e.what();
            if(reason.rfind("IO21: ",0)==0)reason.erase(0,6);
        }
        catch (...) {reason="UNEXPECTED_EXCEPTION";}
        const addr_t pc1=m.C_reg;
        const word_t k1=m.K_reg;
        const size_t h1=m.h;
        bool guarded=true, unchanged=true;
        for(addr_t a=0;a<02000;++a) {
            const bool eligible=start<=end && a>=start && a<=end && a<02000;
            const auto actual=m.kmem.read_memory(a);
            if(actual!=before[a]) {
                unchanged=false;
                if(!eligible) guarded=false;
            }
        }
        std::string words;
        if(start<=end && end<02000 && end-start < 5) {
            for(addr_t a=start;a<=end;++a) {
                if(!words.empty())words+='/';
                words+=octal(m.kmem.read_memory(a));
            }
        } else words="NA";
        const bool stable=(m.A_reg==wasA && m.P_reg==wasP &&
                           m.Loop_reg==wasL && m.T_reg==wasT && m.perfo_num==7);
        bool second=false; bool k2=false;
        if(accepted) {
            try {second=m.execute_opcode(); k2=(m.K_reg==next);}
            catch (...) {reason="SECOND_STEP_EXCEPTION";}
        }
        std::cout<<"D11B-CPU tag="<<tag
                 <<" status="<<(accepted?"OK":"ERROR")
                 <<" reason="<<reason
                 <<" pc1="<<octal(pc1)
                 <<" pc2="<<octal(m.C_reg)
                 <<" k1="<<(k1==(accepted?next:opcode))
                 <<" k2="<<k2
                 <<" h0="<<wasH<<" h1="<<h1
                 <<" guard="<<guarded<<" unchanged="<<unchanged
                 <<" stable="<<stable
                 <<" words="<<words
                 <<" second="<<second
                 <<" xor="<<m.kmem.read_memory(dest)
                 <<" HARDWARE_ORACLE=0\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr<<"D11B-PROBE-ERROR "<<e.what()<<'\n';
        return 3;
    }
}
