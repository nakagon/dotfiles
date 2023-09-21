# history
HISTFILE=$HOME/.zsh_history
HISTSIZE=100000
SAVEHIST=1000000

# share .zshhistory
setopt inc_append_history
setopt share_history

export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="codespaces"

plugins=(git)
source $ZSH/oh-my-zsh.sh

# cool-peco
# === cool-peco init ===
FPATH="$FPATH:$HOME/dotfiles/cool-peco"
autoload -Uz cool-peco
cool-peco
# ======================
bindkey '^r' cool-peco-history
bindkey '^h' cool-peco-ssh
bindkey '^p' cool-peco-ps
bindkey '^f' cool-peco-filename-search
alias cps=cool-peco-ps
alias gitc=cool-peco-git-checkout
alias gitl=cool-peco-git-log
alias pecoref="cat ~/.zshrc | grep -i cool-peco"

eval "$(direnv hook zsh)"
