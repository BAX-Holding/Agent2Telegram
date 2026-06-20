"""Unit tests for the Codex TUI scraper (`_extract_tui_tools`).

Codex's live tool bubbles are produced by scraping the tmux pane (its rollout logs tools only
at completion). This parser is therefore the fragile, regression-prone part — so it gets pinned
here with fixtures captured from the real Codex TUI. Both bugs found on 2026-06-20 are covered:

  * system calls on the bullet line ("● Ran df -h /") must produce a bubble — they were missed
    when the parser only looked at nested "└" lines;
  * a stale line still visible in the pane from a previous turn must NOT be re-emitted — the
    per-turn dedup is seeded with what's already on screen.

Pure function, no tmux/network — runs in milliseconds in CI, so the behavior Petr used to verify
by hand in Telegram is now checked automatically.
"""
from agent2telegram.attach import _extract_tui_tools

# A real Codex TUI capture: agent text on bullet lines, a command on a bullet line with its
# output nested under "└", a file read, and trailing UI chrome.
PANE_DISK = """\
  [TG] Kolik máme místa na disku?
● Ověřím aktuální volné místo na hlavním oddílu.
● Ran df -h /
  └ Filesystem      Size  Used Avail Use% Mounted on
    /dev/sda1        48G  2.3G   46G   5% /
● Read /etc/hosts
● Na hlavním disku / je volno 46 GB z celkových 48 GB.
> 0;10;1c
  gpt-5.5 default · ~
"""

PANE_WEB = """\
● Ověřím to z webu, protože výška veřejné osoby bývá často špatně opsaná.
● Searching the web
● Searched the web for Warhorse Studios Daniel Vávra bio official
● Nenašel jsem spolehlivě doložený údaj o výšce.
"""


def test_system_call_on_bullet_line():
    """`● Ran df -h /` must surface as a bubble (the 2026-06-20 bullet-line bug)."""
    out = _extract_tui_tools(PANE_DISK)
    assert "🛠️ Ran df -h /" in out


def test_file_read_bullet_line():
    out = _extract_tui_tools(PANE_DISK)
    assert "📄 Read /etc/hosts" in out


def test_command_output_is_not_a_bubble():
    """The nested `└ Filesystem …` output line is not a tool call — no bubble for it."""
    out = _extract_tui_tools(PANE_DISK)
    assert not any("Filesystem" in s for s in out)
    assert not any("/dev/sda1" in s for s in out)


def test_agent_text_is_not_a_bubble():
    """Plain agent prose on a bullet line (Czech, not a known verb) must be ignored."""
    out = _extract_tui_tools(PANE_DISK)
    assert not any("Ověřím" in s for s in out)
    assert not any("volno" in s for s in out)


def test_web_search_query_extracted():
    out = _extract_tui_tools(PANE_WEB)
    assert any(s.startswith("🔎 Web search:") and "Warhorse" in s for s in out)


def test_web_search_in_progress():
    out = _extract_tui_tools("● Searching the web")
    assert out == ["🔎 Searching the web"]


def test_stale_lines_not_reemitted():
    """Re-extraction of a pane that still shows a previous turn's tool line yields nothing new
    once the per-turn dedup is seeded with what's already on screen (the stale-bubble bug)."""
    seen = set(_extract_tui_tools(PANE_DISK))      # seed at turn start, as _handle() does
    fresh = [s for s in _extract_tui_tools(PANE_DISK) if s not in seen]
    assert fresh == []                              # nothing re-sent under the new turn


def test_new_call_after_seed_is_emitted():
    """A genuinely new tool line appearing during the turn still fires."""
    seen = set(_extract_tui_tools(PANE_DISK))
    later = PANE_DISK + "● Ran echo hello\n"
    fresh = [s for s in _extract_tui_tools(later) if s not in seen]
    assert fresh == ["🛠️ Ran echo hello"]


def test_empty_pane():
    assert _extract_tui_tools("") == []
