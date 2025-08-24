# PydanticAI typed tool example – wire to MCP clients/servers as needed
from pydantic_ai import tool
from pydantic import BaseModel

class SearchIn(BaseModel):
    query: str

class SearchOut(BaseModel):
    results: list[str]

@tool
def web_search(inp: SearchIn) -> SearchOut:
    # TODO: call an MCP client/server here
    return SearchOut(results=[f"stub result for: {inp.query}"])
