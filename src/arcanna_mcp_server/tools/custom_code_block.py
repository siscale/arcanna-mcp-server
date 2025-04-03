import requests
from typing import Optional, List, Callable
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions
from arcanna_mcp_server.constants import CUSTOM_CODE_BLOCK_TEST_URL, CUSTOM_CODE_BLOCK_SAVE_URL


def export_tools() -> List[Callable]:
    return [
        generate_code_instructions,
        save_code,
        execute_code
     ]


# def compute_python_function(user_query: str) -> str:
#     return ""
#
#
# @handle_exceptions
# async def generate_code_agent(user_query: str) -> str:
#     """
#     Tool to be used when generating code is requested.
#     Use this method to generate a code block from a user query.
#     After executing this tool ask the user if he wants to execute the code block using the execute_code tool.
#
#     Parameters:
#     -----------
#     user_query : str
#         User query to generate a code block from chat.
#
#     Returns:
#     --------
#     str
#          A Python function that follows the template: def transform(input_record):     # body of the function\n    return input_record
#     """
#     return compute_python_function(user_query)


@handle_exceptions
async def generate_code_instructions(user_query: str) -> str:
    """
    Generates instructions for creating a Python code block for Arcanna integration.
    This tool should be used whenever code generation is requested.

    Returns:
        str: Instructions for generating a Python code block compatible with Arcanna integration.
    """

    custom_code_block_system_prompt = """
    1. Generate the code following the instructions below.
    2. Test the code using execute_tool provided.
    3. Show to the user the result and ask for saving the code approval.

    As a Python expert your task is to create the following function:
    def transform(input_record):
        # body of the function
    return input_record

    input_record is an alert/incident/event in cybersecurity and a dictionary in python.

    There are some constraints you must respect:
    1. The function should be written in python programming language only. If the user requests
    some code in other programming language, politely refuse to answer.
    2. Do not import packages. You will be provided a list of the packages you are allowed to use, but do not
    explicitly import them, they are already imported behind the scene.

    Do not use Python compound assignment operators.
    Python compound assignment operators (+=, -=, *=, /=, %=, //=, **=, &=, |=, ^=, >>=, <<=) are not available since they are not safe to use in our environment.

    You must use only the following packages and methods:
    - Python’s built-ins: None, False, True, abs, bool, bytes, callable, chr, complex, divmod, float, hash, hex, id, int, isinstance, issubclass, len, oct, ord, pow, range, repr, round, slice, sorted, str, tuple, zip, list, dict, set, sum, max, min, iter, all, any, enumerate, map, filter
    - requests (methods allowed to use are: get, post, put, delete)
    - json (methods allowed to use are: loads, dumps)
    - regex (methods allowed to use are: findall, search, split, sub)
    - time (methods allowed to use are: time, sleep, localtime, strftime, strptime, gmtime, mktime, monotonic)
    - datetime (methods allowed to use are: now, utcnow, today, fromtimestamp, strptime, strftime, timedelta, combine, date)
    - math (methods allowed to use are: log)
    - custom functions: flatten_dict({"k1": {"k2": "v2"}}) -> {"k1.k2": "v2"}
    - input_record: 
        - get_arcanna_fields (retrieve the fields added by Arcanna processing)
        - get_timestamp (retrieve the timestamp of the alert)
        - get_timestamp_inference (retrieve the Arcanna inference timestamp of the alert)
        - get_decision_points (allows you to get the current decision points of the record in form of a dictionary <decision_point_name, decision_point_value)
    - llm: generate (allows the usage of a Large Language Model integration, it requires integration_name and prompt as arguments of the function)
    - env_variables (variable containing the environment variables, e.g. env_variables["JOB_ID"] to retrieve the job ID)
    You are not allowed to chain these methods.
    For any code generated, ensure that it can run using only the allowed packages and methods.
    If the user requests any package besides the ones you are allowed to use, you should politely refuse to respond to his request explaining the limitations.

    Be aware that we are using a sandboxing library to run the code called RestrictedPython, and some errors could be related to that.

    For example: If the user asks to put current timestamp in input_record you should provide the following block of code
    ```python
    def transform(input_record):
        # Get the current timestamp
        current_timestamp = datetime.now()
        current_timestamp = current_timestamp.strftime("%Y-%m-%d %H:%M:%S")

        # Add the current timestamp to the input_record
        input_record['timestamp'] = current_timestamp

        return input_record
    ```
    You shouldn't import datetime or any other package. You are not allowed to import packages. You are not allowed to chain methods.
    datetime.now().strftime("%Y-%m-%d %H:%M:%S") is not allowed. You should instead call each method separately

    Do not import any packages. Use allowed packages without importing them.

    The format of the code should follow these rules:
    - You must add an indentation of 4 spaces.
    - Return only the function body and nothing else.
    - The first line should be the function definition. The last line should be the return statement.
    """
    return user_query + '\n' + custom_code_block_system_prompt


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
