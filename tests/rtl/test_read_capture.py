import random

import cocotb
from cocotb.triggers import NextTimeStep, ReadOnly, RisingEdge

from rowbit.program import Command, encode_instruction
from rowbit.sequencer import LANES
from sequencer_bench import READ_DATA, REGISTERS, Bench, bus_address, run_simulation

READ_LATENCY = 8  # sys cycles; any PHY-like value below DRAIN_CYCLES


async def phy(dut, bursts):
    """Plays the PHY: answers each rddata_en with the next burst READ_LATENCY cycles later."""
    cycles_left = []  # one entry per requested burst
    while True:
        await RisingEdge(dut.clk)
        await ReadOnly()
        requested = int(dut.dfi_rddata_en.value) != 0
        await NextTimeStep()
        cycles_left = [left - 1 for left in cycles_left]
        answer = bool(cycles_left) and cycles_left[0] == 0
        if answer:
            cycles_left.pop(0)
        if requested:
            cycles_left.append(READ_LATENCY)
        dut.dfi_rddata_valid.value = int(answer)
        dut.dfi_rddata.value = bursts.pop(0) if answer else 0


@cocotb.test()
async def stores_only_bursts_answering_its_own_reads(dut):
    bursts = [random.Random(index).getrandbits(128) for index in range(5)]
    bench = Bench(dut)
    await bench.start()
    await bench.load([encode_instruction([(Command.RD, 0, 8 * index)]) for index in range(5)])
    await bench.run()
    await bench.controller_refresh()

    # The controller's last read lands just after the handover: not ours.
    await RisingEdge(dut.clk)
    dut.dfi_rddata.value = (1 << 128) - 1
    dut.dfi_rddata_valid.value = 1
    await RisingEdge(dut.clk)
    dut.dfi_rddata_valid.value = 0

    cocotb.start_soon(phy(dut, list(bursts)))
    await bench.wait_done()

    assert await bench.read(bus_address(REGISTERS, 0, 2)) == len(bursts)
    for index, burst in enumerate(bursts):
        words = [await bench.read(bus_address(READ_DATA, index, lane)) for lane in range(LANES)]
        assert sum(word << (32 * lane) for lane, word in enumerate(words)) == burst


def test_read_capture():
    run_simulation(__file__)
