# ccmux — tmux for Claude Code (fish version)
#
# Worktree lifecycle manager for parallel Claude Code sessions.
# Each agent gets its own worktree — no conflicts, one command each.
#
# Fish-native port of https://github.com/craigsc/cmux

set -g _CCMUX_DOWNLOAD_URL "https://github.com/craigsc/cmux/releases/latest/download"
set -g CCMUX_VERSION "unknown"
if test -f "$HOME/.cmux/VERSION"
    set -g CCMUX_VERSION (string trim < "$HOME/.cmux/VERSION")
end

function ccmux -d "Worktree lifecycle manager for parallel Claude Code sessions"
    set -l cmd $argv[1]
    set -e argv[1]

    _ccmux_check_update

    switch "$cmd"
        case new
            _ccmux_new $argv
        case start
            _ccmux_start $argv
        case cd
            _ccmux_cd $argv
        case ls
            _ccmux_ls $argv
        case merge
            _ccmux_merge $argv
        case rm
            _ccmux_rm $argv
        case init
            _ccmux_init $argv
        case update
            _ccmux_update $argv
        case version
            echo "ccmux $CCMUX_VERSION"
        case --help -h ''
            echo "Usage: ccmux <new|start|cd|ls|merge|rm|init|update> [branch]"
            echo ""
            echo "  new <branch>     New worktree + branch, run setup hook, launch Claude"
            echo "  start <branch>   Continue where you left off in an existing worktree"
            echo "  cd [branch]      cd into worktree (no args = repo root)"
            echo "  ls               List worktrees"
            echo "  merge [branch]   Merge worktree branch into primary checkout"
            echo "  rm [branch]      Remove worktree + branch (no args = current, -f to force)"
            echo "  rm --all         Remove ALL worktrees (requires confirmation)"
            echo "  init [--replace] Generate .cmux/setup hook using Claude"
            echo "  update           Update ccmux to the latest version"
            echo "  version          Show current version"
        case '*'
            echo "Unknown command: $cmd"
            echo "Run 'ccmux --help' for usage."
            return 1
    end
end

# ── Helpers ──────────────────────────────────────────────────────────

function _ccmux_repo_root
    set -l git_common_dir (git rev-parse --git-common-dir 2>/dev/null)
    or return 1
    echo (builtin cd (dirname "$git_common_dir") && pwd)
end

function _ccmux_safe_name
    string replace -a '/' '-' -- $argv[1]
end

function _ccmux_worktree_dir
    set -l repo_root $argv[1]
    set -l safe_name (_ccmux_safe_name $argv[2])
    echo "$repo_root/.worktrees/$safe_name"
end

function _ccmux_check_update
    set -l cache_dir "$HOME/.cmux"
    set -l version_file "$cache_dir/.latest_version"
    set -l check_file "$cache_dir/.last_check"

    # Show notice if a newer version is known
    if test -f "$version_file"
        set -l latest (string trim < "$version_file")
        if test -n "$latest"; and test "$latest" != "$CCMUX_VERSION"
            printf 'ccmux: update available (%s → %s). Run "ccmux update" to upgrade.\n' \
                "$CCMUX_VERSION" "$latest"
        end
    end

    # Throttle: check at most once per day (86400 seconds)
    set -l now (date +%s)
    if test -f "$check_file"
        set -l last_check (string trim < "$check_file")
        if test (math "$now - $last_check") -lt 86400
            return
        end
    end

    # Background fetch
    fish -c "
        set -l v (curl -fsSL '$_CCMUX_DOWNLOAD_URL/VERSION' 2>/dev/null | string trim)
        if test -n \"\$v\"
            printf '%s' \$v > '$version_file'
        end
        printf '%s' '$now' > '$check_file'
    " &
    disown 2>/dev/null
end

# ── Subcommands ──────────────────────────────────────────────────────

