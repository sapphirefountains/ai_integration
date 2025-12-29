from frappe_mcp import MCP

mcp = MCP("ai-integration")

@mcp.register()
def handle_mcp():
    # Import tools here to ensure they are registered
    import ai_integration.ai_integration.tools.rag
    import ai_integration.ai_integration.tools.db
