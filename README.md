# Arcanna MCP Server

The Arcanna MCP server allows user to interact with Arcanna's AI use cases through the Model Context Protocol (MCP).

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
        "arcanna-mcp-server"
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
2. Run ```docker build -t arcanna/arcanna-mcp-server. --progress=plain --no-cache```
3. Add the configuration bellow to your claude desktop config.
```json
{
  "mcpServers": {
    "arcanna-mcp-server": {
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


## Features

- **Job Management**: Create, retrieve, start, stop, and train jobs
- **Event Processing**: Send events for AI-powered decision making
- **Feedback System**: Provide feedback on decisions to improve model accuracy
- **Health Monitoring**: Check server and API key status

## Tools

### Job Management
- **get_jobs**
  - Retrieve all jobs associated with your API key
  - Returns a list of job details including status, labels, and processing metrics

- **get_job_by_id**
  - Retrieve specific job details by ID

- **get_job_by_name**
  - Retrieve specific job details by name

- **get_job_labels**
  - Retrieve decision labels for a specific job

- **get_labels_of_job_by_name**
  - Retrieve decision labels for a job by name

- **start_job**
  - Begin event ingestion for a job

- **stop_job**
  - Stop event ingestion for a job

- **train_job**
  - Train the job's AI model using the provided feedback

### Event Management
- **send_event**
  - Submit an event to Arcanna for AI decision-making

- **send_event_with_id**
  - Submit an event with a custom identifier

- **get_event_by_id**
  - Retrieve event details and decision results

### Feedback System
- **send_feedback_for_event**
  - Provide feedback on AI decisions for model improvement

### System Health
- **health_check**
  - Verify server status and API key validity
  - Returns API key authorization status

