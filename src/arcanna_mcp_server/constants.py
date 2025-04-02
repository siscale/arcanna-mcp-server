from arcanna_mcp_server.environment import ARCANNA_HOST

# healthcheck
HEALTH_CHECK_URL = ARCANNA_HOST + "/api/v2/health/"

# custom code block
CUSTOM_CODE_BLOCK_TEST_URL = ARCANNA_HOST + "/api/v2/custom_code_execution/test"
CUSTOM_CODE_BLOCK_SAVE_URL = ARCANNA_HOST + "/api/v2/custom_code_execution/save"

# resources CRUD operations
RESOURCES_CRUD_URL = ARCANNA_HOST + "/api/v2/resources"

# integration parameters schema
INTEGRATION_PARAMETERS_SCHEMA_URL = ARCANNA_HOST + "/api/v2/resources/integration/parameters/schema"

# events operations
QUERY_EVENTS_URL = ARCANNA_HOST + "/api/v2/events/query"

FILTER_FIELDS_URL = ARCANNA_HOST + "/api/v2/filters/fields"

EVENT_FEEDBACK_URL_V2 = ARCANNA_HOST + "/api/v2/events/{}/{}/feedback"

# jobs
START_JOB_URL = ARCANNA_HOST + "/api/v2/jobs/{}/start"
STOP_JOB_URL = ARCANNA_HOST + "/api/v2/jobs/{}/stop"
TRAIN_JOB_URL = ARCANNA_HOST + "/api/v2/jobs/{}/train"

# metrics
METRICS_JOB_URL = ARCANNA_HOST + "/api/v2/metrics/job"
METRICS_JOB_AND_LATEST_MODEL_URL = ARCANNA_HOST + "/api/v2/metrics/job_and_latest_model"
METRICS_MODEL_URL = ARCANNA_HOST + "/api/v2/metrics/model"
METRICS_MODEL_URL_REQUEST_RECOMPUTE_METRICS = ARCANNA_HOST + "/api/v2/metrics/model/request_recompute_metrics"
