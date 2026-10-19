#ifndef KYIVEMU_D14B3_DRUM_PERSISTENCE_H
#define KYIVEMU_D14B3_DRUM_PERSISTENCE_H

// ISA-07 D14-B3. Host-defined, canonical, uncompressed binary logical media.
// NOT the historical magnetic recording or a physical disk/drum dump.
// The source media and CPU are untouched. All error codes are HOST_POLICY.
// KYIVDRM1 v1 wire format (.kdr); all integers unsigned little-endian:
//   0:8 magic "KYIVDRM1"; 8:4 version=1; 12:4 header_size=64
//  16:8 drums; 24:8 tracks; 32:8 slots; 40:8 N; 48:8 written_count
//  56:4 P=profile_len; 60:4 reserved=0
//  64:P ASCII profile_id; 64+P:B written bitmap
//  64+P+B:8*N raw words; final 8: CRC64/ECMA-182, LE
// N=drums*tracks*slots; B=ceil(N/8); total=64+P+B+8*N+8.
// Linear index i=((drum*tracks)+track)*slots+slot.
// Bitmap byte i/8, bit i%8 (LSB-first); unused bits are zero.
// Every payload is uint64 LE, bits 63..41 zero; bit 40 is sign.
// UNWRITTEN: bitmap=0 and payload=0; WRITTEN +0/-0 stay distinct.
// CRC covers every byte before the trailer, not the trailer itself.
// Canonical HOST format, NOT physical drum encoding.
// Full specification: docs/ISA_07_D14B3_BINARY_IMAGE_V1.md.
#include "kyiv_drum_logical_media.h"
#include <array>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <limits>
#include <string>
#include <system_error>
#include <vector>

