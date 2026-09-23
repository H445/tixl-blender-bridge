"""JSON-lines client for TiXL's local debug bridge."""
import json
import os
import socket
import time


def call(method, **params):
    request = {"id": str(time.time_ns()), "method": method, **params}
    port = int(os.environ.get("TIXL_BRIDGE_PORT", "9042"))
    with socket.create_connection(("127.0.0.1", port), timeout=20) as connection:
        connection.settimeout(120)
        connection.sendall((json.dumps(request) + "\n").encode())
        response = json.loads(connection.makefile("r", encoding="utf-8").readline())
    if not response.get("ok"):
        raise RuntimeError(json.dumps(response))
    return response.get("result")
