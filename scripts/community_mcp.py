#!/usr/bin/env python3
"""Stdio MCP entrypoint for the Aftergraph engineering crew (community edition).

Accepts both newline-delimited JSON and LSP-style Content-Length framing, and
answers in the same framing the client used, so generic MCP clients connect
without a shim.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from aftergraph_crew.community_server import CommunityMCPServer


def _read_framed(stream):
    """Yield (request, framed) pairs from stdin, whichever framing arrives."""
    while True:
        line = stream.readline()
        if not line:
            return
        text = line.decode("utf-8", "replace").strip()
        if not text:
            continue
        if text.lower().startswith("content-length:"):
            length = int(text.split(":", 1)[1])
            while True:
                nxt = stream.readline()
                if not nxt or nxt in (b"\r\n", b"\n"):
                    break
            body = stream.read(length)
            yield json.loads(body.decode("utf-8")), True
        else:
            yield json.loads(text), False


def _write(stream, payload, framed):
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    if framed:
        stream.write(b"Content-Length: %d\r\n\r\n%s" % (len(body), body))
    else:
        stream.write(body + b"\n")
    stream.flush()


def main():
    server = CommunityMCPServer()
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    for request, framed in _read_framed(stdin):
        try:
            response = server.handle(request)
        except Exception as exc:  # pragma: no cover - defensive
            response = {"jsonrpc": "2.0", "id": request.get("id"),
                        "error": {"code": -32000, "message": str(exc)}}
        if response is None:  # notification
            continue
        _write(stdout, response, framed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
