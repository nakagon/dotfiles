#!/bin/bash

set -Ceuxo pipefail

is_mac() {
  [ "$(uname)" == 'Darwin' ]
}

is_linux() {
  [ "$(expr substr $(uname -s) 1 5)" == 'Linux' ]
}

is_ubuntu() {
  grep '^NAME="Ubuntu' /etc/os-release >/dev/null 2>&1
}

download() {
  if is_mac; then
    brew install peco
  elif is_ubuntu; then
    apt install peco
  fi
}

install() {
  # ln -sf ~/dotfiles/.zshrc ~/.zshrc
}

main() {
  local -r dotfiles_path="$(realpath "${1:-"${HOME}/dotfiles"}")"

  echo ${dotfiles_path}
  download
  install
}

main @*