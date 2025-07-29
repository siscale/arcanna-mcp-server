import requests
from typing import Callable, List, Optional, Union, Dict, Any
from arcanna_mcp_server.constants import LIST_WORKFLOWS_URL, RUN_WORKFLOW_BY_ID_URL, UPSERT_WORKFLOWS_URL
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions
from arcanna_mcp_server.utils.post_data import post_data
from arcanna_mcp_server.utils.tool_scopes import requires_scope


def export_tools() -> List[Callable]:
    return [
        list_agentic_workflows,
        run_agentic_workflow,
        create_agentic_workflow,
        generate_agentic_code_instructions
    ]


@handle_exceptions
@requires_scope('public')
async def generate_agentic_code_instructions() -> str:
    """
    Generates instructions for creating Python Agents code for Arcanna Agentic Workflows.
    This tool should be used whenever create_agentic_workflow tool is requested.

    Returns:
        str: Instructions for generating Python Agents ADK code compatible with Arcanna Agentic Workflows.
    """

    agentic_code_system_prompt = f"""
    You are an expert Python developer specializing in creating intelligent agents and complex agent workflows using the Google ADK framework. Your task is to write clean, verbose, and well-commented Python code based on user requirements. Your solutions should be robust, efficient, and adhere to ADK best practices.

Follow these instructions carefully:

Before writing any code, thoroughly think through the implementation process. Wrap your detailed thoughts within a \`thoughts\` block:

<thoughts>

1.  **Analyze the User Request:**
    * Clearly identify the core problem the user wants to solve.
    * Extract all key functional and non-functional requirements (e.g., input format, desired output, performance considerations).
    * Determine if the request can be handled by a single, monolithic agent or if it necessitates a workflow of multiple, interconnected agents. Justify your decision.

2.  **Identify Relevant Tools:**
    * Review the \`AVAILABLE_TOOLS\` list.
    * For each identified requirement, determine if an existing **MCP tool** can fulfill it.
    * If a requirement cannot be met by an \`AVAILABLE_TOOLS\` entry, plan for the creation of a **custom tool function**. Detail the purpose and expected input/output for each planned custom tool.

3.  **Outline the Agent Structure:**
    * **If a single agent:** Describe its primary responsibilities, the LLM it will use, and the tools it will have access to.
    * **If a multi-agent workflow:**
        * List all necessary agents (e.g., \`LlmAgent\`, \`SequentialAgent\`, \`ParallelAgent\`, \`LoopAgent\`), assigning a descriptive \`name\` and \`description\` to each.
        * Define the specific role and responsibilities of each agent within the workflow.
        * Specify the LLM model and the tools each individual agent will utilize.

4.  **Plan the Logical Flow and Data Management:**
    * Describe the step-by-step execution flow of the agent(s).
    * **For multi-agent workflows:**
        * Clearly define how data will be passed between agents, including the format and content of inputs and outputs at each transition.
        * Outline how control flow will be managed (e.g., using \`SequentialAgent\` for linear progression, \`ParallelAgent\` for concurrent tasks, \`LoopAgent\` for iterative processing).
        * Consider the state of the overall conversation or task. How will context be maintained across different agents or turns?

5.  **Consider Error Handling and Edge Cases:**
    * Anticipate potential points of failure within the agent's logic or during tool execution (e.g., invalid user input, tool failures, LLM hallucinations, API errors).
    * Plan robust error handling mechanisms, including retries, fallback strategies, and informative error messages to the user or for debugging.
    * Identify and plan how to handle edge cases or unusual inputs that might deviate from the primary flow.

This planning section should be exhaustive and detailed, forming a clear blueprint for your code. The more thorough your plan, the more efficient and robust your implementation will be.
</thoughts>

Now, write the Python code for the agent(s) based on your detailed analysis. Follow these strict guidelines:

1.  **Imports:** Always start by importing the necessary modules from the Google ADK framework and other required libraries.
    \`\`\`python
    import os
    from google.adk.agents import Agent, LlmAgent, SequentialAgent, ParallelAgent, LoopAgent
    from google.adk.models.lite_llm import LiteLlm
    # ... other standard library imports (e.g., typing, logging)
    \`\`\`

2.  **LLM Configuration:**
    * Define a global \`MODEL\` constant after imports to ensure consistency across all agents.
    * **\`LiteLlm\`:** This class acts as a flexible wrapper for various foundational LLMs (e.g., Gemini, Anthropic, OpenAI, OpenRouter).
        * **Usage Examples:**
            * \`MODEL = LiteLlm(model="gemini/gemini-2.5-flash")\`
            * \`MODEL = LiteLlm(model="bedrock/us-east-1.anthropic.claude-3-sonnet-20240229-v1:0")\`
            * \`MODEL = LiteLlm(model="openai/gpt-4o")\`
        * **API Keys:** If using a non-Gemini model (e.g., Anthropic, OpenAI), ensure the user is informed to set the necessary API keys as environment variables (e.g., \`ANTHROPIC_API_KEY\`, \`OPENAI_API_KEY\`). LiteLLM automatically picks these up. For more advanced LiteLLM proxy configurations (e.g., \`api_base\`, \`timeout\`, \`max_retries\`), these are typically managed via LiteLLM environment variables or a separate LiteLLM proxy instance that your ADK \`LiteLlm\` connects to.

3.  **Root Agent:** Create a \`root_agent\` instance as the sole entry point for your agent or multi-agent workflow. This agent will orchestrate the entire process.

4.  **Workflow Design:**
    * If the user request necessitates multiple agents, construct a workflow that logically connects them, always starting from the \`root_agent\`.
    * **Workflow Agents (\`SequentialAgent\`, \`ParallelAgent\`, \`LoopAgent\`):** These agents orchestrate sub-agents.
        * **Parameters:**
            * \`name\` (str, required): A unique, descriptive identifier for the workflow agent.
            * \`sub_agents\` (list[Agent | LlmAgent | SequentialAgent | ParallelAgent | LoopAgent], required): A list containing instances of the sub-agents that this workflow agent will manage.
            * \`description\` (str, optional, recommended): A concise summary of the workflow agent's purpose, used by other LLM agents for routing decisions.
        * **Execution Flow:**
            * \`SequentialAgent\`: Executes \`sub_agents\` in the order they appear in the \`sub_agents\` list. The output of one sub-agent becomes the input context for the next.
            * \`ParallelAgent\`: Executes \`sub_agents\` concurrently. It typically collects results from all sub-agents before proceeding. Data flow usually involves a shared initial context or a collection of independent results.
            * \`LoopAgent\`: Executes a sequence of \`sub_agents\` repeatedly based on a specified \`max_iterations\` or a dynamic condition. Useful for iterative refinement or polling.

5.  **Core Agents (\`Agent\`, \`LlmAgent\`):** These are the foundational agents responsible for reasoning and tool execution. \`Agent\` is often an alias for \`LlmAgent\`.
    * **Parameters:**
        * \`name\` (str, required): A unique, descriptive identifier (e.g., \`data_extractor\`, \`response_generator\`). Crucial for multi-agent systems.
        * \`model\` (str or LiteLlm instance, required): The LLM that powers this agent's reasoning (e.g., \`"gemini-2.5-flash-latest"\` or your \`MODEL\` constant).
        * \`description\` (str, optional, recommended for multi-agent): A concise summary of the agent's specific capabilities. This is critical for other LLM agents to determine if they should delegate a task.
        * \`instruction\` (str, optional): A system-level prompt that guides the LLM's behavior and reasoning for this specific agent. Use this to define the agent's persona, goals, and constraints.
        * \`tools\` (list[FunctionTool | MCPToolset], optional): A list of tools available to this agent. The agent's LLM can choose to call these tools based on its reasoning.
        * \`output_key\` (str, optional): When part of a workflow, this specifies the key under which this agent's output will be stored in the context for subsequent agents.

6.  **Tool Integration:**
    * **MCP Tools:** If \`AVAILABLE_TOOLS\` contains MCP tools, incorporate them by passing their names AWLAYS PREFIXED BY mcp_tools. to the \`tools\` array of the relevant agent(s). The prefix represents a namespace that we created under the hood and must always be used when writing the tools in the array. DO NOT pass their names as strings, but as variables in the array.
    * **Custom Tool Functions:** If a required tool is not available, create a custom Python function.
        * **Definition:**
            * Must be a standard Python function.
            * Should include **type hints** for all parameters and its return value.
            * Must have a clear, descriptive **docstring** that explains its purpose, parameters, and return value. This docstring is crucial for the LLM to understand how and when to use the tool.
            * **Example Structure:**
                \`\`\`python
                from pydantic import BaseModel, Field

                # Define Pydantic models for structured input/output if needed
                class SearchQueryParams(BaseModel):
                    query: str = Field(description="The search query string.")
                    max_results: int = Field(default=5, description="Maximum number of search results to return.")

                def search_web(params: SearchQueryParams) -> list[str]:
                    \"\"\"Searches the web for the given query and returns a list of relevant URLs.

                    Args:
                        params: An instance of SearchQueryParams containing the query and max_results.

                    Returns:
                        A list of strings, where each string is a URL.
                    \"\"\"
                    # ... implementation details ...
                    return ["[http://example.com/result1](http://example.com/result1)", "[http://example.com/result2](http://example.com/result2)"]

                # Then, pass it to an agent:
                # my_agent = LlmAgent(
                #     name="information_gatherer",
                #     model=MODEL,
                #     tools=[search_web],
                #     instruction="You are an expert at finding information online. Use the search_web tool."
                # )
                \`\`\`
        * **Integration:** Write your custom function name in the \`tools\` list of the appropriate agent(s).

7.  **Code Quality:**
    * Write clean, readable, and idiomatic Python code.
    * Use meaningful variable names that clearly convey their purpose.
    * Include comprehensive docstrings for all classes, functions, and methods.
    * Add inline comments to explain complex logic, design choices, or non-obvious parts of the code.

8.  **ADK Consistency:** Ensure your code strictly adheres to the Google ADK framework and consistently leverages its components.

9.  **External Libraries:** Remember you have access to various Python libraries beyond ADK, such as \`pydantic\` for data validation and structured outputs, standard libraries (e.g., \`os\`, \`json\`, \`logging\`), and more, which you can use to enhance your agent's functionality.

10. **Do not add any __main__ block for testing:** Testing is being done in our UI.

Present your code solution in the following format:
\`\`\`python
# Your python code here
\`\`\`
"""
    return agentic_code_system_prompt


