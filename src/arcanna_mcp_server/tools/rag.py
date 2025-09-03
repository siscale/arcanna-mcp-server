import json
from typing import Callable, List
import requests

from arcanna_mcp_server.constants import RAG_QUERY_URL, RAG_LIST_COLLECTIONS_URL
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions
from arcanna_mcp_server.utils.tool_scopes import requires_scope


def export_tools() -> List[Callable]:
    return [
        search_collection
    ]


def list_collections():
    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.get(RAG_LIST_COLLECTIONS_URL, headers=headers)
    response.raise_for_status()
    return response.json()


@handle_exceptions
@requires_scope('read:rag')
async def search_collection(query: str, collection_name=None, retrieval_level=5) -> dict:
    """
        Search through a collection of documents to find semantic related content based on the query parameter.
    Parameters:
    --------
    query (str): The text to semantically search in a collection of documents
    collection_name (str or None): The collection to search in. If collection_name is None or the parameter is not present, the search is performed in all collections
    retrieval_level (str): If parameter is not present, by default retrieval_level is 5. If not specified by the function caller, retrieval_level should not be given in the payload. The collection is split in chunks. Only one chunk(the winner chunk) will have the highest semantic score. The retrieval level
    is a number that specifies how many adjacent chunks (left and right to the winner) to be additionally retrieved. If the user specifies he wants a deeper search, retrieval level should be increased.
    Returns:
    --------
    request: dict
        A dictionary with the following keys:
        - status (str): The current status of the operation
        - reason (str): Short description of the error if one occurred; empty if successful.
        - reason_details (str): A message describing the error if one occurred; empty if successful.
    result (str): The content that can answer the query.
     """

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }

    collection_id = None
    if collection_name is not None or collection_name == "":
        collections = list_collections().get("collections", [])
        for collection in collections:
            if collection.get("collection_name") == collection_name:
                collection_id = collection.get("collection_id")

    if collection_id is None and (collection_name is not None or collection_name == ""):
        raise Exception(f"Collection with name: {collection_name} doesn't exist.")

    payload = json.dumps({
        "query": query,
        "collection_id": collection_id,
        "retrieval_level": retrieval_level
    })
    response = requests.post(RAG_QUERY_URL, data=payload, headers=headers)
    response.raise_for_status()
    return response.json()
