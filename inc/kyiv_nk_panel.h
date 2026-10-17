#ifndef KYIVEMU_KYIV_NK_PANEL_H
#define KYIVEMU_KYIV_NK_PANEL_H

#include <array>
#include <cstddef>
#include <cstdint>
#include <stdexcept>

// Operator-settable NK3000..3002, GY62 printed pp. 8 and 161.
// This is a software SOURCE SELECTION model, not a reconstruction of the
// front-panel contacts or an assertion about historical power-on positions.
class Kyiv_NK_panel_t {
public:
    static constexpr std::uint64_t first_addr = 03000;
    static constexpr std::uint64_t last_addr = 03002;
    static constexpr std::uint64_t word_mask = (std::uint64_t{1} << 41) - 1;

    static constexpr bool is_selectable(std::uint64_t addr) {
        return addr >= first_addr && addr <= last_addr;
    }

    void set_panel_word(std::uint64_t addr, std::uint64_t word) {
        const auto i = index(addr);
        if ((word & ~word_mask) != 0) {
            throw std::out_of_range("NK panel word exceeds 41 bits");
        }
        panel_words_[i] = word;
        configured_[i] = true;
    }

    void select_panel(std::uint64_t addr, bool enabled) {
        const auto i = index(addr);
        if (enabled && !configured_[i]) {
            throw std::logic_error("NK panel source selected without a configured word");
        }
        selected_[i] = enabled;
    }

    bool is_panel_selected(std::uint64_t addr) const {
        return selected_[index(addr)];
    }

    bool is_panel_configured(std::uint64_t addr) const {
        return configured_[index(addr)];
    }

    std::uint64_t panel_word(std::uint64_t addr) const {
        const auto i = index(addr);
        if (!configured_[i]) {
            throw std::logic_error("NK panel word was not configured");
        }
        return panel_words_[i];
    }

private:
    static std::size_t index(std::uint64_t addr) {
        if (!is_selectable(addr)) {
            throw std::out_of_range("Only NK3000..3002 have documented source selectors");
        }
        return static_cast<std::size_t>(addr - first_addr);
    }

    std::array<std::uint64_t, 3> panel_words_{};
    std::array<bool, 3> configured_{};
    std::array<bool, 3> selected_{}; // Default: existing cabinet ROM storage.
};

#endif // KYIVEMU_KYIV_NK_PANEL_H
