from typing import Any, Callable, Dict, List, Optional, Literal, Union

from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
from arcanna_mcp_server.constants import RESOURCES_CRUD_URL, INTEGRATION_METADATA_URL
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions
from arcanna_mcp_server.utils.tool_scopes import requires_scope
import requests


JOB_TYPE_MAPPING = {
    'Decision Intelligence': ['Decision intelligence', 'Event centric decision intelligence'],
    'Automation': ['Automated root cause analysis'],
}


def export_tools() -> List[Callable]:
    return [
        search_integrations,
        get_integration_details,
        search_jobs,
        get_job_details,
        list_integration_types,
        get_integration_type_metadata,
        setup_integration,
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
        roles = entry.get("pipeline_role_identifiers", [])
        if integration_subcategory_id:
            type_to_roles[integration_subcategory_id] = {
                "roles": roles,
                "name": entry.get("name")
            }
    return type_to_roles


def _extract_list(data, resource_type: str) -> List[Dict]:
    """Extract a flat list of resource dicts from the API response, tolerating multiple wrapper formats."""
    def _flatten_resource_item(item: Dict) -> Dict:
        if not isinstance(item, dict):
            return {}
        if any(key in item for key in ['title', 'name', 'id', 'internal_id', 'properties', 'subcategory_id']):
            if 'properties' in item and isinstance(item.get('properties'), dict):
                flat_item = dict(item['properties'])
                if 'type' in item and 'type' not in flat_item:
                    flat_item['type'] = item.get('type')
                return flat_item
            return item

        # Handle keyed format: {"Resource Title": {"properties": {...}, "type": "job"}}
        if len(item) == 1:
            resource_name, raw_item = next(iter(item.items()))
            if isinstance(raw_item, dict):
                if isinstance(raw_item.get('properties'), dict):
                    flat_item = dict(raw_item['properties'])
                else:
                    flat_item = dict(raw_item)
                if isinstance(resource_name, str) and not flat_item.get('title') and not flat_item.get('name'):
                    flat_item['title'] = resource_name
                if 'type' in raw_item and 'type' not in flat_item:
                    flat_item['type'] = raw_item.get('type')
                return flat_item
        return item

    if isinstance(data, list):
        return [_flatten_resource_item(item) for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in [resource_type + 's', resource_type, 'resources', 'results', 'data']:
            if key in data and isinstance(data[key], list):
                return [_flatten_resource_item(item) for item in data[key] if isinstance(item, dict)]
        if 'title' in data or 'internal_id' in data:
            return [_flatten_resource_item(data)]
    return []


def _get_field(resource: Dict, *field_names, default=None):
    for name in field_names:
        if name in resource:
            return resource[name]
    return default


def _title_matches(resource_title: str, query: Optional[str]) -> bool:
    if not query:
        return True
    return query.lower() in resource_title.lower()


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
    integrations = _extract_list(response_data, 'integration')

    results = []
    for item in integrations:
        name = _get_field(item, 'title', 'name', default='')
        int_id = _get_field(item, 'internal_id', 'id')
        int_subcategory_id = _get_field(item, 'subcategory_id', default='')
        supported_roles = role_mapping.get(int_subcategory_id, {}).get('roles', [])
        integration_type = role_mapping.get(int_subcategory_id, {}).get('name', '')

        if not _title_matches(name, title):
            continue
        if role and role not in supported_roles:
            continue

        results.append({
            'name': name,
            'id': int_id,
            'integration_type': integration_type,
            'supported_roles': supported_roles,
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
    integrations = _extract_list(response_data, 'integration')
    if not integrations:
        return {"error": "Integration not found"}
    if len(integrations) == 1:
        return integrations[0]
    return {'integrations': integrations, 'total': len(integrations)}


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
            Filter by high-level job type.
            'Decision Intelligence' includes both 'Decision intelligence' and
            'Event centric decision intelligence' categories.
            'Automation' includes 'Automated root cause analysis' category.

        Returns:
        --------
        A dict with key 'jobs' containing a list of matches.
        Each entry has: name, id, type, category, and when available:
        decisions (list of custom label names),
        decision_points (list of job decision point field paths), and
        flow (list of pipeline integration entries with integration_id, title, role).
    """
    response_data = _fetch_resources(resource_type='job')
    jobs = _extract_list(response_data, 'job')

    allowed_categories = JOB_TYPE_MAPPING.get(job_type) if job_type else None

    results = []
    for item in jobs:
        name = _get_field(item, 'title', 'name', default='')
        job_id = _get_field(item, 'internal_id', 'id')
        category = _get_field(item, 'category', default='')

        if not _title_matches(name, title):
            continue
        if allowed_categories and category not in allowed_categories:
            continue

        friendly_type = next(
            (t for t, cats in JOB_TYPE_MAPPING.items() if category in cats),
            category,
        )

        entry: Dict = {
            'name': name,
            'id': job_id,
            'type': friendly_type,
            'category': category,
        }

        advanced_settings = _get_field(item, 'advanced_settings', default={})
        custom_labels = advanced_settings.get('custom_labels', []) if isinstance(advanced_settings, dict) else []
        if isinstance(custom_labels, list):
            label_names = [
                label.get('name') for label in custom_labels
                if isinstance(label, dict) and label.get('name')
            ]
            if label_names:
                entry['decisions'] = label_names

        decision_points = _get_field(item, 'decision_points')
        if decision_points:
            entry['decision_points'] = decision_points

        pipeline = _get_field(item, 'pipeline_integrations')
        if pipeline and isinstance(pipeline, list):
            entry['flow'] = [
                {
                    'integration_id': _get_field(pi, 'internal_id', 'id', 'resource'),
                    'title': _get_field(pi, 'title', 'resource', default=''),
                    'role': _get_field(pi, 'integration_type', 'role', default=''),
                }
                for pi in pipeline
            ]

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
    jobs = _extract_list(response_data, 'job')
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
