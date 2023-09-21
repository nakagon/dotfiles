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
  if [ ! -d "${HOME}/.oh-my-zsh" ]; then
    curl -L https://github.com/robbyrussell/oh-my-zsh/raw/master/tools/install.sh | sh
  fi
  if is_mac; then
    brew install peco lv
  elif is_ubuntu; then
    apt update
    apt install peco lv
  else
    apt update
    apt install peco lv
  fi
}

backup () {
  [[ ! -d "$backup_dir" ]] && mkdir -p "$backup_dir"
  
  for file in "${dotfiles_path}"/.*; do
    [[ $(basename "$file") == "." || $(basename "$file") == ".." ]] && continue
    if [[ -f "${HOME}/$(basename "$file")" ]]; then
      mv "${HOME}/$(basename "$file")" "$backup_dir/"
    fi
  done
}

install() {
  for file in "${dotfiles_path}"/.*; do
    [[ $(basename "$file") == "." || $(basename "$file") == ".." || $(basename "$file") == ".git" ]] && continue
    cp -r "${file}" "${HOME}/"
  done
  source "${HOME}/.bash_profile"
}

main() {
  local -r dotfiles_path="$(realpath "${1:-"${HOME}/dotfiles"}")"
  local -r backup_dir="${HOME}/backups/$(date +%Y%m%d)"

  if [[ $dotfiles_path == "" ]]; then 
    echo "dotfiles path is empty"
    return 0
  fi

  download
  backup
  install
}

main "$@"