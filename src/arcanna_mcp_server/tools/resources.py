from typing import Callable, Dict, List, Optional
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
from arcanna_mcp_server.constants import INTEGRATION_PARAMETERS_SCHEMA_URL, RESOURCES_CRUD_URL
from arcanna_mcp_server.models.base_resource import BaseResource
from arcanna_mcp_server.models.resource_type import ResourceType
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions
import requests


def export_tools() -> List[Callable]:
    return [
        integration_parameters_schema,
        upsert_resources,
        get_resources,
        delete_resources,
    ]


@handle_exceptions
async def integration_parameters_schema(integration_type: Optional[str] = None, role: Optional[str] = None) -> Dict:
    """
        Returns the parameters definition for all integrations (or a selected one) as a JSON schema.
        Can be used to determine the types of the integration parameters and determine which are required.
        Some of the parameters given when creating or updating an integration definitions are optional.
        This is specified as such in the response of this endpoint.

        Calling this endpoint with the role parameter returns the type and other specifications of parameters
        needed when creating a job with this type of integration. Integration <-> job parameters are given
        when creating or updating a job using the /api/v2/resources endpoint on the
        job_resource.pipeline_integrations.parameters path. Expected parameters must be specified depending
        on job_resource.pipeline_integrations.role value.
    """
    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }

    params = {}

    if integration_type:
        params["integration_type"] = integration_type

    if role:
        params["role"] = role

    response = requests.get(INTEGRATION_PARAMETERS_SCHEMA_URL, headers=headers, params=params)
    return response.json()


