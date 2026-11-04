// H115-B15: autonomous Euler ODE time-stepping, private FP-ROM reconstruction, no HOST PC updates
// H115-B11: private ROM-only machine-branch candidate; no HOST PC overrides
// vectors. No production CPU changes, guessed ROM words, or I/O.
// Build with src/main.cpp and -Iinc. Not a physical-hardware oracle.
#include "kyiv.h"
#include "kyiv_rom_boot_v1.h"
#include "kyiv_host_image_v1.h"
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

// src/main.cpp deliberately leaves its command disassembler in the other CLI
// TU (which also has main()). Supply a no-op display function; CPU is unchanged.
int disassembly(const std::uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

using W=std::uint64_t;
static constexpr W mask41=(W{1}<<41)-1;
static constexpr W signbit=(W{1}<<40);
static W pack(unsigned op,unsigned a1,unsigned a2,unsigned a3){
    if(op>037 || a1>07777 || a2>07777 || a3>07777) throw std::runtime_error("pack out of range");
    return (W(op)<<36)|(W(a1)<<24)|(W(a2)<<12)|W(a3);
}
static std::string oct(W n,int width){std::ostringstream o;o<<std::oct<<std::setfill('0')<<std::setw(width)<<n;return o.str();}
static W fp(bool neg,unsigned mantissa_numerator,unsigned mantissa_den_power,int p){
    // Exact binary fractions for diagnostic fixtures (not general-purpose FP converter).
    if(p < -64 || p > 63 || mantissa_den_power>33 || !mantissa_numerator)
        throw std::runtime_error("bad FP fixture");
    const W mant=(W(mantissa_numerator)<<(40-mantissa_den_power));
    if(!(mant&(W(1)<<39)) || mant>=(W(1)<<40)) throw std::runtime_error("unnormalized FP fixture");
    return (neg?signbit:0)|mant|W(p+64);
}
static bool in_valid_memory(W a){return a<02000 || (a>=03000 && a<04000);}
static bool known(W a,const std::set<W>&rom){
    if(a>=03000 && a<04000) return rom.count(a)!=0;
    return a<02000;
}
static W effective(unsigned field,W A){
    const W base=W(field)&03777;
    return (base+((field&04000)?A:0))&03777;
}
static std::string check_instruction(Kyiv_t& cpu,W w,const std::set<W>&source){
    const unsigned op=static_cast<unsigned>(w>>36),
      a1=static_cast<unsigned>((w>>24)&07777),
      a2=static_cast<unsigned>((w>>12)&07777),
      a3=static_cast<unsigned>(w&07777);
    if(op>=020 && op<=025) return "HOLD_IO_OPCODE";
    const W A=cpu.A_reg;
    const W x=effective(a1,A),y=effective(a2,A),z=effective(a3,A);
    std::vector<W> reads;
    if((op>=001 && op<=017 && op!=004 && op!=005 && op!=016) || op==035)
        reads.push_back(x);
    if(op==001 || op==002 || op==003 || op==004 || op==005 || op==006 ||
       op==007 || op==010 || op==011 || op==012 || op==013 || op==014 ||
       op==015 || op==016 || op==017) {
        if(op==004 || op==005 || op==016) reads.push_back(x);
        reads.push_back(y);
    }
    if(op==030 || op==031 || op==034) reads.push_back(x);
    if(op==034 && known(x,source)) {
        const W fetched=cpu.kmem.read_memory(x);
        // F reads its second 12-bit address field as the indirect register;
        // the CPU's actual opcode_F will use precisely this 12-bit value.
        reads.push_back((fetched>>12)&07777);
    }
    for(W a:reads){
        if(!in_valid_memory(a)) return "HOLD_OPERAND_INVALID_"+oct(a,4);
        if(!known(a,source)) return "HOLD_UNKNOWN_ROM_OPERAND_"+oct(a,4);
    }
    // At least syntactically known opcode; no blanket permission for zero-filled ROM.
    if(op>037 || op==036 || op==037) return "HOLD_UNSUPPORTED_OPCODE";
    // Detect any attempt to write outside RAM, prior to CPU execution.
    const bool writes_dest = op==001||op==002||op==003||op==006||op==007||
        op==010||op==011||op==012||op==013||op==014||op==015||op==017||
        op==034||op==035;
    if(writes_dest && z>=02000) return "HOLD_DESTINATION_NOT_RAM_"+oct(z,4);
    if(op==035 && y>=02000) return "HOLD_NORMALIZE_ORDER_DEST_NOT_RAM_"+oct(y,4);
    return "OK";
}


// One interpreter session: explicit Euler for dy/dt=-y, h=1/4.
// The six user instructions are *modeled* opcodes fetched by F(34) through
// the floating-point ROM. They must never run directly as CPU instructions.
// The HOST inspects checkpoint RAM words; it does not alter CPU after C=3300.
struct Mark {W pointer,y,t,delta,d;};
struct Iter {W delta,y,t,d;};
static const std::vector<Iter> EXPECT_ITERS={
  {fp(false,1,1,-1), fp(false,3,2,0), fp(false,1,1,-1), fp(false,5,3,0)},
  {fp(false,3,2,-2), fp(false,9,4,0), fp(false,1,1,0),  fp(false,3,2,-1)},
  {fp(false,9,4,-2), fp(false,27,5,-1), fp(false,3,2,0),fp(false,1,1,-2)},
  {fp(false,27,5,-3),fp(false,81,7,-1),fp(false,1,1,1),fp(true,1,1,-2)}
};
static std::vector<Mark> marks(){
    std::vector<Mark> v;
    W y=fp(false,1,1,1),t=0,delta=0,d=0;
    v.push_back({0230,y,t,delta,d});
    for(std::size_t i=0;i<EXPECT_ITERS.size();++i){
        const auto& st=EXPECT_ITERS[i];
        delta=st.delta;
        v.push_back({0231,y,t,delta,d});         // delta=h*y
        y=st.y;
        v.push_back({0232,y,t,delta,d});         // y=y-delta
        t=st.t;
        v.push_back({0233,y,t,delta,d});         // t=t+h
        d=st.d;
        v.push_back({0234,y,t,delta,d});         // d=(7/8)-t
        if(i+1<EXPECT_ITERS.size()){
            v.push_back({0235,y,t,delta,d});     // branch on positive d
            v.push_back({0230,y,t,delta,d});     // explicit back-edge
        }else{
            v.push_back({0236,y,t,delta,d});     // negative d => exit
        }
    }
    return v;
}
static const std::map<W,W> EXPECT_IMAGE={
    {0100,fp(false,1,1,1)},     // y=1
    {0101,fp(false,1,1,-1)},    // h=1/4
    {0102,0},                    // t=0
    {0103,fp(false,7,3,0)},     // exit threshold 7/8
    {0104,0},                    // delta
    {0105,0},                    // threshold-t
    {0230,pack(011,0100,0101,0104)}, // delta <- y*h
    {0231,pack(002,0100,0104,0100)}, // y <- y-delta
    {0232,pack(001,0102,0101,0102)}, // t <- t+h
    {0233,pack(002,0103,0102,0105)}, // d <- threshold-t
    {0234,pack(031,0105,0235,0236)}, // d<0 => exit
    {0235,pack(031,0,0230,0230)},    // back-edge
    {0236,pack(033,0,0,0)}           // sentinel: not executed
};
int main(int argc,char**argv){
    if(argc!=8){std::cerr<<"usage: H115_B15_NATIVE FIXED_ROM FP_K41 EULER_K41 TRACE.tsv CHECKPOINTS.tsv SESSIONS.tsv EVENTS.tsv\n";return 2;}
    try{
        kyiv_rom_boot_v1::arguments boot;
        boot.explicit_rom=true;boot.rom_filename=argv[1];
        boot.expected_sha256=kyiv_rom_boot_v1::pinned_default_sha256;
        const auto fixed=kyiv_rom_boot_v1::read(boot,argv[0]);
        const auto fp_words=kyiv_host_image_v1::load_file(argv[2],true);
        const auto user_words=kyiv_host_image_v1::load_file(argv[3],true);
        std::map<W,W> source,user;
        std::set<W> qualified;
        for(const auto& w:fixed.words)qualified.insert(w.first);
        for(const auto& w:fp_words){
            if(w.first<03300||w.first>03777||w.second>mask41||!source.emplace(w.first,w.second).second)
                throw std::runtime_error("HOLD_FP_SOURCE_FORMAT");
            qualified.insert(w.first);
        }
        if(source.size()!=251||source.count(03574)||source.count(03706)||source.count(03707)||
           source.at(03455)!=pack(004,0,0022,03376)||
           source.at(03476)!=pack(004,0,0022,03502)||
           source.at(03467)!=pack(015,0020,03607,0021)||
           source.at(03470)!=pack(015,0020,03607,0022)||
           source.at(03474)!=pack(010,0022,03611,0022))
            throw std::runtime_error("HOLD_SOURCE_ANCHOR_DRIFT");
        qualified.insert(03000);qualified.insert(03706);qualified.insert(03707);
        for(const auto& w:user_words){
            if(w.first==0||w.first>=02000||w.second>mask41||!user.emplace(w.first,w.second).second)
                throw std::runtime_error("HOLD_USER_IMAGE_INVALID");
        }
        if(user!=EXPECT_IMAGE) throw std::runtime_error("HOLD_USER_IMAGE_WORD_DRIFT");
        std::ofstream trace(argv[4],std::ios::binary), checkpoints(argv[5],std::ios::binary),
                      sessions(argv[6],std::ios::binary),events(argv[7],std::ios::binary);
        if(!trace||!checkpoints||!sessions||!events)throw std::runtime_error("HOLD_REPORT_OPEN");
        trace<<"step\tpc_before\tword\tpc_after\tprogram_pointer_before\tprogram_pointer_after\ty_after\tt_after\tdelta_after\td_after\tgate\n";
        checkpoints<<"ordinal\tpointer\ty_expected\ty_observed\tt_expected\tt_observed\tdelta_expected\tdelta_observed\td_expected\td_observed\tstatus\tsteps\n";
        sessions<<"case\tstatus\tsteps\tcheckpoints\tend_pc\tend_pointer\tarithmetic_ops\titerations\tback_edge_count\tdecisions\tactual_cpu_run\thardware_oracle\n";
        events<<"step\tpc_before\topcode\tcurrent_pointer\tnew_pointer\tcomment\n";
        Kyiv_t cpu(Kyiv_t::rom_boot_mode::deferred);
        kyiv_rom_boot_v1::install(cpu,fixed);
        for(const auto& w:fp_words)cpu.kmem.write_rom(w.first,w.second);
        cpu.kmem.write_rom(03467,pack(015,0020,03605,0021));
        cpu.kmem.write_rom(03470,pack(015,0020,03606,0022));
        cpu.kmem.write_rom(03474,pack(001,0022,03611,0022));
        cpu.kmem.write_rom(03476,pack(005,0,0,03706));
        cpu.kmem.write_rom(03706,pack(005,0023,0021,03502));
        cpu.kmem.write_rom(03707,pack(005,0,0,03504));
        cpu.kmem.write_rom(03455,pack(004,0,0022,03370));
        for(const auto& w:user)cpu.kmem.write_memory(w.first,w.second);
        cpu.kmem.set_panel_nk_word(03000,pack(0,0,0230,0));
        cpu.kmem.select_panel_nk(03000,true);
        cpu.emergency_stop_blocked=true;
        cpu.C_reg=03300; // only HOST PC assignment, before run
        const auto m=marks();
        unsigned steps=0,idx=0,arith=0,backs=0,decisions=0;
        bool derived10=false,derived25=false,derived26=false,derived27=false;
        W d10=0,d25=0,d26=0,d27=0;
        std::string state="HOLD_MAX_STEPS";
        constexpr unsigned LIMIT=2500;
        while(steps<LIMIT){
            const W pc=cpu.C_reg;
            const W ptr=(cpu.kmem.read_memory(0014)>>12)&07777;
            if(pc==03305){
                if(idx>=m.size()){state="HOLD_EXTRA_DISPATCH";break;}
                const Mark& ck=m[idx];
                const W y=cpu.kmem.read_memory(0100),t=cpu.kmem.read_memory(0102),
                    delta=cpu.kmem.read_memory(0104),d=cpu.kmem.read_memory(0105);
                const bool good=ptr==ck.pointer&&y==ck.y&&t==ck.t&&delta==ck.delta&&d==ck.d;
                checkpoints<<idx<<'\t'<<oct(ptr,4)<<'\t'
                  <<oct(ck.y,14)<<'\t'<<oct(y,14)<<'\t'
                  <<oct(ck.t,14)<<'\t'<<oct(t,14)<<'\t'
                  <<oct(ck.delta,14)<<'\t'<<oct(delta,14)<<'\t'
                  <<oct(ck.d,14)<<'\t'<<oct(d,14)<<'\t'
                  <<(good?"WORD_MATCH":"WORD_MISMATCH")<<'\t'<<steps<<'\n';
                if(!good){state="HOLD_CHECKPOINT_DRIFT";break;}
                ++idx;
                if(idx==m.size()){state="PASS_EULER_MACHINE_LOOP_NOT_HISTORICAL";break;}
            }
            if(!in_valid_memory(pc)||!known(pc,qualified)){
                state="HOLD_UNKNOWN_EXECUTION_ADDRESS_"+oct(pc,4);break;
            }
            if(user.count(pc)){state="HOLD_RAW_USER_INSTRUCTION_FETCH_"+oct(pc,4);break;}
            const bool admit10=pc==0010&&derived10&&cpu.kmem.read_memory(0010)==d10;
            const bool admit25=pc==0025&&derived25&&cpu.kmem.read_memory(0025)==d25;
            const bool admit26=pc==0026&&derived26&&cpu.kmem.read_memory(0026)==d26;
            const bool admit27=pc==0027&&derived27&&cpu.kmem.read_memory(0027)==d27;
            if(pc<03000 && pc!=0011 && pc!=0012 && !admit10 && !admit25 && !admit26 && !admit27){
                state="HOLD_UNQUALIFIED_RAM_EXEC_"+oct(pc,4);break;
            }
            if(pc==03574){state="HOLD_UNPRINTED_ROM_3574";break;}
            if(pc>=03600 && pc<=03627){state="HOLD_ROM_CONSTANT_EXEC";break;}
            const W w=cpu.kmem.read_memory(pc);
            if(pc<03000 && w==0){state="HOLD_RAM_ZERO_EXEC";break;}
            const std::string safe=check_instruction(cpu,w,qualified);
            if(safe!="OK"){state="HOLD_PRE_EXECUTION_"+safe;break;}
            W ex10=0,ex25=0,ex26=0,ex27=0;
            if(pc==03317){if(w!=pack(001,0011,0,0010)){state="HOLD_SOURCE_3317";break;}ex10=cpu.kmem.read_memory(0011);}
            if(pc==03300){if(w!=pack(001,0,03621,0026)){state="HOLD_SOURCE_3300";break;}ex26=cpu.kmem.read_memory(03621);}
            if(pc==03301){if(w!=pack(001,0,03622,0027)){state="HOLD_SOURCE_3301";break;}ex27=cpu.kmem.read_memory(03622);}
            if(pc==03333){if(w!=pack(014,0013,03613,0025)){state="HOLD_SOURCE_3333";break;}ex25=cpu.kmem.read_memory(0013)|cpu.kmem.read_memory(03613);}
            const bool cont=cpu.execute_opcode();
            if(pc==03317){d10=ex10;derived10=cpu.kmem.read_memory(0010)==d10;}
            if(pc==03300){d26=ex26;derived26=cpu.kmem.read_memory(0026)==d26;}
            if(pc==03301){d27=ex27;derived27=cpu.kmem.read_memory(0027)==d27;}
            if(pc==03333){d25=ex25;derived25=cpu.kmem.read_memory(0025)==d25;}
            if((pc==03317&&!derived10)||(pc==03300&&!derived26)||(pc==03301&&!derived27)||(pc==03333&&!derived25)){
                state="HOLD_SOURCE_DERIVED_TRAMPOLINE";break;
            }
            if(pc==03455 && w!=pack(004,0,0022,03370)){state="HOLD_ROUNDING_PRIVATE_DRIFT";break;}
            if(pc==03476 && (w!=pack(005,0,0,03706)||cpu.C_reg!=03706)){state="HOLD_DIVISION_ROUTER_DRIFT";break;}
            if(pc==03706 && w!=pack(005,0023,0021,03502)){state="HOLD_DIVISION_COMP_DRIFT";break;}
            if(pc==03707 && (w!=pack(005,0,0,03504)||cpu.C_reg!=03504)){state="HOLD_DIVISION_FALLTHROUGH_DRIFT";break;}
            if(pc==03474 && w!=pack(001,0022,03611,0022)){state="HOLD_BIAS_WORD_DRIFT";break;}
            // Restrict every user RAM write to four declared state/temporary cells.
            for(const auto& e:user)if(e.first!=0100&&e.first!=0102&&e.first!=0104&&e.first!=0105 &&cpu.kmem.read_memory(e.first)!=e.second){
                state="HOLD_USER_SOURCE_MUTATION";break;
            }
            if(state=="HOLD_USER_SOURCE_MUTATION")break;
            const W newptr=(cpu.kmem.read_memory(0014)>>12)&07777;
            if(ptr!=newptr && (pc==03304||pc==03305||pc==03320||pc==03372||pc==03317||pc==03572)){
                events<<steps+1<<'\t'<<oct(pc,4)<<'\t'<<oct(w>>36,2)
                      <<'\t'<<oct(ptr,4)<<'\t'<<oct(newptr,4)<<"\tPOINTER_CHANGE\n";
            }
            ++steps;
            trace<<steps<<'\t'<<oct(pc,4)<<'\t'<<oct(w,14)<<'\t'
                 <<oct(cpu.C_reg,4)<<'\t'<<oct(ptr,4)<<'\t'<<oct(newptr,4)<<'\t'
                 <<oct(cpu.kmem.read_memory(0100),14)<<'\t'<<oct(cpu.kmem.read_memory(0102),14)
                 <<'\t'<<oct(cpu.kmem.read_memory(0104),14)<<'\t'<<oct(cpu.kmem.read_memory(0105),14)
                 <<'\t'<<(cont?"CONTINUE":"CPU_STOP")<<'\n';
            if(!cont){state="HOLD_CPU_STOP";break;}
        }
        // Count loop structure from verified dispatcher checkpoints.
        for(std::size_t j=1;j<idx;++j)if(m[j].pointer==0230 && m[j-1].pointer!=0230)++backs;
        for(std::size_t j=0;j<idx;++j)if(m[j].pointer==0234)++decisions;
        for(std::size_t j=0;j<idx;++j)if(m[j].pointer==0231||m[j].pointer==0232||m[j].pointer==0233||m[j].pointer==0234)++arith;
        if(state=="PASS_EULER_MACHINE_LOOP_NOT_HISTORICAL"){
            if(idx!=m.size()||backs!=3||decisions!=4||arith!=16||
               cpu.C_reg!=03305||((cpu.kmem.read_memory(0014)>>12)&07777)!=0236)
                state="HOLD_EULER_COVERAGE";
        }
        sessions<<"EULER_NEG_Y"<<'\t'<<state<<'\t'<<steps<<'\t'<<idx<<'\t'
          <<oct(cpu.C_reg,4)<<'\t'<<oct((cpu.kmem.read_memory(0014)>>12)&07777,4)<<'\t'
          <<arith<<'\t'<<4<<'\t'<<backs<<'\t'<<decisions<<"\t1\tNO\n";
        trace.flush();checkpoints.flush();sessions.flush();events.flush();
        if(!trace||!checkpoints||!sessions||!events)throw std::runtime_error("HOLD_REPORT_WRITE");
        std::cerr<<"H115_B15 EULER_NEG_Y "<<state<<" steps="<<steps<<" checkpoints="<<idx
          <<" backs="<<backs<<" decisions="<<decisions<<" arithmetic="<<arith<<"\n";
        return state=="PASS_EULER_MACHINE_LOOP_NOT_HISTORICAL"?0:4;
    }catch(const std::exception&ex){std::cerr<<"HOLD_H115_B15_NATIVE_EXCEPTION "<<ex.what()<<"\n";return 5;}
}
