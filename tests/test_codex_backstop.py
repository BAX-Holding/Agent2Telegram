"""Regression test: Codex explicit turn-end must not tail-scan historical answers."""
import json
import tempfile
import unittest
from pathlib import Path

from agent2telegram.readers import CodexReader
from tests.test_attach_backstop import _bridge


class CodexBackstopTests(unittest.TestCase):
    def test_task_complete_without_current_agent_message_never_reuses_history(self):
        with tempfile.TemporaryDirectory() as td:
            bridge = _bridge(td)
            bridge.cfg.agent = "codex"
            bridge._reader = CodexReader()
            bridge._transcript.write_text(
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
            bridge._pending_turn_end = True

            bridge._finish_turn()

            self.assertEqual(bridge.tg.sent, [])
            self.assertFalse(bridge._turn_active.is_set())


if __name__ == "__main__":
    unittest.main()
