# Fish Shell Configuration
# Migrated from .zshrc

if status is-interactive
    # ================================
    # PATH Settings
    # ================================
    fish_add_path $HOME/.local/bin
    fish_add_path $HOME/.rbenv/bin
    fish_add_path $HOME/.cargo/bin
    fish_add_path $HOME/.pyenv/shims
    fish_add_path $HOME/.antigravity/antigravity/bin
    fish_add_path $HOME/workspace/Claude-Code-Communication
    fish_add_path /opt/homebrew/bin
    fish_add_path /opt/homebrew/opt/openssl@1.1/bin
    fish_add_path /opt/homebrew/opt/libpq/bin
    fish_add_path (npm prefix -g)/bin

    # ================================
    # Environment Variables
    # ================================
    # Go
    set -gx GOPATH $HOME
    set -gx GOENV_ROOT $HOME/.goenv
    fish_add_path $GOPATH/bin

    # Build flags
    set -gx LDFLAGS "-L/opt/homebrew/opt/libffi/lib"
    set -gx CPPFLAGS "-I/opt/homebrew/opt/libffi/include"

    # ================================
    # Tool Initializations
    # ================================
    # rbenv
    if type -q rbenv
        status --is-interactive; and rbenv init - fish | source
    end

    # pyenv
    if type -q pyenv
        pyenv init - | source
    end

    # goenv
    if type -q goenv
        status --is-interactive; and goenv init - fish | source
    end

    # direnv
    if type -q direnv
        direnv hook fish | source
    end

    # starship prompt
    if type -q starship
        starship init fish | source
    end

    # zoxide (smart cd)
    if type -q zoxide
        zoxide init fish | source
    end

    # fzf.fish keybindings (avoid Ctrl+Alt combos that conflict with cmux)
    #   Ctrl+R  = history (default, kept)
    #   Ctrl+F  = file search
    #   Ctrl+G  = git log
    #   Ctrl+S  = git status
    fzf_configure_bindings --directory=\cf --git_log=\cg --git_status=\cs

    # anyenv (if installed and supports fish)
    if test -d $HOME/.anyenv
        fish_add_path $HOME/.anyenv/bin
        if type -q anyenv
            status --is-interactive; and source (anyenv init - fish | psub)
        end
    end

    # ================================
    # Abbreviations (better than aliases in fish)
    # ================================
    # Modern CLI replacements
    if type -q eza
        abbr -a ls 'eza --icons'
        abbr -a ll 'eza -la --icons --git'
        abbr -a lt 'eza --tree --level=2 --icons'
        abbr -a tree 'eza --tree --icons'
    end

    if type -q bat
        abbr -a cat 'bat --style=plain'
    end

    abbr -a lg lazygit
    abbr -a y yazi

    # Git
    abbr -a git 'git --no-pager'
    abbr -a gits 'git sta'
    abbr -a gitci 'git ci'
    abbr -a gitco 'git co'
    abbr -a gitbr 'git br'
    abbr -a gitd 'git diff'
    abbr -a gitdh 'git diff HEAD^'
    abbr -a gitdd 'git diff develop'
    abbr -a gitad 'git add'
    abbr -a gitla 'git loga'
    abbr -a gitp 'git pull --rebase'
    abbr -a gitcim 'git ci -am'
    abbr -a gitps 'git push'
    abbr -a gitrs 'git reset --soft HEAD^'
    abbr -a gitsu 'git submodule update --init --recursive'
    abbr -a gitsta 'git stash'
    abbr -a gitstap 'git stash pop'

    # Docker
    abbr -a dc 'docker compose'

    # ================================
    # CIPHER Settings
    # ================================
    set -gx CIPHER_LOG_LEVEL info
    set -gx REDACT_SECRETS true
    set -gx MCP_SERVER_MODE aggregator
    set -gx CIPHER_API_PREFIX /api
    set -gx API_PORT 3001

    # Vector Store (Qdrant)
    set -gx VECTOR_STORE_TYPE qdrant
    set -gx VECTOR_STORE_URL http://localhost:6333
    set -gx VECTOR_STORE_COLLECTION knowledge_memory
    set -gx VECTOR_STORE_DIMENSION 1536
    set -gx VECTOR_STORE_DISTANCE Cosine
    set -gx REFLECTION_VECTOR_STORE_COLLECTION reflection_memory
    set -gx DISABLE_REFLECTION_MEMORY true

    # PostgreSQL
    set -gx CIPHER_PG_URL postgresql://cipher:cipher@localhost:5433/cipher_db
    set -gx STORAGE_DATABASE_TYPE postgres

    # ================================
    # API Keys - Use direnv instead!
    # ================================
    # SECURITY WARNING: API keys should NOT be in shell config.
    # Use direnv with .envrc files per project instead.
    #
    # Create ~/.envrc or project-specific .envrc:
    #   export GITHUB_TOKEN=xxx
    #   export OPENAI_API_KEY=xxx
    #   export GEMINI_API_KEY=xxx
    # Then run: direnv allow

    # Codex alias
    abbr -a codex 'CODEX_HOME=$PWD/.codex codex'

    # Disable MallocStackLogging
    set -e MallocStackLogging
end

# bun
set --export BUN_INSTALL "$HOME/.bun"
set --export PATH $BUN_INSTALL/bin $PATH

# The next line updates PATH for the Google Cloud SDK.
if [ -f '/Users/nakahiro/workspace/discord_translator/google-cloud-sdk/path.fish.inc' ]; . '/Users/nakahiro/workspace/discord_translator/google-cloud-sdk/path.fish.inc'; end
