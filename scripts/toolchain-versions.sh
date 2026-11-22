# Pinned toolchain

BREW_PACKAGES="yosys openfpgaloader riscv64-elf-gcc icarus-verilog verilator python@3.14"
YOSYS_VERSION="0.71+post"
OPENFPGALOADER_VERSION="1.2.0"
RISCV_GCC_VERSION="16.2.0"
ICARUS_VERSION="13.0"
VERILATOR_VERSION="5.054"
PYTHON_VERSION="3.14"

PRJXRAY_FLAKE="github:openxc7/toolchain-nix/68a64b2137d6229599ae149f43c8dfa43235cd26#prjxray"
PRJXRAY_VERSION="0.9.2"
PRJXRAY_DB_REPO="https://github.com/openXC7/prjxray-db.git"
PRJXRAY_DB_COMMIT="a90f27c1caefee5276f47440f4c730b50519a86f"

# nextpnr-himbaechel with the xilinx uarch (successor of the archived nextpnr-xilinx)
NEXTPNR_REPO="https://github.com/openXC7/nextpnr.git"
NEXTPNR_COMMIT="42d06c5ff00aa04fd06f414b8e0e1ef3673c3a33"

ROWBIT_TOOLS_DIR="${ROWBIT_TOOLS_DIR:-$HOME/opt/openxc7}"

# Arty's xc7a35ticsg324-1L is the same die
ROWBIT_PART="xc7a35tcsg324-1"
ROWBIT_FAMILY="artix7"
ROWBIT_DIE="xc7a50t"  # prjxray's fabric for the 35T; the nextpnr chipdb is built for it
