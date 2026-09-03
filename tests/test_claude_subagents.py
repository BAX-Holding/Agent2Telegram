"""Regression tests for Telegram turns continued by Claude Code background agents."""
import io
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from agent2telegram import stop_hook
from agent2telegram.attach import AttachBridge
from agent2telegram.readers import ClaudeCodeReader, Ev


class ClaudeContinuationReaderTests(unittest.TestCase):
    def test_resume_position_keeps_telegram_origin_across_task_notification(self):
        records = [
            {"type": "user", "message": {"content": [{"type": "text", "text": "[TG] research this"}]}},
            {"type": "user", "message": {"content": [{"type": "text", "text": "<task-notification><task-id>abc</task-id></task-notification>"}]}},
            {"type": "user", "isCompactSummary": True, "message": {"content": "harness summary"}},
        ]
        with tempfile.TemporaryDirectory() as td:
            transcript = Path(td) / "parent.jsonl"
            transcript.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
            bridge = object.__new__(AttachBridge)
            bridge._transcript = transcript
            bridge._tpos = transcript.stat().st_size
            bridge._reader = ClaudeCodeReader()
            bridge._origins = ("[TG]",)
            bridge._turn_from_tg = False
            bridge._resume_position()
        self.assertTrue(bridge._turn_from_tg)

    def test_task_notification_is_internal_continuation_not_a_new_user_turn(self):
        record = {"type": "user", "message": {"content": [{"type": "text", "text": "<task-notification><task-id>abc</task-id></task-notification>"}]}}
        self.assertEqual(list(ClaudeCodeReader().parse(record)), [Ev("continuation")])

    def test_internal_continuation_reactivates_existing_telegram_lineage(self):
        bridge = object.__new__(AttachBridge)
        bridge._turn_from_tg = True
        bridge._turn_active = threading.Event()
        bridge._last_activity = 0.0
        bridge._owner_chat = 123
        before = time.monotonic()
        bridge._handle_event(Ev("continuation"))
        self.assertTrue(bridge._turn_active.is_set())
        self.assertGreaterEqual(bridge._last_activity, before)

    def test_internal_continuation_does_not_create_telegram_lineage(self):
        bridge = object.__new__(AttachBridge)
        bridge._turn_from_tg = False
        bridge._turn_active = threading.Event()
        bridge._last_activity = 0.0
        bridge._owner_chat = 123
        bridge._handle_event(Ev("continuation"))
        self.assertFalse(bridge._turn_active.is_set())
        self.assertEqual(bridge._last_activity, 0.0)


class ClaudeStopHookTests(unittest.TestCase):
    def test_guardless_bridge_ignores_subagent_stop_event(self):
        payload = {"transcript_path": "/work/parent-session/subagents/agent-child.jsonl"}
        cfg = {"signal_file": "/tmp/claudia/answer.txt", "claude_session_id": ""}
        with patch("agent2telegram.stop_hook._all_cfgs", return_value=[cfg]), \
             patch("agent2telegram.stop_hook._mark") as mark, \
             patch("sys.stdin", io.StringIO(json.dumps(payload))):
            stop_hook.main()
        mark.assert_not_called()


if __name__ == "__main__":
    unittest.main()
