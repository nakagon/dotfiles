---
name: agent-browser
description: Browser automation using agent-browser CLI for web research, testing, and interaction. Use when browsing websites, scraping pages, testing web UIs, filling forms, taking screenshots, or performing any web research and investigation tasks. Prefer this over Playwright MCP for browser automation.
---

# agent-browser - Browser Automation CLI

Headless browser automation CLI for AI agents. Use `agent-browser` via the Bash tool for all web browsing, research, and UI testing tasks.

## When to Use This Skill

- Web research and investigation (opening URLs, reading page content)
- Filling forms, clicking buttons, navigating websites
- Taking screenshots of web pages
- Testing web UIs and checking element states
- Scraping structured data from websites
- Any task that requires a web browser

## Core Workflow (Snapshot + Ref Pattern)

This is the primary workflow. Always follow this pattern:

```bash
# 1. Open the target page
agent-browser open https://example.com

# 2. Get accessibility tree with element refs
agent-browser snapshot -i

# 3. Interact using refs from the snapshot
agent-browser click @e2
agent-browser fill @e3 "search query"

# 4. After page changes, re-snapshot
agent-browser snapshot -i
```

### Reading Page Content

```bash
# Get full accessibility tree (best for understanding page structure)
agent-browser snapshot

# Get only interactive elements (buttons, inputs, links)
agent-browser snapshot -i

# Compact output (remove empty structural elements)
agent-browser snapshot -i -c

# Limit depth for large pages
agent-browser snapshot -i -c -d 3

# Scope to a specific section
agent-browser snapshot -s "#main-content"

# Get text content of a specific element
agent-browser get text @e1

# Get page title and URL
agent-browser get title
agent-browser get url
```

### Interacting with Elements

```bash
# Click by ref
agent-browser click @e2

# Fill input (clears first)
agent-browser fill @e3 "text to enter"

# Type without clearing
agent-browser type @e3 "additional text"

# Press keyboard keys
agent-browser press Enter
agent-browser press Tab

# Select dropdown
agent-browser select @e5 "option-value"

# Check/uncheck checkbox
agent-browser check @e6
agent-browser uncheck @e6

# Scroll
agent-browser scroll down 500
agent-browser scrollintoview @e7
```

### Screenshots

```bash
# Take screenshot (saves to temp directory)
agent-browser screenshot

# Save to specific path
agent-browser screenshot /path/to/screenshot.png

# Full page screenshot
agent-browser screenshot --full /path/to/full.png
```

### Waiting

```bash
# Wait for element to appear
agent-browser wait "#loading-complete"

# Wait for text to appear
agent-browser wait --text "Welcome"

# Wait for URL change
agent-browser wait --url "**/dashboard"

# Wait for network idle
agent-browser wait --load networkidle

# Wait milliseconds
agent-browser wait 2000
```

### Navigation

```bash
agent-browser back
agent-browser forward
agent-browser reload
```

### Session Management

```bash
# Use named sessions for parallel browsing
agent-browser --session research open https://site-a.com
agent-browser --session testing open https://site-b.com

# List active sessions
agent-browser session list

# Close browser
agent-browser close
```

## AI Assistant Instructions

When this skill is activated:

1. **Always use snapshot-ref workflow**: Open page, snapshot, interact via refs, re-snapshot after changes
2. **Use `snapshot -i` by default**: Interactive-only mode reduces noise
3. **Add `-c` for large pages**: Compact mode removes empty structural elements
4. **Re-snapshot after navigation or interaction**: Refs change when the DOM changes
5. **Use `agent-browser get text @ref`** to extract specific text content
6. **Close browser when done**: Run `agent-browser close` after completing the task
7. **For research tasks**: Focus on `snapshot` for reading content, not `screenshot`

### Common Patterns

**Web Research:**
```bash
agent-browser open https://example.com
agent-browser snapshot -i -c        # Read the page
agent-browser get text @e1           # Extract specific text
agent-browser click @e5              # Follow a link
agent-browser snapshot -i -c        # Read the new page
agent-browser close                  # Done
```

**Form Submission:**
```bash
agent-browser open https://example.com/form
agent-browser snapshot -i            # Find form elements
agent-browser fill @e3 "value1"
agent-browser fill @e4 "value2"
agent-browser click @e5              # Submit button
agent-browser wait --load networkidle
agent-browser snapshot -i            # Verify result
agent-browser close
```

**Screenshot Capture:**
```bash
agent-browser open https://example.com
agent-browser wait --load networkidle
agent-browser screenshot /tmp/page.png
agent-browser close
```

For the full command reference, see [reference.md](reference.md).
