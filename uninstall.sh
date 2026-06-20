#!/usr/bin/env bash
# Agent2Telegram one-command uninstaller — the mirror of install.sh.
# Usage:  curl -fsSL <raw-url>/uninstall.sh | bash
# Stops any running bridge and removes config, state, the source clone and the pip package.
set -euo pipefail

# Recover the working directory if it was deleted out from under us.
cd "$PWD" 2>/dev/null || cd "$HOME" 2>/dev/null || cd /

say() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }

PY="$(command -v python3 || command -v python || true)"

# Find a way to run the package's own `uninstall` (it does all the heavy lifting):
#   1) installed on PATH (pip), or 2) the source clone we created at install time.
run_uninstall() {
  [ -n "$PY" ] || return 1
  if "$PY" -m agent2telegram --version >/dev/null 2>&1; then
    "$PY" -m agent2telegram uninstall --yes; return 0
  fi
  if [ -d "$HOME/.agent2telegram-src/agent2telegram" ]; then
    env "PYTHONPATH=$HOME/.agent2telegram-src" "$PY" -m agent2telegram uninstall --yes; return 0
  fi
  return 1
}

if run_uninstall; then
  exit 0
fi

# Fallback: the package is already gone but leftovers may remain — clean them by hand.
say "Package not found — removing leftover files directly."
pkill -f "agent2telegram run" 2>/dev/null || true
command -v tmux >/dev/null 2>&1 && tmux kill-session -t a2t-bridge 2>/dev/null || true
for d in "$HOME/.config/agent2telegram" \
         "$HOME/.local/state/agent2telegram" \
         "$HOME/.agent2telegram-src" \
         "$HOME/start-a2t-bridge.sh"; do
  if [ -e "$d" ]; then rm -rf "$d" && say "removed $d"; fi
done
say "Done. (If you installed via pip earlier, run: $PY -m pip uninstall -y agent2telegram)"
