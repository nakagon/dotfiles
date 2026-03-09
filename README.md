# dotfiles

macOS 向けの開発環境設定。シンボリックリンクで管理。

## セットアップ

```bash
git clone https://github.com/nakagon/dotfiles.git ~/dotfiles
cd ~/dotfiles

# 確認（変更なし）
./install.sh --dry-run

# 実行
./install.sh
```

既存ファイルは `~/.dotfiles-backup/YYYYMMDD/` に自動退避される。

## アンインストール

```bash
./uninstall.sh          # シンボリックリンクのみ削除
./uninstall.sh --dry-run  # 確認
```

## 構成

```
dotfiles/
├── fish/                 # Fish shell
│   ├── config.fish       #   メイン設定
│   ├── fish_plugins      #   Fisher プラグインリスト
│   ├── functions/        #   カスタム関数 (ccmux)
│   └── completions/      #   補完定義 (bun)
├── claude/               # Claude Code
│   ├── CLAUDE.md         #   グローバル指示
│   ├── settings.json     #   設定 + MCP サーバー
│   ├── rules/            #   カスタムルール
│   ├── skills/           #   インストール済みスキル
│   └── commands/         #   カスタムコマンド
├── git/
│   ├── .gitconfig        #   Git 設定 (delta, エイリアス)
│   └── .gitignore_global #   グローバル gitignore
├── mise/
│   └── config.toml       #   ランタイムバージョン管理
├── zsh/                  # Zsh (レガシー)
│   ├── .zshrc
│   ├── .aliases
│   └── .bash_profile
├── starship.toml         # Starship プロンプト設定
├── install.sh            # シンボリックリンク作成
└── uninstall.sh          # リンク解除
```

## 主要ツール

| ツール | 用途 | 設定場所 |
|--------|------|----------|
| [fish](https://fishshell.com/) | メインシェル | `fish/config.fish` |
| [mise](https://mise.jdx.dev/) | ランタイム管理 (Python, Node, Ruby, Go, Bun) | `mise/config.toml` |
| [starship](https://starship.rs/) | プロンプト | `starship.toml` |
| [fzf](https://github.com/junegunn/fzf) | ファジーファインダー | Fisher plugin |
| [zoxide](https://github.com/ajeetdsouza/zoxide) | スマート cd | `config.fish` |
| [delta](https://github.com/dandavison/delta) | Git diff ビューア | `git/.gitconfig` |
| [eza](https://github.com/eza-community/eza) | ls 代替 | `config.fish` abbr |
| [bat](https://github.com/sharkdp/bat) | cat 代替 | `config.fish` abbr |
| [lazygit](https://github.com/jesseduffield/lazygit) | Git TUI | `lg` |
| [yazi](https://github.com/sxyazi/yazi) | ファイラー TUI | `y` |
| [lazytail](https://github.com/raaymax/lazytail) | ログビューア | MCP 連携 |
| [difit](https://github.com/nicolo-ribaudo/difit) | コードレビュー diff ビューア | `difit` abbr |
| [codex](https://github.com/openai/codex) | OpenAI Codex CLI | `codex` abbr |

## Fish キーバインド

| キー | 操作 |
|------|------|
| `Ctrl+R` | 履歴検索 (fzf) |
| `Ctrl+F` | ファイル検索 (fzf) |
| `Ctrl+G` | Git log (fzf) |
| `Ctrl+S` | Git status (fzf) |
| `z <keyword>` | ディレクトリジャンプ (zoxide) |

## mise でバージョン管理

```bash
# グローバルデフォルト確認
mise list

# プロジェクト別バージョン（.ruby-version 等を自動認識）
cd ~/project && ruby --version  # .ruby-version があれば自動切替

# 手動でバージョン追加
mise install ruby@3.3.1
mise use ruby@3.3.1  # カレントディレクトリに .mise.toml 作成
```
