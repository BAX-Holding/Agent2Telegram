"""Transcription language, key validation, and setup ownership boundaries.

A three-second Czech voice note came back as the English word "Down": Scribe was never told
the language, so it guessed — and on a short clip it guesses badly.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent2telegram import stt, wizard
from agent2telegram.config import Config, load, save


class LanguageIsSent(unittest.TestCase):
    def _capture(self, **kw):
        """Run a transcription against a fake opener and return the request body."""
        telo = {}

        class FakeResp:
            def __enter__(self_inner): return self_inner
            def __exit__(self_inner, *a): return False
            def read(self_inner): return b'{"text": "ahoj"}'

        class FakeOpener:
            def open(self_inner, req, timeout=None):
                telo["body"] = req.data.decode("utf-8", "replace")
                return FakeResp()

        text = stt.transcribe_elevenlabs(b"audio", api_key="sk_x", opener=FakeOpener(), **kw)
        return text, telo["body"]

    def test_language_appears_in_the_request(self):
        text, body = self._capture(language="cs")
        self.assertEqual(text, "ahoj")
        self.assertIn("language_code", body)
        self.assertIn("cs", body)

    def test_no_language_means_no_field(self):
        """Auto-detect stays available — we must not force a language on everyone."""
        _, body = self._capture()
        self.assertNotIn("language_code", body)

    def test_model_is_always_sent(self):
        _, body = self._capture(language="de")
        self.assertIn("scribe_v1", body)

    def test_dispatcher_passes_the_language_through(self):
        videno = {}
        orig = stt.transcribe_elevenlabs
        stt.transcribe_elevenlabs = lambda audio, **kw: videno.update(kw) or "x"
        try:
            stt.transcribe(b"a", api_key="sk_x", language="cs")
        finally:
            stt.transcribe_elevenlabs = orig
        self.assertEqual(videno.get("language"), "cs")


class KeyShape(unittest.TestCase):
    """The web UI offers "Copy Key ID" but never shows the key again, so pasting the ID is
    the easy mistake. Caught here it costs one retype; caught later it looks like a broken
    bridge answering HTTP 400."""

    def test_key_id_is_rejected(self):
        self.assertFalse(stt.looks_like_api_key("a21b9f0c4e2d4f8b9c1a2b3c4d5e6f70"))

    def test_real_key_is_accepted(self):
        self.assertTrue(stt.looks_like_api_key("sk_abc123"))

    def test_blank_is_rejected(self):
        self.assertFalse(stt.looks_like_api_key(""))


class SetupOwnershipBoundary(unittest.TestCase):
    def test_set_elevenlabs_updates_only_agent2telegram_and_never_touches_hermes(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bridge.json"
            save(Config(agent="codex", token="1:2", allowed_user_ids=[7]), path)
            with patch.dict(os.environ, {"AGENT2TELEGRAM_CONFIG": str(path)}), \
                 patch("agent2telegram.wizard._ask_secret", return_value="sk_secret"), \
                 patch("builtins.input", return_value="cs"), \
                 patch("agent2telegram.updater._running_bridges", return_value=[]), \
                 patch("shutil.which", return_value="/usr/bin/hermes"), \
                 patch("subprocess.run") as run:
                rc = wizard.set_elevenlabs(str(path))

            configured = load(path)
            self.assertEqual(rc, 0)
            self.assertEqual(configured.elevenlabs_api_key, "sk_secret")
            self.assertEqual(configured.elevenlabs_language, "cs")
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
