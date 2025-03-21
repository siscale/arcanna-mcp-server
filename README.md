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

### Option 2 - Building local image from this repository
#### Prerequisites
- Docker - https://docs.docker.com/engine/install/

#### Configuration
1. Change directory to the directory where the Dockerfile is.
2. Run ```docker build -t mcp/arcanna . --progress=plain --no-cache```
3. Add the configuration bellow to your claude desktop config.
```json
{
  "mcpServers": {
    "arcanna-mcp": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "ARCANNA_INPUT_API_KEY",
        "-e",
        "ARCANNA_MANAGEMENT_API_KEY",
        "-e",
        "ARCANNA_HOST",
        "-e",
        "ARCANNA_USER",
        "mcp/arcanna"
      ],
      "env": {
        "ARCANNA_INPUT_API_KEY": "<YOUR_ARCANNA_API_KEY_HERE>",
        "ARCANNA_MANAGEMENT_API_KEY": "<ARCANNA_MANAGEMENT_API_KEY>",
        "ARCANNA_HOST": "<YOUR_ARCANNA_HOST_HERE>",
        "ARCANNA_USER": "<YOUR_USERNAME_HERE>"
      }
    }
  }
}
```