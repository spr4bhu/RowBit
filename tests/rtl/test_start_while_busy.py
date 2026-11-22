import cocotb
from cocotb.triggers import ClockCycles

from rowbit.program import Command, encode_instruction
from sequencer_bench import Bench, run_simulation


@cocotb.test()
async def start_while_busy_is_ignored(dut):
    bench = Bench(dut)
    await bench.start()
    await bench.load([encode_instruction([(Command.ACT, 0, 1)], wait=30),
                      encode_instruction([(Command.PRE, 0, 0)], wait=30)])
    await bench.run()
    await bench.controller_refresh()
    await ClockCycles(dut.clk, 25)  # inside the first instruction's wait
    await bench.run()
    await bench.wait_done()

    assert [command for _, _, command, *_ in bench.issued()] == ["ACT", "PRE"]


def test_start_while_busy():
    run_simulation(__file__)
