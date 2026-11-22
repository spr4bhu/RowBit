import cocotb
from cocotb.triggers import ClockCycles

from sequencer_bench import REGISTERS, Bench, bus_address, run_simulation


@cocotb.test()
async def empty_or_oversized_program_finishes_without_taking_the_bus(dut):
    depth = int(dut.PROGRAM_DEPTH.value)
    bench = Bench(dut)
    await bench.start()
    for length in (0, depth + 1):
        await bench.write(bus_address(REGISTERS, 0, 1), length)
        await bench.run()
        await bench.controller_refresh()
        await ClockCycles(dut.clk, 50)
        assert await bench.status() == {"busy": 0, "done": 1}, f"length {length} did not finish"
        assert not any(entry["select"] for entry in bench.dfi_log), f"length {length} took the bus"


def test_program_length_limits():
    run_simulation(__file__)
