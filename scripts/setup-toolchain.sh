#!/usr/bin/env bash
# Installs the pinned toolchain. Safe to re-run: finished steps are skipped.
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
. "$repo_dir/scripts/toolchain-versions.sh"
nextpnr_dir="$ROWBIT_TOOLS_DIR/nextpnr-xilinx"

fail() { echo "error: $1" >&2; exit 1; }
[ "$(uname -s)-$(uname -m)" = Darwin-arm64 ] || fail "only Apple Silicon macOS is supported for now"
command -v brew >/dev/null || fail "Homebrew not found. Install it from https://brew.sh and re-run."
command -v nix >/dev/null || fail "Nix not found. Install it from https://determinate.systems/nix-installer and re-run."

checkout_submodule() {
  local name="$1" commit="$2"
  git -C "$nextpnr_dir" submodule update --init --depth 1 "xilinx/external/$name"
  git -C "$nextpnr_dir/xilinx/external/$name" fetch --depth 1 origin "$commit"
  git -C "$nextpnr_dir/xilinx/external/$name" checkout -q "$commit"
}

# Only install what's missing: brew install would upgrade installed tools past the pins.
for package in $BREW_PACKAGES; do
  brew list --versions "$package" >/dev/null || HOMEBREW_NO_INSTALL_UPGRADE=1 brew install "$package"
done
nix profile list | grep -q "$PRJXRAY_FLAKE" || nix profile add "$PRJXRAY_FLAKE"

if [ ! -d "$nextpnr_dir/.git" ]; then
  mkdir -p "$ROWBIT_TOOLS_DIR"
  git clone "$NEXTPNR_XILINX_REPO" "$nextpnr_dir"
fi
git -C "$nextpnr_dir" fetch --depth 1 origin "$NEXTPNR_XILINX_COMMIT"
git -C "$nextpnr_dir" checkout -q "$NEXTPNR_XILINX_COMMIT"
checkout_submodule prjxray-db "$PRJXRAY_DB_COMMIT"
checkout_submodule nextpnr-xilinx-meta "$NEXTPNR_XILINX_META_COMMIT"

# OpenMP off: Apple clang has none, and it only speeds up one placer.
if [ ! -x "$nextpnr_dir/build/nextpnr-xilinx" ]; then
  cmake -S "$nextpnr_dir" -B "$nextpnr_dir/build" -G Ninja -DARCH=xilinx -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_GUI=OFF -DBUILD_PYTHON=OFF -DUSE_OPENMP=OFF
  ninja -C "$nextpnr_dir/build"
fi

chipdb_file="$nextpnr_dir/chipdb/$ROWBIT_CHIPDB_NAME.bin"
if [ ! -f "$chipdb_file" ]; then
  mkdir -p "$nextpnr_dir/chipdb"
  python3 "$nextpnr_dir/xilinx/python/bbaexport.py" --device "$ROWBIT_PART" --bba "$chipdb_file.bba"
  "$nextpnr_dir/build/bbasm" -l "$chipdb_file.bba" "$chipdb_file"
  rm "$chipdb_file.bba"
fi

[ -d "$repo_dir/.venv" ] || "python$PYTHON_VERSION" -m venv "$repo_dir/.venv"
"$repo_dir/.venv/bin/pip" install -q -r "$repo_dir/requirements.txt"
"$repo_dir/.venv/bin/pip" install -q -e "$repo_dir"
