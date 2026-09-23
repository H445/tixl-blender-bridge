"""Optional local JSON-lines client for TiXL's opt-in debug server."""
import json
import socket
import time


def call(method: str, port: int, timeout: float = 120, **params):
    request = {"id": str(time.time_ns()), "method": method, **params}
    with socket.create_connection(("127.0.0.1", port), timeout=min(3, timeout)) as connection:
        connection.settimeout(timeout)
        connection.sendall((json.dumps(request) + "\n").encode("utf-8"))
        line = connection.makefile("r", encoding="utf-8").readline()
    if not line:
        raise ConnectionError("TiXL debug bridge closed without a response")
    response = json.loads(line)
    if not response.get("ok"):
        raise RuntimeError(json.dumps(response))
    return response.get("result")
