#!/bin/bash
#
# dotfiles installer — symlink-based
# Usage: install.sh [--dry-run]
#

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$HOME/.dotfiles-backup/$(date +%Y%m%d)"
DRY_RUN=false

# ================================
# Helpers
# ================================

is_mac() { [ "$(uname)" = 'Darwin' ]; }

log()  { printf '\033[0;34m[INFO]\033[0m  %s\n' "$1"; }
warn() { printf '\033[0;33m[WARN]\033[0m  %s\n' "$1"; }
ok()   { printf '\033[0;32m[ OK ]\033[0m  %s\n' "$1"; }
skip() { printf '\033[0;90m[SKIP]\033[0m  %s\n' "$1"; }

# Create a symlink: link_file <source> <target>
link_file() {
  local src="$1"
  local dst="$2"

  if [ ! -e "$src" ]; then
    warn "Source does not exist: $src"
    return
  fi

  if $DRY_RUN; then
    if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
      skip "$dst → $src (already linked)"
    elif [ -e "$dst" ]; then
      log "[DRY-RUN] backup $dst → $BACKUP_DIR/"
      log "[DRY-RUN] ln -sf $src $dst"
    else
      log "[DRY-RUN] ln -sf $src $dst"
    fi
    return
  fi

  # Already correct symlink
  if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
    skip "$dst (already linked)"
    return
  fi

  # Backup existing file/dir
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    mkdir -p "$BACKUP_DIR"
    mv "$dst" "$BACKUP_DIR/"
    warn "Backed up: $dst → $BACKUP_DIR/$(basename "$dst")"
  fi

  # Ensure parent directory exists
  mkdir -p "$(dirname "$dst")"

  ln -sf "$src" "$dst"
  ok "$dst → $src"
}

# ================================
# Install sections
# ================================

install_git() {
  log "=== Git ==="
  link_file "$DOTFILES_DIR/git/.gitconfig"      "$HOME/.gitconfig"
  link_file "$DOTFILES_DIR/git/.gitignore_global" "$HOME/.gitignore"
}

install_zsh() {
  log "=== Zsh (legacy) ==="
  link_file "$DOTFILES_DIR/zsh/.zshrc"        "$HOME/.zshrc"
  link_file "$DOTFILES_DIR/zsh/.aliases"      "$HOME/.aliases"
  link_file "$DOTFILES_DIR/zsh/.bash_profile" "$HOME/.bash_profile"

  # oh-my-zsh custom dir
  if [ -d "$DOTFILES_DIR/.oh-my-zsh" ]; then
    link_file "$DOTFILES_DIR/.oh-my-zsh" "$HOME/.oh-my-zsh"
  fi

  # .zsh dir (git completions etc.)
  if [ -d "$DOTFILES_DIR/.zsh" ]; then
    link_file "$DOTFILES_DIR/.zsh" "$HOME/.zsh"
  fi
}

install_fish() {
  log "=== Fish shell ==="
  local fish_config="$HOME/.config/fish"
  mkdir -p "$fish_config"

  link_file "$DOTFILES_DIR/fish/config.fish" "$fish_config/config.fish"

  # Starship config
  if [ -f "$DOTFILES_DIR/starship.toml" ]; then
    link_file "$DOTFILES_DIR/starship.toml" "$HOME/.config/starship.toml"
  fi

  # Functions
  if [ -d "$DOTFILES_DIR/fish/functions" ]; then
    mkdir -p "$fish_config/functions"
    for f in "$DOTFILES_DIR/fish/functions/"*.fish; do
      [ -f "$f" ] && link_file "$f" "$fish_config/functions/$(basename "$f")"
    done
  fi

  # Completions
  if [ -d "$DOTFILES_DIR/fish/completions" ]; then
    mkdir -p "$fish_config/completions"
    for f in "$DOTFILES_DIR/fish/completions/"*.fish; do
      [ -f "$f" ] && link_file "$f" "$fish_config/completions/$(basename "$f")"
    done
  fi

  # conf.d — only link user-managed files (skip fig auto-generated)
  if [ -d "$DOTFILES_DIR/fish/conf.d" ] && [ -n "$(ls -A "$DOTFILES_DIR/fish/conf.d/" 2>/dev/null)" ]; then
    mkdir -p "$fish_config/conf.d"
    for f in "$DOTFILES_DIR/fish/conf.d/"*.fish; do
      [ -f "$f" ] && link_file "$f" "$fish_config/conf.d/$(basename "$f")"
    done
  fi

  # Fisher plugin list
  if [ -f "$DOTFILES_DIR/fish/fish_plugins" ]; then
    link_file "$DOTFILES_DIR/fish/fish_plugins" "$fish_config/fish_plugins"
    # Install plugins if fisher is available
    if ! $DRY_RUN && command -v fish >/dev/null 2>&1; then
      if fish -c 'type -q fisher' 2>/dev/null; then
        log "Restoring Fisher plugins..."
        fish -c 'fisher update' 2>/dev/null && ok "Fisher plugins restored" || warn "Fisher plugin restore failed (run 'fisher update' manually)"
      else
        warn "Fisher not installed. Run: curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source && fisher install jorgebucaran/fisher && fisher update"
      fi
    fi
  fi
}

install_claude() {
  log "=== Claude Code ==="
  local claude_dir="$HOME/.claude"
  mkdir -p "$claude_dir"

  # Individual files
  link_file "$DOTFILES_DIR/claude/CLAUDE.md"      "$claude_dir/CLAUDE.md"
  link_file "$DOTFILES_DIR/claude/settings.json"  "$claude_dir/settings.json"

  # Directory symlinks
  link_file "$DOTFILES_DIR/claude/rules"    "$claude_dir/rules"
  link_file "$DOTFILES_DIR/claude/skills"   "$claude_dir/skills"
  link_file "$DOTFILES_DIR/claude/commands" "$claude_dir/commands"
}

install_cool_peco() {
  log "=== cool-peco ==="
  # Init submodule
  if ! $DRY_RUN; then
    (cd "$DOTFILES_DIR" && git submodule update --init --recursive 2>/dev/null || true)
  fi
  if [ -d "$DOTFILES_DIR/.cool-peco" ]; then
    link_file "$DOTFILES_DIR/.cool-peco" "$HOME/cool-peco"
  fi
}

# ================================
# Main
# ================================

main() {
  # Parse args
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

  log "Dotfiles: $DOTFILES_DIR"
  log "Backup:   $BACKUP_DIR"
  echo ""

  install_git
  echo ""
  install_zsh
  echo ""
  install_fish
  echo ""
  install_claude
  echo ""
  install_cool_peco

  echo ""
  if $DRY_RUN; then
    log "Dry run complete. Re-run without --dry-run to apply."
  else
    ok "All done!"
  fi
}

main "$@"
