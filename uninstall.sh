#!/bin/bash
#
# dotfiles uninstaller — removes symlinks created by install.sh
# Usage: uninstall.sh [--dry-run]
#

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"
DRY_RUN=false

log()  { printf '\033[0;34m[INFO]\033[0m  %s\n' "$1"; }
warn() { printf '\033[0;33m[WARN]\033[0m  %s\n' "$1"; }
ok()   { printf '\033[0;32m[ OK ]\033[0m  %s\n' "$1"; }
skip() { printf '\033[0;90m[SKIP]\033[0m  %s\n' "$1"; }

# Remove a symlink only if it points back to our dotfiles
unlink_file() {
  local dst="$1"

  if [ ! -L "$dst" ]; then
    skip "$dst (not a symlink)"
    return
  fi

  local target
  target="$(readlink "$dst")"

  # Only remove if it points into our dotfiles dir
  case "$target" in
    "$DOTFILES_DIR"*)
      if $DRY_RUN; then
        log "[DRY-RUN] rm $dst (→ $target)"
      else
        rm "$dst"
        ok "Removed: $dst"
      fi
      ;;
    *)
      skip "$dst (points to $target, not our dotfiles)"
      ;;
  esac
}

main() {
  for arg in "$@"; do
    case "$arg" in
      --dry-run) DRY_RUN=true ;;
      *) warn "Unknown option: $arg" ;;
    esac
  done

  if $DRY_RUN; then
    log "========================================="
    log "  DRY RUN — no changes will be made"
    log "========================================="
  fi

  echo ""
  log "=== Git ==="
  unlink_file "$HOME/.gitconfig"
  unlink_file "$HOME/.gitignore"

  echo ""
  log "=== Zsh ==="
  unlink_file "$HOME/.zshrc"
  unlink_file "$HOME/.aliases"
  unlink_file "$HOME/.bash_profile"
  unlink_file "$HOME/.oh-my-zsh"
  unlink_file "$HOME/.zsh"

  echo ""
  log "=== Fish shell ==="
  unlink_file "$HOME/.config/starship.toml"
  unlink_file "$HOME/.config/fish/config.fish"
  unlink_file "$HOME/.config/fish/fish_plugins"
  for f in "$DOTFILES_DIR/fish/functions/"*.fish 2>/dev/null; do
    [ -f "$f" ] && unlink_file "$HOME/.config/fish/functions/$(basename "$f")"
  done
  for f in "$DOTFILES_DIR/fish/completions/"*.fish 2>/dev/null; do
    [ -f "$f" ] && unlink_file "$HOME/.config/fish/completions/$(basename "$f")"
  done

  echo ""
  log "=== Claude Code ==="
  unlink_file "$HOME/.claude/CLAUDE.md"
  unlink_file "$HOME/.claude/settings.json"
  unlink_file "$HOME/.claude/rules"
  unlink_file "$HOME/.claude/skills"
  unlink_file "$HOME/.claude/commands"

  echo ""
  log "=== mise ==="
  unlink_file "$HOME/.config/mise/config.toml"

  echo ""
  log "=== cool-peco ==="
  unlink_file "$HOME/cool-peco"

  echo ""
  if $DRY_RUN; then
    log "Dry run complete. Re-run without --dry-run to apply."
  else
    ok "All symlinks removed."
  fi
}

main "$@"
