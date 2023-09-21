if command -v zsh > /dev/null 2>&1 && [ "$SHELL" != "$(command -v zsh)" ]; then
    exec zsh -l
fi