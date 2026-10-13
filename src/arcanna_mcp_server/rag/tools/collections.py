from typing import Annotated, Any, Callable, List, Optional

from pydantic import Field

from arcanna_mcp_server.common.errors import handle_exceptions
from arcanna_mcp_server.common.http import call
from arcanna_mcp_server.common.scopes import requires_scope

CollectionId = Annotated[str, Field(description="Id of the top level collection, as returned by"
                                                " query_rag_collections.")]
SubcollectionId = Annotated[str, Field(description="Id of the subcollection, as returned by query_rag_collections.")]
Name = Annotated[str, Field(description="Display name, unique among its siblings.")]
NewName = Annotated[str, Field(description="Name, unique among its siblings; required, send the current one to keep"
                                           " it.")]
Description = Annotated[Optional[str], Field(description="What it holds (max 1000 chars).")]
NewDescription = Annotated[Optional[str], Field(description="Description; replaces the stored one, omitting it"
                                                            " clears it.")]
Tags = Annotated[Optional[List[str]], Field(description="Free-form labels for grouping and filtering.")]
NewTags = Annotated[Optional[List[str]], Field(description="Full tag list; replaces the existing tags, omitting it"
                                                           " clears them.")]
Confirm = Annotated[bool, Field(description="Must be true to delete; set it only after the user confirmed.")]


def export_tools() -> List[Callable]:
    return [
        query_rag_collections,
        create_rag_collection,
        update_rag_collection,
        delete_rag_collection,
        create_rag_subcollection,
        update_rag_subcollection,
        delete_rag_subcollection,
        list_rag_tags,
    ]


@handle_exceptions
@requires_scope('read:rag')
async def query_rag_collections() -> Any:
    """List every knowledge base collection (id, name, description, tags, document count) with its
    subcollections nested inside.

    Documents live only in subcollections: use this to find the subcollection id upload_rag_documents needs.
    To list the documents themselves use query_rag_documents."""
    return await call('POST', "/api/v2/rag/collections/query")


@handle_exceptions
@requires_scope('write:rag')
async def create_rag_collection(name: Name, description: Description = None, tags: Tags = None) -> Any:
    """Create a top level collection and return it with its id.

    Documents cannot be uploaded into it directly: add a subcollection with create_rag_subcollection first."""
    return await call('POST', "/api/v2/rag/collections", json={"name": name, "description": description,
                                                               "tags": tags})


@handle_exceptions
@requires_scope('write:rag')
async def update_rag_collection(collection_id: CollectionId, name: NewName, description: NewDescription = None,
                                tags: NewTags = None) -> Any:
    """Change a collection's name, description and tags; all three are replaced by what is sent, so pass the
    current values (from query_rag_collections) for those that should stay. Documents are not affected."""
    return await call('PUT', f"/api/v2/rag/collections/{collection_id}",
                      json={"name": name, "description": description, "tags": tags})


@handle_exceptions
@requires_scope('write:rag')
async def delete_rag_collection(collection_id: CollectionId, confirm: Confirm = False) -> Any:
    """Permanently delete a collection with all its subcollections and every document in them (files and
    vector index entries).

    Irreversible. Confirm with the user first, then call again with confirm=true. Refused while any document
    inside is being processed. To remove only one subcollection use delete_rag_subcollection."""
    return await call('DELETE', f"/api/v2/rag/collections/{collection_id}", params={"confirm": confirm})


@handle_exceptions
@requires_scope('write:rag')
async def create_rag_subcollection(
        collection_id: Annotated[str, Field(description="Parent top level collection id (subcollections do not"
                                                        " nest further).")],
        name: Name,
        description: Description = None,
        tags: Tags = None,
) -> Any:
    """Create a subcollection under a top level collection and return it with the id upload_rag_documents needs."""
    return await call('POST', "/api/v2/rag/subcollections", json={
        "collection_id": collection_id, "name": name, "description": description, "tags": tags})


@handle_exceptions
@requires_scope('write:rag')
async def update_rag_subcollection(subcollection_id: SubcollectionId, collection_id: CollectionId, name: NewName,
                                   description: NewDescription = None, tags: NewTags = None) -> Any:
    """Change a subcollection's name, description and tags; all three are replaced by what is sent, so pass
    the current values for those that should stay. Cannot move it to another parent; documents unaffected."""
    return await call('PUT', f"/api/v2/rag/subcollections/{subcollection_id}", json={
        "collection_id": collection_id, "name": name, "description": description, "tags": tags})


@handle_exceptions
@requires_scope('write:rag')
async def delete_rag_subcollection(subcollection_id: SubcollectionId, collection_id: CollectionId,
                                   confirm: Confirm = False) -> Any:
    """Permanently delete a subcollection and every document in it (files and vector index entries); the
    parent collection stays.

    Irreversible. Confirm with the user first, then call again with confirm=true. Refused while any document
    inside is being processed."""
    return await call('DELETE', f"/api/v2/rag/subcollections/{subcollection_id}",
                      params={"collection_id": collection_id, "confirm": confirm})


@handle_exceptions
@requires_scope('read:rag')
async def list_rag_tags() -> Any:
    """List every tag in use and where it sits, under 'items': each entry names its collection, and its
    subcollection or document when the tag is on one.

    Use it to discover tag values before filtering, since tags are free-form."""
    return await call('GET', "/api/v2/rag/tags")
