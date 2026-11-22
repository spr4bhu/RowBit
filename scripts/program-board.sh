#!/usr/bin/env bash
# Loads the SoC bitstream into the Arty's FPGA (lost at power off).
set -euo pipefail
. "$(cd "$(dirname "$0")/.." && pwd)/env.sh"
openFPGALoader -b arty_a7_35t "${1:-$ROWBIT_ROOT/build/soc/gateware/digilent_arty.bit}"
