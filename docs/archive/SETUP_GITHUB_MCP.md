# 🐙 How to Setup GitHub MCP Server

This will give me (Antigravity) the power to **create repositories**, **commit code**, and **manage PRs** directly on your behalf.

### Step 1: Get a Personal Access Token (PAT)
1.  Go to **[GitHub Templates: Tokens](https://github.com/settings/tokens/new)**.
2.  Choose **"Generate new token (Classic)"** (easiest compatibility).
3.  **Scopes**: Select `repo` (Full control of private repositories).
4.  **Generate** and **Copy** the token (starts with `ghp_`).

### Step 2: Edit MCP Configuration
Open your **IDE Settings** (or the MCP Config file `.vscode/mcp.json` / `~/.config/mcp.json` depending on your setup) and add:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_TOKEN_HERE"
      }
    }
  }
}
```

### Step 3: Reload
Restart the Agent/IDE. I should then see the `github` tools available.

---

### ⚠️ Alternative: The "Fast" Way (Manual URL)
If you don't want to mess with keys right now:
1.  Create the repo manually at [github.com/new](https://github.com/new).
2.  Paste the **HTTPS URL** in the chat.
3.  I will run `git push` using your cached credentials (if authorized) or ask for them once.
