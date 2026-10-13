from datetime import datetime, timezone
from typing import Annotated, Any, Callable, List, Literal, Optional

from pydantic import Field

from arcanna_mcp_server.common.errors import handle_exceptions
from arcanna_mcp_server.common.http import call
from arcanna_mcp_server.common.scopes import requires_scope

PLATFORM_SECTIONS = {
    "status": "status",
    "license": "license",
    "settings": "settings",
    "feature_flags": "feature-flags",
    "migration_status": "migration-status",
    "components": "components",
    "audit_log": "audit-log",
}


def export_tools() -> List[Callable]:
    return [
        health_check,
        get_platform_info,
        get_system_timestamp,
        delete_storage_data,
    ]


@handle_exceptions
@requires_scope('public')
async def health_check() -> Any:
    """Check that the Arcanna API is reachable and the configured API key is valid.

    Returns {status, reason, reason_details}. Use it first when every other tool fails. It says nothing about
    job or integration health: use get_job_status / check_integration_health for those."""
    return await call('GET', "/api/v2/health/")


@handle_exceptions
@requires_scope('read:platform_monitoring')
async def get_platform_info(
        section: Annotated[Literal['status', 'license', 'settings', 'feature_flags', 'migration_status', 'components',
                                   'audit_log'], Field(
            description="status: version/build; license: plan, expiry, licensed features; settings: base URL, default"
                        " LLM, MFA, telemetry; feature_flags; migration_status: last data migration; components:"
                        " integration/job counts; audit_log: audit forwarding settings.")],
        components: Annotated[Optional[List[Literal['integration', 'job']]], Field(
            description="Only for section 'components': restrict the counts to these kinds.")] = None,
) -> Any:
    """Read one section of the platform's own state: version, license, settings, feature flags, migration,
    component counts or audit forwarding config.

    A capability needs both its license feature and its feature flag. audit_log holds forwarding settings only,
    never audit entries: who did what cannot be answered here. Container/service health is not covered."""
    params = {"components": components} if section == "components" else None
    return await call('GET', f"/api/v2/platform/{PLATFORM_SECTIONS[section]}", params=params)


@handle_exceptions
@requires_scope('public')
async def get_system_timestamp() -> Any:
    """Current UTC time as an ISO 8601 string (YYYY-MM-DDTHH:MM:SSZ).

    Call it whenever the current date or time is needed, e.g. to build relative date filters."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


@handle_exceptions
@requires_scope('delete:job_storage')
async def delete_storage_data(
        storage_name: Annotated[str, Field(
            description="Display name of the storage (as shown on the job's input), not an Elasticsearch index.")],
        job_ids: Annotated[Optional[List[int]], Field(
            description="Jobs to delete from. Omit for every job using this storage, usually more than intended.")]
        = None,
        simulate: Annotated[bool, Field(
            description="True only reports which jobs and storages would be affected, deleting nothing.")] = False,
        confirm: Annotated[bool, Field(
            description="Must be true for a real deletion; only set it after the user confirmed.")] = False,
) -> Any:
    """Delete the events ingested into one named storage across jobs; jobs and their config stay.

    Irreversible. Always call with simulate=true first and show the user what would be removed; after the user
    confirms, call again with confirm=true. To delete specific events use delete_events instead."""
    return await call('POST', "/api/v2/data_management/delete", params={"simulate": simulate, "confirm": confirm},
                      json={"storage_name": storage_name, "delete_type": "SOFT", "job_ids": job_ids})
