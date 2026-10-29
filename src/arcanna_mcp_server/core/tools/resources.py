from typing import Annotated, Any, Callable, Dict, List, Literal, Optional

from pydantic import Field

from arcanna_mcp_server.common.errors import handle_exceptions
from arcanna_mcp_server.common.http import call
from arcanna_mcp_server.common.scopes import requires_scope

MASKED = "******"
RESOURCES = "/api/v2/resources"

Role = Literal['input', 'enrichment', 'context_enrichment', 'processor', 'case_creation', 'post_decision', 'output',
               'alerting', 'llm', 'graph', 'agentic_workflow', 'decision_model']
IntegrationId = Annotated[str, Field(description="Numeric id of the integration.")]
IntegrationTitle = Annotated[str, Field(description="Exact integration title; titles are unique.")]
JobTitle = Annotated[str, Field(description="Exact job title; titles are unique and identify the job.")]
LookupTitle = Annotated[Optional[str], Field(description="Exact title. Give title or id, not both.")]
LookupId = Annotated[Optional[str], Field(description="Numeric id. Give title or id, not both.")]
Confirm = Annotated[bool, Field(description="Must be true to actually delete; only set it after the user confirmed.")]
ConnectionParameters = Annotated[Dict[str, Any], Field(
    description="Connection parameters keyed by field name, as listed in get_integration_type_metadata"
                " connection_parameters.")]
PipelineIntegrations = Annotated[List[dict], Field(
    description="Ordered pipeline steps, each {title: existing integration title, integration_type: pipeline role"
                " (e.g. input, enrichment, context_enrichment, post_decision, output), enabled: bool, parameters:"
                " role parameters from get_integration_type_metadata(type, role)}. Needs at least one input; an"
                " output defaults to Arcanna's internal one. Input-only optional keys: storage_tag,"
                " skip_input_validation.")]
DecisionPoints = Annotated[List[str], Field(
    description="Dotted event field paths the model decides on, e.g. 'rule.name'. Use [] for Automation jobs.")]
CustomLabels = Annotated[Optional[List[dict]], Field(
    description="Decision labels [{name, hex_color}], at least 2 unless Automation. Omit for the category defaults.")]
AutoRetrain = Annotated[Optional[dict], Field(
    description="{enabled: bool, cron: str, blockers: {outliers, low_confidence_score, ...: bool}}.")]


def export_tools() -> List[Callable]:
    return [
        search_integrations,
        get_integration_details,
        search_jobs,
        get_job_details,
        list_integration_types,
        get_integration_type_metadata,
        get_job_category_metadata,
        create_integration,
        update_integration,
        delete_integration,
        create_job,
        update_job,
        delete_job,
        check_integration_health,
        list_llm_models,
        get_job_decision_points,
        apply_iac,
        export_iac,
        get_roles,
        upsert_roles,
        delete_roles,
    ]


def _matches(text: Optional[str], needle: Optional[str]) -> bool:
    return not needle or needle.lower() in (text or "").lower()


def _lookup(title: Optional[str], resource_id: Optional[str]) -> dict:
    if not title and resource_id is None:
        raise ValueError("Either 'title' or 'id' must be provided.")
    return {"title": title} if title else {"id": str(resource_id)}


def _job_properties(response: Any) -> List[dict]:
    return [value.get("properties", {}) for item in response or [] for value in item.values()
            if isinstance(value, dict) and value.get("type") == "job"]


def _plain_parameters(parameters: Any) -> Dict[str, Any]:
    """Stored integrations keep parameters as [{field, type, value}]; flatten them and mask secrets."""
    if isinstance(parameters, dict):
        return parameters
    return {str(p.get("field")): MASKED if p.get("type") == "password" else p.get("value")
            for p in parameters or [] if isinstance(p, dict) and p.get("field")}


def _one_resource(resource_type: str, properties: dict) -> dict:
    return {"resources": {properties["title"]: {"type": resource_type, "properties": properties}}}


async def _get_integration(title: Optional[str], integration_id: Optional[str]) -> Optional[dict]:
    found = await call('GET', RESOURCES, params={"resource_type": "integration", **_lookup(title, integration_id)})
    if not found:
        return None
    integration = dict(found[0])
    if "parameters" in integration:
        integration["parameters"] = _plain_parameters(integration["parameters"])
    return integration


