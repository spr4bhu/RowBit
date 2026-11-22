#!/usr/bin/env bash
# Installs the pinned toolchain. Safe to re-run: finished steps are skipped.
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
. "$repo_dir/scripts/toolchain-versions.sh"
nextpnr_dir="$ROWBIT_TOOLS_DIR/nextpnr"
prjxray_db_dir="$ROWBIT_TOOLS_DIR/prjxray-db-$PRJXRAY_DB_COMMIT"  # new db, new path: ninja rebuilds the chipdb

fail() { echo "error: $1" >&2; exit 1; }
[ "$(uname -s)-$(uname -m)" = Darwin-arm64 ] || fail "only Apple Silicon macOS is supported for now"
command -v brew >/dev/null || fail "Homebrew not found. Install it from https://brew.sh and re-run."
command -v nix >/dev/null || fail "Nix not found. Install it from https://determinate.systems/nix-installer and re-run."

# Fetches only the pinned commit (prjxray-db's history is large).
checkout() {
  local repo="$1" dir="$2" commit="$3"
  [ -d "$dir/.git" ] || { git init -q "$dir" && git -C "$dir" remote add origin "$repo"; }
  git -C "$dir" fetch -q --depth 1 origin "$commit"
  git -C "$dir" checkout -q "$commit"
}

# Only install what's missing: brew install would upgrade installed tools past the pins.
for package in $BREW_PACKAGES; do
  brew list --versions "$package" >/dev/null || HOMEBREW_NO_INSTALL_UPGRADE=1 brew install "$package"
done
nix profile list | grep -q "$PRJXRAY_FLAKE" || nix profile add "$PRJXRAY_FLAKE"

mkdir -p "$ROWBIT_TOOLS_DIR"
checkout "$PRJXRAY_DB_REPO" "$prjxray_db_dir" "$PRJXRAY_DB_COMMIT"
checkout "$NEXTPNR_REPO" "$nextpnr_dir" "$NEXTPNR_COMMIT"
git -C "$nextpnr_dir" submodule update --init himbaechel/uarch/xilinx/meta

# OpenMP off: Apple clang has none. Always run: a no-op when up to date; also builds the chipdb.
cmake -S "$nextpnr_dir" -B "$nextpnr_dir/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DARCH=himbaechel -DHIMBAECHEL_UARCH=xilinx -DHIMBAECHEL_XILINX_DEVICES="$ROWBIT_DIE" \
  -DHIMBAECHEL_PRJXRAY_DB="$prjxray_db_dir" -DBUILD_GUI=OFF -DBUILD_PYTHON=OFF -DBUILD_TESTS=OFF -DUSE_OPENMP=OFF
ninja -C "$nextpnr_dir/build"

[ -d "$repo_dir/.venv" ] || "python$PYTHON_VERSION" -m venv "$repo_dir/.venv"
"$repo_dir/.venv/bin/pip" install -q -r "$repo_dir/requirements.txt"
"$repo_dir/.venv/bin/pip" install -q -e "$repo_dir"
