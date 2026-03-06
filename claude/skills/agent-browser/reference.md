# agent-browser Full Command Reference

## Core Commands

| Command | Description |
|---------|-------------|
| `open <url>` | Navigate to URL |
| `click <sel>` | Click element (or @ref) |
| `dblclick <sel>` | Double-click element |
| `type <sel> <text>` | Type into element |
| `fill <sel> <text>` | Clear and fill |
| `press <key>` | Press key (Enter, Tab, Control+a) |
| `hover <sel>` | Hover element |
| `focus <sel>` | Focus element |
| `check <sel>` | Check checkbox |
| `uncheck <sel>` | Uncheck checkbox |
| `select <sel> <val>` | Select dropdown option |
| `drag <src> <dst>` | Drag and drop |
| `upload <sel> <files>` | Upload files |
| `scroll <dir> [px]` | Scroll (up/down/left/right) |
| `scrollintoview <sel>` | Scroll element into view |
| `screenshot [path]` | Take screenshot (--full for full page) |
| `pdf <path>` | Save as PDF |
| `snapshot` | Accessibility tree with refs |
| `eval <js>` | Run JavaScript |
| `connect <port>` | Connect via CDP |
| `close` | Close browser |

## Get Info

| Command | Description |
|---------|-------------|
| `get text <sel>` | Get text content |
| `get html <sel>` | Get innerHTML |
| `get value <sel>` | Get input value |
| `get attr <sel> <attr>` | Get attribute |
| `get title` | Get page title |
| `get url` | Get current URL |
| `get count <sel>` | Count matching elements |
| `get box <sel>` | Get bounding box |

## Check State

| Command | Description |
|---------|-------------|
| `is visible <sel>` | Check if visible |
| `is enabled <sel>` | Check if enabled |
| `is checked <sel>` | Check if checked |

## Find Elements (Semantic Locators)

```bash
agent-browser find role <role> <action> [value]       # By ARIA role
agent-browser find text <text> <action>               # By text content
agent-browser find label <label> <action> [value]     # By label
agent-browser find placeholder <ph> <action> [value]  # By placeholder
agent-browser find alt <text> <action>                # By alt text
agent-browser find title <text> <action>              # By title attr
agent-browser find testid <id> <action> [value]       # By data-testid
agent-browser find first <sel> <action> [value]       # First match
agent-browser find last <sel> <action> [value]        # Last match
agent-browser find nth <n> <sel> <action> [value]     # Nth match
```

Actions: `click`, `fill`, `check`, `hover`, `text`

## Wait

| Command | Description |
|---------|-------------|
| `wait <selector>` | Wait for element visible |
| `wait <ms>` | Wait milliseconds |
| `wait --text "text"` | Wait for text to appear |
| `wait --url "pattern"` | Wait for URL pattern |
| `wait --load networkidle` | Wait for network idle |
| `wait --fn "js expression"` | Wait for JS condition |

## Snapshot Options

| Option | Description |
|--------|-------------|
| `-i, --interactive` | Only interactive elements |
| `-C, --cursor` | Include cursor-interactive elements |
| `-c, --compact` | Remove empty structural elements |
| `-d, --depth <n>` | Limit tree depth |
| `-s, --selector <sel>` | Scope to CSS selector |

## Navigation

| Command | Description |
|---------|-------------|
| `back` | Go back |
| `forward` | Go forward |
| `reload` | Reload page |

## Mouse Control

| Command | Description |
|---------|-------------|
| `mouse move <x> <y>` | Move mouse |
| `mouse down [button]` | Press button |
| `mouse up [button]` | Release button |
| `mouse wheel <dy> [dx]` | Scroll wheel |

## Browser Settings

| Command | Description |
|---------|-------------|
| `set viewport <w> <h>` | Set viewport size |
| `set device <name>` | Emulate device |
| `set geo <lat> <lng>` | Set geolocation |
| `set offline [on/off]` | Toggle offline mode |
| `set headers <json>` | Extra HTTP headers |
| `set credentials <u> <p>` | HTTP basic auth |
| `set media [dark/light]` | Emulate color scheme |

## Cookies & Storage

```bash
agent-browser cookies                       # Get all cookies
agent-browser cookies set <name> <val>      # Set cookie
agent-browser cookies clear                 # Clear cookies
agent-browser storage local                 # Get localStorage
agent-browser storage local <key>           # Get specific key
agent-browser storage local set <k> <v>     # Set value
agent-browser storage local clear           # Clear all
agent-browser storage session               # sessionStorage (same API)
```

## Network

```bash
agent-browser network route <url>              # Intercept requests
agent-browser network route <url> --abort      # Block requests
agent-browser network route <url> --body <json>  # Mock response
agent-browser network unroute [url]            # Remove routes
agent-browser network requests                 # View tracked requests
agent-browser network requests --filter api    # Filter requests
```

## Tabs

```bash
agent-browser tab                    # List tabs
agent-browser tab new [url]          # New tab
agent-browser tab <n>                # Switch to tab n
agent-browser tab close [n]          # Close tab
```

## Debug

```bash
agent-browser trace start [path]     # Start trace
agent-browser trace stop [path]      # Stop trace
agent-browser console                # View console messages
agent-browser errors                 # View page errors
agent-browser highlight <sel>        # Highlight element
agent-browser state save <path>      # Save auth state
agent-browser state load <path>      # Load auth state
```

## Sessions & Profiles

```bash
# Named sessions (isolated browser instances)
agent-browser --session name open url
agent-browser session list

# Persistent profiles (cookies/storage survive browser restart)
agent-browser --profile ~/.myapp-profile open url

# Authenticated sessions
agent-browser open api.example.com --headers '{"Authorization": "Bearer token"}'
```

## Global Options

| Option | Description |
|--------|-------------|
| `--session <name>` | Isolated session |
| `--profile <path>` | Persistent browser profile |
| `--headers <json>` | HTTP headers scoped to origin |
| `--json` | JSON output (for agents) |
| `--full, -f` | Full page screenshot |
| `--headed` | Show browser window |
| `--cdp <port>` | Connect via CDP |
| `--ignore-https-errors` | Ignore HTTPS cert errors |
| `--allow-file-access` | Allow file:// URLs |
| `-p, --provider <name>` | Browser provider (ios, browserbase, kernel, browseruse) |
| `--debug` | Debug output |
