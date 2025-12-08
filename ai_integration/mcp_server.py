import frappe
from mcp.server import Server # type: ignore
from mcp.server.stdio import stdio_server # type: ignore
import asyncio
from typing import List, Dict, Any
from ai_integration.ai_integration.doctype.ai_api_key.ai_api_key import get_api_key

# Initialize MCP Server
mcp_server = Server("ai_integration_mcp")

def get_active_llm_key(provider="Gemini API Studio"):
	"""
	Helper to retrieve LLM Key for agent operations inside MCP.
	"""
	return get_api_key(provider)


@mcp_server.list_resources()
async def list_resources() -> List[Dict[str, Any]]:
	"""
	List available resources exposed by this Frappe app via MCP.
	"""
	# Example: Exposing a list of ToDo items or similar text/data resources from Frappe
	return [
		{
			"uri": "frappe://todo/list",
			"name": "ToDo List",
			"mimeType": "application/json",
		}
	]

@mcp_server.read_resource()
async def read_resource(uri: str) -> str:
	"""
	Read a specific resource.
	"""
	if uri == "frappe://todo/list":
		# In a real app, query frappe.get_list('ToDo')
		# This requires the sync context methods if running in async loop, 
		# or using frappe.get_doc inside a sync wrapper if not supported in async directly.
		# For demonstration, returning static string.
		todos = frappe.get_all("ToDo", fields=["name", "description", "status"], limit=5)
		return str(todos)
	raise ValueError(f"Resource not found: {uri}")

@mcp_server.list_tools()
async def list_tools() -> List[Dict[str, Any]]:
	"""
	List available tools.
	"""
	return [
		{
			"name": "create_todo",
			"description": "Create a new ToDo item in Frappe",
			"inputSchema": {
				"type": "object",
				"properties": {
					"description": {"type": "string"},
					"status": {"type": "string", "enum": ["Open", "Closed"]}
				},
				"required": ["description"]
			}
		}
	]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[Any]:
	"""
	Handle tool calls.
	"""
	if name == "create_todo":
		description = arguments.get("description")
		status = arguments.get("status", "Open")
		
		# Use frappe.get_doc to insert. Warning: database access in async context 
		# might require special handling (e.g. running in thread executor)
		# For this skeleton, we are defining the structure.
		
		# Define a sync wrapper
		def _create_todo_sync(desc, stat):
			doc = frappe.get_doc({
				"doctype": "ToDo",
				"description": desc,
				"status": stat
			})
			doc.insert()
			return doc.name

		# Run sync in thread
		todo_name = await asyncio.to_thread(_create_todo_sync, description, status)
		
		return [
			{
				"type": "text",
				"text": f"Created ToDo: {todo_name}"
			}
		]

	raise ValueError(f"Tool not found: {name}")

@frappe.whitelist()
def start_stdio_server():
	"""
	Entry point to start the MCP server over stdio. 
	Can be called via 'bench execute ai_integration.mcp_server.start_stdio_server'
	"""
	import sys
	# Check if running in a suitable environment (e.g. CLI)
	asyncio.run(mcp_server.run(stdio_server()))

@frappe.whitelist()
def handle_request_via_http(request_data: Dict[str, Any]):
	"""
	Placeholder for HTTP handler if MCP over SSE/HTTP is desired.
	"""
	pass
