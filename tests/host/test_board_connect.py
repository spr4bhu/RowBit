import socket
import threading

import pytest

from rowbit import Board, board


def test_connect_refuses_a_port_another_server_holds(monkeypatch):
    other_server = socket.create_server(("localhost", 0))
    monkeypatch.setattr(board, "SERVER_PORT", other_server.getsockname()[1])

    def answer_like_litex_server():
        try:
            while True:
                client, _ = other_server.accept()
                with client:
                    client.sendall(b"CommUART:localhost:0")
        except OSError:
            pass  # the test closed the server

    threading.Thread(target=answer_like_litex_server, daemon=True).start()
    arty = Board(uart="/dev/no-such-uart")
    with pytest.raises(RuntimeError, match="already in use"):
        arty.connect()
    arty.close()
    other_server.close()
