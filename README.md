# Arcanna MCP Server

The Arcanna MCP Server is a specialized server application designed to interface with Claude via the MCP (Model Control Protocol)
framework. This server provides a seamless way to execute tools and commands within the Claude client environment.

## Usage with Claude Desktop or other MCP Clients

### Option 1 - uvx
#### Prerequisites
- uv - https://docs.astral.sh/uv/getting-started/installation/#installation-methods

#### Configuration
Add the following entry to the `mcpServers` section in your MCP client config file (`claude_desktop_config.json` for Claude
Desktop).

```json
{
  "mcpServers": {
    "arcanna": {
      "command": "uvx",
      "args": [
        "--from git+https://github.com/siscale/arcanna-mcp-server@master",
        "arcanna-mcp"
      ],
      "env": {
        "ARCANNA_INPUT_API_KEY": "YOUR_ARCANNA_INPUT_API_KEY",
        "ARCANNA_MANAGEMENT_API_KEY": "YOUR_ARCANNA_MANAGEMENT_API_KEY",
        "ARCANNA_HOST": "YOUR_ARCANNA_HOST",
        "ARCANNA_USER": "YOUR_USERNAME"
      }
    }
  }
}
```