from typing import Annotated, Any, Callable, Dict, List, Optional

from pydantic import Field

from arcanna_mcp_server.common.errors import handle_exceptions
from arcanna_mcp_server.common.http import call
from arcanna_mcp_server.common.scopes import requires_scope

JobId = Annotated[int, Field(description="Numeric id of the job that holds the event.")]
EventId = Annotated[str, Field(description="Id of the job event to run the code on.")]
IntegrationId = Annotated[Optional[int], Field(
    description="Id of the code block integration. Give integration_id or integration_title.")]
IntegrationTitle = Annotated[Optional[str], Field(description="Exact title of the code block integration.")]
Parameters = Annotated[Optional[Dict[str, Any]], Field(
    description="Values for the code block's declared parameters, by field_name; defaults fill the rest.")]
StorageName = Annotated[Optional[str], Field(
    description="Storage holding the event; needed only when the job has several inputs.")]

CODE_INSTRUCTIONS = """
    1. Generate the code following the instructions below.
    2. Show the code to the user and ask for approval to save it with save_code (creates or updates a code block
       integration).
    3. Test it with execute_code on one event of a job, show the user the result and fix the code if needed.

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
    Python compound assignment operators (+=, -=, *=, /=, %=, //=, **=, &=, |=, ^=, >>=, <<=) are not available since
    they are not safe to use in our environment.

    You must use only the following packages and methods:
    - Python's built-ins: None, False, True, abs, bool, bytes, callable, chr, complex, divmod, float, hash, hex, id,
      int, isinstance, issubclass, len, oct, ord, pow, range, repr, round, slice, sorted, str, tuple, zip, list, dict,
      set, sum, max, min, iter, all, any, enumerate, map, filter
    - requests (methods allowed to use are: get, post, put, delete)
    - json (methods allowed to use are: loads, dumps)
    - regex (methods allowed to use are: findall, search, split, sub)
    - time (methods allowed to use are: time, sleep, localtime, strftime, strptime, gmtime, mktime, monotonic)
    - datetime (methods allowed to use are: now, utcnow, today, fromtimestamp, strptime, strftime, timedelta, combine,
      date)
    - math (methods allowed to use are: log)
    - custom functions: flatten_dict({"k1": {"k2": "v2"}}) -> {"k1.k2": "v2"}
    - input_record:
        - get_arcanna_fields (retrieve the fields added by Arcanna processing)
        - get_timestamp (retrieve the timestamp of the alert)
        - get_timestamp_inference (retrieve the Arcanna inference timestamp of the alert)
        - get_decision_points (allows you to get the current decision points of the record in form of a dictionary
          <decision_point_name, decision_point_value)
    - llm: generate (allows the usage of a Large Language Model integration, it requires integration_name and prompt
      as arguments of the function)
    - env_variables (variable containing the environment variables, e.g. env_variables["JOB_ID"] to retrieve the
      job ID)
    - parameters (dictionary with the values of the code block's declared parameters, keyed by field_name)
    You are not allowed to chain these methods.
    For any code generated, ensure that it can run using only the allowed packages and methods.
    If the user requests any package besides the ones you are allowed to use, you should politely refuse to respond
    to his request explaining the limitations.

    Be aware that we are using a sandboxing library to run the code called RestrictedPython, and some errors could
    be related to that.

    For example: If the user asks to put current timestamp in input_record you should provide the following block
    of code
    ```python
    def transform(input_record):
        # Get the current timestamp
        current_timestamp = datetime.now()
        current_timestamp = current_timestamp.strftime("%Y-%m-%d %H:%M:%S")

        # Add the current timestamp to the input_record
        input_record['timestamp'] = current_timestamp

        return input_record
    ```
    You shouldn't import datetime or any other package. You are not allowed to import packages. You are not allowed
    to chain methods.
    datetime.now().strftime("%Y-%m-%d %H:%M:%S") is not allowed. You should instead call each method separately

    Do not import any packages. Use allowed packages without importing them.

    The format of the code should follow these rules:
    - You must add an indentation of 4 spaces.
    - Return only the function body and nothing else.
    - The first line should be the function definition. The last line should be the return statement.
    """


