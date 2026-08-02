"""Regression test: Codex explicit turn-end must not tail-scan historical answers."""
from __future__ import annotations

import json
import tempfile
import threading
import types
import unittest
from pathlib import Path

from agent2telegram.attach import AttachBridge
from agent2telegram.readers import CodexReader


class _Telegram:
    def __init__(self):
        self.sent: list[str] = []

    def send_message(self, _chat_id: int, text: str):
        self.sent.append(text)


class CodexBackstopTests(unittest.TestCase):
    def test_task_complete_without_current_agent_message_never_reuses_history(self):
        with tempfile.TemporaryDirectory() as td:
            transcript = Path(td) / "rollout.jsonl"
            transcript.write_text(
                json.dumps({
                    "timestamp": "old",
                    "type": "event_msg",
                    "payload": {
                        "type": "agent_message",
                        "message": "OLD SUCCESSFUL ANSWER",
                        "phase": "final_answer",
                    },
                }) + "\n",
                encoding="utf-8",
            )
            bridge = object.__new__(AttachBridge)
            bridge.cfg = types.SimpleNamespace(agent="codex")
            bridge._reader = CodexReader()
            bridge._transcript = transcript
            bridge._turn_active = threading.Event()
            bridge._turn_active.set()
            bridge._turn_from_tg = True
            bridge._turn_text_sent = False
            bridge._owner_chat = 123
            bridge._status = {"mid": None, "shown": ""}
            bridge._seen_tools = set()
            bridge._status_path = None
            bridge._pending_turn_end = True
            bridge._turn_end = None
            bridge._turn_started = 0.0
            bridge._typing_count = 0
            bridge._max_gap = 0.0
            bridge._marker = "[TG]"
            bridge._pending_send = []
            bridge._queue_path = None
            bridge._sent_keys = set()
            bridge.tg = _Telegram()

            bridge._finish_turn()

            self.assertEqual(bridge.tg.sent, [])
            self.assertFalse(bridge._turn_active.is_set())


if __name__ == "__main__":
    unittest.main()
