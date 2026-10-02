#!/usr/bin/env bash
# Terminal init: load user .bashrc then ensure the HA-UV environment is ready
# Referenced by .vscode/settings.json → terminal.integrated.profiles.linux

# 1. Load your standard aliases and paths
[[ -f "$HOME/.bashrc" ]] && source "$HOME/.bashrc"

# 2. Ensure uv is in the path (standard 2026 installation path)
export PATH="$HOME/.local/bin:$PATH"

# 3. Activate the repository-local .venv environment if available
if [[ -d "${PWD}/.venv" ]]; then
    source "${PWD}/.venv/bin/activate"
elif [[ -d "/home/lucian/HA-UV" ]]; then
    source /home/lucian/HA-UV/bin/activate
else
    echo "⚠️ Warning: no repository venv found at ${PWD}/.venv. Run 'uv venv .venv' or restore HA-UV."
fi
