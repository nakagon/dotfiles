# history
HISTFILE=$HOME/.zsh_history
HISTSIZE=100000
SAVEHIST=1000000

# share .zshhistory
setopt inc_append_history
setopt share_history

# prompt (minimal, no oh-my-zsh dependency)
autoload -Uz compinit && compinit
PS1='%n@%m %1~ %# '

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

# direnv
if command -v direnv &>/dev/null; then
    eval "$(direnv hook zsh)"
fi

# mise (if available, replaces rbenv/goenv/pyenv)
if command -v mise &>/dev/null; then
    eval "$(mise activate zsh)"
fi

# AUTOLOAD
autoload -U zcalc
autoload -Uz zmv

source $HOME/.aliases

DISABLE_AUTO_UPDATE=true
DISABLE_UPDATE_PROMPT=true