namespace kyiv_drum_persistence {
using kyiv_drum_media::coordinate;
using kyiv_drum_media::geometry;
using kyiv_drum_media::logical_media;
using kyiv_drum_media::media_error;
using kyiv_drum_media::raw_word_t;

constexpr std::size_t fixed_header_size = 64;
constexpr std::size_t trailer_size = 8;
constexpr std::size_t max_file_size = 9 * 1024 * 1024; // host safety bound
constexpr std::uint32_t version = 1;
constexpr std::array<std::uint8_t,8> magic{{'K','Y','I','V','D','R','M','1'}};

inline void put_le(std::vector<std::uint8_t>& out, std::uint64_t v, unsigned n) {
    for (unsigned i=0; i<n; ++i)
        out.push_back(static_cast<std::uint8_t>((v >> (8*i)) & 0xff));
}
inline std::uint64_t read_le(const std::vector<std::uint8_t>& bytes,
                             std::size_t pos, unsigned n) {
    if (pos > bytes.size() || n > bytes.size()-pos)
        throw media_error("TRUNCATED_IMAGE");
    std::uint64_t result=0;
    for (unsigned i=0; i<n; ++i)
        result |= std::uint64_t(bytes[pos+i]) << (8*i);
    return result;
}
// CRC64/ECMA-182: poly=42F0E1EBA9EA3693, non-reflected, init=0, xorout=0.
inline std::uint64_t crc64(const std::uint8_t* data, std::size_t n) noexcept {
    constexpr std::uint64_t poly=UINT64_C(0x42F0E1EBA9EA3693);
    std::uint64_t crc=0;
    for (std::size_t i=0; i<n; ++i) {
        crc ^= std::uint64_t(data[i]) << 56;
        for (unsigned j=0; j<8; ++j)
            crc=(crc & (UINT64_C(1)<<63)) ? ((crc<<1)^poly) : (crc<<1);
    }
    return crc;
}
inline std::size_t linear_capacity(const geometry& g) {
    // B1 validates profile, dimensional overflow and the 1,000,000-cell bound.
    const logical_media check(g);
    return check.capacity();
}
inline coordinate from_linear(const geometry& g, std::size_t i) noexcept {
    const std::size_t per_drum=g.tracks_per_drum*g.slots_per_track;
    const std::size_t in_drum=i%per_drum;
    return {i/per_drum, in_drum/g.slots_per_track, in_drum%g.slots_per_track};
}
inline std::vector<std::uint8_t> encode(const logical_media& source) {
    const geometry& g=source.profile();
    const std::size_t count=source.capacity();
    const std::size_t bitmap=(count+7)/8;
    const std::size_t needed=fixed_header_size+g.profile_id.size()+bitmap+8*count+trailer_size;
    if (needed>max_file_size) throw media_error("IMAGE_TOO_LARGE");
    std::vector<std::uint8_t> out;
    out.reserve(needed);
    out.insert(out.end(),magic.begin(),magic.end());
    put_le(out,version,4);
    put_le(out,fixed_header_size,4);
    put_le(out,g.drums,8);
    put_le(out,g.tracks_per_drum,8);
    put_le(out,g.slots_per_track,8);
    put_le(out,count,8);
    put_le(out,source.written_count(),8);
    put_le(out,g.profile_id.size(),4);
    put_le(out,0,4); // reserved=zero
    out.insert(out.end(),g.profile_id.begin(),g.profile_id.end());
    const std::size_t bitmap_start=out.size();
    out.insert(out.end(),bitmap,0);
    std::size_t observed_written=0;
    for (std::size_t i=0; i<count; ++i) {
        const auto c=source.inspect(from_linear(g,i));
        if (c.written) {
            if ((c.word & ~kyiv_drum_media::word_mask)!=0)
                throw media_error("INVALID_WORD");
            out[bitmap_start+i/8] |= static_cast<std::uint8_t>(1u << (i%8));
            ++observed_written;
        }
        put_le(out,c.written ? c.word : 0,8);
    }
    if (observed_written != source.written_count())
        throw media_error("INVALID_COUNT");
    const auto digest=crc64(out.data(),out.size());
    put_le(out,digest,8);
    if (out.size()!=needed) throw media_error("INVALID_LENGTH");
    return out;
}
inline logical_media decode(const std::vector<std::uint8_t>& data) {
    if (data.size()>max_file_size) throw media_error("IMAGE_TOO_LARGE");
    if (data.size()<fixed_header_size+trailer_size)
        throw media_error("TRUNCATED_IMAGE");
    for (unsigned i=0;i<8;++i)
        if(data[i]!=magic[i]) throw media_error("BAD_MAGIC");
    if (read_le(data,8,4)!=version) throw media_error("UNSUPPORTED_VERSION");
    if (read_le(data,12,4)!=fixed_header_size || read_le(data,60,4)!=0)
        throw media_error("INVALID_HEADER");
    const auto nd=read_le(data,16,8), nt=read_le(data,24,8), ns=read_le(data,32,8);
    const auto count64=read_le(data,40,8);
    const auto written64=read_le(data,48,8);
    const auto plen64=read_le(data,56,4);
    if (!plen64 || plen64>64) throw media_error("INVALID_PROFILE");
    if(nd>std::numeric_limits<std::size_t>::max() ||
       nt>std::numeric_limits<std::size_t>::max() ||
       ns>std::numeric_limits<std::size_t>::max())
        throw media_error("INVALID_GEOMETRY");
    const std::size_t plen=static_cast<std::size_t>(plen64);
    if (data.size()<fixed_header_size+plen+trailer_size)
        throw media_error("TRUNCATED_IMAGE");
    const std::string label(data.begin()+fixed_header_size,
                            data.begin()+fixed_header_size+plen);
    const geometry g{label,static_cast<std::size_t>(nd),
                     static_cast<std::size_t>(nt),static_cast<std::size_t>(ns)};
    logical_media result(g); // validates source profile + geometry without trust.
    const std::size_t count=result.capacity();
    if (count64!=count || written64>count)
        throw media_error("INVALID_COUNT");
    const std::size_t bitmap=(count+7)/8;
    const std::size_t wanted=fixed_header_size+plen+bitmap+8*count+trailer_size;
    if(wanted!=data.size()) throw media_error("INVALID_LENGTH");
    if(read_le(data,wanted-8,8)!=crc64(data.data(),wanted-8))
        throw media_error("CHECKSUM_MISMATCH");
    const std::size_t bstart=fixed_header_size+plen;
    if(count%8 && (data[bstart+bitmap-1] >> (count%8))!=0)
        throw media_error("NONCANONICAL_BITMAP");
    const std::size_t wstart=bstart+bitmap;
    std::size_t actual_written=0;
    for(std::size_t i=0;i<count;++i) {
        const bool written=(data[bstart+i/8] & (1u << (i%8)))!=0;
        const raw_word_t raw=read_le(data,wstart+8*i,8);
        if ((raw & ~kyiv_drum_media::word_mask)!=0)
            throw media_error("INVALID_WORD");
        if (!written && raw!=0)
            throw media_error("NONCANONICAL_UNWRITTEN");
        if (written) { result.store(from_linear(g,i),raw); ++actual_written; }
    }
    if(actual_written!=written64) throw media_error("INVALID_COUNT");
    return result;
}
inline bool same_geometry(const geometry& a,const geometry& b) noexcept {
    return a.profile_id==b.profile_id && a.drums==b.drums &&
           a.tracks_per_drum==b.tracks_per_drum && a.slots_per_track==b.slots_per_track;
}
inline logical_media load(const std::filesystem::path& path) {
    std::error_code ec;
    const auto sz=std::filesystem::file_size(path,ec);
    if(ec) throw media_error("IMAGE_OPEN_FAILED");
    if(sz>max_file_size) throw media_error("IMAGE_TOO_LARGE");
    std::ifstream in(path,std::ios::binary);
    if(!in) throw media_error("IMAGE_OPEN_FAILED");
    std::vector<std::uint8_t> data(static_cast<std::size_t>(sz));
    if(!data.empty()) {
        in.read(reinterpret_cast<char*>(data.data()),static_cast<std::streamsize>(data.size()));
        if(!in || in.gcount()!=static_cast<std::streamsize>(data.size()))
            throw media_error("IMAGE_READ_FAILED");
    }
    char extra=0;
    if(in.get(extra)) throw media_error("INVALID_LENGTH");
    if(in.bad()) throw media_error("IMAGE_READ_FAILED");
    return decode(data);
}
inline void load_into(logical_media& destination,const std::filesystem::path& path) {
    logical_media prepared=load(path);
    if(!same_geometry(destination.profile(),prepared.profile()))
        throw media_error("GEOMETRY_MISMATCH");
    // No operation below this line can throw for std::vector<cell>'s allocator,
    // string contents or the same-geometry profile: noexcept swap is sufficient.
    using std::swap;
    swap(destination,prepared);
}
inline void save_atomic(const logical_media& source,const std::filesystem::path& path) {
    const auto bytes=encode(source); // BEFORE any filesystem mutation
    std::filesystem::path temp;
    bool made=false;
    try {
        const std::filesystem::path parent=path.has_parent_path()?path.parent_path():".";
        static std::atomic<std::uint64_t> serial{0};
        const auto nonce=static_cast<std::uint64_t>(
            std::chrono::steady_clock::now().time_since_epoch().count());
        for(unsigned attempt=0;attempt<32;++attempt) {
            temp=parent / (path.filename().string()+".tmp."+
                  std::to_string(nonce)+"."+std::to_string(serial.fetch_add(1)));
            std::error_code ec;
            if(!std::filesystem::exists(temp,ec) && !ec) {made=true;break;}
        }
        if(!made) throw media_error("TEMP_NAME_FAILED");
        {
            std::ofstream out(temp,std::ios::binary|std::ios::trunc);
            if(!out) throw media_error("IMAGE_WRITE_FAILED");
            out.write(reinterpret_cast<const char*>(bytes.data()),
                      static_cast<std::streamsize>(bytes.size()));
            out.flush();
            if(!out) throw media_error("IMAGE_WRITE_FAILED");
            out.close();
            if(!out) throw media_error("IMAGE_WRITE_FAILED");
        }
        std::error_code error;
        std::filesystem::rename(temp,path,error);
        if(error) throw media_error("REPLACE_FAILED");
    } catch (...) {
        if(made) {std::error_code ignored;std::filesystem::remove(temp,ignored);}
        throw;
    }
    // No fsync nor multi-process writer serialization: crash durability OPEN.
}
}
#endif
