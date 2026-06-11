#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_update_db import SESSION_PAYLOAD, make_fixtures

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER = REPO_ROOT / "scripts" / "fluent-mcp.py"


class FluentMcpTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fluent-mcp-test-"))
        self.data_dir = self.tmp / "data"
        self.data_dir.mkdir()
        make_fixtures(self.data_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _request(self, requests):
        env = os.environ.copy()
        env["FLUENT_DATA_DIR"] = str(self.data_dir)
        proc = subprocess.run(
            [sys.executable, str(SERVER)],
            input="\n".join(json.dumps(req) for req in requests).encode(),
            cwd=str(REPO_ROOT),
            capture_output=True,
            env=env,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr.decode())
        return [json.loads(line) for line in proc.stdout.decode().splitlines() if line.strip()]

    def test_lists_tools_and_maps_quality(self):
        responses = self._request([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "fluent_score_to_quality", "arguments": {"score": 9}},
            },
        ])
        tools = {tool["name"] for tool in responses[1]["result"]["tools"]}
        self.assertIn("fluent_read_state", tools)
        self.assertIn("fluent_update_session", tools)
        self.assertIn("fluent_score_to_quality", tools)
        self.assertEqual(responses[2]["result"]["structuredContent"]["quality"], 4)

    def test_read_state_and_update_session(self):
        responses = self._request([
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "fluent_read_state", "arguments": {}},
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "fluent_update_session", "arguments": {"session": SESSION_PAYLOAD}},
            },
        ])
        state = responses[0]["result"]["structuredContent"]
        self.assertEqual(state["view"], "compact")
        self.assertEqual(state["computed"]["storage_backend"], "sql")
        self.assertEqual(len(state["databases"]["session_log"]["sessions"]), 1)
        summary = responses[1]["result"]["structuredContent"]
        self.assertEqual(summary["session_id"], "session-002")
        self.assertEqual(summary["session_correct"], 4)
        self.assertTrue((self.data_dir / "fluent.sqlite").exists())

    def test_read_state_accepts_full_view_and_limits(self):
        first = dict(SESSION_PAYLOAD)
        first["session_id"] = "session-002"
        second = dict(SESSION_PAYLOAD)
        second["session_id"] = "session-003"
        responses = self._request([
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "fluent_update_session", "arguments": {"session": first}},
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "fluent_update_session", "arguments": {"session": second}},
            },
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "fluent_read_state",
                    "arguments": {"view": "full", "session_limit": 1, "include_databases": ["session_log"]},
                },
            },
        ])
        state = responses[2]["result"]["structuredContent"]
        self.assertEqual(state["view"], "full")
        self.assertEqual(set(state["databases"]), {"session_log"})
        self.assertEqual(len(state["databases"]["session_log"]["sessions"]), 1)
        self.assertEqual(state["databases"]["session_log"]["sessions"][0]["session_id"], "session-003")
        self.assertEqual(state["databases"]["session_log"]["sessions_omitted"], 2)


if __name__ == "__main__":
    unittest.main()