@handle_exceptions
async def upsert_resources(resources: Dict[str, BaseResource], overwrite: Optional[bool] = False) -> Dict:
    """
        Execute a request that creates or updates a set of resources. 
        Resources are given as a JSON document in which on the top level the keys
        are the identifiers of the resources and the values are the resource definitions.

        If the resources don't exist they will be created. If they exists they will be overwritten.
        If the overwrite parameter is set to false an exception will be raised and no change will be made
        to the given set of resources.

        Available resource types that can be created or updated are:
        - 'api_key', 'integration', 'job'.

        Request is handled in a generic way as parameters for each type of available resource can differ.

        The end goal is to be able to create or update a job (alias for use case).

        When updating the job, always call get_resources() by title to make sure you are not overwriting by mistake parameters that 
        are already found in the job. Parameters present in the job shouldn't be changed if the user doesn't explicity requests for it.
        When attempting to update an existing job always confirm with the user before calling upsert_resources().

        job.properties.pipeline_integrations.parameters can be discovered by calling integration_parameters_schema() based on
        integration_type. They are dynamic for each integration, and they change by the role they have in the pipeline.
        Role of an integration in the job's pipeline_integrations is specified by the parameter
        job.properties.pipeline_integrations.integration_type.

        --------------------------

        The base structure of a resource of type 'api_key' is the following (placeholders are between angular brackets <>):
        {
            '<api_key_identifier>': {
                'properties': {
                    'name': '<api_key_name>',
                },
                'type': 'api_key'
            }
        }

        Placeholder details:

        '<api_key_identifier>' is used for referencing the resource in the request. It is not saved on arcanna in any way.

        '<api_key_name>' represents the name which will be used to save the api key in arcanna.


        The definition of this type of resource is fixed, it doesn't use any dynamic parameters as other type of resources.

        Internally an api key can be used for an integration of type 'External REST API'.
        This type of integration ca be used to send events to arcanna for ingestion.

        When sending events via an integration of type 'External REST API' the value of the api key must be used, not the name.
        Take notice that the value is returned in the response only when creating the api key.
        If the api key with the same title exists it won't return is value again. So the value should be presented to the user or saved locally for later use.

        --------------------------

        The base structure of a resource of type 'integration' is the following (placeholders are between angular brackets <>):
        
        {
            '<integration_identifier>': {
                'properties': {
                    'title': '<integration_title>',
                    'integration_type': '<integration_type>',
                    'parameters': {
                        '<param_key_1>': '<param_value_1>'
                    }
                },
                'type': 'integration'
            }
        }

        Placeholders details:

        '<integration_identifier>': is used for referencing the resource in the request. It is not saved in arcanna.

        '<integration_title>' represents the title of the integration, which will be saved in arcanna.

        '<integration_type>': Available values for integration types and their available parameters
        can be retrieved by calling integration_parameters_schema(). Response is returned as a JSON schema. 
        'integration_type' can be any of the keys from integration_parameters_schema() response on the properties path.
        Examples can be: 'Elasticsearch', 'External REST API', 'QRadar', 'VirusTotal', etc.

        'parameters': <param_key_1>, <param_value_1> keys and values are dynamic for each type of integration.
        They are described  in the response from  integration_parameters_schema() on the path
        properties.<integration_type>.properties. Being returned as a JSON schema the data type, description,
        mandatory requirement or available valid values for each parameter can be deduced by analysing fields such as:
        'type', 'required' and 'enum' in the response.

        Defining an integration helps defining an external entity to arcanna with the connection details.

        --------------------------

        The base structure of a resource of type job is the following (placeholders are between angular brackets <>):

        {
            '<job_identifier>': {
                'properties': {
                    'title': '<job_title>',
                    'description': '<job_description>',
                    'category': <job_category>',
                    'decision_points': [
                        '<decision_point_name1>', '<decision_point_name2'>
                    ],
                    'advanced_settings: [
                        'custom_labels': [
                            {
                                'name': '<label_name>',
                                'hex_color': '<hex_color>'
                            }
                        ]
                    ],
                    'pipeline_integrations': [
                        {
                            'resource': '<resource_identifier>',
                            'integration_type': '<integration_role>',
                            'enabled': true,
                            'parameters': {
                                '<param_key_1>': '<param_value_1>'
                            }
                        }
                    ],
                    'remove_missing_pipeline_integrations': false
                },
                'type': 'job'
            }
        }

        Placeholder details:

        '<job_identifier>': is used for referencing the resource in the request. It is not saved in arcanna.

        '<job_title>': represents the title of the job, which will be saved in arcanna.

        '<job_description>': description of the job, to be saved in arcanna. it's used just for informative purposes.

        '<job_category>': Arcanna suports the following types of jobs: 'Decision intelligence', 'Event centric decision intelligence'
        and 'Automated root cause analysis'. 'Decision intelligence' does alert triage by tagging alerts with different labels.
        For ease of use this type of jobs groups alerts by the selected decision points set. A group of alerts with the same decision points
        set is called bucket. By doing this groupping the amount of feedback the user must give is reduced.
        'Event centric decision intelligence' is similar with Decision intelligence in the sense that it does the same
        alert triage. However in this case there is no grouping in buckets. 'Automated root cause analysis' jobs do clustering
        of alerts by a set of fields and within a clusters it splits the events between a root cause and sympthomps. All type of
        jobs are not making any decisions until user feedback is given and a neural network is trained using this feedback.

        By selecting one of the available job categories the 'pipeline_integrations' will have automatically added an integration
        with role 'processor'. In the case of 'Automated root cause analysis jobs' the job will have two 'processor' integrations
        added: one will be doing clustering and one root cause - sympthom classification inside the cluster.

        Predominantly, users will want to create 'Decision intelligence' jobs.

        '<decision_point_name1>': represents the path of input fields which are used by arcanna in the alert triage procesess.
        Nested fields used dot notation. E.g.: source.ip, source.domain. Only the selected will be used in training and
        decision making.

        '<label_name>', '<hex_color>': - are the labels which are used to split alerts in different categories.
        label_name is the user friendly displayed name. Internally arcanna will use labels ids with the format 
        'label_n' where n is gradually incremented from 0 to n number of labels. 'hex_color' is the hex color code
        used by the label to display this category in Arcanna's UI. A job has a mandatory number of 3 labels.
        If no labels are given the job will be created with default labels for the given 'job_category'. For 
        'Decision intelligence' jobs the default labels will be: 'Escalate', 'Drop', 'Investigate'.
    
        
        '<resource_identifier>' - A job is build from multiple integrations with different roles: 'input', 'processor',
        'output', etc. 
        This field can specify:
            - either the name of the resource. In case this is used the resource must be defined in the same request.
              Take notice that defining the integration in the same request will override the integration if an integration
              with the same title exists in Arcanna.
            - the title of integration as it was saved in arcanna on a previous resource create/update.
            - a query expression where we reference an existing resource eiter by title or by internal id. E.g.:
            "{{integrations(title='Elastic integration')}}", {{integrations(internal_id=1001)}}
        
        '<integration_role>' - Represents the role the integration has in the job. The roles
        in this case can be: 'input', 'processor', 'output', 'enrichment', 'case_creation', 'post_decision'. An integration
        can have multiple roles. For example an Elasticsearch integration can be used both as input and as output.
        All integration types which support a particular role can be discovered by calling integration_parameters_schema()
        with the optional role argument specified.

        'parameters': <param_key_1>, <param_value_1> keys and values are dynamic for each type of integration.
        This are different than integration connection parameters, which are given when defining the integration.
        This represents the parameters that can be used in the combination job <-> integration <-> role.
        To discover the parameters, as well as their data type, description, mandatory requirement or available valid values
        integration_parameters_schema() must be called with the role parameter specified. The parameters are returned as a 
        JSON schema and information about them can be found in the response on path properties.<integration_type>.properties.


        A job allows to define a flow by chaining integrations to collect data, making alert triage, do some post
        decisions and saving the results. Usually a job covers a use case for a class of security threats.

        If the 'pipeline_integrations' is given empty and the job exists it will leave the resulting job.pipeline_integrations
        unchanged.


        Examples:

        1). Decision intelligence job with an External REST API input and an Elasticsearch output.
        
        Request: 
        {
            "Api Key": {
                "properties": {
                    "name": "Api Key from REST API"
                },
                "type": "api_key"
            },
            "Elasticsearch from REST API": {
                "properties": {
                    "title": "Elasticsearch from REST API",
                    "integration_type": "Elasticsearch",
                    "parameters": {
                        "hosts": "192.168.175.175",
                        "password": "elastic",
                        "port": 9200,
                        "schema": "https",
                        "user": "elastic"
                    }
                },
                "type": "integration"
            },
            "Exposer integration from REST API": {
                "properties": {
                    "title": "Exposer integration from REST API",
                    "integration_type": "External REST API",
                    "parameters": {
                        "api_key": "{{api_keys(name='Api Key from REST API')}}",
                        "data_type": "JSON alerts"
                    }
                },
                "type": "integration"
            },
            "Exposer input job from REST API": {
                "properties": {
                    "title": "Exposer input job from REST API",
                    "description": "This is a sample job",
                    "category": "Decision intelligence",
                    "decision_points": [
                        "event.outcome",
                        "event.category"
                    ],
                    "advanced_settings": {
                        "custom_labels": [
                            {
                                "name": "Important",
                                "hex_color": "#a83232"
                            },
                            {
                                "name": "Discard",
                                "hex_color": "#030bff"
                            },
                            {
                                "name": "Potential risk",
                                "hex_color": "#ffcd03"
                            }
                        ]
                    },
                    "pipeline_integrations": [
                        {
                            "resource": "Exposer integration from REST API",
                            "integration_type": "input",
                            "enabled": true,
                            "parameters": {
                                "exposed_rest_api_job_tag": "rest_api_exposer",
                                "max_batch_size": 100
                            }
                        },
                        {
                            "resource": "Elasticsearch from REST API",
                            "integration_type": "output",
                            "enabled": true,
                            "parameters": {}
                        }
                    ]
                },
                "type": "job"
            }
        }

        Response:
        {
            "request": {
                "status": "OK"
            },
            "created": [
                {
                "type": "api_key",
                "resource_name": "Api Key",
                "title": "Api Key from REST API",
                "internal_id": "vGWeqZUB_vwgb0JGPPGE",
                "url": "https://192.168.175.175/api-keys",
                "value": "liNUI2_Ppr5YMag1YD4yuztjH-zlWf7n3C9udVy6QKPGIbisqzJgc-1jdbnbgfi9jCPaaTPj5qkEq5SamNUVCw"
                },
                {
                "type": "integration",
                "resource_name": "Exposer integration from REST API",
                "title": "Exposer integration from REST API",
                "internal_id": 1234,
                "url": "https://192.168.175.175/integrations/1234/edit"
                },
                {
                "type": "integration",
                "resource_name": "Elasticsearch from REST API",
                "title": "Elasticsearch from REST API",
                "internal_id": 1235,
                "url": "https://192.168.175.175/integrations/1235/edit"
                },
                {
                "type": "job",
                "resource_name": "Exposer input job from REST API",
                "title": "Exposer input job from REST API",
                "internal_id": 1316,
                "url": "https://192.168.175.175/use-cases/overview/1316"
                }
            ],
            "updated": []
        }

    """
    try:
        for resource_id, resource in resources.items():
            resources[resource_id] = resource.model_dump()

        body = {
            "resources": resources
        }

        headers = {
            "x-arcanna-api-key": MANAGEMENT_API_KEY,
            "Content-Type": "application/json"
        }

        params = {
            "overwrite": overwrite
        }

        response = requests.post(RESOURCES_CRUD_URL, json=body, headers=headers, params=params)
        response_json = response.json()
    except Exception as e:
        return {"error": str(e)}
    return response_json


