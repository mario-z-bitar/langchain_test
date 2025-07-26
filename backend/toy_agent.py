from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
import dotenv

# Import your Langchain and Google Generative AI components
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from fastapi.middleware.cors import CORSMiddleware # NEW: Import CORS middleware

# Load environment variables (for your Google API key)
dotenv.load_dotenv()

# --- Your Existing LLM Agent Code (slightly modified for async and return format) ---
@tool
def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: First integer
        b: Second integer
    """
    return a + b

@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers.

    Args:
        a: First integer
        b: Second integer
    """
    return a * b

tools = [add, multiply]

# Initialize the LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
llm_with_tools = llm.bind_tools(tools)

# Modified to be an async function and return a dictionary for JSON serialization
async def run_llm_chain(query: str) -> Dict[str, Any]:
    messages = [HumanMessage(query)]
    ai_msg = await llm_with_tools.ainvoke(messages) # Use ainvoke for async
    messages.append(ai_msg)

    tool_results = []
    if ai_msg.tool_calls:
        for tool_call in ai_msg.tool_calls:
            selected_tool = {"add": add, "multiply": multiply}[tool_call["name"].lower()]
            # Ensure tool_call["args"] is a dictionary and unpack it
            tool_msg_content = selected_tool.invoke(tool_call["args"]) # Removed the ** (double-asterisk)
            tool_results.append({
                "tool_name": tool_call["name"],
                "args": tool_call["args"],
                "result": tool_msg_content
            })
            # Add ToolMessage to the messages for the final invoke
            messages.append(ToolMessage(content=str(tool_msg_content), tool_call_id=tool_call["id"]))

    final_response = await llm_with_tools.ainvoke(messages) # Use ainvoke for async

    return {
        "initial_ai_response": ai_msg.dict(), # Convert AIMessage to dictionary
        "tool_executions": tool_results,
        "final_llm_response": final_response.content
    }

# --- FastAPI Application Setup ---
app = FastAPI() # NEW: Create the FastAPI application instance

# NEW: CORS Middleware (Crucial for frontend communication)
# This allows your Node.js frontend (which will likely run on a different port)
# to make requests to your FastAPI backend.
origins = [
    "http://localhost",
    "http://localhost:3000", # Common for frontend dev servers
    "http://localhost:3001", # Common for Node/Express static servers
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)
# NEW: Simple test endpoint to check if FastAPI and CORS are working
@app.get("/ping")
async def ping():
    return {"message": "pong"}

# NEW: Pydantic model to define the expected request body for our API
class QueryInput(BaseModel):
    query: str

# NEW: Define the API endpoint
@app.post("/query") # This means it will respond to POST requests at /query
async def process_llm_query(query_input: QueryInput):
    """
    API endpoint to receive a query and return results from the LLM agent.
    """
    results = await run_llm_chain(query_input.query)
    return results

# NEW: Standard way to run the FastAPI application when this file is executed directly
if __name__ == "__main__":
    import uvicorn
    # Make sure to run this from the 'backend' directory or adjust the app reference
    uvicorn.run("toy_agent:app", host="127.0.0.1", port=8000, reload=True)