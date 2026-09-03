"""Explicit transcript directories follow new files; explicit files remain pinned."""
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

from agent2telegram.attach import AttachBridge
from agent2telegram.config import Config


class ExplicitTranscriptDirectoryTests(unittest.TestCase):
    def _bridge(self, transcript_path: Path, current: Path) -> AttachBridge:
        bridge = object.__new__(AttachBridge)
        bridge.cfg = Config(agent="codex", token="1:2", allowed_user_ids=[7], tmux_session="Ari", transcript_path=str(transcript_path))
        bridge._transcript = current
        bridge._last_resolve = 0.0
        bridge._turn_active = threading.Event()
        bridge._tpos = current.stat().st_size
        bridge._turn_tpos = 12_345
        bridge._session_cwd = lambda: "/home/meta/ari"
        bridge._resume_position = lambda: None
        return bridge

    def test_reresolves_when_new_rollout_appears_in_explicit_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = root / "rollout-old.jsonl"
            old.write_text("{}\n", encoding="utf-8")
            bridge = self._bridge(root, old)
            new = root / "rollout-new.jsonl"
            new.write_text("{}\n", encoding="utf-8")
            newer = time.time() + 2
            os.utime(new, (newer, newer))
            bridge._maybe_reresolve()
            self.assertEqual(new, bridge._transcript)
            self.assertEqual(0, bridge._tpos)
            self.assertEqual(0, bridge._turn_tpos)

    def test_keeps_explicit_transcript_file_pinned(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pinned = root / "rollout-pinned.jsonl"
            pinned.write_text("{}\n", encoding="utf-8")
            bridge = self._bridge(pinned, pinned)
            newer = root / "rollout-newer.jsonl"
            newer.write_text("{}\n", encoding="utf-8")
            future = time.time() + 2
            os.utime(newer, (future, future))
            bridge._maybe_reresolve()
            self.assertEqual(pinned, bridge._transcript)
            self.assertEqual(pinned.stat().st_size, bridge._tpos)
            self.assertEqual(12_345, bridge._turn_tpos)


if __name__ == "__main__":
    unittest.main()
