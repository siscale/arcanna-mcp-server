from typing import Any, Callable, Dict, List, Optional, Literal, Union

from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
from arcanna_mcp_server.constants import RESOURCES_CRUD_URL, INTEGRATION_METADATA_URL
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions
from arcanna_mcp_server.utils.tool_scopes import requires_scope
import requests


def export_tools() -> List[Callable]:
    return [
        search_integrations,
        get_integration_details,
        search_jobs,
        get_job_details,
        list_integration_types,
        get_integration_type_metadata,
        setup_integration,
        setup_job,
    ]


def _api_headers() -> Dict[str, str]:
    return {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json",
    }


def _fetch_resources(resource_type: str = None, title: str = None, resource_id: Union[str, int] = None):
    params = {}
    if resource_type:
        params["resource_type"] = resource_type
    if title:
        params["title"] = title
    elif resource_id is not None:
        params["id"] = str(resource_id)
    response = requests.get(RESOURCES_CRUD_URL, headers=_api_headers(), params=params)
    return response.json()


def _fetch_integration_metadata(integration_type: str = None, role: str = None) -> Dict:
    params = {}
    if integration_type:
        params["type"] = integration_type
    if role:
        params["role"] = role
    response = requests.get(INTEGRATION_METADATA_URL, headers=_api_headers(), params=params)
    return response.json()


def _build_role_mapping_from_metadata(metadata: Dict) -> Dict[int, Dict]:
    """Extract an integration_subcategory_id -> list of pipeline_role_identifiers mapping."""
    type_to_roles: Dict[int, Dict] = {}
    for entry in metadata.get("integration_types", []):
        integration_subcategory_id = entry.get("id")
        roles = entry.get("roles", [])
        if integration_subcategory_id:
            type_to_roles[integration_subcategory_id] = {
                "roles": roles,
                "name": entry.get("name")
            }
    return type_to_roles

def _text_matches(text: str, text_to_match: Optional[str]) -> bool:
    if not text_to_match:
        return True
    return text_to_match.lower() in text.lower()


# ---------------------------------------------------------------------------
# Integration instance tools (search configured integrations / get details)
# ---------------------------------------------------------------------------


@handle_exceptions
@requires_scope('read:resources')
async def search_integrations(
    title: Optional[str] = None,
    role: Optional[Literal['input', 'enrichment', 'processor', 'case_creation', 'post_decision', 'output']] = None,
) -> Dict:
    """
        Search for configured integration instances with optional filtering by title and/or pipeline role.
        Returns a concise list of matching integrations.

        Parameters:
        -----------
        title : Optional[str]
            Partial or full integration name to match (case-insensitive substring search).
        role : Optional[str]
            Keep only integrations whose type supports this pipeline role.
            Available roles: 'input', 'enrichment', 'processor', 'case_creation', 'post_decision', 'output'.

        Returns:
        --------
        A dict with key 'integrations' containing a list of matches.
        Each entry has: name, id, integration_type, supported_roles.
    """
    response_data = _fetch_resources(resource_type='integration')
    metadata = _fetch_integration_metadata()
    role_mapping = _build_role_mapping_from_metadata(metadata)

    results = []
    for item in response_data:
        integration_name = item.get('title', '')
        int_id = item.get('id', '')
        int_subcategory_id = item.get('subcategory_id')
        if not int_subcategory_id:
            continue
        supported_roles = role_mapping.get(int_subcategory_id, {}).get('roles', [])
        integration_type = role_mapping.get(int_subcategory_id, {}).get('name', '')
        creatable = role_mapping.get(int_subcategory_id, {}).get('creatable', True)

        if not _text_matches(integration_name, title):
            continue
        if role and role not in supported_roles:
            continue

        results.append({
            'name': integration_name,
            'id': int_id,
            'integration_type': integration_type,
            'supported_roles': supported_roles,
            'creatable': creatable
        })

    return {'integrations': results, 'total': len(results)}


