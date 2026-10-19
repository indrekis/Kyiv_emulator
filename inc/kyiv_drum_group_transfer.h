#ifndef KYIVEMU_D14B2_GROUP_TRANSFER_H
#define KYIVEMU_D14B2_GROUP_TRANSFER_H

// ISA-07 D14-B2: stand-alone HOST_POLICY multiword transfers over D14-B1 media.
// Coordinates are zero-based API indices, never opcode 25's raw fields.
// Traversal wraps from the end of a track to the next track on the SAME drum.
// No crossing from the final track to another drum; that hardware behavior is OPEN.
#include "kyiv_drum_logical_media.h"
#include <cstddef>
#include <vector>

namespace kyiv_drum_media {

struct transfer_span {
    coordinate first;
    coordinate last;
    std::size_t count;
};

// No heap allocation; checks the entire request before any mutation.
inline transfer_span validate_span(const logical_media& media,
                                   coordinate start, std::size_t count) {
    if (count == 0) throw media_error("INVALID_COUNT");
    // B1's coordinate validation gives INVALID_DRUM/TRACK/SLOT in this order.
    (void)media.inspect(start);
    const auto& g = media.profile();
    // Geometry was checked at construction. Products cannot exceed host capacity.
    const std::size_t remaining =
        (g.tracks_per_drum - start.track - 1) * g.slots_per_track +
        (g.slots_per_track - start.slot);
    if (count > remaining) throw media_error("END_OF_DRUM");
    const std::size_t relative_end = start.slot + count - 1;
    return {start,
            {start.drum,
             start.track + relative_end / g.slots_per_track,
             relative_end % g.slots_per_track},
            count};
}

inline coordinate span_coordinate(const logical_media& media,
                                  const transfer_span& span, std::size_t i) {
    // INTERNAL: call only with 0 <= i < validated span.count.
    const auto slots = media.profile().slots_per_track;
    const std::size_t linear = span.first.slot + i;
    return {span.first.drum,
            span.first.track + linear / slots,
            linear % slots};
}

// Strong state guarantee: validation of entire span and ALL words precedes
// commit. B1::store() performs no allocation and cannot throw once both its
// coordinate and word are valid. Does not duplicate the entire media image.
inline transfer_span write_group(logical_media& media, coordinate start,
                                 const std::vector<raw_word_t>& words) {
    const auto span = validate_span(media, start, words.size());
    for (const auto w : words)
        if ((w & ~word_mask) != 0)
            throw media_error("INVALID_WORD");
    for (std::size_t i = 0; i < words.size(); ++i)
        media.store(span_coordinate(media, span, i), words[i]);
    return span;
}

// Throws UNWRITTEN rather than silently converting uninitialized slots to +0.
// No side effects on media, even if allocation or validation fails.
inline std::vector<raw_word_t> read_group(const logical_media& media,
                                           coordinate start, std::size_t count) {
    const auto span = validate_span(media, start, count);
    std::vector<raw_word_t> result;
    result.reserve(count);
    for (std::size_t i = 0; i < count; ++i) {
        const auto data = media.inspect(span_coordinate(media, span, i));
        if (!data.written) throw media_error("UNWRITTEN");
        result.push_back(data.word);
    }
    return result;
}

} // namespace kyiv_drum_media
#endif // KYIVEMU_D14B2_GROUP_TRANSFER_H
