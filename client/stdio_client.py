"""A deliberately minimal MCP client over stdio.

No SDK on purpose: every message that goes in or out is printed, so the demos
show exactly what travels on the wire.
"""

import json
import queue
import subprocess
import threading
import time

PROTOCOL_VERSION = "2026-07-28"


def meta(version: str = PROTOCOL_VERSION) -> dict:
    """The per-request `_meta` block required by the stateless 2026-07-28 protocol."""
    return {
        "io.modelcontextprotocol/protocolVersion": version,
        "io.modelcontextprotocol/clientCapabilities": {},
        "io.modelcontextprotocol/clientInfo": {"name": "raw-client", "version": "0.1"},
    }


class RawStdioClient:
    """Spawns an MCP server and talks to it line by line, logging the transcript."""

    def __init__(self, cmd: list[str], env: dict | None = None, show_stderr: bool = False,
                 stderr_file=None):
        """stderr goes to stderr_file if given, else to the terminal or nowhere."""
        if stderr_file is not None:
            stderr = stderr_file
        else:
            stderr = None if show_stderr else subprocess.DEVNULL
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
            env=env,
            text=True,
            bufsize=1,
        )
        self.transcript: list[str] = []  # every stdout line received, in order
        self._lines: queue.Queue[str] = queue.Queue()
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()

    def _read_stdout(self) -> None:
        for line in self.proc.stdout:
            self._lines.put(line.rstrip("\n"))

    def send(self, message: dict) -> None:
        raw = json.dumps(message)
        print(f"-> {raw}")
        self.proc.stdin.write(raw + "\n")
        self.proc.stdin.flush()

    def read_line(self, timeout: float = 10.0) -> str | None:
        """Return the next raw stdout line, or None if nothing arrives in time."""
        try:
            line = self._lines.get(timeout=timeout)
        except queue.Empty:
            print(f"   (no message within {timeout:.0f}s)")
            return None
        self.transcript.append(line)
        print(f"<- {describe(line)}")
        return line

    def wait_for(self, request_id: int, timeout: float = 10.0) -> dict | None:
        """Read lines until the response with this id arrives, logging everything else."""
        deadline = time.monotonic() + timeout
        while (remaining := deadline - time.monotonic()) > 0:
            line = self.read_line(timeout=remaining)
            if line is None:
                return None
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(message, dict) and message.get("id") == request_id:
                return message
        return None

    def close(self, grace: float = 2.0) -> list[str]:
        """Close stdin, let the server exit, and return any lines it printed late."""
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self._reader.join(timeout=grace)
        late = []
        while not self._lines.empty():
            line = self._lines.get()
            print(f"<- (after close) {describe(line)}")
            self.transcript.append(line)
            late.append(line)
        return late


def describe(line: str) -> str:
    """Show a stdout line, flagging anything that is not a JSON-RPC message."""
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        return f"!! NOT JSON-RPC: {line!r}"
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return f"!! NOT JSON-RPC: {line!r}"
    return shorten(line)


def shorten(text: str, limit: int = 160) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def elapsed(start: float) -> str:
    return f"{time.monotonic() - start:.2f}s"