@handle_exceptions
@requires_scope('read:agents')
async def list_agentic_workflows() -> list:
    """
        An agentic workflow is a suite of AI Agents that solve user defined tasks. This function lists all agentic workflows available.

    Returns:
    --------
    list
        A list containing all agentic workflows. Each workflow is a dictionary with the following keys:
        - id(str): id of the workflow
        - name(str): name of the workflow
        - description(str): description of the workflow
     """

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(LIST_WORKFLOWS_URL, headers=headers)
    entries = response.json().get("entries")
    return [{"id": entry.get("id"), "name": entry.get("name"), "description": entry.get("description")}
            for entry in entries]


@handle_exceptions
@requires_scope('execute:agents')
async def run_agentic_workflow(workflow_id: Union[str, int], workflow_input: str, session_id: Optional[str] = None) -> dict:
    """
        Run an agentic workflow with a given workflow input.

    Parameters:
    --------
    workflow_id: str or int
        Unique identifier of the workflow to run
    workflow_input: str
        Input for the agentic workflow

    Returns:
    --------
    dict
        A dictionary with the following keys:
        - workflow_result(dict): Result of the workflow.
            workflow_result is a list of events. Each event is represented by a dictionary with the following keys:
                - author(str): name of the agent that created the event. Can be either the user (like a user message) or the name of an agent in the workflow
                - final(bool): flag that states the agent in the workflow finished its task or not.
                - function_calls(list): List of dictionaries with the following keys:
                    - id(str): id of the function call
                    - name(str): name of the tool/function to be called
                    - args(str): json that represents the arguments of the function/tool call
                - function_responses(list): List of dictionaries with the following keys:
                    - id(str): id of the function that was called
                    - name(str): name of the tool/function that was called
                    - response(str): the result of the function call
                - content(str): Message of the author
        - session_id(str): Workflow session id. To continue the conversation, run_agentic_workflow tool must be provided the session_id of the conversation.
     """
    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "input": workflow_input,
        "wait_for_completion": True,
        "session_id": session_id
    }

    response = await post_data(RUN_WORKFLOW_BY_ID_URL.format(str(workflow_id)), headers, payload)
    return response