function _ccmux_new
    if test "$argv[1]" = --help; or test "$argv[1]" = -h
        echo "Usage: ccmux new <branch>"
        echo ""
        echo "  Create a new worktree and branch, run setup hook, and launch Claude Code."
        return 0
    end
    if test (count $argv) -eq 0
        echo "Usage: ccmux new <branch>"
        return 1
    end

    set -l branch (string join '-' -- $argv)
    set -l repo_root (_ccmux_repo_root)
    or begin
        echo "Not in a git repo"
        return 1
    end

    set -l worktree_dir (_ccmux_worktree_dir "$repo_root" "$branch")

    if test -d "$worktree_dir"
        echo "Worktree already exists: $worktree_dir"
        builtin cd "$worktree_dir"
    else
        mkdir -p "$repo_root/.worktrees"
        git -C "$repo_root" worktree add "$worktree_dir" -b "$branch"
        or return 1
        builtin cd "$worktree_dir"

        # Run project-specific setup hook
        if test -x "$worktree_dir/.cmux/setup"
            echo "Running .cmux/setup..."
            "$worktree_dir/.cmux/setup"
        else if test -x "$repo_root/.cmux/setup"
            echo "Running .cmux/setup from repo root (not yet committed to branch)..."
            "$repo_root/.cmux/setup"
            echo "Tip: commit .cmux/setup so it's available in new worktrees automatically."
        else
            echo "No .cmux/setup found — worktree will skip project-specific setup."
            read -P "Run 'ccmux init' to generate one? (y/N) " reply
            if string match -qi 'y' -- "$reply"
                _ccmux_init
                if test -x "$repo_root/.cmux/setup"
                    echo "Running .cmux/setup..."
                    "$repo_root/.cmux/setup"
                end
            end
        end
    end

    echo "Worktree ready: $worktree_dir"
    claude
end

function _ccmux_start
    if test "$argv[1]" = --help; or test "$argv[1]" = -h
        echo "Usage: ccmux start <branch>"
        echo ""
        echo "  Resume work in an existing worktree by launching Claude Code with --continue."
        return 0
    end
    if test (count $argv) -eq 0
        echo "Usage: ccmux start <branch>"
        return 1
    end

    set -l branch $argv[1]
    set -l repo_root (_ccmux_repo_root)
    or begin
        echo "Not in a git repo"
        return 1
    end

    set -l worktree_dir (_ccmux_worktree_dir "$repo_root" "$branch")

    if not test -d "$worktree_dir"
        echo "Worktree not found: $worktree_dir"
        echo "Run 'ccmux ls' to see available worktrees, or 'ccmux new $branch' to create one."
        return 1
    end

    builtin cd "$worktree_dir"
    claude -c
end

function _ccmux_cd
    if test "$argv[1]" = --help; or test "$argv[1]" = -h
        echo "Usage: ccmux cd [branch]"
        echo ""
        echo "  cd into a worktree directory (no args = repo root)."
        return 0
    end

    set -l repo_root (_ccmux_repo_root)
    or begin
        echo "Not in a git repo"
        return 1
    end

    if test (count $argv) -eq 0
        builtin cd "$repo_root"
        return
    end

    set -l branch $argv[1]
    set -l worktree_dir (_ccmux_worktree_dir "$repo_root" "$branch")

    if not test -d "$worktree_dir"
        echo "Worktree not found: $worktree_dir"
        echo "Run 'ccmux ls' to see available worktrees."
        return 1
    end

    builtin cd "$worktree_dir"
end

function _ccmux_ls
    if test "$argv[1]" = --help; or test "$argv[1]" = -h
        echo "Usage: ccmux ls"
        echo ""
        echo "  List all ccmux worktrees."
        return 0
    end

    set -l repo_root (_ccmux_repo_root)
    or begin
        echo "Not in a git repo"
        return 1
    end

    git -C "$repo_root" worktree list | grep '\.worktrees/'
end

