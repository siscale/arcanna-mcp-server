from enum import Enum


class ResourceType(str, Enum):
    API_KEY = 'api_key'
    JOB = 'job'
    INTEGRATION = 'integration'
