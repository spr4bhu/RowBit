# Usage: source env.sh  (works from bash and zsh)
export ROWBIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-${(%):-%x}}")" && pwd)"
. "$ROWBIT_ROOT/scripts/toolchain-versions.sh"
export ROWBIT_PART

export NEXTPNR_XILINX_DIR="$ROWBIT_TOOLS_DIR/nextpnr-xilinx"
export PRJXRAY_DB_DIR="$NEXTPNR_XILINX_DIR/xilinx/external/prjxray-db"
export CHIPDB="$NEXTPNR_XILINX_DIR/chipdb"
export PATH="$ROWBIT_ROOT/scripts:$NEXTPNR_XILINX_DIR/build:$HOME/.nix-profile/bin:$PATH"

# Homebrew's RISC-V compiler is named riscv64-elf-*.
export LITEX_ENV_CC_TRIPLE="riscv64-elf"
# Hide fasm's harmless "slow parser" warning.
export PYTHONWARNINGS="ignore::RuntimeWarning"
# The Arty's UART is the second FTDI port.
export ARTY_UART="${ARTY_UART:-$(ls /dev/cu.usbserial-*1 2>/dev/null | head -1)}"

. "$ROWBIT_ROOT/.venv/bin/activate"
