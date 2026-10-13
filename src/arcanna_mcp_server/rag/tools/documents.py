import base64
import mimetypes
from typing import Annotated, Any, Callable, List, Literal, Optional

from pydantic import Field

from arcanna_mcp_server.common.errors import handle_exceptions
from arcanna_mcp_server.common.http import call
from arcanna_mcp_server.common.scopes import requires_scope

BASE = "/api/v2/rag/documents"

DocumentId = Annotated[str, Field(description="Id of the document, as returned by query_rag_documents.")]
CollectionFilter = Annotated[Optional[str], Field(
    description="Restrict to one top level collection (covers all its subcollections).")]
SubcollectionFilter = Annotated[Optional[str], Field(
    description="Restrict to one subcollection; when set, collection_id is ignored.")]


def export_tools() -> List[Callable]:
    return [
        query_rag_documents,
        get_rag_document,
        upload_rag_documents,
        update_rag_document,
        delete_rag_document,
        approve_rag_document,
        reject_rag_document,
        retry_rag_document,
        get_rag_pipeline_status,
    ]


@handle_exceptions
@requires_scope('read:rag')
async def query_rag_documents(
        collection_id: CollectionFilter = None,
        subcollection_id: SubcollectionFilter = None,
        search: Annotated[Optional[str], Field(description="Substring match on the document name only.")] = None,
        status: Annotated[Optional[Literal['pending', 'processing', 'in_review', 'approved', 'rejected', 'failed']],
                          Field(description="Ingestion stage; documents are searchable only once 'approved'.")]
        = None,
        rag_status: Annotated[Optional[Literal['idle', 'pending', 'loading', 'success', 'error']], Field(
            description="Vector indexing stage; 'error' = approved but failed to index.")] = None,
        sort_by: Annotated[Literal['created_at', 'updated_at', 'name', 'file_size', 'confidence_score'], Field(
            description="Sort field.")] = 'updated_at',
        sort_order: Annotated[Literal['asc', 'desc'], Field(description="Sort direction.")] = 'desc',
        page: Annotated[int, Field(description="1-based page number.")] = 1,
        page_size: Annotated[int, Field(description="Documents per page, at most 100.")] = 50,
) -> Any:
    """Page through knowledge base documents: name, collection, status, rag_status, tags, plus the total count.

    Filters by collection and pipeline status; search matches names only. Does NOT search or return document
    contents, use get_rag_document for one document's content."""
    return await call('POST', f"{BASE}/query", json={
        "collection_id": collection_id, "subcollection_id": subcollection_id, "search": search, "status": status,
        "rag_status": rag_status, "sort_by": sort_by, "sort_order": sort_order, "page": page,
        "page_size": page_size})


@handle_exceptions
@requires_scope('read:rag')
async def get_rag_document(document_id: DocumentId) -> Any:
    """Get one document with full metadata, activity history, error (if failed) and extracted markdown.

    The response is large: find the document with query_rag_documents first."""
    return await call('GET', f"{BASE}/{document_id}")


def _file_part(document: dict) -> tuple:
    filename = document.get("filename")
    if not filename:
        raise ValueError("every document needs a filename")
    if document.get("content_base64") is not None:
        payload = base64.b64decode(document["content_base64"])
    elif document.get("content") is not None:
        payload = str(document["content"]).encode("utf-8")
    else:
        raise ValueError(f"document {filename} needs content or content_base64")
    return "files", (filename, payload, mimetypes.guess_type(filename)[0] or "application/octet-stream")


