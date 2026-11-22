import socket
import threading

import pytest

from rowbit.board import open_bus


def test_a_read_with_no_answer_raises_instead_of_returning_zeros():
    silent_server = socket.create_server(("localhost", 0))
    clients = []

    def accept_and_never_answer_reads():
        client, _ = silent_server.accept()
        client.sendall(b"CommUART:localhost:0")
        clients.append(client)

    threading.Thread(target=accept_and_never_answer_reads, daemon=True).start()
    bus = open_bus(silent_server.getsockname()[1], csr_csv=None, timeout=0.2)
    with pytest.raises(TimeoutError):
        bus.read(0)
    bus.close()
    for client in clients:
        client.close()
    silent_server.close()