@handle_exceptions
@requires_scope('read:resources')
async def get_integration_details(
    title: Optional[str] = None,
    id: Optional[Union[str, int]] = None,
) -> Dict:
    """
        Retrieve the full definition of a specific configured integration instance.

        Parameters:
        -----------
        title : Optional[str]
            Exact title of the integration (mutually exclusive with id).
        id : Optional[Union[str, int]]
            Arcanna internal id of the integration (mutually exclusive with title).

        Returns:
        --------
        The complete integration resource as returned by Arcanna.
    """
    if not title and id is None:
        return {"error": "Either 'title' or 'id' must be provided."}

    response_data = _fetch_resources(resource_type='integration', title=title, resource_id=id)
    if not response_data:
        return {"error": "Integration not found"}
    if len(response_data) == 1:
        return response_data[0]
    return {'integrations': response_data, 'total': len(response_data)}


# ---------------------------------------------------------------------------
# Job tools (search jobs / get details)
# ---------------------------------------------------------------------------


@handle_exceptions
@requires_scope('read:resources')
async def search_jobs(
    title: Optional[str] = None,
    job_type: Optional[Literal['Decision Intelligence', 'Automation']] = None,
) -> Dict:
    """
        Search for jobs with optional filtering by title and/or job type.
        Returns a concise list of matching jobs.

        Parameters:
        -----------
        title : Optional[str]
            Partial or full job name to match (case-insensitive substring search).
        job_type : Optional[str]
            Filter by high-level job type. Possible values:
            'Decision Intelligence'
            'Event centric decision intelligence'
            'Automated root cause analysis'
            'Automation'

        Returns:
        --------
        A dict with key 'jobs' containing a list of matches.
        Each entry has: name, id, type, category, and when available:
        decisions (list of custom label names),
        decision_points (list of job decision point field paths), and
        flow (list of pipeline integration entries with integration_id, title, role).
    """
    response_data = _fetch_resources(resource_type='job')
    jobs = [v.get("properties", {}) for item in response_data for v in item.values() if v.get("type") == "job"]
        

    results = []
    for item in jobs:
        job_name = item.get('title', '')
        job_id = item.get('id', '')
        category = item.get('category', '')

        if not _text_matches(job_name, title):
            continue
            
        if not _text_matches(category, job_type):
            continue

        entry = {
            'name': job_name,
            'id': job_id,
            'category': category,
        }

        advanced_settings = item.get('advanced_settings', {})
        custom_labels = advanced_settings.get('custom_labels', []) if isinstance(advanced_settings, dict) else []
        if isinstance(custom_labels, list):
            label_names = [
                label.get('name') for label in custom_labels
                if isinstance(label, dict) and label.get('name')
            ]
            if label_names:
                entry['decisions'] = label_names

        decision_points = item.get('decision_points')
        if decision_points:
            entry['decision_points'] = decision_points
        results.append(entry)

    return {'jobs': results, 'total': len(results)}


@handle_exceptions
@requires_scope('read:resources')
async def get_job_details(
    title: Optional[str] = None,
    id: Optional[Union[str, int]] = None,
) -> Dict:
    """
        Retrieve the full definition of a specific job.

        Parameters:
        -----------
        title : Optional[str]
            Exact title of the job (mutually exclusive with id).
        id : Optional[Union[str, int]]
            Arcanna internal id of the job (mutually exclusive with title).

        Returns:
        --------
        The complete job resource as returned by Arcanna.
    """
    if not title and id is None:
        return {"error": "Either 'title' or 'id' must be provided."}

    response_data = _fetch_resources(resource_type='job', title=title, resource_id=id)
    jobs = [v.get("properties", {}) for item in response_data for v in item.values() if v.get("type") == "job"]
    if not jobs:
        return {"error": "Job not found"}
    if len(jobs) == 1:
        return jobs[0]
    return {'jobs': jobs, 'total': len(jobs)}


# ---------------------------------------------------------------------------
# Integration type metadata tools (catalog of available integration types)
# ---------------------------------------------------------------------------


@handle_exceptions
@requires_scope('read:resources')
async def list_integration_types(
    role: Optional[str] = None,
) -> Dict:
    """
        List all available integration types with their supported roles.
        Use this to discover what kinds of integrations can be created and what
        pipeline roles each type supports.

        Parameters:
        -----------
        role : Optional[str]
            If provided, only return integration types that support this pipeline role.
            Common role identifiers: 'input', 'output', 'enrichment', 'context_enrichment',
            'post_decision', 'case_creation', 'alerting', 'agentic_workflow', 'decision_model'.

        Returns:
        --------
        A dict with key 'integration_types' containing a list of entries.
        Each entry has: id, name, description, creatable, roles (display names),
        roles_details (role descriptions), pipeline_role_identifiers (internal keys
        to use when configuring pipeline_integrations in a job).
    """
    return _fetch_integration_metadata(role=role)


