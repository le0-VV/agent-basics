#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(os.environ.get("AGENT_BASICS_PROJECT_DIR", os.getcwd()))
MODEL_PATH = ROOT / ".agents/openviking/models/bge-small-zh-v1.5-q4_k_m.gguf"
MODEL_NAME = "bge-small-zh-v1.5-q4_k_m"
PORT = int(os.environ.get("AGENT_BASICS_EMBEDDING_PORT", "1934"))
DIMENSION = 512


def run_embedding(text):
    base = [
        "llama-embedding",
        "--model",
        str(MODEL_PATH),
        "--prompt",
        text,
        "--log-verbosity",
        "1",
        "--no-warmup",
    ]
    attempts = [base, base + ["--device", "none"]]
    last = None
    for command in attempts:
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        match = re.search(r"embedding\s+0:\s+(.+?)(?:\n\n|$)", result.stdout, re.S)
        if match:
            values = [float(part) for part in match.group(1).split()]
            if len(values) != DIMENSION:
                raise RuntimeError(f"expected {DIMENSION} embedding values, got {len(values)}")
            return values
        last = result.stdout + result.stderr
    raise RuntimeError(last or "llama-embedding failed")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/health", "/v1/health"):
            self._json(200, {"status": "ok", "model": MODEL_NAME, "dimension": DIMENSION})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path in ("/v1/chat/completions", "/chat/completions"):
            self._json(200, {
                "id": "agent-basics-local-summary",
                "object": "chat.completion",
                "model": "agent-basics-local-summary",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Local OpenViking context item. Use the source content directly for details.",
                    },
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            })
            return
        if self.path not in ("/v1/embeddings", "/embeddings"):
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            inputs = payload.get("input", "")
            if isinstance(inputs, str):
                inputs = [inputs]
            data = []
            for index, text in enumerate(inputs):
                data.append({
                    "object": "embedding",
                    "index": index,
                    "embedding": run_embedding(str(text)),
                })
            self._json(200, {
                "object": "list",
                "model": payload.get("model") or MODEL_NAME,
                "data": data,
                "usage": {"prompt_tokens": 0, "total_tokens": 0},
            })
        except Exception as exc:
            self._json(500, {"error": str(exc)})


if __name__ == "__main__":
    if not MODEL_PATH.exists():
        print(f"missing model: {MODEL_PATH}", file=sys.stderr)
        sys.exit(1)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
