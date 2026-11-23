# RowBit

Processing using DRAM on an FPGA: copying and initialising rows inside the DRAM chip itself, without moving the
data to the CPU.

## Hardware

| Item | Value |
|---|---|
| Board | Digilent Arty A7-35T |
| DRAM | Micron MT41K128M16 DDR3L, 256 MB, 8 banks × 16384 rows |
| Clock | 87.5 MHz system clock, DDR3-700 (one command step = 2.86 ns) |
| Host link | USB-UART at 1 Mbaud |

## Installation

Only tested on Apple Silicon Macs. Needs [Homebrew](https://brew.sh) and [Nix](https://determinate.systems/nix-installer).

```sh
scripts/setup-toolchain.sh   # installs the pinned toolchain and .venv; safe to re-run
scripts/check-toolchain.sh   # every line should say ok
source env.sh                # once per shell
```

Plug the Arty in over USB; `env.sh` finds its UART (override with `ARTY_UART=/dev/cu.usbserial-...`).

## Build and run

```sh
scripts/build-soc.sh         # bitstream into build/soc
scripts/program-board.sh     # load it onto the FPGA
scripts/map-subarrays.sh     # once per board: maps its subarrays into results/
```

See [scripts/README.md](scripts/README.md) for what each script does.

## Tests

```sh
python3 -m pytest tests/rtl tests/host   # no board needed
python3 -m pytest tests/hardware         # on the board; build the bitstream first
```

Each folder's README lists its tests: [rtl](tests/rtl/README.md), [host](tests/host/README.md),
[installer](tests/installer/README.md), [hardware](tests/hardware/README.md).

## References

- V. Seshadri et al., "RowClone: Fast and Energy-Efficient In-DRAM Bulk Data Copy and Initialization", MICRO 2013.
- [SoftMC](https://github.com/CMU-SAFARI/SoftMC), [DRAM-Bender](https://github.com/CMU-SAFARI/DRAM-Bender),
  [PiDRAM](https://github.com/CMU-SAFARI/PiDRAM): FPGA DRAM testing and processing-using-memory platforms.
- Built on [LiteX](https://github.com/enjoy-digital/litex), [LiteDRAM](https://github.com/enjoy-digital/litedram)
  and [VexRiscv](https://github.com/SpinalHDL/VexRiscv).
