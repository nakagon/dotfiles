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
    brew install peco lv goenv
  elif is_ubuntu; then
    apt-get update
    apt-get install -y peco lv
    git clone https://github.com/syndbg/goenv.git ~/.goenv
  else
    apt-get update
    apt-get install -y peco lv
    git clone https://github.com/syndbg/goenv.git ~/.goenv
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
  # add submodule
  git submodule update --init --recursive

  for file in "${dotfiles_path}"/.*; do
    [[ $(basename "$file") == "." || $(basename "$file") == ".." || $(basename "$file") == ".git" ]] && continue
    cp -r "${file}" "${HOME}/"
  done
  mv ${HOME}/.cool-peco ${HOME}/cool-peco
  source "${HOME}/.bash_profile"
}

main() {
  if [[ -d "/workspaces/.codespaces/.persistedshare/" ]]; then
    # Codespacesの場合
    dotfiles_path="/workspaces/.codespaces/.persistedshare/dotfiles"
  else
    dotfiles_path="${HOME}/dotfiles"
  fi
  local -r dotfiles_path="$(realpath "${1:-"$dotfiles_path"}")"
  local -r backup_dir="${HOME}/backups/$(date +%Y%m%d)"

  if [[ $dotfiles_path == "" ]]; then 
    echo "dotfiles path is empty"
    return 0
  fi

  download
  backup
  install

  #change shell
  # chsh -s $(which gizsh)
}

main "$@"