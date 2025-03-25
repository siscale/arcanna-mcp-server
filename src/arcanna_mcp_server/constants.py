from arcanna_mcp_server.environment import ARCANNA_HOST

# event ingestion
SEND_EVENT_URL = ARCANNA_HOST + "/api/v1/events"
SEND_EVENT_WITH_ID_URL = ARCANNA_HOST + "/api/v1/events/{}"

# event retrieval
RETRIEVE_EVENT_BY_ID_URL = ARCANNA_HOST + "/api/v1/events/{}/{}"  # /job_id/event_id

# event feedback
EVENT_FEEDBACK_URL = ARCANNA_HOST + "/api/v1/events/{}/{}/feedback"

GET_JOBS_URL = ARCANNA_HOST + "/api/v1/jobs"
GET_JOB_BY_ID_URL = ARCANNA_HOST + "/api/v1/jobs/{}"
GET_JOB_LABELS_URL = ARCANNA_HOST + "/api/v1/jobs/{}/labels"
START_JOB_URL = ARCANNA_HOST + "/api/v1/jobs/{}/start"
STOP_JOB_URL = ARCANNA_HOST + "/api/v1/jobs/{}/stop"
TRAIN_JOB_URL = ARCANNA_HOST + "/api/v1/jobs/{}/train"
GET_JOB_BY_NAME_URL = ARCANNA_HOST + "/api/v1/jobs/get_by_name"
GET_LABELS_OF_JOB_BY_NAME_URL = ARCANNA_HOST + "/api/v1/jobs/get_by_name/labels"

# healthcheck
HEALTH_CHECK_URL = ARCANNA_HOST + "/api/v1/health/"

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
