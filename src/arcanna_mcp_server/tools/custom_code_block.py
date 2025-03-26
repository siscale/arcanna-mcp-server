import requests
from typing import Optional, List, Callable
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions
from arcanna_mcp_server.constants import CUSTOM_CODE_BLOCK_TEST_URL, CUSTOM_CODE_BLOCK_SAVE_URL


def export_tools() -> List[Callable]:
    return [
        generate_code_agent,
        save_code,
        execute_code
     ]


def compute_python_function(user_query: str) -> str:
    return ""


@handle_exceptions
async def generate_code_agent(user_query: str) -> str:
    """
    Tool to be used when generating code is requested.
    Use this method to generate a code block from a user query.
    After executing this tool ask the user if he wants to execute the code block using the execute_code tool.

    Parameters:
    -----------
    user_query : str
        User query to generate a code block from chat.

    Returns:
    --------
    str
         A Python function that follows the template: def transform(input_record):     # body of the function\n    return input_record
    """
    return compute_python_function(user_query)


@handle_exceptions
async def execute_code(source_code: str, job_id: Optional[int], input_test: dict, env_variables: Optional[list], settings: Optional[dict]) -> dict:
    """
    Send Python function to be executed on Arcanna.
    The function body must follow the template: def transform(input_record):     # body of the function\n    return input_record
    Ask the user before executing this tool for approval, providing the request details.
    In case of an internal server error, show the error to the user and do not use any other tool, ask the user how he would like to continue.

    Parameters:
    -----------
    source_code : str
        The source code to be executed.
    job_id : (int or None)
        Unique identifier for the job.
    input_test : (dict or string of dict)
        Test inputs for the code execution.
    env_variables : (list or None)
        A list of dictionaries containing environment variables with:
        - name (str): Variable name
        - value (str): Variable value
        - is_secret (bool): If the variable contains sensitive data
        - should_encrypt (bool): If the variable should be encrypted
    settings : (dict or None)
        Execution settings including:
        - limits (dict):
            - cpu_time_limit_seconds (int): Maximum CPU execution time
            - memory_limit_mb (int): Memory limit in megabytes

    Returns:
    --------
    dict
        A dictionary containing execution results with the following keys:
        - stdout (str or None): Standard output of execution.
        - stderr (str or None): Standard error output of execution.
        - output_record (str or None): JSON string containing execution records.
    """

    body = {
        "source_code": source_code,
        "input_test": input_test
    }

    if job_id:
        body["job_id"] = job_id

    if env_variables:
        body["env_variables"] = env_variables

    if settings:
        body["settings"] = settings

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(CUSTOM_CODE_BLOCK_TEST_URL, json=body, headers=headers)
    return response.json()


@handle_exceptions
async def save_code(title: str, description: str, source_code: str, job_id: Optional[int],
                    reprocess_event_id: Optional[str], input_test: dict,
                    env_variables: Optional[list], settings: Optional[dict]) -> dict:
    """
    Code block integration save request. It adds a new code block integration to specified job_id.
    Ask the user before executing this tool for approval, providing the request details.
    In case of an internal server error, show the error to the user and do not use any other tool, ask the user how he would like to continue.

    Parameters:
    -----------
    title : str
        Title of the integration.
    description : str
        A short description of the integration.
    source_code : str
        The source code to be executed.
    job_id : int
        Unique identifier for the job.
    reprocess_event_id : (str or None)
        ID for reprocessing events.
    input_test : (dict or string of dict)
        Test inputs for the code execution.
    env_variables : (list or None)
        A list of dictionaries containing environment variables with:
        - name (str): Variable name
        - value (str): Variable value
        - is_secret (bool): If the variable contains sensitive data
        - should_encrypt (bool): If the variable should be encrypted
    settings : (dict or None)
        Execution settings including:
        - limits (dict):
            - cpu_time_limit_seconds (int): Maximum CPU execution time
            - memory_limit_mb (int): Memory limit in megabytes

    Returns:
    --------
    dict
        A dictionary containing execution results with the following keys:
        - stdout (str or None): Standard output of execution.
        - stderr (str or None): Standard error output of execution.
        - output_record (str or None): JSON string containing execution records.
    """

    body = {
        "description": description,
        "title": title,
        "job_id": job_id,
        "source_code": source_code,
        "input_test": input_test
    }

    if reprocess_event_id:
        body["reprocess_event_id"] = reprocess_event_id

    if env_variables:
        body["env_variables"] = env_variables

    if settings:
        body["settings"] = settings

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(CUSTOM_CODE_BLOCK_SAVE_URL, json=body, headers=headers)
    return response.json()
