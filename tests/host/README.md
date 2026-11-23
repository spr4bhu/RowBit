# Host tests

Python host code. No board needed: `python3 -m pytest tests/host`

| File | What it checks |
|---|---|
| `test_program_builder.py` | Commands keep their spacing, reads and writes move to their phase, write data limit. |
| `test_program_encoding.py` | Out-of-range banks and addresses are rejected. |
| `test_init_rows_programs.py` | Row init splits many rows over programs that fit. |
| `test_subarray_map.py` | Saved subarray maps load, an unmapped board gets the plain grid. |
| `test_board_connect.py` | Connect refuses a port another server holds. |
| `test_bus_timeout.py` | A read with no answer raises instead of returning zeros. |