function _ccmux_merge
    if test "$argv[1]" = --help; or test "$argv[1]" = -h
        echo "Usage: ccmux merge [branch] [--squash]"
        echo ""
        echo "  Merge a worktree branch into the primary checkout."
        echo "  Run with no args from inside a .worktrees/ directory to auto-detect."
        return 0
    end

    set -l branch ""
    set -l squash false

    for arg in $argv
        switch $arg
            case --squash
                set squash true
            case '*'
                set branch $arg
        end
    end

    set -l repo_root (_ccmux_repo_root)
    or begin
        echo "Not in a git repo"
        return 1
    end

    # No branch arg: detect from current worktree
    if test -z "$branch"
        if string match -q '*/.worktrees/*' "$PWD"
            set -l safe_name (string replace -r '.*/.worktrees/([^/]+).*' '$1' "$PWD")
            set branch (git -C "$repo_root" worktree list --porcelain \
                | grep -A2 "$repo_root/.worktrees/$safe_name\$" \
                | grep '^branch ' \
                | sed 's|^branch refs/heads/||')
            if test -z "$branch"
                echo "Could not detect branch for current worktree."
                return 1
            end
        else
            echo "Usage: ccmux merge <branch> [--squash]"
            echo "  (or run with no args from inside a .worktrees/ directory)"
            return 1
        end
    end

    set -l worktree_dir (_ccmux_worktree_dir "$repo_root" "$branch")

    if not test -d "$worktree_dir"
        echo "Worktree not found: $worktree_dir"
        echo "Run 'ccmux ls' to see available worktrees."
        return 1
    end

    # Check for uncommitted changes in the worktree
    if not git -C "$worktree_dir" diff --quiet 2>/dev/null
        or not git -C "$worktree_dir" diff --cached --quiet 2>/dev/null
        echo "Worktree has uncommitted changes: $worktree_dir"
        echo "Commit or stash them before merging."
        return 1
    end

    set -l target_branch (git -C "$repo_root" rev-parse --abbrev-ref HEAD 2>/dev/null)
    if test -z "$target_branch"
        echo "Could not determine branch in main checkout."
        return 1
    end

    if test "$branch" = "$target_branch"
        echo "Cannot merge '$branch' into itself."
        return 1
    end

    builtin cd "$repo_root"
    echo "Merging '$branch' into '$target_branch'..."

    if test "$squash" = true
        git merge --squash "$branch"
        or return 1
        echo ""
        echo "Squash merge staged. Review and commit the changes:"
        echo "  cd $repo_root && git commit"
    else
        git merge "$branch"
        or return 1
        echo "Merged '$branch' into '$target_branch'."
    end
end

function _ccmux_rm
    if test "$argv[1]" = --help; or test "$argv[1]" = -h
        echo "Usage: ccmux rm [branch] [-f|--force]"
        echo "       ccmux rm --all"
        echo ""
        echo "  Remove a worktree and its branch."
        echo "  Run with no args from inside a .worktrees/ directory to auto-detect."
        echo "  Use -f/--force to remove a worktree with uncommitted changes."
        echo "  Use --all to remove all ccmux worktrees (requires confirmation)."
        return 0
    end

    set -l force false
    set -l branch ""

    for arg in $argv
        switch $arg
            case --force -f
                set force true
            case --all
                set branch --all
            case '*'
                set branch $arg
        end
    end

    set -l repo_root (_ccmux_repo_root)
    or begin
        echo "Not in a git repo"
        return 1
    end

    if test "$branch" = --all
        _ccmux_rm_all "$repo_root"
        return $status
    end

    # No args: detect current worktree
    if test -z "$branch"
        if string match -q '*/.worktrees/*' "$PWD"
            set -l safe_name (string replace -r '.*/.worktrees/([^/]+).*' '$1' "$PWD")
            set branch (git -C "$repo_root" worktree list --porcelain \
                | grep -A2 "$repo_root/.worktrees/$safe_name\$" \
                | grep '^branch ' \
                | sed 's|^branch refs/heads/||')
            if test -z "$branch"
                echo "Could not detect branch for current worktree"
                return 1
            end
        else
            echo "Usage: ccmux rm <branch>  (or run with no args from inside a .worktrees/ directory)"
            return 1
        end
    end

    set -l worktree_dir (_ccmux_worktree_dir "$repo_root" "$branch")

    if not test -d "$worktree_dir"
        echo "Worktree not found: $worktree_dir"
        return 1
    end

    set -l remove_args $worktree_dir
    if test "$force" = true
        set remove_args --force $remove_args
    end

    if git -C "$repo_root" worktree remove $remove_args
        git -C "$repo_root" branch -d "$branch" 2>/dev/null
        if string match -q "$worktree_dir*" "$PWD"
            builtin cd "$repo_root"
        end
        echo "Removed worktree and branch: $branch"
    else
        echo "Failed to remove worktree: $branch"
        if test "$force" = false
            echo "Hint: use 'ccmux rm --force $branch' to remove a worktree with uncommitted changes"
        end
        return 1
    end
