"""Every MCP tool, the server/module that hosts it and the Arcanna operation(s) it calls.

op:      operationId in scripts/specs/<service>.json; gen_tools.py generates a stub from it.
ops:     for hand-written tools that call several operations (never generated).
scopes:  override when the endpoint checks its scope inside the handler, so the dumped spec cannot see it.
"""


def _core(module, op=None, ops=None, scopes=None):
    return {"server": "core", "module": module, "service": "exposer", "op": op, "ops": ops, "scopes": scopes}


def _agents(op=None, ops=None, scopes=None):
    return {"server": "agents", "module": "workflows", "service": "agents", "op": op, "ops": ops, "scopes": scopes}


def _rag(module, op):
    return {"server": "rag", "module": module, "service": "exposer", "op": op, "ops": None, "scopes": None}


TOOLS = {
    # core / jobs
    "start_job": _core("jobs", "v2_start_job"),
    "stop_job": _core("jobs", "v2_stop_job"),
    "train_job": _core("jobs", "v2_train_job"),
    "get_job_status": _core("jobs", "v2_get_job_status"),
    "get_job_input_state": _core("jobs", "v2_get_input_integration_state"),
    "reset_job_input_state": _core("jobs", "v2_reset_input_integration_state"),
    "submit_training_config_validation": _core("jobs", "v2_create_training_config_validation"),
    "get_training_config_validation": _core("jobs", ops=["v2_get_latest_training_config_validation",
                                                         "v2_get_training_config_validation"],
                                            scopes=["read:job_metrics"]),
    "list_training_config_validations": _core("jobs", "v2_list_training_config_validations"),
    "cancel_training_config_validation": _core("jobs", "v2_cancel_training_config_validation"),

    # core / resources
    "search_integrations": _core("resources", ops=["v2_get_resources", "v2_get_integration_metadata"],
                                 scopes=["read:resources"]),
    "get_integration_details": _core("resources", ops=["v2_get_resources"], scopes=["read:resources"]),
    "search_jobs": _core("resources", ops=["v2_get_resources"], scopes=["read:resources"]),
    "get_job_details": _core("resources", ops=["v2_get_resources"], scopes=["read:resources"]),
    "list_integration_types": _core("resources", ops=["v2_get_integration_metadata"]),
    "get_integration_type_metadata": _core("resources", ops=["v2_get_integration_metadata"]),
    "get_job_category_metadata": _core("resources", ops=["v2_get_job_metadata"]),
    "create_integration": _core("resources", ops=["v2_upsert_resources"], scopes=["write:resources"]),
    "update_integration": _core("resources", ops=["v2_get_resources", "v2_update"], scopes=["write:resources"]),
    "delete_integration": _core("resources", ops=["v2_delete_resources"], scopes=["delete:resources"]),
    "create_job": _core("resources", ops=["v2_upsert_resources"], scopes=["write:resources"]),
    "update_job": _core("resources", ops=["v2_get_resources", "v2_update"], scopes=["write:resources"]),
    "delete_job": _core("resources", ops=["v2_delete_resources"], scopes=["delete:resources"]),
    "check_integration_health": _core("resources", "v2_check_integration_health"),
    "list_llm_models": _core("resources", "v2_get_llm_integration_models"),
    "get_job_decision_points": _core("resources", "v2_get_job_decision_points"),
    "apply_iac": _core("resources", "v2_apply_iac"),
    "export_iac": _core("resources", "v2_export_iac"),
    "get_roles": _core("resources", "v2_get_roles"),
    "upsert_roles": _core("resources", "v2_upsert_roles"),
    "delete_roles": _core("resources", "v2_delete_roles"),

    # core / events
    "query_arcanna_events": _core("events", ops=["v2_raw_es_query_events"], scopes=["read:event_query"]),
    "count_events": _core("events", "v2_count_events", scopes=["read:event_query"]),
    "get_field_stats": _core("events", "v2_get_field_stats", scopes=["read:event_query"]),
    "get_field_groups": _core("events", "v2_get_field_groups", scopes=["read:event_query"]),
    "get_filter_fields": _core("events", ops=["v2_filters_fields"], scopes=["read:event_query"]),
    "get_fields_mapping": _core("events", ops=["v2_post_fields_mapping"], scopes=["read:event_query"]),
    "get_event_explanation": _core("events", "v2_get_event_explanation"),
    "get_similar_events": _core("events", "v2_get_similar_events"),
    "get_event_agentic_workflows": _core("events", "v2_get_event_agentic_workflows"),
    "get_job_outliers": _core("events", "v2_get_job_outliers"),
    "add_feedback_to_event": _core("events", ops=["v2_add_feedback_label"], scopes=["write:event_feedback"]),
    "clear_event_feedback": _core("events", "v2_clear_feedback_label"),
    "add_agentic_notes": _core("events", ops=["v2_add_agentic_notes"], scopes=["write:event_agentic_notes"]),
    "reprocess_events": _core("events", ops=["v2_reprocess_events"], scopes=["execute:reprocess_events"]),
    "reprocess_event_by_id": _core("events", ops=["v2_reprocess_event_by_id"], scopes=["execute:reprocess_events"]),
    "delete_events": _core("events", "v2_delete_events"),
    "ingest_event": _core("events", "v1_raw_event_input"),
    "export_event_by_id": _core("events", ops=["v1_export_event"], scopes=["read:event_export"]),
    "transfer_event": _core("events", ops=["v1_export_event", "v1_raw_event_input"],
                            scopes=["read:event_export", "write:events"]),

    # core / buckets
    "query_buckets": _core("buckets", "v2_query_buckets", scopes=["read:event_query"]),
    "get_bucket": _core("buckets", "v2_get_bucket"),
    "get_similar_buckets": _core("buckets", "v2_get_similar_buckets"),
    "reprocess_buckets": _core("buckets", "v2_reprocess_buckets"),
    "request_bucket_model_update": _core("buckets", "v2_request_model_update"),
    "request_bucket_model_update_by_filters": _core("buckets", "v2_request_model_update_by_filters",
                                                    scopes=["execute:job_operations"]),
    "approve_bucket_feedback": _core("buckets", "v2_approve_buckets_feedback"),
    "update_bucket_feedback_state": _core("buckets", "v2_update_bucket_feedback_state"),
    "delete_buckets": _core("buckets", "v2_delete_buckets"),

    # core / metrics
    "get_job_metrics": _core("metrics", ops=["v2_get_job_metrics"], scopes=["read:job_metrics"]),
    "get_job_and_model_metrics": _core("metrics", ops=["v2_get_job_and_latest_model_metrics"],
                                       scopes=["read:job_metrics", "execute:recompute_model_metrics"]),
    "get_model_metrics": _core("metrics", ops=["v2_get_model_metrics"], scopes=["read:job_metrics"]),
    "request_model_metrics_recompute": _core("metrics", ops=["v2_recompute_model_metrics"],
                                             scopes=["execute:recompute_model_metrics"]),
    "get_platform_metrics": _core("metrics", "v2_post_platform_metrics", scopes=["read:platform_monitoring"]),
    "get_internal_metrics": _core("metrics", "v2_post_internal_metrics", scopes=["read:platform_monitoring"]),
    "get_field_metrics": _core("metrics", "v2_get_field_metrics", scopes=["read:job_metrics"]),
    "export_feedback": _core("metrics", "v2_export_feedback", scopes=["read:job_metrics"]),
    "set_production_date": _core("metrics", "v2_put_production_date"),

    # core / platform
    "health_check": _core("platform", ops=["v2_get_status"], scopes=["public"]),
    "get_platform_info": _core("platform", ops=["v2_get_platform_status", "v2_get_platform_license",
                                                "v2_get_platform_settings", "v2_get_platform_feature_flags",
                                                "v2_get_platform_migration_status", "v2_get_platform_components",
                                                "v2_get_platform_audit_log"], scopes=["read:platform_monitoring"]),
    "get_system_timestamp": _core("platform", ops=[], scopes=["public"]),
    "delete_storage_data": _core("platform", "v2_data_delete", scopes=["delete:job_storage"]),

    # core / code blocks
    "generate_code_instructions": _core("code_blocks", ops=[], scopes=["public"]),
    "execute_code": _core("code_blocks", ops=["v2_execute_code_block_integration"],
                          scopes=["execute:job_code_blocks"]),
    "execute_code_async": _core("code_blocks", ops=["v2_execute_code_block_integration_async"],
                                scopes=["execute:job_code_blocks"]),
    "save_code": _core("code_blocks", ops=["v2_apply_iac"], scopes=["write:iac", "write:resources"]),

    # agents
    "list_agentic_workflows": _agents(ops=["v1_list_workflows"], scopes=["read:agents"]),
    "get_agentic_workflow_by_id": _agents(ops=["v1_get_workflow_by_id"], scopes=["read:agents"]),
    "create_agentic_workflow": _agents(ops=["v1_upsert_agentic_workflow"], scopes=["write:agents"]),
    "update_agentic_workflow": _agents(ops=["v1_get_workflow_by_id", "v1_upsert_agentic_workflow"],
                                      scopes=["write:agents"]),
    "run_agentic_workflow": _agents(ops=["v1_run_workflow"], scopes=["execute:agents"]),
    "test_agentic_workflow": _agents(ops=["v1_run_test"], scopes=["execute:agents"]),
    "list_agent_tools": _agents(ops=["v1_discover_tools"], scopes=["read:agents"]),
    "list_llm_providers": _agents(ops=["v1_list_llm_providers"], scopes=["read:agents"]),
    "get_workflow_session": _agents("v1_get_session_by_id", scopes=["read:agents"]),
    "answer_workflow_decision": _agents("v1_submit_decision", scopes=["execute:agents"]),
    "continue_workflow_session": _agents("v1_continue_from_model_input_breakpoint", scopes=["execute:agents"]),
    "stop_workflow_sessions": _agents("v1_stop_sessions_bulk", scopes=["execute:agents"]),

    # rag
    "query_rag_documents": _rag("documents", "v2_query_rag_documents"),
    "get_rag_document": _rag("documents", "v2_get_rag_document"),
    "upload_rag_documents": {**_rag("documents", None), "ops": ["v2_upload_rag_documents"], "scopes": ["write:rag"]},
    "update_rag_document": _rag("documents", "v2_update_rag_document"),
    "delete_rag_document": _rag("documents", "v2_delete_rag_document"),
    "approve_rag_document": _rag("documents", "v2_approve_rag_document"),
    "reject_rag_document": _rag("documents", "v2_reject_rag_document"),
    "retry_rag_document": _rag("documents", "v2_retry_rag_document_processing"),
    "get_rag_pipeline_status": _rag("documents", "v2_get_rag_documents_pipeline_status"),
    "query_rag_collections": _rag("collections", "v2_query_rag_collections"),
    "create_rag_collection": _rag("collections", "v2_create_rag_collection"),
    "update_rag_collection": _rag("collections", "v2_update_rag_collection"),
    "delete_rag_collection": _rag("collections", "v2_delete_rag_collection"),
    "create_rag_subcollection": _rag("collections", "v2_create_rag_subcollection"),
    "update_rag_subcollection": _rag("collections", "v2_update_rag_subcollection"),
    "delete_rag_subcollection": _rag("collections", "v2_delete_rag_subcollection"),
    "list_rag_tags": _rag("collections", "v2_list_rag_tags"),
}

DEPRECATED = {
    "upsert_resources": "create_integration / update_integration / create_job / update_job",
    "get_resources": "search_integrations / search_jobs / get_integration_details / get_job_details",
    "delete_resources": "delete_integration / delete_job",
    "integration_parameters_schema": "get_integration_type_metadata",
    "setup_integration": "create_integration",
    "setup_job": "create_job",
    "metrics_job": "get_job_metrics",
    "metrics_job_and_latest_model": "get_job_and_model_metrics",
    "metrics_model": "get_model_metrics",
    "metrics_model_request_recompute_metrics": "request_model_metrics_recompute",
    "agents_tool_discovery": "list_agent_tools",
    "get_llm_integrations": "list_llm_providers",
}
