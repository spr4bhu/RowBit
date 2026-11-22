# The DRAM chip's geometry and JEDEC timings, from the constants the SoC build wrote to csr.csv.


class DRAM:
    def __init__(self, constants):
        self.bank_bits = constants.dram_bank_bits
        self.column_bits = constants.dram_column_bits
        self.banks = 2**self.bank_bits
        self.rows = 2**constants.dram_row_bits
        self.columns = 2**self.column_bits
        self.burst_length = constants.dram_burst_length  # columns per RD or WR
        # Minimum tCK from one command to the next.
        self.activate_to_read = constants.dram_trcd  # also ACT->WR
        self.activate_to_precharge = constants.dram_tras
        self.read_to_precharge = constants.dram_trtp
        self.write_to_precharge = constants.dram_cwl + self.burst_length // 2 + constants.dram_twr
        self.precharge_to_activate = constants.dram_trp

    def random_locations(self, rng, count):
        """`count` distinct (bank, row, column) burst starts, sorted."""
        locations = set()
        while len(locations) < count:
            column = self.burst_length * rng.randrange(self.columns // self.burst_length)
            locations.add((rng.randrange(self.banks), rng.randrange(self.rows), column))
        return sorted(locations)