@handle_exceptions
@requires_scope('read:resources')
async def search_integrations(
        title: Annotated[Optional[str], Field(description="Case-insensitive substring of the integration title.")]
        = None,
        integration_type: Annotated[Optional[str], Field(
            description="Case-insensitive substring of the integration type, e.g. 'Elasticsearch', 'Splunk'.")] = None,
        role: Annotated[Optional[Role], Field(description="Keep only integrations whose type supports this role.")]
        = None,
) -> Any:
    """Find configured integration instances (connections to external systems).

    Returns {integrations: [{name, id, integration_type, supported_roles, creatable}], total}. Use
    get_integration_details for one integration's full definition; to discover integration *types* that can
    be created, use list_integration_types."""
    integrations = await call('GET', RESOURCES, params={"resource_type": "integration"})
    metadata = await call('GET', f"{RESOURCES}/integration/metadata")
    types = {entry.get("id"): entry for entry in metadata.get("integration_types", []) if entry.get("id")}
    results = []
    for item in integrations or []:
        subcategory_id = item.get("subcategory_id")
        if not subcategory_id:
            continue
        type_info = types.get(subcategory_id, {})
        roles = type_info.get("roles", [])
        if not _matches(item.get("title"), title) or not _matches(type_info.get("name"), integration_type):
            continue
        if role and role not in roles:
            continue
        results.append({"name": item.get("title"), "id": item.get("id"), "integration_type": type_info.get("name"),
                        "supported_roles": roles, "creatable": type_info.get("creatable", True)})
    return {"integrations": results, "total": len(results)}


@handle_exceptions
@requires_scope('read:resources')
async def get_integration_details(title: LookupTitle = None, id: LookupId = None) -> Any:
    """Full definition of one configured integration: type, connection parameters, validity.

    Parameters are flattened to {field: value}; secrets always come back as '******' and cannot be read.
    Use search_integrations to find the title or id first."""
    integration = await _get_integration(title, id)
    return integration or {"error": "Integration not found"}


@handle_exceptions
@requires_scope('read:resources')
async def search_jobs(
        title: Annotated[Optional[str], Field(description="Case-insensitive substring of the job title.")] = None,
        category: Annotated[Optional[str], Field(
            description="Case-insensitive substring of the job category, e.g. 'Decision intelligence', 'Automation'.")]
        = None,
) -> Any:
    """Find jobs (use cases) by title and/or category.

    Returns {jobs: [{name, id, category, decisions (label names), decision_points}], total}. Use get_job_details
    for the full definition incl. pipeline, get_job_status for run state and health."""
    results = []
    for job in _job_properties(await call('GET', RESOURCES, params={"resource_type": "job"})):
        if not _matches(job.get("title"), title) or not _matches(job.get("category"), category):
            continue
        entry = {"name": job.get("title"), "id": job.get("id"), "category": job.get("category")}
        labels = (job.get("advanced_settings") or {}).get("custom_labels") or []
        names = [label.get("name") for label in labels if isinstance(label, dict) and label.get("name")]
        if names:
            entry["decisions"] = names
        if job.get("decision_points"):
            entry["decision_points"] = job["decision_points"]
        results.append(entry)
    return {"jobs": results, "total": len(results)}


@handle_exceptions
@requires_scope('read:resources')
async def get_job_details(title: LookupTitle = None, id: LookupId = None) -> Any:
    """Full definition of one job: category, decision points, labels, auto retrain, pipeline integrations with
    their per-job parameters (secrets masked as '******').

    For run state, errors and counters use get_job_status instead."""
    jobs = _job_properties(await call('GET', RESOURCES, params={"resource_type": "job", **_lookup(title, id)}))
    if not jobs:
        return {"error": "Job not found"}
    return jobs[0] if len(jobs) == 1 else {"jobs": jobs, "total": len(jobs)}


@handle_exceptions
@requires_scope('read:resources')
async def list_integration_types(
        role: Annotated[Optional[str], Field(
            description="Only types supporting this pipeline role, e.g. 'input', 'enrichment', 'output'.")] = None,
) -> Any:
    """Catalog of integration types that can be created, with the pipeline roles each supports.

    Returns {integration_types: [{id, name, description, creatable, roles, roles_details}]}, without parameter
    definitions; call get_integration_type_metadata for those. For already configured instances use
    search_integrations."""
    return await call('GET', f"{RESOURCES}/integration/metadata", params={"role": role})


