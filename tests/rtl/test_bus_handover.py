import cocotb
from cocotb.triggers import ClockCycles

from rowbit.program import Command, encode_instruction
from sequencer_bench import Bench, run_simulation

DRAIN_CYCLES = 16


@cocotb.test()
async def takes_bus_after_controller_refresh_and_hands_it_back(dut):
    bench = Bench(dut)
    await bench.start()
    await bench.load([encode_instruction([(Command.ACT, 1, 7)]), encode_instruction([(Command.PRE, 1, 0)])])
    await bench.run()

    await ClockCycles(dut.clk, 20)
    assert (await bench.status())["busy"] == 1
    assert not any(entry["select"] for entry in bench.dfi_log), "took the bus before any refresh"

    await bench.controller_refresh()
    await bench.wait_done()
    assert (await bench.status()) == {"busy": 0, "done": 1}

    selected = [entry["cycle"] for entry in bench.dfi_log if entry["select"]]
    last_command = bench.issued()[-1][0]
    assert bench.issued()[0][0] > selected[0], "issued before taking the bus"
    assert selected[-1] - last_command >= DRAIN_CYCLES, "released before reads could land"
    assert bench.dfi_log[-1]["select"] == 0


def test_bus_handover():
    run_simulation(__file__)
