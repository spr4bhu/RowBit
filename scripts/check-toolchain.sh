#!/usr/bin/env bash
# Fails if any installed tool or Python package differs from its pin.
set -uo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
. "$repo_dir/scripts/toolchain-versions.sh"
nextpnr_dir="$ROWBIT_TOOLS_DIR/nextpnr-xilinx"
failed=0

check() {
  local name="$1" wanted="$2" installed="$3"
  if [ "$wanted" = "$installed" ]; then
    echo "ok   $name $installed"
  else
    echo "BAD  $name: want $wanted, have ${installed:-none}"
    failed=1
  fi
}

commit_of() { git -C "$1" rev-parse HEAD 2>/dev/null; }

prjxray_flake_installed() {
  nix profile list 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' \
    | awk '/Locked flake URL/ && /toolchain-nix/ {print $4 "#prjxray"; exit}'
}

check yosys "$YOSYS_VERSION" "$(yosys -V 2>/dev/null | awk '{print $2}')"
check openfpgaloader "$OPENFPGALOADER_VERSION" "$(openFPGALoader --version 2>&1 | sed -n 's/^openFPGALoader v//p')"
check riscv64-elf-gcc "$RISCV_GCC_VERSION" "$(riscv64-elf-gcc -dumpversion 2>/dev/null)"
check iverilog "$ICARUS_VERSION" "$(iverilog -V 2>/dev/null | sed -n '1s/.*version \([0-9.]*\).*/\1/p')"
check verilator "$VERILATOR_VERSION" "$(verilator --version 2>/dev/null | awk '{print $2}')"
check python "$PYTHON_VERSION" "$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
check prjxray "$PRJXRAY_FLAKE" "$(prjxray_flake_installed)"
check nextpnr-xilinx "$NEXTPNR_XILINX_COMMIT" "$(commit_of "$nextpnr_dir")"
check prjxray-db "$PRJXRAY_DB_COMMIT" "$(commit_of "$nextpnr_dir/xilinx/external/prjxray-db")"
check nextpnr-xilinx-meta "$NEXTPNR_XILINX_META_COMMIT" "$(commit_of "$nextpnr_dir/xilinx/external/nextpnr-xilinx-meta")"

if [ -f "$nextpnr_dir/chipdb/$ROWBIT_CHIPDB_NAME.bin" ]; then echo "ok   chipdb"; else echo "BAD  chipdb missing"; failed=1; fi

installed_packages="$(pip freeze 2>/dev/null)"
while read -r pinned_package; do
  if grep -qxF "$pinned_package" <<<"$installed_packages"; then
    echo "ok   $pinned_package"
  else
    echo "BAD  not installed: $pinned_package"
    failed=1
  fi
done <"$repo_dir/requirements.txt"

exit $failed
