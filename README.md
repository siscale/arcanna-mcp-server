# Arcanna MCP Server

The Arcanna MCP server allows user to interact with Arcanna's AI use cases through the Model Context Protocol (MCP).

## Usage with Claude Desktop or other MCP Clients

#### Configuration
Add the following entry to the `mcpServers` section in your MCP client config file (`claude_desktop_config.json` for Claude
Desktop).

### Use docker image (https://hub.docker.com/r/arcanna/arcanna-mcp-server) or PyPi package (https://pypi.org/project/arcanna-mcp-server/)

### Building local image from this repository
#### Prerequisites
- Docker - https://docs.docker.com/engine/install/

#### Configuration
1. Change directory to the directory where the Dockerfile is.
2. Run ```docker build -t arcanna/arcanna-mcp-server . --progress=plain --no-cache```
3. Add the configuration bellow to your claude desktop/mcp client config.

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
        "ARCANNA_MANAGEMENT_API_KEY",
        "-e",
        "ARCANNA_HOST",
        "arcanna/arcanna-mcp-server"
      ],
      "env": {
        "ARCANNA_MANAGEMENT_API_KEY": "<ARCANNA_MANAGEMENT_API_KEY>",
        "ARCANNA_HOST": "<YOUR_ARCANNA_HOST_HERE>"
      }
    }
  }
}
```


## Features
- **Resource Management**: Create, update and retrieve Arcanna resources (jobs, integrations)
- **Python Coding**: Code generation, execution and saving the code block as an Arcanna integration
- **Query Arcanna events**: Query events processed by Arcanna
- **Job Management**: Create, retrieve, start, stop, and train jobs
- **Feedback System**: Provide feedback on decisions to improve model accuracy
- **Health Monitoring**: Check server and API key status

## Tools

### Query Arcanna events
- **query_arcanna_events**
  - Used to get events processed by Arcanna, multiple filters can be provided

- **get_filter_fields**
  - used as a helper tool (retrieve Arcanna possible fields to apply filters on)

### Resource Management
- **upsert_resources**
  - Create/update Arcanna resources

- **get_resources**
  - Retrieve Arcanna resources (jobs/integrations)

- **delete_resources**
  - Delete Arcanna resources

- **integration_parameters_schema**
  - used in this context as a helper tool

### Python Coding
- **generate_code_agent**
  - Used to generate code

- **execute_code**
  - Used to execute the generated code

- **save_code**
  - Use to save the code block in Arcanna pipeline as an integration

### Job Management
- **start_job**
  - Begin event ingestion for a job

- **stop_job**
  - Stop event ingestion for a job

- **train_job**
  - Train the job's AI model using the provided feedback

### Feedback System
- **add_feedback_to_event**
  - Provide feedback on AI decisions for model improvement

### System Health
- **health_check**
  - Verify server status and Management API key validity
  - Returns Management API key authorization status
