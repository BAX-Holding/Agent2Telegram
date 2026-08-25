"""Attach-mode slash command tests — no Telegram network or real tmux."""
import types
import unittest
from typing import Any
from unittest.mock import PropertyMock, patch

from agent2telegram.attach import AttachBridge
from agent2telegram.session import TmuxSession


class _FakeTelegram:
    def __init__(self):
        self.sent = []

    def send_message(self, chat_id, text, parse_mode=None):
        self.sent.append((chat_id, text))


class _FakeSession:
    def __init__(self):
        self.raw = []

    def inject_raw(self, text):
        self.raw.append(text)


class AttachCommandTests(unittest.TestCase):
    def test_reset_sends_unprefixed_clear_to_claude(self):
        bridge: Any = object.__new__(AttachBridge)
        bridge.cfg = types.SimpleNamespace(
            agent="claude-code",
            tmux_session="Claudia",
            elevenlabs_api_key="",
        )
        bridge.tg = _FakeTelegram()
        bridge._session = _FakeSession()

        handled = bridge._handle_command("/reset", 123)

        self.assertTrue(handled)
        self.assertEqual(bridge._session.raw, ["/clear"])
        self.assertTrue(any("fresh" in text.lower() for _, text in bridge.tg.sent))

    def test_reset_sends_unprefixed_new_to_codex(self):
        bridge: Any = object.__new__(AttachBridge)
        bridge.cfg = types.SimpleNamespace(
            agent="codex",
            tmux_session="meta - Master",
            elevenlabs_api_key="",
        )
        bridge.tg = _FakeTelegram()
        bridge._session = _FakeSession()

        handled = bridge._handle_command("/reset", 123)

        self.assertTrue(handled)
        self.assertEqual(bridge._session.raw, ["/new"])
        self.assertTrue(any("fresh" in text.lower() for _, text in bridge.tg.sent))

    def test_inject_raw_does_not_add_origin_prefix(self):
        session: Any = object.__new__(TmuxSession)
        session.name = "Claudia"
        session._origin = "[TG] "
        with patch.object(TmuxSession, "alive", new_callable=PropertyMock, return_value=True), \
             patch("agent2telegram.session._tmux") as tmux:
            session.inject_raw("/clear")

        literal_calls = [c for c in tmux.call_args_list if "-l" in c.args]
        self.assertEqual(len(literal_calls), 1)
        self.assertEqual(literal_calls[0].args[-1], "/clear")

    def test_inject_raw_uses_pane_guard_and_sanitizes_control_characters(self):
        session: Any = object.__new__(TmuxSession)
        session.name = "Claudia"
        session._origin = "[TG] "
        session._expected_agent_commands = ("claude",)
        with patch.object(TmuxSession, "alive", new_callable=PropertyMock, return_value=True), \
             patch.object(TmuxSession, "_pane_ok", return_value=(True, "claude")) as pane_ok, \
             patch("agent2telegram.session._tmux") as tmux:
            session.inject_raw("/clear\x1b\nignored")

        pane_ok.assert_called_once_with()
        literal_calls = [c for c in tmux.call_args_list if "-l" in c.args]
        self.assertEqual(literal_calls[0].args[-1], "/clear ignored")

    def test_inject_raw_fails_closed_for_wrong_pane(self):
        session: Any = object.__new__(TmuxSession)
        session.name = "Claudia"
        session._origin = "[TG] "
        with patch.object(TmuxSession, "alive", new_callable=PropertyMock, return_value=True), \
             patch.object(TmuxSession, "_pane_ok", return_value=(False, "shell prompt")), \
             patch("agent2telegram.session._tmux") as tmux:
            with self.assertRaisesRegex(Exception, "refusing to inject"):
                session.inject_raw("/clear")

        tmux.assert_not_called()

    def test_voice_transcription_passes_configured_language_code(self):
        bridge: Any = object.__new__(AttachBridge)
        bridge.cfg = types.SimpleNamespace(
            elevenlabs_api_key="key",
            stt_language_code="sk",
        )
        bridge.tg = types.SimpleNamespace(
            get_file_path=lambda _file_id: "voice.ogg",
            download=lambda _path: b"audio",
            send_message=lambda *_args, **_kwargs: None,
        )

        with patch("agent2telegram.stt.transcribe", return_value="ahoj") as transcribe:
            out = bridge._transcribe({"file_id": "telegram-file"}, 123)

        self.assertEqual(out, "ahoj")
        transcribe.assert_called_once_with(
            b"audio", api_key="key", filename="voice.ogg", language_code="sk"
        )


if __name__ == "__main__":
    unittest.main()