end

function _ccmux_rm_all
    set -l repo_root $argv[1]
    set -l worktrees_dir "$repo_root/.worktrees"

    if not test -d "$worktrees_dir"
        echo "No .worktrees directory found."
        return 0
    end

    set -l dirs
    set -l branches

    for line in (git -C "$repo_root" worktree list | grep '\.worktrees/')
        set -l wt_dir (echo $line | awk '{print $1}')
        set -l wt_branch (git -C "$repo_root" worktree list --porcelain \
            | grep -A2 "^worktree $wt_dir\$" \
            | grep '^branch ' \
            | sed 's|^branch refs/heads/||')
        set -a dirs $wt_dir
        if test -n "$wt_branch"
            set -a branches $wt_branch
        else
            set -a branches "unknown"
        end
    end

    set -l count (count $dirs)

    if test $count -eq 0
        echo "No ccmux worktrees to remove."
        return 0
    end

    echo "This will remove ALL ccmux worktrees and their branches:"
    echo ""
    for i in (seq $count)
        set -l rel_dir (string replace "$repo_root/" "" $dirs[$i])
        echo "  $rel_dir  (branch: $branches[$i])"
    end
    echo ""

    set -l expected "DELETE $count WORKTREES"
    read -P "Type \"$expected\" to confirm: " confirmation
    if test "$confirmation" != "$expected"
        echo "Aborted."
        return 1
    end

    if string match -q "$worktrees_dir*" "$PWD"
        builtin cd "$repo_root"
    end

    echo ""
    set -l failed 0
    for i in (seq $count)
        if git -C "$repo_root" worktree remove --force $dirs[$i] 2>/dev/null
            git -C "$repo_root" branch -d $branches[$i] 2>/dev/null
            echo "  Removed: $branches[$i]"
        else
            echo "  Failed:  $branches[$i]"
            set failed (math $failed + 1)
        end
    end

    echo ""
    if test $failed -eq 0
        echo "All $count worktrees removed."
    else
        echo "Done. "(math $count - $failed)"/$count removed ($failed failed)."
    end
end

