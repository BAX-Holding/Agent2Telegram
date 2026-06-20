"""Adapter for OpenAI's Codex CLI (``codex``).

Uses the non-interactive subcommand: ``codex exec "<prompt>"``. Continuity is handled by
running each chat in its own working directory; pass ``--last`` (resume last session) on
follow-ups where supported. Both commands are overridable in config if your Codex build
uses different flags.

Install / auth: https://github.com/openai/codex  (run ``codex`` once to sign in).
"""
from __future__ import annotations

from .base import Adapter


class CodexAdapter(Adapter):
    name = "codex"
    label = "Codex"
    binary = "codex"
    # Interactive TUI for attach mode: bypass per-command approval/sandbox prompts so the bridge
    # can drive it unattended from Telegram (only allow-listed users reach it). Without this flag
    # Codex would block on an approval prompt nobody can answer from the chat.
    tui_command = ["codex", "--dangerously-bypass-approvals-and-sandbox"]
    default_command = ["codex", "exec", "{prompt}"]
    # `resume` is a subcommand of `codex exec`; `--last` picks the most recent session.
    # (Verified against `codex exec --help`.)
    continue_command = ["codex", "exec", "resume", "--last", "{prompt}"]