@handle_exceptions
@requires_scope('read:resources')
async def get_integration_type_metadata(
        integration_type: Annotated[str, Field(
            description="Exact integration type name from list_integration_types, e.g. 'Elasticsearch'.")],
        role: Annotated[Optional[str], Field(
            description="Only include the pipeline parameters of this role.")] = None,
) -> Any:
    """Parameter definitions of one integration type: connection_parameters (for create_integration) and
    per-role pipeline_parameters (for a job's pipeline_integrations entry).

    Call it before create_integration or create_job."""
    return await call('GET', f"{RESOURCES}/integration/metadata", params={"type": integration_type, "role": role})


@handle_exceptions
@requires_scope('read:resources')
async def get_job_category_metadata(
        category: Annotated[Optional[str], Field(
            description="Exact category name, e.g. 'Decision intelligence'. Omit to list all categories.")] = None,
) -> Any:
    """Job categories and what each needs.

    Without category: {job_categories: [{id, name, description}]}. With one: its parameters (type, required,
    description, defaults), e.g. whether decision points, custom labels or auto retrain apply. Call it before
    create_job."""
    return await call('GET', f"{RESOURCES}/job/metadata", params={"category": category})


@handle_exceptions
@requires_scope('write:resources')
async def create_integration(
        title: Annotated[str, Field(description="Unique display name, e.g. 'Production Elasticsearch'.")],
        integration_type: Annotated[str, Field(
            description="Exact integration type name from list_integration_types, e.g. 'QRadar'.")],
        parameters: ConnectionParameters,
) -> Any:
    """Create a connection to an external system. Arcanna health-checks the connection before saving.

    Fails if the title already exists; use update_integration for that. Discover the type with
    list_integration_types and its connection_parameters with get_integration_type_metadata. Returns the new
    internal id and URL. For code block integrations use save_code."""
    body = _one_resource("integration", {"title": title, "integration_type": integration_type,
                                         "parameters": parameters})
    return await call('POST', RESOURCES, params={"overwrite": False}, json=body)


@handle_exceptions
@requires_scope('write:resources')
async def update_integration(
        title: IntegrationTitle,
        parameters: Annotated[Dict[str, Any], Field(
            description="Connection parameters to change, keyed by field name; others keep their stored value.")],
) -> Any:
    """Change connection parameters of an existing integration; the type cannot change. Health-checked before
    saving.

    Secrets cannot be read back, so every secret parameter (e.g. password, api key) must be sent again, even
    unchanged: ask the user for it. Jobs using the integration pick up the change."""
    current = await _get_integration(title, None)
    if not current:
        raise ValueError(f"Integration '{title}' not found.")
    if current.get("code_block"):
        raise ValueError("This is a code block integration; use save_code to change it.")
    merged = {**current.get("parameters", {}), **parameters}
    missing = sorted(field for field, value in merged.items() if value == MASKED)
    if missing:
        raise ValueError(f"Secret parameters must be provided again: {missing}.")
    body = _one_resource("integration", {"title": title, "integration_type": current.get("integration_type"),
                                         "parameters": merged})
    return await call('PUT', RESOURCES, json=body)


@handle_exceptions
@requires_scope('delete:resources')
async def delete_integration(title: LookupTitle = None, id: LookupId = None, confirm: Confirm = False) -> Any:
    """Delete a configured integration. Irreversible.

    Jobs using it lose that pipeline step. Confirm with the user first (name the integration and the jobs using
    it), then call again with confirm=true; without it nothing is deleted."""
    lookup = _lookup(title, id)
    if not confirm:
        return {"error": "Not deleted: ask the user to confirm, then call again with confirm=true."}
    return await call('DELETE', RESOURCES, params={"resource_type": "integration", **lookup})


