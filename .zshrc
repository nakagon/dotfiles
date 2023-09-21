# history
HISTFILE=$HOME/.zsh_history
HISTSIZE=100000
SAVEHIST=1000000

# share .zshhistory
setopt inc_append_history
setopt share_history


function peco-history-selection() {
  BUFFER=$(\history -n -r 1 | peco --query "$LBUFFER")
  CURSOR=$#BUFFER
  zle clear-screen
}

zle -N peco-history-selection
bindkey '^R' peco-history-selection

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
bindkey '^E' peco-cdr