@handle_exceptions
@requires_scope('write:agents')
async def create_agentic_workflow(
        workflow_id: str,
        name: str,
        source_code: str,
        description: Optional[str] = "",
        env_variables: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None
) -> dict:
    """
        Create or update an agentic workflow with the provided configuration.
        Before using this tool, make sure to generate the code instructions for your workflow using the generate_agentic_code_instructions tool.

    Parameters:
    --------
    workflow_id: str
        Unique identifier for the workflow
    name: str
        Name of the workflow
    source_code: str
        Python source code for the workflow containing agent definitions
    description: str, optional
        Description of the workflow (default: "")
    env_variables: list of dict, optional
        List of environment variables for the workflow. Each dict should contain:
        - name(str): variable name
        - value(str): variable value
        - is_secret(bool): whether the variable is secret (default: False)
        - should_encrypt(bool): whether the variable should be encrypted (default: False)
    settings: dict, optional
        Resource settings for the workflow (default: empty dict). Should contain:
        - limits(dict): Resource limits configuration with nested limit settings

    Returns:
    --------
    dict
        A dictionary with the response from the workflow creation endpoint.
        Success response typically contains confirmation of workflow creation.
     """

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "id": workflow_id,
        "name": name,
        "description": description,
        "source_code": source_code,
        "env_variables": env_variables or [],
        "settings": settings or {}
    }

    response = await post_data(UPSERT_WORKFLOWS_URL, headers, payload)
    return response
