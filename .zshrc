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


# cdr
# $HOME/.cache/chpwd-recent-dirs ファイルが存在しなければ作成
[[ ! -d "$HOME/.cache" ]] && mkdir "$HOME/.cache"
[[ ! -f "$HOME/.cache/chpwd-recent-dirs" ]] && touch "$HOME/.cache/chpwd-recent-dirs"

if [[ -n $(echo ${^fpath}/chpwd_recent_dirs(N)) && -n $(echo ${^fpath}/cdr(N)) ]]; then
    autoload -Uz chpwd_recent_dirs cdr add-zsh-hook
    add-zsh-hook chpwd chpwd_recent_dirs
    zstyle ':completion:*' recent-dirs-insert both
    zstyle ':chpwd:*' recent-dirs-default true
    zstyle ':chpwd:*' recent-dirs-max 1000
    zstyle ':chpwd:*' recent-dirs-file "$HOME/.cache/chpwd-recent-dirs"
fi

function peco-get-destination-from-cdr() {
  cdr -l | \
  sed -e 's/^[[:digit:]]*[[:blank:]]*//' | \
  peco --query "$LBUFFER"
}

function peco-cdr() {
  local destination="$(peco-get-destination-from-cdr)"
  if [ -n "$destination" ]; then
    BUFFER="cd $destination"
    zle accept-line
  else
    zle reset-prompt
  fi
}
zle -N peco-cdr
bindkey '^W' peco-cdr

eval "$(direnv hook zsh)"

source $HOME/.aliases 