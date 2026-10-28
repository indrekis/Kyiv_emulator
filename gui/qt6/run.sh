#!/usr/bin/env bash
# MSYS2 MINGW64: tracked GUI sources; build outputs inside tempkyiv/qt6_build.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd -- "$HERE/../.." && pwd -P)"
BUILD="$ROOT/tempkyiv/qt6_build"
ROM="$ROOT/mem/ROM.txt"
IMAGE="$ROOT/examples/historical/gy1962/au1_addition_0143_0150.k41"

[[ -f "$ROOT/inc/kyiv.h" && -f "$ROOT/src/main.cpp" && -f "$ROOT/src/asm_disasm.cpp" ]] || { echo 'QTGUI_FAIL=REPOSITORY_LAYOUT' >&2; exit 2; }
[[ -d "$ROOT/tempkyiv" && "$HERE" == "$ROOT/gui/qt6" ]] || { echo 'QTGUI_FAIL=INSTALL_LOCATION' >&2; exit 2; }
[[ ! -L "$HERE" && ! -L "$ROOT/tempkyiv" && ! -L "$BUILD" ]] || { echo 'QTGUI_FAIL=SYMLINK_PATH' >&2; exit 2; }
[[ -f "$ROM" && -f "$IMAGE" ]] || { echo 'QTGUI_FAIL=ROM_OR_IMAGE_MISSING' >&2; exit 2; }
[[ -f "$HERE/kyiv_gui_backend.cpp" && -f "$HERE/qt_main.cpp" ]] || { echo 'QTGUI_FAIL=GUI_SOURCE_MISSING' >&2; exit 2; }
command -v g++ >/dev/null || { echo 'QTGUI_FAIL=GPP_MISSING' >&2; exit 2; }
command -v pkg-config >/dev/null || { echo 'QTGUI_FAIL=PKG_CONFIG_MISSING' >&2; exit 2; }
pkg-config --exists Qt6Widgets || { echo 'QTGUI_FAIL=QT6_WIDGETS_NOT_FOUND' >&2; exit 2; }
expected_rom='a1d9c28e969fa1d74966a78fdbb1bf85b4c45354a764cb8665a73b0a62bdab38'
printf '%s  %s\n' "$expected_rom" "$ROM" | sha256sum -c - >/dev/null || { echo 'QTGUI_FAIL=ROM_SHA256' >&2; exit 2; }
mkdir -p -- "$BUILD"
for output in "$BUILD/asm.o" "$BUILD/kyiv_gui_qt6.exe" "$BUILD/kyiv_gui_backend.exe" "$BUILD/native_smoke.txt"; do
  [[ ! -L "$output" ]] || { echo "QTGUI_FAIL=OUTPUT_SYMLINK: $output" >&2; exit 2; }
done

frontend="$BUILD/kyiv_gui_qt6.exe"
backend="$BUILD/kyiv_gui_backend.exe"
if [[ "${1:-}" != '--reuse-build' ]]; then
  echo "QTGUI_BUILD=START; QT=$(pkg-config --modversion Qt6Widgets)"
  qt_flags=( $(pkg-config --cflags Qt6Widgets) )
  qt_libs=( $(pkg-config --libs Qt6Widgets) )
  # Compile Qt first: frontend errors must fail fast, before rebuilding the CPU.
  g++ -std=c++17 -O0 -Wall -Wextra "${qt_flags[@]}" "$HERE/qt_main.cpp" -o "$frontend" "${qt_libs[@]}"
  g++ -std=c++17 -O0 -Wall -Wextra -I"$ROOT/inc" -Dmain=kyiv_cli_original_main \
      -c "$ROOT/src/asm_disasm.cpp" -o "$BUILD/asm.o"
  g++ -std=c++17 -O0 -Wall -Wextra -I"$ROOT/inc" \
      "$ROOT/src/main.cpp" "$HERE/kyiv_gui_backend.cpp" "$BUILD/asm.o" -o "$backend"
  echo 'QTGUI_BUILD=PASS; FRONTEND=QT6_WIDGETS; BACKEND=PERSISTENT_CPP; TRACKED_FILES=UNCHANGED'
else
  [[ -f "$frontend" && -f "$backend" ]] || { echo 'QTGUI_FAIL=REUSED_BINARIES_MISSING' >&2; exit 2; }
  echo 'QTGUI_BUILD=REUSED'
fi

# Verify the actual backend protocol/ROM/H9/checkpoint before opening a window.
smoke="$BUILD/native_smoke.txt"
# Paths written over stdin do NOT pass through MSYS2 native-argv conversion.
native_path() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf "%s\n" "$1"; fi
}
IMAGE_NATIVE="$(native_path "$IMAGE")"
ROM_NATIVE="$(native_path "$ROM")"
ROOT_NATIVE="$(native_path "$ROOT")"
{
  printf 'PING\n'
  printf 'LOAD\t%s\t0143\n' "$IMAGE_NATIVE"
  printf 'SAVE\n'
  printf 'STEP\t1\n'
  printf 'DUMP\t0347\t1\n'
  printf 'RESTORE\n'
  printf 'STEP\t1\n'
  printf 'DUMP\t0347\t1\n'
  printf 'QUIT\n'
} | "$backend" "$ROM_NATIVE" > "$smoke"
[[ $(grep -c '^OK' "$smoke") -eq 9 ]] || { echo 'QTGUI_FAIL=BACKEND_PROTOCOL'; cat "$smoke"; exit 1; }
[[ $(grep -c '^OK.*STEP.*C=0144' "$smoke") -eq 2 ]] || { echo 'QTGUI_FAIL=BACKEND_STEP'; cat "$smoke"; exit 1; }
[[ $(grep -c 'DATA=00010004002001' "$smoke") -eq 2 ]] || { echo 'QTGUI_FAIL=BACKEND_CHECKPOINT'; cat "$smoke"; exit 1; }
echo 'QTGUI_NATIVE_SMOKE=PASS; ROM=PINNED; H9=SOURCE_MATCH; CHECKPOINT_REPLAY=EQUIVALENT; PROTOCOL=1'
if [[ "${1:-}" != '--smoke-only' ]]; then
  "$frontend" "$ROOT_NATIVE" "$ROM_NATIVE"
fi