function _ccmux_init
    if test "$argv[1]" = --help; or test "$argv[1]" = -h
        echo "Usage: ccmux init [--replace]"
        echo ""
        echo "  Generate a .cmux/setup hook using Claude Code."
        echo "  Use --replace to regenerate an existing setup hook."
        return 0
    end

    set -l replace false
    for arg in $argv
        switch $arg
            case --replace
                set replace true
        end
    end

    set -l repo_root (_ccmux_repo_root)
    or begin
        echo "Not in a git repo"
        return 1
    end

    if not command -q claude
        echo "claude CLI not found. Install it: https://docs.anthropic.com/en/docs/claude-code"
        return 1
    end

    set -l target_dir (git rev-parse --show-toplevel 2>/dev/null)
    or set target_dir "$repo_root"
    set -l setup_file "$target_dir/.cmux/setup"

    if test -f "$setup_file"; and test "$replace" != true
        echo ".cmux/setup already exists: $setup_file"
        echo "Run 'ccmux init --replace' to regenerate it."
        return 1
    end

    printf "Analyzing repo to generate .cmux/setup...  "
    mkdir -p "$target_dir/.cmux"

    set -l system_prompt 'You generate bash scripts. Output ONLY the script itself — no markdown fences, no prose, no explanation. The first line of your response must be #!/bin/bash. Do not wrap the script in ``` code blocks.'

    set -l prompt 'Generate a .cmux/setup script for this repo. This script runs after a git worktree is created, from within the new worktree directory.

Rules:
- Start with #!/bin/bash
- Set REPO_ROOT="$(git rev-parse --git-common-dir | xargs dirname)"
- Symlink any gitignored secret/config files (e.g. .env, .env.local) from $REPO_ROOT
- Install dependencies if a lock file exists (detect package manager)
- Run codegen/build steps if applicable
- Only include steps relevant to THIS repo — omit anything that doesn\'t apply
- Use short bash comments for non-obvious lines
- No echo statements, no status messages, no decorative output
- If the repo needs no setup, output just: #!/bin/bash followed by a one-line comment explaining why

IMPORTANT: Output ONLY the raw bash script. The very first characters of your response must be #!/bin/bash — no preamble, no markdown, no commentary.'

    set -l tmpfile (mktemp)
    or begin
        echo "Failed to create temp file"
        return 1
    end

    claude -p --system-prompt "$system_prompt" "$prompt" </dev/null >"$tmpfile" 2>/dev/null
    set -l claude_status $status

    if test $claude_status -ne 0
        rm -f "$tmpfile"
        echo "Failed to generate setup script"
        return 1
    end

    set -l raw_output (cat "$tmpfile")
    rm -f "$tmpfile"

    if not string match -q '*#!/bin/bash*' "$raw_output"
        echo "Error: generated output did not contain a valid bash script."
        echo ""
        echo "Raw output:"
        echo "$raw_output"
        return 1
    end

    echo ""
    echo "Generated .cmux/setup:"
    echo "────────────────────────────────"
    echo "$raw_output"
    echo "────────────────────────────────"
    echo ""

    while true
        echo "  [enter] Accept   [e] Edit in \$EDITOR   [r] Regenerate   [q] Quit"
        echo ""
        read -P "> " choice
        switch "$choice"
            case ''
                printf '%s\n' $raw_output >"$setup_file"
                chmod +x "$setup_file"
                echo ""
                echo "Created $setup_file"
                echo "Tip: commit .cmux/setup to your repo so it's available in new worktrees."
                return 0
            case e E
                printf '%s\n' $raw_output >"$setup_file"
                chmod +x "$setup_file"
                set -l editor_cmd (test -n "$EDITOR" && echo $EDITOR || echo vi)
                eval $editor_cmd "$setup_file"
                if test -f "$setup_file"
                    echo ""
                    echo "Saved $setup_file"
                    echo "Tip: commit .cmux/setup to your repo so it's available in new worktrees."
                    return 0
                else
                    echo "File was removed during editing. Aborting."
                    return 1
                end
            case r R
                echo ""
                printf "Regenerating...  "
                set tmpfile (mktemp)
                claude -p --system-prompt "$system_prompt" "$prompt" </dev/null >"$tmpfile" 2>/dev/null
                if test $status -ne 0
                    rm -f "$tmpfile"
                    echo "Failed to generate setup script"
                    return 1
                end
                set raw_output (cat "$tmpfile")
                rm -f "$tmpfile"
                if not string match -q '*#!/bin/bash*' "$raw_output"
                    echo "Error: generated output did not contain a valid bash script."
                    echo ""
                    echo "Raw output:"
                    echo "$raw_output"
                    return 1
                end
                echo ""
                echo "Generated .cmux/setup:"
                echo "────────────────────────────────"
                echo "$raw_output"
                echo "────────────────────────────────"
                echo ""
            case q Q
                echo "Aborted."
                return 1
            case '*'
                echo "Invalid choice."
        end
    end