@handle_exceptions
@requires_scope('read:resources')
async def get_integration_type_metadata(
    integration_type: str = None,
    role: Optional[str] = None,
) -> Dict:
    """
        Get full metadata for a specific integration type, including connection
        parameters and per-role pipeline parameters.
        Use this to understand what parameters are needed to create an integration
        of this type and how to configure it within a job pipeline.

        Parameters:
        -----------
        integration_type : str
            The name of the integration type (e.g. 'Elasticsearch', 'QRadar',
            'External REST API'). Use list_integration_types() to discover available names.
        role : Optional[str]
            If provided, only include pipeline parameters for this specific role.

        Returns:
        --------
        A dict with: id, name, description, creatable, roles, roles_details,
        pipeline_role_identifiers, connection_parameters (params needed to set up
        the integration), and pipeline_parameters (per-role params needed when
        adding this integration to a job's pipeline).
    """
    if not integration_type:
        return {"error": "'integration_type' must be provided. Use list_integration_types() to discover available names."}

    return _fetch_integration_metadata(integration_type=integration_type, role=role)


# ---------------------------------------------------------------------------
# Integration setup tool (create / update an integration instance)
# ---------------------------------------------------------------------------


@handle_exceptions
@requires_scope('write:resources')
async def setup_integration(
    title: str,
    integration_type: str,
    parameters: Dict[str, Any],
    overwrite: Optional[bool] = False,
) -> Dict:
    """
        Create or update an integration with the given connection parameters.

        Before calling this tool, use list_integration_types() to discover available
        integration type names and get_integration_type_metadata() to find the
        required connection_parameters for the chosen type.

        Parameters:
        -----------
        title : str
            Display name for the integration (e.g. 'Production Elasticsearch').
        integration_type : str
            The type of integration to create (e.g. 'Elasticsearch', 'QRadar',
            'External REST API'). Must match a name from list_integration_types().
        parameters : Dict[str, Any]
            Connection parameters specific to the integration type.
            Use get_integration_type_metadata() to discover required and optional
            parameters for the chosen type.
        overwrite : Optional[bool]
            If False (default) and an integration with the same title already
            exists, the request will be rejected. Set to True to update an
            existing integration.

        Returns:
        --------
        The API response indicating success or failure, including the internal id
        and URL of the created/updated integration.
    """
    body = {
        "resources": {
            title: {
                "properties": {
                    "title": title,
                    "integration_type": integration_type,
                    "parameters": parameters,
                },
                "type": "integration",
            }
        }
    }

    response = requests.post(
        RESOURCES_CRUD_URL,
        json=body,
        headers=_api_headers(),
        params={"overwrite": overwrite},
    )
    return response.json()


# ---------------------------------------------------------------------------
# Job setup tool (create / update a job)
# ---------------------------------------------------------------------------


