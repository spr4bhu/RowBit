# Puts rtl/dram_sequencer.v on LiteDRAM's external DFI port and on the SoC bus.
import os

from migen import Cat, ClockSignal, Instance, Module, ResetSignal
from litex.soc.integration.soc import SoCRegion
from litex.soc.interconnect import wishbone

RTL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rtl")
BUS_ORIGIN = 0x90000000  # uncached IO region, so the CPU sees it directly
BUS_SIZE = 4 * 2**16     # 16-bit word address: [15:14] region, [13:2] entry, [1:0] lane
DRAIN_CYCLES = 16


class DRAMSequencer(Module):
    def __init__(self, platform, sdram):
        phy = sdram.controller.settings.phy
        assert phy.nphases == 4 and phy.nranks == 1
        assert phy.read_latency < DRAIN_CYCLES and phy.write_latency >= 1
        self.bus = wishbone.Interface(data_width=32)
        dfi = sdram.dfii.ext_dfi.phases
        controller = sdram.dfii.slave.phases[0]

        def per_phase(name):
            return Cat(*(getattr(phase, name) for phase in dfi))

        self.specials += Instance("dram_sequencer",
            p_ADDRESS_BITS=len(dfi[0].address),
            p_BANK_BITS=len(dfi[0].bank),
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


def add_sequencer(soc):
    soc.submodules.sequencer = sequencer = DRAMSequencer(soc.platform, soc.sdram)
    soc.bus.add_slave("sequencer", sequencer.bus, SoCRegion(origin=BUS_ORIGIN, size=BUS_SIZE, cached=False))