end

function _ccmux_update
    if test "$argv[1]" = --help; or test "$argv[1]" = -h
        echo "Usage: ccmux update"
        echo ""
        echo "  Update ccmux to the latest version."
        return 0
    end

    set -l install_path "$HOME/.cmux/cmux.sh"

    echo "Checking for updates..."
    set -l remote_version (curl -fsSL "$_CCMUX_DOWNLOAD_URL/VERSION" 2>/dev/null | string trim)

    if test -z "$remote_version"
        echo "Failed to check for updates (network error?)."
        return 1
    end

    if test "$remote_version" = "$CCMUX_VERSION"
        echo "ccmux is already up to date ($CCMUX_VERSION)."
        return 0
    end

    echo "Updating ccmux ($CCMUX_VERSION → $remote_version)..."
    if curl -fsSL "$_CCMUX_DOWNLOAD_URL/cmux.sh" -o "$install_path"
        printf '%s' "$remote_version" >"$HOME/.cmux/VERSION"
        printf '%s' "$remote_version" >"$HOME/.cmux/.latest_version"
        set -g CCMUX_VERSION "$remote_version"
        echo "ccmux updated to $CCMUX_VERSION."
        echo "Note: Restart your shell or run 'source ~/.config/fish/functions/ccmux.fish' to reload."
    else
        echo "Failed to download update."
        return 1
    end
end

# ── Completions ──────────────────────────────────────────────────────

function _ccmux_worktree_names
    set -l repo_root (_ccmux_repo_root 2>/dev/null)
    or return
    git -C "$repo_root" worktree list --porcelain 2>/dev/null \
        | awk -v prefix="$repo_root/.worktrees/" '
            /^worktree / { wt=substr($0,10); in_wt=(index(wt,prefix)==1) }
            /^branch / && in_wt { sub(/^branch refs\/heads\//,""); print }'
end

# Fish completions
complete -c ccmux -f
complete -c ccmux -n '__fish_use_subcommand' -a 'new' -d 'New worktree + branch, launch Claude'
complete -c ccmux -n '__fish_use_subcommand' -a 'start' -d 'Continue where you left off'
complete -c ccmux -n '__fish_use_subcommand' -a 'cd' -d 'cd into worktree'
complete -c ccmux -n '__fish_use_subcommand' -a 'ls' -d 'List worktrees'
complete -c ccmux -n '__fish_use_subcommand' -a 'merge' -d 'Merge worktree branch into primary checkout'
complete -c ccmux -n '__fish_use_subcommand' -a 'rm' -d 'Remove worktree + branch'
complete -c ccmux -n '__fish_use_subcommand' -a 'init' -d 'Generate .cmux/setup hook'
complete -c ccmux -n '__fish_use_subcommand' -a 'update' -d 'Update ccmux to latest version'
complete -c ccmux -n '__fish_use_subcommand' -a 'version' -d 'Show current version'
complete -c ccmux -n '__fish_seen_subcommand_from start cd merge' -a '(_ccmux_worktree_names)'
complete -c ccmux -n '__fish_seen_subcommand_from rm' -a '(_ccmux_worktree_names)'
complete -c ccmux -n '__fish_seen_subcommand_from rm' -l all -d 'Remove all worktrees'
complete -c ccmux -n '__fish_seen_subcommand_from rm' -s f -l force -d 'Force remove'
complete -c ccmux -n '__fish_seen_subcommand_from merge' -l squash -d 'Squash merge'
complete -c ccmux -n '__fish_seen_subcommand_from init' -l replace -d 'Regenerate existing setup'