@handle_exceptions
@requires_scope('write:resources')
async def create_job(
        title: Annotated[str, Field(description="Unique job title, e.g. 'Triage - Exfiltration Alerts'.")],
        category: Annotated[str, Field(
            description="Job category name from get_job_category_metadata, e.g. 'Decision intelligence'. Fixed once"
                        " created.")],
        decision_points: DecisionPoints,
        pipeline_integrations: PipelineIntegrations,
        description: Annotated[Optional[str], Field(description="Free-text purpose of the job.")] = None,
        custom_labels: CustomLabels = None,
        auto_retrain: AutoRetrain = None,
        state: Annotated[Optional[Literal['COLLECTING_DATA', 'DISABLED']], Field(
            description="COLLECTING_DATA (default) starts ingesting right away; DISABLED creates it stopped.")]
        = None,
) -> Any:
    """Create a job (use case): its category, pipeline of integrations, decision points and labels.

    Before: get_job_category_metadata(category), search_integrations for titles, get_integration_type_metadata
    (type, role) for each step's parameters. Input integrations are health-checked. Fails if the title exists;
    use update_job. Returns the new job id and URL."""
    advanced = {key: value for key, value in (("custom_labels", custom_labels), ("auto_retrain", auto_retrain))
                if value is not None}
    properties = {"title": title, "category": category, "decision_points": decision_points,
                  "pipeline_integrations": pipeline_integrations, "description": description, "state": state,
                  "advanced_settings": advanced or None}
    body = _one_resource("job", {key: value for key, value in properties.items() if value is not None})
    return await call('POST', RESOURCES, params={"overwrite": False}, json=body)


@handle_exceptions
@requires_scope('write:resources')
async def update_job(
        title: JobTitle,
        pipeline_integrations: Annotated[Optional[List[dict]], Field(
            description="Steps to add or change, same shape as create_job; a step matching a saved one (title +"
                        " role) replaces it, unlisted steps are kept. Do not copy '******' values back.")] = None,
        remove_missing_pipeline_integrations: Annotated[bool, Field(
            description="True drops saved steps not listed in pipeline_integrations.")] = False,
        decision_points: Annotated[Optional[List[str]], Field(
            description="New full list of decision point field paths; changing it needs a retrain.")] = None,
        description: Annotated[Optional[str], Field(description="New description.")] = None,
        custom_labels: CustomLabels = None,
        auto_retrain: AutoRetrain = None,
) -> Any:
    """Change an existing job; only the given fields change, the rest is kept from the saved job.

    The category cannot change. Use get_job_details to see the current definition first. Do NOT use it to
    start/stop a job (start_job, stop_job) or retrain (train_job)."""
    jobs = _job_properties(await call('GET', RESOURCES, params={"resource_type": "job", "title": title}))
    if not jobs:
        raise ValueError(f"Job '{title}' not found.")
    current = jobs[0]
    advanced = dict(current.get("advanced_settings") or {})
    advanced.update({key: value for key, value in (("custom_labels", custom_labels), ("auto_retrain", auto_retrain))
                     if value is not None})
    properties = {
        "title": title, "category": current.get("category"), "state": current.get("state"),
        "description": description if description is not None else current.get("description"),
        "decision_points": decision_points if decision_points is not None else current.get("decision_points", []),
        "decision_point_preprocessors": current.get("decision_point_preprocessors") or None,
        "advanced_settings": advanced or None,
        "pipeline_integrations": pipeline_integrations or [],
        "remove_missing_pipeline_integrations": remove_missing_pipeline_integrations,
    }
    body = _one_resource("job", {key: value for key, value in properties.items() if value is not None})
    return await call('PUT', RESOURCES, json=body)


@handle_exceptions
@requires_scope('delete:resources')
async def delete_job(title: LookupTitle = None, id: LookupId = None, confirm: Confirm = False) -> Any:
    """Delete a job with its events, feedback and models. Irreversible.

    Confirm with the user first (name the job), then call again with confirm=true; without it nothing is
    deleted. To only pause ingestion use stop_job."""
    lookup = _lookup(title, id)
    if not confirm:
        return {"error": "Not deleted: ask the user to confirm, then call again with confirm=true."}
    return await call('DELETE', RESOURCES, params={"resource_type": "job", **lookup})


@handle_exceptions
@requires_scope('read:resources')
async def check_integration_health(integration_id: IntegrationId) -> Any:
    """Test live whether an integration's external system answers now: {healthy: bool}.

    Opens a real connection, so it is slower than stored status. Use it after changing credentials or to tell a
    broken integration from a broken job. It reports healthy when there is nothing to check (no parameters, or
    External REST API whose own check errored)."""
    return await call('POST', f"{RESOURCES}/integration/{integration_id}/health-check")


