"""Exercise Auto's live path with a local TiXL-protocol stub.

Run with Blender's bundled Python and pass absolute paths for --blend,
--cache, --operator-project, --editor, and --blender.
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path

parser = argparse.ArgumentParser()
for name in ("blend", "cache", "operator-project", "editor", "blender"):
    parser.add_argument("--" + name, required=True)
args = parser.parse_args()

server = socket.socket()
server.bind(("127.0.0.1", 0))
server.listen()
server.settimeout(0.5)
port = server.getsockname()[1]
done = threading.Event()
methods = []


def serve():
    while not done.is_set():
        try:
            connection, _ = server.accept()
        except socket.timeout:
            continue
        except OSError:
            if done.is_set():
                break
            raise
        with connection:
            request = json.loads(connection.makefile("r", encoding="utf-8").readline())
            methods.append(request["method"])
            result = {"protocolVersion": 1} if request["method"] == "getVersion" else {}
            connection.sendall((json.dumps({"id": request["id"], "ok": True, "result": result}) + "\n").encode())


thread = threading.Thread(target=serve, daemon=True)
thread.start()
env = dict(os.environ)
env.update(TIXL_BRIDGE_OPERATOR_PROJECT=args.operator_project, TIXL_BRIDGE_EDITOR=args.editor,
           TIXL_BRIDGE_BLENDER=args.blender, TIXL_BRIDGE_MODE="auto",
           TIXL_BRIDGE_PORT=str(port), TIXL_BRIDGE_LAUNCH_EDITOR="0")
try:
    command = [sys.executable, str(Path(__file__).resolve().parents[1] / "blender_tixl_bridge" / "source" / "blend_sync.py"),
               "sync", "--blend", args.blend, "--cache-root", args.cache, "--force"]
    result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=90)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    assert {"getVersion", "reload", "openProject"} <= set(methods), methods
    print("DEBUG_BRIDGE_LIVE_PATH_OK", methods)
    count = len(methods)
    env["TIXL_BRIDGE_MODE"] = "offline"
    result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=90)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    assert len(methods) == count, methods
    print("OFFLINE_MODE_SKIPPED_DEBUG_BRIDGE_OK")
finally:
    done.set()
    server.close()
    thread.join(timeout=2)
