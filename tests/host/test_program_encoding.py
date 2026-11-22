import pytest

from rowbit.program import Command, encode_instruction


@pytest.mark.parametrize("slot", [(Command.ACT, 8, 0), (Command.ACT, 0, 1 << 14)])
def test_out_of_range_bank_or_address_is_rejected(slot):
    with pytest.raises(ValueError):
        encode_instruction([slot])