@handle_exceptions
@requires_scope('read:resources')
async def list_llm_models(integration_id: IntegrationId) -> Any:
    """List the models an LLM integration can serve, each with a 'disabled' flag.

    Use it to find a valid model name before configuring anything that names one. Fails for non-LLM
    integrations."""
    return await call('GET', f"{RESOURCES}/integration/{integration_id}/llm/models")


@handle_exceptions
@requires_scope('read:resources')
async def get_job_decision_points(
        integration_subcategory_id: Annotated[int, Field(
            description="Integration type id (the id in list_integration_types) of a threat intelligence type.")],
        job_id: Annotated[Optional[int], Field(
            description="Job to flag fields already used as decision points or columns. Omit before the job"
                        " exists.")] = None,
) -> Any:
    """List the fields a threat intelligence integration type adds to events, with their Elasticsearch type and
    whether the job already uses each as a decision point or column.

    Derived from the integration's output shape, so it works before it ever ran. Other integration types are
    rejected; for a job's current decision points use get_job_details."""
    return await call('GET', f"{RESOURCES}/job/decision-points",
                      params={"integration_subcategory_id": integration_subcategory_id, "job_id": job_id})


@handle_exceptions
@requires_scope('write:iac')
async def apply_iac(
        resources: Annotated[List[dict], Field(
            description="Resources [{type: job|integration|api_key|workflow|graph, properties, reference_id?,"
                        " depends_on?}], shaped like export_iac output. Properties may use ${ref.prop} and"
                        " ${var.NAME}.")],
        variables: Annotated[Optional[dict], Field(description="Values for ${var.NAME} references.")] = None,
) -> Any:
    """Declaratively create or update several resources in one idempotent call (infrastructure as code).

    Missing resources are created, existing ones (by title) updated; unlisted ones are untouched and nothing is
    ever deleted. Use it to copy/restore configs from export_iac; for a single integration or job prefer
    create_/update_integration and create_/update_job."""
    return await call('POST', f"{RESOURCES}/iac", json={"resources": resources, "variables": variables})


@handle_exceptions
@requires_scope('read:iac')
async def export_iac(
        resource_type: Annotated[Optional[List[Literal['job', 'integration', 'api_key', 'workflow', 'graph']]], Field(
            description="Only these resource types. Omit for every type the key can read.")] = None,
        title: Annotated[Optional[str], Field(description="Only the resource with this exact title.")] = None,
        include_dependencies: Annotated[bool, Field(
            description="Also export what the selected resources depend on, e.g. a job's integrations.")] = False,
) -> Any:
    """Export resources in the declarative shape apply_iac accepts, to copy config between environments or
    version it.

    Can be large without filters; narrow by type or title. For reading one job or integration prefer
    get_job_details / get_integration_details."""
    return await call('GET', f"{RESOURCES}/iac/export",
                      params={"resource_type": resource_type, "title": title,
                              "include_dependencies": include_dependencies})


@handle_exceptions
@requires_scope('read:role')
async def get_roles(
        id: Annotated[Optional[str], Field(description="Role id. Give id or display_name, not both.")] = None,
        display_name: Annotated[Optional[str], Field(description="Role display name.")] = None,
) -> Any:
    """List custom user roles, or one by id or display name, with their permissions and job / MCP server
    access."""
    return await call('GET', "/api/v2/roles", params={"id": id, "display_name": display_name})


@handle_exceptions
@requires_scope('write:role')
async def upsert_roles(
        roles: Annotated[List[dict], Field(
            description="Roles [{display_name, description, allow_all_jobs, allow_all_mcp_servers, permissions?:"
                        " ['JOB_READ', ...], job_permission_rules?: [{job_ids, storage_tags}], mcp_servers?:"
                        " [{mcp_server, mcp_tools}], allow_all_graphs?, graph_ids?}].")],
) -> Any:
    """Create or replace custom user roles, matched on display_name.

    An existing role is overwritten in full, not merged: read it with get_roles and send the complete
    definition."""
    return await call('POST', "/api/v2/roles", json={"roles": roles})


@handle_exceptions
@requires_scope('delete:role')
async def delete_roles(
        id: Annotated[Optional[str], Field(description="Role id. Give id or display_name, not both.")] = None,
        display_name: Annotated[Optional[str], Field(description="Role display name.")] = None,
) -> Any:
    """Delete one custom role by id or display name. Irreversible; users holding it lose its access.

    Confirm with the user first."""
    return await call('DELETE', "/api/v2/roles", params={"id": id, "display_name": display_name})
