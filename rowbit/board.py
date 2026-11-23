import os
import re
import socket
import subprocess
import time

from litex import RemoteClient
from serial.tools import list_ports

ROOT = os.environ["ROWBIT_ROOT"]
BITSTREAM = os.path.join(ROOT, "build", "soc", "gateware", "digilent_arty.bit")
CSR_CSV = os.path.join(ROOT, "build", "soc", "csr.csv")
SERVER_PORT = 1234
BUS_TIMEOUT = 30  # seconds; a read is answered only after every queued write has crossed the UART
ANSI_COLOUR = re.compile(r"\x1b\[[0-9;]*m")


class Board:
    """The Arty over UARTBone: program it, reach its bus, read its BIOS console."""

    def __init__(self, uart=None):
        self.uart = uart or os.environ["ARTY_UART"]
        self.server = None
        self.bus = None

    @property
    def serial(self):
        """The USB serial number of the board's FTDI chip: names this board's measured files."""
        port = next((port for port in list_ports.comports() if port.device == self.uart), None)
        if port is None or not port.serial_number:
            raise RuntimeError(f"no USB serial number for {self.uart}")
        return port.serial_number

    def program(self, bitstream=BITSTREAM):
        subprocess.run(["openFPGALoader", "-b", "arty_a7_35t", bitstream], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def connect(self):
        # Our server would fail to bind and exit silently, leaving us talking to the other one.
        if port_is_open(SERVER_PORT):
            raise RuntimeError(f"port {SERVER_PORT} already in use (a litex_server left running?)")
        baudrate = RemoteClient(csr_csv=CSR_CSV).constants.uart_baudrate
        self.server = subprocess.Popen(
            ["litex_server", "--uart", "--uart-port", self.uart, "--uart-baudrate", str(baudrate),
             "--bind-port", str(SERVER_PORT)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_for_port(SERVER_PORT)
        self.bus = open_bus(SERVER_PORT)

    def close(self):
        if self.bus:
            self.bus.close()
        if self.server:
            self.server.terminate()
            self.server.wait()

    def read_console(self, until, timeout=120):
        """Reads the BIOS console (crossover UART) until `until` appears; returns the text."""
        regs = self.bus.regs
        text = ""
        deadline = time.time() + timeout
        while until not in text:
            if time.time() > deadline:
                raise TimeoutError(f"no {until!r} on console, got:\n{text}")
            # Same as litex_term: a full FIFO is drained in one 16-byte burst.
            if regs.uart_xover_rxfull.read():
                count = 16
            elif not regs.uart_xover_rxempty.read():
                count = 1
            else:
                time.sleep(0.001)
                continue
            chars = self.bus.read(regs.uart_xover_rxtx.addr, length=count, burst="fixed")
            text += "".join(chr(c) for c in chars)
            text = ANSI_COLOUR.sub("", text)
        return text


def open_bus(port, csr_csv=CSR_CSV, timeout=BUS_TIMEOUT):
    # RemoteClient returns zeros on a timeout unless told to raise.
    bus = RemoteClient(port=port, csr_csv=csr_csv, timeout=timeout, raise_on_timeout=True)
    bus.open()
    return bus


def port_is_open(port):
    try:
        socket.create_connection(("localhost", port), timeout=0.2).close()
        return True
    except OSError:
        return False


def wait_for_port(port, timeout=10):
    deadline = time.time() + timeout
    while not port_is_open(port):
        if time.time() > deadline:
            raise TimeoutError(f"litex_server did not open port {port}")
        time.sleep(0.1)