async def get_resources(
        resource_type: Optional[ResourceType] = None, title: Optional[str] = None, id: Optional[str] = None) -> Dict:
    """
        Returns a list of resources. Parameters behave as filters.
        If no parameter is provided all available resources from arcanna are returned. Information about jobs/use cases
        is minimal if no filters are provided. To get full information about a resource it must be called with title, id
        filter present.

        Parameters:
        -----------
        resource_type : Optional[str]
            Type of resource you want to filter. If not provided it will apply the other filters on all type of resources.
            Available resource types are: api_key, integration or job.
        title : Optional[str]
            The title or name of the searched resource (mutually exclusive with id)
        id : str
            The arcanna internal id of the searched resource (mutually exclusive with title)
    """
    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }

    params = {}

    if resource_type:
        params["resource_type"] = resource_type

    if title:
        params["title"] = title
    elif id:
        params["id"] = id

    response = requests.get(RESOURCES_CRUD_URL, headers=headers, params=params)
    return response.json()


async def delete_resources(
        resource_type: ResourceType, title: Optional[str] = None, id: Optional[str] = None) -> Dict:
    """
        Returns a list of resources. Parameters behave as filters.
        If no parameter is provided all available resources from arcanna are returned.

        Parameters:
        -----------
        resource_type : Optional[str]
            Type of resource for which the delete operation will take place.
            Available resource types are: api_key, integration or job.
        title : Optional[str]
            The title or name of resource that will be deleted (mutually exclusive with id)
        id : str
            The arcanna internal id the resource that will be deleted (mutually exclusive with title)
    """
    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }

    params = {
        "resource_type": resource_type
    }

    if title:
        params["title"] = title
    elif id:
        params["id"] = id

    response = requests.delete(RESOURCES_CRUD_URL, headers=headers, params=params)
    return response.json()
