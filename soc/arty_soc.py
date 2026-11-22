#!/usr/bin/env python3
# Arty A7-35T SoC: LiteDRAM DDR3, VexRiscv BIOS (calibrates DRAM at boot), UARTBone for the host, DRAM sequencer.
# Writes the netlist sources and constraints; scripts/build-soc.sh runs synthesis, place and route.
import argparse
import os

from litex.soc.integration.builder import Builder
from litex_boards.targets.digilent_arty import BaseSoC

from sequencer import add_sequencer

SYS_CLK_FREQ = 87.5e6  # tCK 2.86 ns: 2 tCK PRE->ACT lands in the RowClone window; 75 MHz steps miss it
UART_BAUDRATE = 1_000_000  # exact on the FT2232H (12 MHz / 12)


class ArtySoC(BaseSoC):
    def add_sdram(self, *args, module=None, **kwargs):
        self.dram_module = module  # the chip litex-boards chose, so its timings can be exported
        super().add_sdram(*args, module=module, **kwargs)


def build_soc():
    soc = ArtySoC(
        toolchain="openxc7",
        sys_clk_freq=SYS_CLK_FREQ,
        cpu_type="vexriscv",
        cpu_variant="lite",  # only runs the BIOS DRAM calibration
        uart_name="crossover+uartbone",
        uart_baudrate=UART_BAUDRATE,
        integrated_rom_size=0x20000,  # LiteX's default size, holds the BIOS
        l2_size=0,  # no write-back cache in front of DRAM, so the bus sees what the sequencer wrote
    )
    soc.platform.device = os.environ["ROWBIT_PART"]
    soc.add_constant("UART_BAUDRATE", UART_BAUDRATE)  # the host reads it from csr.csv
    add_sequencer(soc)
    return soc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=os.path.join(os.environ["ROWBIT_ROOT"], "build", "soc"))
    args = parser.parse_args()
    Builder(build_soc(), output_dir=args.output_dir, csr_csv=os.path.join(args.output_dir, "csr.csv")).build(run=False)


if __name__ == "__main__":
    main()
