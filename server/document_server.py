from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP("DocumentMCP", log_level="ERROR")


docs = {
    "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
    "report.pdf": "The report details the state of a 20m condenser tower.",
    "financials.docx": "These financials outline the project's budget and expenditures.",
    "outlook.pdf": "This document presents the projected future performance of the system.",
    "plan.md": "The plan outlines the steps for the project's implementation.",
    "spec.txt": "These specifications define the technical requirements for the equipment.",
}

# Metadata about documents (simulating a database)
doc_metadata = {
    "deposition.md": {"created": "2024-01-15", "author": "Legal Team", "category": "legal"},
    "report.pdf": {"created": "2024-02-20", "author": "Engineering", "category": "technical"},
    "financials.docx": {"created": "2024-03-10", "author": "Finance", "category": "financial"},
    "outlook.pdf": {"created": "2024-03-15", "author": "Analytics", "category": "business"},
    "plan.md": {"created": "2024-01-05", "author": "Project Manager", "category": "planning"},
    "spec.txt": {"created": "2024-02-01", "author": "Engineering", "category": "technical"},
}

@mcp.tool(
    name="read_doc_contents",
    description="Read the contents of a document and return it as a string.",
)
def read_document(
    doc_id: str = Field(description="Id of the document to read"),
):
    if doc_id not in docs:
        raise ValueError(f"Doc with id {doc_id} not found")

    return docs[doc_id]


@mcp.tool(
    name="edit_document",
    description="Edit a document by replacing a string in the documents content with a new string",
)
def edit_document(
    doc_id: str = Field(description="Id of the document that will be edited"),
    old_str: str = Field(
        description="The text to replace. Must match exactly, including whitespace"
    ),
    new_str: str = Field(
        description="The new text to insert in place of the old text"
    ),
):
    if doc_id not in docs:
        raise ValueError(f"Doc with id {doc_id} not found")

    docs[doc_id] = docs[doc_id].replace(old_str, new_str)



# TODO: Write a resource to return all doc id's
@mcp.resource("docs://documents",
              mime_type="application/json"
              ) 
def list_documents():
    return list(docs.keys())

# TODO: Write a resource to return the contents of a particular doc
@mcp.resource("docs://documents/{doc_id}",
              mime_type="text/plain"
              )
def get_document_content(doc_id: str):
    if doc_id not in docs:
        raise ValueError(f"Doc with id {doc_id} not found")

    return docs[doc_id]

# Write a resource to return metadata about a particular doc
@mcp.resource("docs://metadata/{doc_id}",
              mime_type="application/json"
              )
def get_document_metadata(doc_id: str):
    if doc_id not in doc_metadata:
        raise ValueError(f"Metadata for doc with id {doc_id} not found")

    return doc_metadata[doc_id]

# Write a resource to return category of metadata about docs
@mcp.resource("docs://documents/categories/{doc_id}",
              mime_type="application/json"
              )
def get_document_category(doc_id: str):
    if doc_id not in doc_metadata:
        raise ValueError(f"Metadata for doc with id {doc_id} not found")

    return {"category": doc_metadata[doc_id]["category"]}

# Wtite a resource to list documents by category
@mcp.resource("docs://categories/{category}",
              mime_type="application/json"
              )
def list_documents_by_category(category: str):
    matching_docs = [
        doc_id for doc_id, metadata in doc_metadata.items() 
        if metadata["category"] == category]

    if not matching_docs:
        raise ValueError(f"No documents found in category {category}")

    return matching_docs
# TODO: Write a prompt to rewrite a doc in markdown format
# TODO: Write a prompt to summarize a doc

@mcp.prompt()
def extract_action_items(doc_id: str = Field(description="Document to analyze")):
    """Extract actionable items from a document"""
    return f"""Please read the document '{doc_id}' and extract all action items.

                For each action item, identify:
                - What needs to be done
                - Who is responsible (if mentioned)
                - When it's due (if mentioned)
                - Priority level (if indicated)

                Format your response as a numbered list:
                1. [Action] - [Owner] - [Due date] - [Priority]

                If any information is not available, use "Not specified"."""



if __name__ == "__main__":
    mcp.run(transport="stdio")


# running using mcp dev server/document_server.py to run the server.