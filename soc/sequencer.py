# Puts rtl/dram_sequencer.v on LiteDRAM's external DFI port and on the SoC bus.
import os

from migen import Cat, ClockSignal, Instance, Module, ResetSignal
from litex.soc.integration.soc import SoCRegion
from litex.soc.interconnect import wishbone
from litedram.common import burst_lengths

from rowbit.program import ADDRESS_BITS, BANKS, PROGRAM_DEPTH, READ_DEPTH, SLOTS, WRITE_DEPTH
from rowbit.sequencer import LANES, REGION_SHIFT

RTL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rtl")
BUS_ORIGIN = 0x90000000  # uncached IO region, so the CPU sees it directly
BUS_SIZE = 4 * (4 << REGION_SHIFT)  # 4 regions of 32-bit words
DRAIN_CYCLES = 16
DRAM_TIMINGS = ("tRCD", "tRP", "tRAS", "tWR", "tRTP")  # exported in tCK for the host


class DRAMSequencer(Module):
    def __init__(self, platform, sdram):
        phy = sdram.controller.settings.phy
        assert phy.nphases == SLOTS and phy.nranks == 1
        assert phy.read_latency < DRAIN_CYCLES and phy.write_latency >= 1
        self.bus = wishbone.Interface(data_width=32)
        dfi = sdram.dfii.ext_dfi.phases
        controller = sdram.dfii.slave.phases[0]
        # The host encodes programs and data with these widths.
        assert len(dfi[0].address) == ADDRESS_BITS and 2 ** len(dfi[0].bank) == BANKS
        assert len(dfi[0].wrdata) * SLOTS == 32 * LANES

        def per_phase(name):
            return Cat(*(getattr(phase, name) for phase in dfi))

        self.specials += Instance("dram_sequencer",
            p_ADDRESS_BITS=ADDRESS_BITS,
            p_BANK_BITS=len(dfi[0].bank),
            p_PROGRAM_DEPTH=PROGRAM_DEPTH,
            p_WRITE_DEPTH=WRITE_DEPTH,
            p_READ_DEPTH=READ_DEPTH,
            p_WRITE_LATENCY=phy.write_latency,
            p_DRAIN_CYCLES=DRAIN_CYCLES,
            p_REFRESH_RECOVERY_CYCLES=sdram.controller.settings.timing.tRFC,
            i_clk=ClockSignal("sys"),
            i_rst=ResetSignal("sys"),
            i_wb_adr=self.bus.adr,
            i_wb_dat_w=self.bus.dat_w,
            o_wb_dat_r=self.bus.dat_r,
            i_wb_cyc=self.bus.cyc,
            i_wb_stb=self.bus.stb,
            i_wb_we=self.bus.we,
            o_wb_ack=self.bus.ack,
            i_ctrl_cs_n=controller.cs_n,
            i_ctrl_ras_n=controller.ras_n,
            i_ctrl_cas_n=controller.cas_n,
            i_ctrl_we_n=controller.we_n,
            o_dfi_select=sdram.dfii.ext_dfi_sel,
            **{f"o_dfi_{name}": per_phase(name) for name in (
                "address", "bank", "cs_n", "ras_n", "cas_n", "we_n", "wrdata_en", "rddata_en", "wrdata",
                "wrdata_mask", "cke", "odt", "reset_n")},
            i_dfi_rddata=per_phase("rddata"),
            i_dfi_rddata_valid=dfi[0].rddata_valid,
        )
        for name in ("dram_sequencer.v", "simple_dual_port_ram.v"):
            platform.add_source(os.path.join(RTL_DIR, name))


def add_dram_constants(soc, module):
    """Puts the chip's geometry and JEDEC timings (in tCK) in csr.csv, so the host never hardcodes them."""
    settings = soc.sdram.controller.settings
    for name in DRAM_TIMINGS:
        soc.add_constant(f"DRAM_{name.upper()}", module.ck_ns_to_dram_cycles(module.get(name)))
    soc.add_constant("DRAM_BURST_LENGTH", burst_lengths[settings.phy.memtype])
    soc.add_constant("DRAM_CWL", settings.phy.cwl)
    soc.add_constant("DRAM_BANK_BITS", settings.geom.bankbits)
    soc.add_constant("DRAM_ROW_BITS", settings.geom.rowbits)
    soc.add_constant("DRAM_COLUMN_BITS", settings.geom.colbits)


def add_sequencer(soc):
    soc.submodules.sequencer = sequencer = DRAMSequencer(soc.platform, soc.sdram)
    soc.bus.add_slave("sequencer", sequencer.bus, SoCRegion(origin=BUS_ORIGIN, size=BUS_SIZE, cached=False))
    add_dram_constants(soc, soc.dram_module)
