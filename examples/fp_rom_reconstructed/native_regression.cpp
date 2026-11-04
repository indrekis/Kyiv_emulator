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
struct Case{const char* name;unsigned opcode;W lhs,rhs,expected;};
static const std::vector<Case> cases={
    {"ADD_HALF_QUARTER",001,fp(false,1,1,0),fp(false,1,1,-1),fp(false,3,2,0)},
    {"SUB_HALF_QUARTER",002,fp(false,1,1,0),fp(false,1,1,-1),fp(false,1,1,-1)},
    {"MUL_HALF_QUARTER",011,fp(false,1,1,0),fp(false,1,1,-1),fp(false,1,1,-2)},
    {"DIV_HALF_QUARTER",012,fp(false,1,1,0),fp(false,1,1,-1),fp(false,1,1,2)},
    {"DIV_HALF_HALF",012,fp(false,1,1,0),fp(false,1,1,0),fp(false,1,1,1)},
    {"DIV_QUARTER_HALF",012,fp(false,1,1,-1),fp(false,1,1,0),fp(false,1,1,0)},
    {"DIV_QUARTER_QUARTER",012,fp(false,1,1,-1),fp(false,1,1,-1),fp(false,1,1,1)},
    {"DIV_EXP_M3_M1",012,fp(false,1,1,-3),fp(false,1,1,-1),010000000000077ULL},
    {"DIV_EXP_M1_M3",012,fp(false,1,1,-1),fp(false,1,1,-3),010000000000103ULL},
    {"DIV_EXP_Z_M3",012,fp(false,1,1,0),fp(false,1,1,-3),010000000000104ULL},
    {"DIV_EXP_M3_Z",012,fp(false,1,1,-3),fp(false,1,1,0),010000000000076ULL},
    {"DIV_EXP_P2_Z",012,fp(false,1,1,2),fp(false,1,1,0),010000000000103ULL},
    {"DIV_EXP_Z_P2",012,fp(false,1,1,0),fp(false,1,1,2),010000000000077ULL},
    {"DIV_EXP_P3_P1",012,fp(false,1,1,3),fp(false,1,1,1),010000000000103ULL},
    {"DIV_EXP_P1_P3",012,fp(false,1,1,1),fp(false,1,1,3),010000000000077ULL},
    {"DIV_EXP_P2_M2",012,fp(false,1,1,2),fp(false,1,1,-2),010000000000105ULL},
    {"DIV_EXP_M2_P2",012,fp(false,1,1,-2),fp(false,1,1,2),010000000000075ULL},
    {"DIV_SIGN_NP",012,fp(true,1,1,0),fp(false,1,1,-1),030000000000102ULL},
    {"DIV_SIGN_PN",012,fp(false,1,1,0),fp(true,1,1,-1),030000000000102ULL},
    {"DIV_SIGN_NN",012,fp(true,1,1,0),fp(true,1,1,-1),010000000000102ULL},
    {"DIV_SIGN_NN_EQUAL",012,fp(true,1,1,0),fp(true,1,1,0),010000000000101ULL},
    {"DIV_SIGN_NEGQUARTER_HALF",012,fp(true,1,1,-1),fp(false,1,1,0),030000000000100ULL},
    {"DIV_SIGN_HALF_NEGHALF",012,fp(false,1,1,0),fp(true,1,1,0),030000000000101ULL},
    {"DIV_SIGN_NEGQUARTER_NEGHALF",012,fp(true,1,1,-1),fp(true,1,1,0),010000000000100ULL},
    {"DIV_SIGN_NEGQUARTER_QUARTER",012,fp(true,1,1,-1),fp(false,1,1,-1),030000000000101ULL},
    {"DIV_MANT_075_05",012,fp(false,3,2,0),fp(false,1,1,0),014000000000101ULL},
    {"DIV_MANT_075_025",012,fp(false,3,2,0),fp(false,1,1,-1),014000000000102ULL},
    {"DIV_MANT_0375_05",012,fp(false,3,2,-1),fp(false,1,1,0),014000000000100ULL},
    {"DIV_MANT_0375_025",012,fp(false,3,2,-1),fp(false,1,1,-1),014000000000101ULL},
    {"DIV_MANT_NEG075_05",012,fp(true,3,2,0),fp(false,1,1,0),034000000000101ULL},
    {"DIV_MANT_075_NEG05",012,fp(false,3,2,0),fp(true,1,1,0),034000000000101ULL},
    {"DIV_MANT_NEG075_NEG05",012,fp(true,3,2,0),fp(true,1,1,0),014000000000101ULL},
    {"DIV_MANT_075_0375",012,fp(false,3,2,0),fp(false,3,2,-1),010000000000102ULL},
    {"ADD_HALF_HALF",001,fp(false,1,1,0),fp(false,1,1,0),010000000000101ULL},
    {"ADD_075_0125",001,fp(false,3,2,0),fp(false,1,1,-2),016000000000100ULL},
    {"SUB_075_0125",002,fp(false,3,2,0),fp(false,1,1,-2),012000000000100ULL},
    {"MUL_075_05",011,fp(false,3,2,0),fp(false,1,1,0),014000000000077ULL},
    {"MUL_NEG05_025",011,fp(true,1,1,0),fp(false,1,1,-1),030000000000076ULL},
    {"ADD_NEG05_025",001,fp(true,1,1,0),fp(false,1,1,-1),030000000000077ULL},
    {"DIV_I_HALF_075",012,fp(false,1,1,0),fp(false,3,2,0),012525252525300ULL},
    {"DIV_I_075_0625",012,fp(false,3,2,0),fp(false,5,3,0),011463146314701ULL},
    {"DIV_I_0625_075",012,fp(false,5,3,0),fp(false,3,2,0),015252525252500ULL},
    {"DIV_I_0875_075",012,fp(false,7,3,0),fp(false,3,2,0),011252525252501ULL},
    {"DIV_I_0625_0875",012,fp(false,5,3,0),fp(false,7,3,0),013333333333300ULL},
    {"DIV_I_HALF_0875",012,fp(false,1,1,0),fp(false,7,3,0),011111111111100ULL},
    {"DIV_I_075_0875",012,fp(false,3,2,0),fp(false,7,3,0),015555555555500ULL},
    {"DIV_I_NEG_HALF_075",012,fp(true,1,1,0),fp(false,3,2,0),032525252525300ULL},
    {"DIV_I_075_NEG_0625",012,fp(false,3,2,0),fp(true,5,3,0),031463146314701ULL},
    {"DIV_I_NEG_0625_NEG_075",012,fp(true,5,3,0),fp(true,3,2,0),015252525252500ULL},
    {"DIV_I_075_M2_0625_P1",012,fp(false,3,2,-2),fp(false,5,3,1),011463146314676ULL},
    {"DIV_I_0625_P2_075_M1",012,fp(false,5,3,2),fp(false,3,2,-1),015252525252503ULL},
};
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
int main(int argc,char**argv){
  if(argc!=7){std::cerr<<"usage: H115_B9_NATIVE FIXED_ROM FP_K41 TRACE_TSV RESULTS_TSV VARIANT INTERVENTIONS_TSV\n";return 2;}
  try{
    const std::string variant=argv[5];
    if(variant!="MACHINE_ROM_BRANCH")
      throw std::runtime_error("UNRECOGNIZED_PRIVATE_VARIANT");
    kyiv_rom_boot_v1::arguments boot;
    boot.explicit_rom=true;
    boot.rom_filename=argv[1];
    boot.expected_sha256=kyiv_rom_boot_v1::pinned_default_sha256;
    const auto fixed=kyiv_rom_boot_v1::read(boot,argv[0]);
    const auto fp_words=kyiv_host_image_v1::load_file(argv[2],true);
    std::set<W> src;
    for(const auto& w:fixed.words) src.insert(w.first);
    std::set<W> fpset;
    std::map<W,W> original;
    for(const auto& w:fp_words){
      original.emplace(w.first,w.second);
      if(w.first<03300 || w.first>03777 || !fpset.insert(w.first).second) throw std::runtime_error("FP_INVALID_ADDRESS");
      if(w.second>mask41) throw std::runtime_error("FP_INVALID_WORD");
    }
    // B20: only one complete, pinned 257-word functional ROM image is admitted.
    if(fpset.size()!=257 || fpset.count(03574) ||
       original.at(03467)!=pack(015,0020,03605,0021) ||
       original.at(03470)!=pack(015,0020,03606,0022) ||
       original.at(03474)!=pack(001,0022,03611,0022) ||
       original.at(03476)!=pack(005,0,0,03706) ||
       original.at(03706)!=pack(005,0023,0021,03502) ||
       original.at(03707)!=pack(005,0,0,03504) ||
       original.at(03455)!=pack(004,0,0022,03370) ||
       original.at(03367)!=pack(031,0021,03710,03712) ||
       original.at(03710)!=pack(001,03042,0021,0021) ||
       original.at(03711)!=pack(005,0,0,03370) ||
       original.at(03712)!=pack(002,0021,03042,0021) ||
       original.at(03713)!=pack(005,0,0,03370))
         throw std::runtime_error("HOLD_FUNCTIONAL_ROM_ANCHOR_DRIFT");
    src.insert(fpset.begin(),fpset.end()); src.insert(03000);
    // STRICT PRIVATE extension: these two octal addresses are NOT printed in GY1962.
    // They are executable only for MACHINE_ROM_BRANCH, never in SOURCE_PRINTED.
    if(variant=="MACHINE_ROM_BRANCH"){
      src.insert(03706);src.insert(03707);
      src.insert(03710);src.insert(03711);src.insert(03712);src.insert(03713);
    }
    std::ofstream trace(argv[3],std::ios::binary),results(argv[4],std::ios::binary),
      interventions(argv[6],std::ios::binary);
    if(!trace||!results||!interventions)throw std::runtime_error("REPORT_OPEN_FAILED");
    interventions<<"case\tclassification\tcomment\n"; // B7 must contain zero interventions.
    trace<<"case\tstep\tpc_before\tword\tpc_after\tA_after\tP_after\tprogram_pointer_after\tresult_after\tgate\tram0025_after\tram0022_after\tram0024_after\tram0013_after\tram0016_after\tderived0025_provenance\tram0020_after\tram0021_after\tram0023_after\tram0026_after\tram0027_after\tderived0026_provenance\tderived0027_provenance\n";
    results<<"case\tstatus\tsteps\tboundary_PC\tprogram_pointer\toperand1\toperand2\texpected\tobserved\temergency_stop_blocked\thardware_oracle\n";
    for(std::size_t case_ix=0;case_ix<cases.size();++case_ix){
      const auto& tc=cases[case_ix];
      Kyiv_t cpu(Kyiv_t::rom_boot_mode::deferred);
      kyiv_rom_boot_v1::install(cpu,fixed);
      for(const auto& w:fp_words)cpu.kmem.write_rom(w.first,w.second);
      // B20: the complete functional ROM has already been loaded above.
      const W nk=pack(0,0,0042,0);
      cpu.kmem.set_panel_nk_word(03000,nk);
      cpu.kmem.select_panel_nk(03000,true);
      cpu.kmem.write_memory(0042,pack(tc.opcode,0100,0101,0102));
      cpu.kmem.write_memory(0100,tc.lhs);
      cpu.kmem.write_memory(0101,tc.rhs);
      cpu.kmem.write_memory(0102,0);
      cpu.emergency_stop_blocked=true; // explicit HOST simulation policy, GY62 p.113
      cpu.C_reg=03300;
      std::string state="HOLD_LIMIT",gate="";
      int steps=0;
      bool derived0025=false, derived0026=false, derived0027=false;
      W derived0025_word=0, derived0026_word=0, derived0027_word=0;
      constexpr int MAX_STEPS=512;
      for(;steps<MAX_STEPS;){
        const W pc=cpu.C_reg;
        if(pc==03305 && ((cpu.kmem.read_memory(0014)>>12)&07777)==0043){
          const bool equal=(cpu.kmem.read_memory(0102)==tc.expected);
          if(case_ix>=39)
            state=equal?"INEXACT_TRUNC_PROXY_MATCH":"INEXACT_TRUNC_PROXY_MISMATCH";
          else
            state=variant=="SOURCE"
                ? (equal?"NUMERIC_EXACT_NATIVE_HOST":"NUMERIC_MISMATCH_NATIVE_HOST")
                : (equal?"SYNTHETIC_MUTANT_NUMERIC_EXACT":"SYNTHETIC_MUTANT_NUMERIC_MISMATCH");
          gate="STOP_BEFORE_UNSOURCED_0043";
          break;
        }
        if(!in_valid_memory(pc) || !known(pc,src)){
          state="HOLD_UNKNOWN_PC";gate="PC_"+oct(pc,4);break;
        }
        // RAM[0025] is only admissible if source-ROM instruction 3333
        // generated it and it remains byte-for-byte identical to that write.
        const bool admitted_derived0025 =
            pc==00025 && derived0025 && cpu.kmem.read_memory(00025)==derived0025_word;
        const bool admitted_derived0026 =
            pc==00026 && derived0026 && cpu.kmem.read_memory(00026)==derived0026_word;
        const bool admitted_derived0027 =
            pc==00027 && derived0027 && cpu.kmem.read_memory(00027)==derived0027_word;
        if(pc<03000 && pc!=00011 && pc!=00012 && pc!=00042 &&
           !admitted_derived0025 && !admitted_derived0026 && !admitted_derived0027){
          state="HOLD_UNQUALIFIED_RAM_EXEC";gate="PC_"+oct(pc,4);break;
        }
        if(pc>=03600 && pc<=03627){
          state="HOLD_EXECUTED_ROM_CONSTANT";gate="PC_"+oct(pc,4);break;
        }
        const W w=cpu.kmem.read_memory(pc);
        if(pc<03000 && w==0){state="HOLD_UNQUALIFIED_ZERO_RAM";gate="PC_"+oct(pc,4);break;}
        gate=check_instruction(cpu,w,src);
        if(gate!="OK"){state="HOLD_PRE_EXECUTION";break;}
        // Audit the *actual* source instruction 3333: 14 0013 3613 0025.
        // Pre-compute its expected OR result but grant no permission until
        // the unchanged CPU executes it and the destination matches exactly.
        W expected_new_0025=0, expected_new_0026=0, expected_new_0027=0;
        // Two historical source instructions initialize the executable RAM
        // trampolines before any dispatcher operation. Verify both provenance
        // and exact word bytes before later admitting a program-counter fetch.
        if(pc==03300){
          if(w!=pack(001,0000,03621,0026)){
            state="HOLD_3300_SOURCE_DRIFT";gate="SOURCE_WORD_3300";break;
          }
          expected_new_0026=cpu.kmem.read_memory(03621);
        }
        if(pc==03301){
          if(w!=pack(001,0000,03622,0027)){
            state="HOLD_3301_SOURCE_DRIFT";gate="SOURCE_WORD_3301";break;
          }
          expected_new_0027=cpu.kmem.read_memory(03622);
        }
        if(pc==03333){
          if(w!=pack(014,0013,03613,0025)){
            state="HOLD_3333_SOURCE_DRIFT";gate="SOURCE_WORD_3333";break;
          }
          expected_new_0025=cpu.kmem.read_memory(0013)|cpu.kmem.read_memory(03613);
        }
        const bool cont=cpu.execute_opcode();
        // H115-B11. No synthetic PC modification after execute_opcode().
        // Conditional flow MUST come from the three genuine CPU instructions
        // (3476,3706,3707) installed privately below.
        if(variant=="MACHINE_ROM_BRANCH" && pc==03476){
          if(w!=pack(005,0000,0000,03706) || cpu.C_reg!=03706)
            throw std::runtime_error("HOLD_B11_ROUTER_3476_WRONG_EXECUTION");
        }
        if(variant=="MACHINE_ROM_BRANCH" && pc==03706){
          const W num=cpu.kmem.read_memory(0021),den=cpu.kmem.read_memory(0023);
          if(num!=((tc.lhs&(~W(0177))) & mask41) ||
             den!=((tc.rhs&(~W(0177))) & mask41))
            throw std::runtime_error("HOLD_B11_MANTISSA_PROVENANCE_DRIFT");
          const W anum=num & ~signbit,aden=den & ~signbit;
          const W expected=aden<=anum?03502:03707;
          if(w!=pack(005,0023,0021,03502) || cpu.C_reg!=expected)
            throw std::runtime_error("HOLD_B11_COMPARE_MACHINE_BRANCH_MISMATCH");
          interventions<<tc.name<<"\tPRIVATE_CPU_ROM_COMPARE\t"
            <<"3706;DEN_LE_NUM="<<(aden<=anum?1:0)
            <<";NEXT="<<oct(cpu.C_reg,4)<<"\n";
        }
        if(variant=="MACHINE_ROM_BRANCH" && pc==03707){
          if(w!=pack(005,0000,0000,03504) || cpu.C_reg!=03504)
            throw std::runtime_error("HOLD_B11_FALLTHROUGH_MACHINE_BRANCH_MISMATCH");
        }
        // For BOTH_ADD_BIAS, the unchanged CPU's opcode 01 at modified ROM
        // address 3474 must itself write the biased exponent into RAM[0022].
        if((variant=="BOTH_ADD_BIAS" || variant=="MACHINE_ROM_BRANCH") && tc.opcode==012 && pc==03474){
          if(w!=pack(001,0022,03611,0022))
            throw std::runtime_error("HOLD_B7_3474_ROM_ONLY_WORD_MISMATCH");
          const int delta=int(tc.lhs&0177)-int(tc.rhs&0177);
          const int biased=delta+0100;
          if(biased<1 || biased>0176 || cpu.kmem.read_memory(0022)!=W(biased))
            throw std::runtime_error("HOLD_B7_3474_PRODUCTION_CPU_BIAS_MISMATCH");
        }
        if(pc==03300){
          derived0026_word=expected_new_0026;
          derived0026=cpu.kmem.read_memory(0026)==expected_new_0026;
          if(!derived0026){state="HOLD_0026_WRITE_MISMATCH";gate="DERIVED_0026_NOT_MATCH";}
        }
        if(pc==03301){
          derived0027_word=expected_new_0027;
          derived0027=cpu.kmem.read_memory(0027)==expected_new_0027;
          if(!derived0027){state="HOLD_0027_WRITE_MISMATCH";gate="DERIVED_0027_NOT_MATCH";}
        }
        if(pc==03333){
          derived0025_word=expected_new_0025;
          derived0025=cpu.kmem.read_memory(0025)==expected_new_0025;
          if(!derived0025){state="HOLD_0025_WRITE_MISMATCH";gate="DERIVED_WORD_NOT_MATCH";}
        }
        ++steps;
        trace<<tc.name<<'\t'<<steps<<'\t'<<oct(pc,4)<<'\t'<<oct(w,14)<<'\t'<<oct(cpu.C_reg,4)
          <<'\t'<<oct(cpu.A_reg,4)<<'\t'<<oct(cpu.P_reg,4)<<'\t'<<oct((cpu.kmem.read_memory(0014)>>12)&07777,4)
          <<'\t'<<oct(cpu.kmem.read_memory(0102),14)<<'\t'<<(cont?"CONTINUE":"CPU_STOP")
          <<'\t'<<oct(cpu.kmem.read_memory(0025),14)
          <<'\t'<<oct(cpu.kmem.read_memory(0022),14)
          <<'\t'<<oct(cpu.kmem.read_memory(0024),14)
          <<'\t'<<oct(cpu.kmem.read_memory(0013),14)
          <<'\t'<<oct(cpu.kmem.read_memory(0016),14)
          <<'\t'<<(derived0025?"SOURCE_3333_OR_VERIFIED":"NOT_QUALIFIED")
          <<'\t'<<oct(cpu.kmem.read_memory(0020),14)
          <<'\t'<<oct(cpu.kmem.read_memory(0021),14)
          <<'\t'<<oct(cpu.kmem.read_memory(0023),14)
          <<'\t'<<oct(cpu.kmem.read_memory(0026),14)
          <<'\t'<<oct(cpu.kmem.read_memory(0027),14)
          <<'\t'<<(derived0026?"SOURCE_3300_COPY_VERIFIED":"NOT_QUALIFIED")
          <<'\t'<<(derived0027?"SOURCE_3301_COPY_VERIFIED":"NOT_QUALIFIED")<<'\n';
        if(state=="HOLD_0025_WRITE_MISMATCH" || state=="HOLD_0026_WRITE_MISMATCH" || state=="HOLD_0027_WRITE_MISMATCH") break;
        if(!cont){state="HOLD_CPU_STOP";gate="CPU_STOP";break;}
      }
      results<<tc.name<<'\t'<<state<<'\t'<<steps<<'\t'<<oct(cpu.C_reg,4)
        <<'\t'<<oct((cpu.kmem.read_memory(0014)>>12)&07777,4)<<'\t'<<oct(tc.lhs,14)<<'\t'<<oct(tc.rhs,14)
        <<'\t'<<oct(tc.expected,14)<<'\t'<<oct(cpu.kmem.read_memory(0102),14)
        <<"\t1\tNO\n";
      std::cerr<<"H115B10_VARIANT="<<variant<<" CASE="<<tc.name<<" STATUS="<<state<<" STEPS="<<steps
        <<" PC="<<oct(cpu.C_reg,4)<<" GATE="<<gate<<"\n";
    }
    trace.flush();results.flush();interventions.flush();
    if(!trace||!results||!interventions)throw std::runtime_error("REPORT_WRITE_FAILED");
    std::cerr<<"H115B10_NATIVE_COMPLETED=51_CASES VARIANT="<<variant<<" NOT_HISTORICAL_ACCEPTANCE\n";
    return 0;
  }catch(const std::exception& e){std::cerr<<"H115B9_NATIVE_FATAL="<<e.what()<<'\n';return 3;}
}
