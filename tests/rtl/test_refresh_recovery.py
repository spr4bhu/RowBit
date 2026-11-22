import cocotb

from rowbit.program import Command, encode_instruction
from sequencer_bench import Bench, run_simulation

RECOVERY_CYCLES = 16  # the RTL default: tRFC (160 ns) at 75 MHz, rounded up


@cocotb.test()
async def first_command_waits_for_refresh_recovery(dut):
    bench = Bench(dut)
    await bench.start()
    await bench.load([encode_instruction([(Command.ACT, 0, 1)])])
    await bench.run()
    await bench.controller_refresh()
    await bench.wait_done()

    first_command = bench.issued()[0][0]
    assert first_command - bench.refresh_cycle > RECOVERY_CYCLES, "ACT inside tRFC of the controller's REF"


def test_refresh_recovery():
    run_simulation(__file__)
