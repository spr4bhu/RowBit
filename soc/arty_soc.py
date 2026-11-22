#!/usr/bin/env python3
# Arty A7-35T SoC: LiteDRAM DDR3, VexRiscv BIOS (calibrates DRAM at boot), UARTBone for the host.
import argparse
import os

from litex.soc.integration.builder import Builder
from litex_boards.targets.digilent_arty import BaseSoC

SYS_CLK_FREQ = 75e6  # 100 MHz doesn't meet timing with openXC7


def build_soc():
    soc = BaseSoC(
        toolchain="openxc7",
        sys_clk_freq=SYS_CLK_FREQ,
        cpu_type="vexriscv",
        uart_name="crossover+uartbone",
        integrated_rom_size=0x20000,  # LiteX's default size, holds the BIOS
    )
    soc.platform.device = os.environ["ROWBIT_PART"]
    return soc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=os.path.join(os.environ["ROWBIT_ROOT"], "build", "soc"))
    args = parser.parse_args()
    Builder(build_soc(), output_dir=args.output_dir, csr_csv=os.path.join(args.output_dir, "csr.csv")).build()


if __name__ == "__main__":
    main()
