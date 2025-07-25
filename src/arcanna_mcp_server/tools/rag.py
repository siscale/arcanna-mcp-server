from typing import Callable, List
import requests

from arcanna_mcp_server.constants import RAG_QUERY_URL
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions


def export_tools() -> List[Callable]:
    return [
        search_document
    ]


@handle_exceptions
async def search_document(query: str, collection_name=None, ) -> dict:
    """
        Search through a collection of documents to find semantic related content based on the query parameter.
    Parameters:
    --------
    query (str): The text to semantically search in a collection of documents
    collection_name (str): The collection to search in. If no collection is specified, the search is performed in all collections
    retrieval_level (str): The collection is split in chunks. Only one chunk(the winner chunk) will have the highest semantic score. The retrieval level
    is a number that specifies how many adjacent chunks (left and right to the winner) to be additionaly retrieved.
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

    response = requests.post(RAG_QUERY_URL, headers=headers)
    return response.json()