@handle_exceptions
@requires_scope('write:rag')
async def upload_rag_documents(
        collection_id: Annotated[str, Field(
            description="SUBCOLLECTION id to upload into (a top level collection id is rejected).")],
        documents: Annotated[List[dict], Field(
            description="Files as {filename, content} (UTF-8 text) or {filename, content_base64} (binary)."
                        " The extension sets the format: pdf, docx, xlsx, pptx, html, csv, md, txt.")],
) -> Any:
    """Upload files into a subcollection and start extraction. Returns accepted and rejected (with reason)
    documents; partial success is normal.

    Documents come back 'pending'. When approval is enabled nothing is indexed until approve_rag_document runs
    on each 'in_review' document. Track progress with get_rag_document or get_rag_pipeline_status. Create a
    subcollection first with create_rag_subcollection if needed."""
    files = [_file_part(document) for document in documents]
    return await call('POST', BASE, files=files, data={"collection_id": collection_id})


@handle_exceptions
@requires_scope('write:rag')
async def update_rag_document(
        document_id: DocumentId,
        name: Annotated[Optional[str], Field(
            description="New name, keeping the original file extension. Omit to leave unchanged.")] = None,
        description: Annotated[Optional[str], Field(
            description="New description; replaces the stored one, omitting it clears it.")] = None,
        tags: Annotated[Optional[List[str]], Field(
            description="Full tag list; replaces the existing tags, omitting it clears them.")] = None,
) -> Any:
    """Change a document's name, description or tags. Does not touch the file, content or status.

    Description and tags are replaced, not merged: read the current values with get_rag_document and send
    them back to keep them."""
    return await call('PUT', f"{BASE}/{document_id}", json={"name": name, "description": description, "tags": tags})


@handle_exceptions
@requires_scope('write:rag')
async def delete_rag_document(
        document_id: DocumentId,
        confirm: Annotated[bool, Field(
            description="Must be true to delete; set it only after the user confirmed.")] = False,
) -> Any:
    """Permanently delete a document, its file and its vector index entries; it leaves semantic search at once.

    Irreversible. Confirm with the user first, then call again with confirm=true. Refused while the document
    is being processed. To keep the file but mark it unwanted, use reject_rag_document."""
    return await call('DELETE', f"{BASE}/{document_id}", params={"confirm": confirm})


@handle_exceptions
@requires_scope('write:rag')
async def approve_rag_document(
        document_id: DocumentId,
        markdown_content: Annotated[Optional[str], Field(
            description="Corrected markdown to store before indexing. Omit to approve the extracted content.")]
        = None,
) -> Any:
    """Approve an 'in_review' document and queue it for vector indexing, which makes it searchable.

    Other states are refused. Indexing is async: watch rag_status via get_rag_document."""
    return await call('POST', f"{BASE}/{document_id}/approve", json={"markdown_content": markdown_content})


@handle_exceptions
@requires_scope('write:rag')
async def reject_rag_document(
        document_id: DocumentId,
        reason: Annotated[Optional[str], Field(description="Why it was rejected; kept in the activity log.")]
        = None,
) -> Any:
    """Reject an 'in_review' or 'approved' document; the document and file are kept (reversible).

    Rejecting an already approved document does NOT remove its vector index entries: use delete_rag_document
    if it must stop being retrievable."""
    return await call('POST', f"{BASE}/{document_id}/reject", json={"reason": reason})


@handle_exceptions
@requires_scope('write:rag')
async def retry_rag_document(document_id: DocumentId) -> Any:
    """Re-run extraction on a 'failed' document (back to 'pending', error cleared). Other states are refused.

    Check the error on get_rag_document and fix its cause first."""
    return await call('POST', f"{BASE}/{document_id}/retry")


@handle_exceptions
@requires_scope('read:rag')
async def get_rag_pipeline_status(
        collection_id: CollectionFilter = None,
        subcollection_id: SubcollectionFilter = None,
) -> Any:
    """Count documents per stage: 'doc_pipeline' (extraction and review) and 'rag_pipeline' (vector indexing),
    for one collection/subcollection or the whole knowledge base.

    Answers how much is waiting or failed; for one document's state use get_rag_document."""
    return await call('GET', f"{BASE}/pipeline-status",
                      params={"collection_id": collection_id, "subcollection_id": subcollection_id})
