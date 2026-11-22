import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ReadOnly, RisingEdge
from cocotb_tools.runner import get_runner, get_results

from rowbit.program import WORDS_PER_INSTRUCTION, Command

ROOT = os.environ["ROWBIT_ROOT"]
RTL = [os.path.join(ROOT, "rtl", name) for name in ("dram_sequencer.v", "simple_dual_port_ram.v")]
PINS_TO_COMMAND = {0b0011: "ACT", 0b0010: "PRE", 0b0101: "RD", 0b0100: "WR", 0b0001: "REF", 0b0110: "ZQCS"}
REGISTERS, PROGRAM, WRITE_DATA, READ_DATA = range(4)


def run_simulation(test_file, parameters=None):
    """Builds the sequencer with Icarus and runs the cocotb tests in `test_file`; fails on any failed test."""
    parameters = parameters or {}
    name = os.path.splitext(os.path.basename(test_file))[0]
    suffix = "".join(f"_{key}{value}" for key, value in sorted(parameters.items()))
    build_dir = os.path.join(ROOT, "build", "rtl-sim", name + suffix)
    runner = get_runner("icarus")
    runner.build(sources=RTL, hdl_toplevel="dram_sequencer", parameters=parameters, build_dir=build_dir,
                 always=True, timescale=("1ns", "1ps"))
    results = runner.test(test_module=name, hdl_toplevel="dram_sequencer", build_dir=build_dir,
                          test_dir=os.path.dirname(test_file))
    total, failed = get_results(results)
    assert total > 0 and failed == 0, f"{failed} of {total} cocotb tests failed, see {build_dir}"


def bus_address(region, entry=0, lane=0):
    return (region << 14) | (entry << 2) | lane


class Bench:
    """Drives the sequencer's bus and controller inputs and records what it puts on DFI."""

    def __init__(self, dut):
        self.dut = dut
        self.cycle = 0
        self.dfi_log = []  # one dict per sys cycle

    async def start(self):
        dut = self.dut
        cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
        for name in ("wb_cyc", "wb_stb", "wb_we", "wb_adr", "wb_dat_w", "dfi_rddata", "dfi_rddata_valid"):
            getattr(dut, name).value = 0
        self.controller_command("NOP")
        dut.rst.value = 1
        for _ in range(3):
            await RisingEdge(dut.clk)
        dut.rst.value = 0
        cocotb.start_soon(self._record_dfi())

    def controller_command(self, command):
        pins = 0b1111 if command == "NOP" else {v: k for k, v in PINS_TO_COMMAND.items()}[command]
        self.dut.ctrl_cs_n.value = pins >> 3 & 1
        self.dut.ctrl_ras_n.value = pins >> 2 & 1
        self.dut.ctrl_cas_n.value = pins >> 1 & 1
        self.dut.ctrl_we_n.value = pins & 1

    async def controller_refresh(self):
        self.refresh_cycle = self.cycle + 1  # the edge that samples it
        self.controller_command("REF")
        await RisingEdge(self.dut.clk)
        self.controller_command("NOP")

    async def _bus(self, address, value=None):
        dut = self.dut
        dut.wb_adr.value = address
        dut.wb_we.value = value is not None
        dut.wb_dat_w.value = value or 0
        dut.wb_cyc.value = 1
        dut.wb_stb.value = 1
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            if dut.wb_ack.value:
                data = int(dut.wb_dat_r.value)
                break
        await RisingEdge(dut.clk)
        dut.wb_cyc.value = 0
        dut.wb_stb.value = 0
        dut.wb_we.value = 0
        return data

    async def write(self, address, value):
        await self._bus(address, value)

    async def read(self, address):
        return await self._bus(address)

    async def load(self, instructions, write_entries=()):
        for index, words in enumerate(instructions):
            for lane in range(WORDS_PER_INSTRUCTION):
                await self.write(bus_address(PROGRAM, index, lane), words[lane])
        for index, entry in enumerate(write_entries):
            for lane in range(4):
                await self.write(bus_address(WRITE_DATA, index, lane), entry >> (32 * lane) & 0xFFFFFFFF)
        await self.write(bus_address(REGISTERS, 0, 1), len(instructions))

    async def run(self):
        await self.write(bus_address(REGISTERS, 0, 0), 1)

    async def status(self):
        value = await self.read(bus_address(REGISTERS, 0, 0))
        return {"busy": value & 1, "done": value >> 1 & 1}

    async def wait_done(self, timeout=10000):
        for _ in range(timeout):
            if (await self.status())["done"]:
                return
        raise TimeoutError("sequencer never finished")

    def issued(self):
        """(cycle, slot, command, bank, address) for every non-NOP command on DFI."""
        return [(entry["cycle"], slot, *command) for entry in self.dfi_log
                for slot, command in enumerate(entry["slots"]) if command]

    async def _record_dfi(self):
        dut = self.dut
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            self.cycle += 1
            cs_n, ras_n, cas_n, we_n, bank, address = (value_of(signal) for signal in (
                dut.dfi_cs_n, dut.dfi_ras_n, dut.dfi_cas_n, dut.dfi_we_n, dut.dfi_bank, dut.dfi_address))
            slots = []
            for slot in range(4):
                if None in (cs_n, ras_n, cas_n, we_n, bank, address):
                    slots.append(("X", None, None))
                    continue
                pins = ((cs_n >> slot & 1) << 3 | (ras_n >> slot & 1) << 2 |
                        (cas_n >> slot & 1) << 1 | (we_n >> slot & 1))
                command = PINS_TO_COMMAND.get(pins)
                slots.append((command, bank >> (3 * slot) & 0b111, address >> (14 * slot) & 0x3FFF)
                             if command else None)
            self.dfi_log.append({
                "cycle": self.cycle,
                "slots": slots,
                "select": value_of(dut.dfi_select),
                "wrdata_en": value_of(dut.dfi_wrdata_en),
                "rddata_en": value_of(dut.dfi_rddata_en),
                "wrdata": value_of(dut.dfi_wrdata),
            })


def value_of(signal):
    """The signal as an int, or None while it is X/Z."""
    return int(signal.value) if signal.value.is_resolvable else None
