# RTL tests

Sequencer Verilog in simulation (cocotb + Icarus). No board needed: `python3 -m pytest tests/rtl`

| File | What it checks |
|---|---|
| `test_command_timing.py` | Each command lands on its slot and cycle. |
| `test_write_data.py` | Write data follows each write by the write latency. |
| `test_read_capture.py` | Only bursts answering the sequencer's own reads are stored. |
| `test_bus_handover.py` | Takes the bus after a controller refresh and hands it back. |
| `test_refresh_recovery.py` | The first command waits for refresh recovery. |
| `test_start_while_busy.py` | A start while busy is ignored. |
| `test_program_length_limits.py` | An empty or oversized program finishes without taking the bus. |
| `sequencer_bench.py` | Shared bench: builds the simulation and drives the sequencer. |