def export_tools() -> List[Callable]:
    return [
        generate_code_instructions,
        execute_code,
        execute_code_async,
        save_code,
    ]


def _execute_body(event_id, integration_id, integration_title, parameters, storage_name) -> dict:
    if integration_id is None and not integration_title:
        raise ValueError("Either 'integration_id' or 'integration_title' must be provided.")
    return {"event_id": event_id, "integration_id": integration_id, "integration_title": integration_title,
            "parameters": parameters or {}, "storage_name": storage_name}


@handle_exceptions
@requires_scope('public')
async def generate_code_instructions() -> Any:
    """Rules and template for writing an Arcanna Python code block (sandboxed transform(input_record)).

    Call it before writing any code block, then follow the returned steps (save_code, then execute_code)."""
    return CODE_INSTRUCTIONS


@handle_exceptions
@requires_scope('execute:job_code_blocks')
async def execute_code(job_id: JobId, event_id: EventId, integration_id: IntegrationId = None,
                       integration_title: IntegrationTitle = None, parameters: Parameters = None,
                       storage_name: StorageName = None) -> Any:
    """Run a saved code block integration (role custom_code) on one stored event and wait for it.

    Returns {stdout, stderr, output_record}. Not a dry run: on success the transformed record is written back
    to the event and a log message added. Ask the user before running it. Code must be saved first with
    save_code; there is no way to run unsaved code. For long code use execute_code_async."""
    return await call('POST', "/api/v2/code_block_integrations/execute", params={"job_id": job_id},
                      json=_execute_body(event_id, integration_id, integration_title, parameters, storage_name))


@handle_exceptions
@requires_scope('execute:job_code_blocks')
async def execute_code_async(job_id: JobId, event_id: EventId, integration_id: IntegrationId = None,
                             integration_title: IntegrationTitle = None, parameters: Parameters = None,
                             storage_name: StorageName = None) -> Any:
    """Queue a saved code block integration to run on one stored event and return at once.

    The code's output is never returned; the event is updated in place when it finishes (check it with the
    events tools). Ask the user first. To see stdout/stderr use execute_code."""
    return await call('POST', "/api/v2/code_block_integrations/execute_async", params={"job_id": job_id},
                      json=_execute_body(event_id, integration_id, integration_title, parameters, storage_name))


@handle_exceptions
@requires_scope('write:iac', 'write:resources')
async def save_code(
        title: Annotated[str, Field(
            description="Unique integration title; an existing code block with it is updated.")],
        source_code: Annotated[str, Field(
            description="Full Python source: def transform(input_record): ... return input_record.")],
        description: Annotated[Optional[str], Field(description="Short description of what the code does.")] = None,
        env_variables: Annotated[Optional[List[dict]], Field(
            description="Environment variables [{name, value, is_secret}], read in code as env_variables[name].")]
        = None,
        params_definition: Annotated[Optional[List[dict]], Field(
            description="Declared parameters [{field_name, type: string|number|boolean|date|dropdown, required,"
                        " default_value, run_test_value}], read in code as parameters[field_name].")] = None,
        cpu_time_limit_seconds: Annotated[Optional[int], Field(description="CPU time limit per run (default 3).")]
        = None,
        memory_limit_mb: Annotated[Optional[int], Field(description="Memory limit per run in MB (default 30).")]
        = None,
) -> Any:
    """Create or update a code block integration (role custom_code) holding the given Python code.

    Replaces the whole code block, so resend all env variables including secrets. It does not add the code to a
    job: add a pipeline step with update_job, or run it on an event with execute_code. Show the code to the user
    and get approval before saving."""
    limits = {key: value for key, value in (("cpu_time_limit_seconds", cpu_time_limit_seconds),
                                            ("memory_limit_mb", memory_limit_mb)) if value is not None}
    code_block = {"source_code": source_code, "description": description, "role": "custom_code",
                  "integration_type_id": 1, "env_variables": env_variables or [],
                  "params_definition": params_definition or []}
    if limits:
        code_block["settings"] = {"limits": limits}
    resource = {"type": "integration", "properties": {"title": title, "code_block": code_block}}
    return await call('POST', "/api/v2/resources/iac", json={"resources": [resource]})