@handle_exceptions
@requires_scope('write:resources')
async def setup_job(
    title: str,
    category: Literal[
        'Decision intelligence',
        'Event centric decision intelligence',
        'Automated root cause analysis',
    ],
    decision_points: List[str],
    pipeline_integrations: List[Dict[str, Any]],
    description: Optional[str] = None,
    custom_labels: Optional[List[Dict[str, str]]] = None,
    auto_retrain: Optional[Dict[str, Any]] = None,
    overwrite: Optional[bool] = False,
) -> Dict:
    """
        Create or update an Arcanna job (use case) with the given configuration.
        A job defines a decision-making pipeline: data flows in from an input
        integration, passes through optional enrichment / processing / model steps,
        and the final decision is written to an output integration.

        --- Recommended workflow before calling this tool ---

        1. Call search_integrations() to list integrations already configured in
           Arcanna. Note the exact 'name' of each integration you want to use.
        2. Call list_integration_types() to see what integration types exist and
           what pipeline roles each type supports.
        3. For every integration you plan to add to the pipeline, call
           get_integration_type_metadata(type, role) to discover the required
           pipeline_parameters for that (type, role) combination.
        4. Build the pipeline_integrations list using the information gathered
           above and call this tool.

        Parameters:
        -----------
        title : str
            Display name for the job (e.g. 'Triage - Exfiltration Alerts').
        category : str
            Determines the AI model behaviour. One of:
            - 'Decision intelligence'
                Alert triage with bucket grouping. Most common choice.
            - 'Event centric decision intelligence'
                Alert triage without bucket grouping.
            - 'Automation'
                Automation job.
            - 'Automated root cause analysis'
                Clustering and root-cause analysis.
        decision_points : List[str]
            Field paths from the ingested events that the AI model will use for
            decision-making (e.g. ['alert_type', 'severity', 'source',
            'description', 'user_agent']). Use dot notation for nested fields
            (e.g. 'source.ip'). These must correspond to real fields present in
            the data ingested by the input integration.
        pipeline_integrations : List[Dict[str, Any]]
            Ordered list of pipeline steps. Each step is a dict with these keys:

            Required keys:
              - 'resource' (str): Title of the integration instance as saved in
                Arcanna. Must match an existing integration name returned by
                `search_integrations`.
              - 'integration_type' (str): The pipeline role for this step.
                Determines when this integration runs in the pipeline. Possible
                values can be discovered dynamically with list_integration_types
              - 'enabled' (bool): Whether this pipeline step is active.

            Optional keys:
              - 'parameters' (dict): Role-specific configuration. The required
                keys depend on the (integration_type, role) pair. Discover them
                by calling get_integration_type_metadata(type, role) and inspecting
                the 'pipeline_parameters' section.
            A typical pipeline has at minimum an 'input' and an 'output' step.

        description : Optional[str]
            Free-text description of the job's purpose.
        custom_labels : Optional[List[Dict[str, str]]]
            Custom decision labels the AI model can assign. Minimum 3 labels.
            Each entry is a dict with:
              - 'name' (str): label text (e.g. 'Escalate', 'Drop', 'Investigate').
              - 'hex_color' (str): colour hex code (e.g. '#ED0A2C').
            If omitted, default labels are applied:
              'Escalate' (#ED0A2C), 'Drop' (#1264FE), 'Investigate' (#9a00ff).
        auto_retrain : Optional[Dict[str, Any]]
            Automatic retraining schedule and guardrail configuration.
            Structure:
              - 'enabled' (bool): Whether automatic retraining is active.
              - 'cron' (str): Cron expression for the retrain schedule
                (e.g. '0 0 * * *' for daily at midnight).
              - 'blockers' (dict): Conditions that block retraining when true.
                  * 'consensus_flipping' (bool)
                  * 'low_confidence_score' (bool)
                  * 'undecided_consensus' (bool)
                  * 'outliers' (bool)
                  * 'consensus_changes' (bool)
            Example:
              {"enabled": true, "cron": "0 0 * * *",
               "blockers": {"undecided_consensus": true}}
            If omitted, auto-retrain is not configured.
        overwrite : Optional[bool]
            If False (default) and a job with the same title already exists,
            the request will be rejected. Set to True to update an existing job.

        Returns:
        --------
        The API response indicating success or failure, including the internal id
        and URL of the created/updated job.
    """
    properties: Dict[str, Any] = {
        "title": title,
        "category": category,
        "decision_points": decision_points,
        "pipeline_integrations": pipeline_integrations,
    }

    if description is not None:
        properties["description"] = description

    advanced_settings: Dict[str, Any] = {}
    if custom_labels is not None:
        advanced_settings["custom_labels"] = custom_labels
    if auto_retrain is not None:
        advanced_settings["auto_retrain"] = auto_retrain
    if advanced_settings:
        properties["advanced_settings"] = advanced_settings

    body = {
        "resources": {
            title: {
                "properties": properties,
                "type": "job",
            }
        }
    }

    response = requests.post(
        RESOURCES_CRUD_URL,
        json=body,
        headers=_api_headers(),
        params={"overwrite": overwrite},
    )
    return response.json()
