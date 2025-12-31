import frappe
import json
import numpy as np
from google import genai
from google.genai import types
from ai_integration.utils.embedding import generate_embedding_vector

# Try importing Tool Registry
try:
    from frappe_assistant_core.core.tool_registry import get_tool_registry
    HAS_FAC = True
except ImportError:
    HAS_FAC = False

_TOOL_CACHE = {}

def get_settings():
    return frappe.get_single("AI Integration Settings")

def adapt_tools_for_gemini(core_tools):
    """Adapts frappe_assistant_core tools to Google GenAI format."""
    gemini_tools = []
    for tool in core_tools:
        # tool is either a dict or an object depending on implementation
        name = getattr(tool, 'name', tool.get('name')) if hasattr(tool, 'get') else tool.name
        description = getattr(tool, 'description', tool.get('description')) if hasattr(tool, 'get') else tool.description
        input_schema = getattr(tool, 'inputSchema', tool.get('inputSchema')) if hasattr(tool, 'get') else tool.inputSchema

        func_decl = types.FunctionDeclaration(
            name=name,
            description=description,
            parameters=input_schema
        )

        # Wrap in Tool object
        gemini_tools.append(types.Tool(function_declarations=[func_decl]))

    return gemini_tools

def fetch_fac_tools(user):
    """
    Fetches available tools from Frappe Assistant Core for the given user.
    Uses a module-level cache to avoid repeated registry lookups.
    """
    if not HAS_FAC:
        return []

    # Check cache
    if user in _TOOL_CACHE:
        return _TOOL_CACHE[user]

    try:
        registry = get_tool_registry()
        core_tools = registry.get_available_tools(user)
        gemini_tools = adapt_tools_for_gemini(core_tools)

        # Cache the result
        _TOOL_CACHE[user] = gemini_tools
        return gemini_tools
    except Exception as e:
        frappe.log_error(f"Error fetching FAC tools: {str(e)}")
        return []

def answer_user_question(message):
    try:
        settings = get_settings()
        if not settings.google_api_key:
            return {"error": "Google API Key not configured."}

        # 1. Embed Query
        query_vector = generate_embedding_vector(message)
        if not query_vector:
            return {"error": "Failed to generate embedding for query."}

        # 2. Search Vector DB
        from ai_integration.utils.vector_store import get_vector_store
        vector_store = get_vector_store()

        search_results = vector_store.search(query_vector, k=20)

        scored_docs = []
        if search_results:
            valid_results = [r for r in search_results if r['score'] > 0.4]

            if valid_results:
                names = [r['name'] for r in valid_results]
                docs = frappe.get_all("AI Embedding",
                    filters={"name": ["in", names]},
                    fields=["name", "reference_doctype", "reference_name", "content"]
                )
                doc_map = {d.name: d for d in docs}

                for res in valid_results:
                    if res['name'] in doc_map:
                        scored_docs.append({
                            "score": res['score'],
                            "doc": doc_map[res['name']]
                        })

        # 3. Filter by Permission & Top K
        top_k = 5
        context_chunks = []

        for item in scored_docs:
            if len(context_chunks) >= top_k:
                break

            ref_doctype = item['doc'].reference_doctype
            ref_name = item['doc'].reference_name

            if frappe.has_permission(ref_doctype, doc=ref_name, ptype="read"):
                context_chunks.append(f"Context from {ref_doctype} ({ref_name}):\n{item['doc'].content}")

        # 4. Construct Prompt
        context_text = "\n\n---\n\n".join(context_chunks)

        system_instruction = (
            "You are a helpful assistant integrated into ERPNext. "
            "Use the provided context to answer the user's question. "
            "If the answer is not in the context, say you don't know based on the available data, "
            "but try to be helpful if it's a general question. "
            "Always be polite and professional."
        )

        full_prompt = f"{system_instruction}\n\nContext:\n{context_text}\n\nUser Question: {message}"

        # 5. Initialize Client
        api_key = settings.get_password("google_api_key")
        client = genai.Client(api_key=api_key)

        model_name = settings.google_model or "gemini-3-pro-preview"
        model_name = model_name.strip()
        if model_name.startswith("models/"):
            model_name = model_name[7:]

        # --- TOOL INTEGRATION LOGIC ---
        if HAS_FAC:
            try:
                gemini_tools = fetch_fac_tools(frappe.session.user)

                if gemini_tools:
                    # Create Chat Session
                    chat = client.chats.create(
                        model=model_name,
                        config=types.GenerateContentConfig(tools=gemini_tools)
                    )

                    # Initial Send
                    response = chat.send_message(full_prompt)

                    # Manual ReAct Loop
                    max_turns = 10
                    turn_count = 0

                    while response.function_calls and turn_count < max_turns:
                        turn_count += 1
                        response_parts = []

                        # Need registry for execution
                        registry = get_tool_registry()

                        for call in response.function_calls:
                            func_name = call.name
                            func_args = call.args

                            # Log Intent
                            frappe.logger("ai_integration").info(f"AI Tool Execution Intent: {func_name} with {func_args}")

                            try:
                                # Execute
                                result = registry.execute_tool(func_name, func_args)
                                result_data = {'result': result}
                            except (frappe.exceptions.ValidationError, frappe.exceptions.DoesNotExist) as fe:
                                # Structured error for expected business logic failures
                                error_msg = f"{type(fe).__name__}: {str(fe)}"
                                result_data = {
                                    "status": "error",
                                    "message": error_msg
                                }
                            except Exception as e:
                                frappe.log_error(f"Tool Execution Error ({func_name}): {str(e)}")
                                result_data = {'error': str(e)}

                            # Create response part
                            # Use dict directly to bypass Pydantic serialization issues in some environments
                            response_parts.append({
                                "function_response": {
                                    "name": func_name,
                                    "response": result_data
                                }
                            })

                        # Send all results back
                        if response_parts:
                            response = chat.send_message(response_parts)
                        else:
                            # Should not happen if function_calls is truthy
                            break

                    return {
                        "response": response.text,
                        "context_used": [c[:100] + "..." for c in context_chunks]
                    }

            except Exception as tool_e:
                frappe.log_error(f"Tool Orchestration Error: {str(tool_e)}")
                # Continue to fallback or return error?
                # Architect said: "gracefully degrade... without crashing"
                # If we are inside the chat logic and it crashes, we might want to fall back to simple generation
                # But we might have already consumed the prompt.
                # Let's return the error for now as it aids debugging, or we could try to call generate_content.
                # Given we might be half-way through a conversation, falling back to generate_content might be weird.
                # I'll log and return a friendly error message.
                return {"error": "An error occurred during tool processing. Please try again."}

        # --- FALLBACK / NO TOOLS ---
        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt
        )

        return {
            "response": response.text,
            "context_used": [c[:100] + "..." for c in context_chunks]
        }

    except Exception as e:
        frappe.log_error(f"Chat Error: {str(e)}")
        return {"error": str(e)}
