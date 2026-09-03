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
    def _bridge(self, agent: str, session: str) -> Any:
        bridge: Any = object.__new__(AttachBridge)
        bridge.cfg = types.SimpleNamespace(
            agent=agent,
            tmux_session=session,
            elevenlabs_api_key="",
        )
        bridge.tg = _FakeTelegram()
        bridge._session = _FakeSession()
        return bridge

    def test_reset_sends_unprefixed_clear_to_claude(self):
        bridge = self._bridge("claude-code", "Claudia")
        handled = bridge._handle_command("/reset", 123)
        self.assertTrue(handled)
        self.assertEqual(bridge._session.raw, ["/clear"])
        self.assertTrue(any("fresh" in text.lower() for _, text in bridge.tg.sent))

    def test_reset_sends_unprefixed_new_to_codex(self):
        bridge = self._bridge("codex", "meta - Master")
        handled = bridge._handle_command("/reset", 123)
        self.assertTrue(handled)
        self.assertEqual(bridge._session.raw, ["/new"])
        self.assertTrue(any("fresh" in text.lower() for _, text in bridge.tg.sent))

    def test_inject_raw_does_not_add_origin_prefix_and_checks_pane_owner(self):
        session: Any = object.__new__(TmuxSession)
        session.name = "Claudia"
        session._origin = "[TG] "
        session._expected_agent_commands = ("claude",)
        with patch.object(TmuxSession, "alive", new_callable=PropertyMock, return_value=True), \
             patch.object(TmuxSession, "_pane_ok", return_value=(True, "agent present")) as pane_ok, \
             patch("agent2telegram.session._tmux") as tmux:
            session.inject_raw("/clear")
        pane_ok.assert_called_once_with()
        literal_calls = [call for call in tmux.call_args_list if "-l" in call.args]
        self.assertEqual(len(literal_calls), 1)
        self.assertEqual(literal_calls[0].args[-1], "/clear")


if __name__ == "__main__":
    unittest.main()
