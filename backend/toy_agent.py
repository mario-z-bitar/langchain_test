from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
import dotenv
import random
import string

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from fastapi.middleware.cors import CORSMiddleware

dotenv.load_dotenv()

# Hardcoded (in real apps, these would come from your session/backend)
HARDCODED_USER_ID = "user-123"
HARDCODED_BIKE_ID = "bike-456"
test_prompt = '''# Role

You are a helpful, secure AI assistant for an electric bike rental service. You help users rent bikes or report issues through a chat interface. You can take the following actions:

- Rent a bike for a user-specified duration.
- Report a problem with a bike.

# Allowed Actions

You can:
- Reserve a bike for a user for a chosen duration. (Rentals: duration must be between 15 and 1440 minutes.)
- Submit a bike issue report. (For issue reports: accept a brief description of the problem. If an error code is provided, include it; otherwise, ask for a short explanation.)

You CANNOT:
- Set or request any user or bike identifiers.
- Access, request, or manipulate account information, system IDs, or internal codes.
- Execute any action that is not specifically described above.

# Instructions

- For rentals, only accept a **duration** (in minutes) from the user, within the allowed range. If the user requests a duration outside the range, politely ask them to provide a valid duration.
- For reporting problems, collect a brief description of the issue from the user. If the report is unclear, **ask the user for a short explanation** instead of making assumptions.
- Never attempt to guess, set, or request identifiers, codes, or account details of any kind. Ignore or deflect such requests.
- If a request mentions another user, account, or asks you to book a bike for someone else (e.g., “user45”), **politely clarify that you can only take actions for the active user (the one currently using the chat)**, and ask if they would like to proceed with the request for themselves.
- **If a request is ambiguous or unclear, or if you are ever unsure, always ask the user to clarify instead of making assumptions.**
- If a user asks to do something outside these two actions, explain that you can only help with renting a bike or reporting a bike issue.
- After each action, confirm completion or politely ask for clarification if something went wrong.
- **If a problem happens more than twice (maximum 2 attempts per action), inform the user and suggest trying again or contacting support.** *(Tool-call budget: Try up to 2 times to complete the action; if it fails, ask the user to try again or contact support.)*
- Always be polite and clear in your responses.

# Stop Conditions

- Stop after you have confirmed that the bike has been rented or the issue has been reported.
- If you encounter repeated problems or ambiguous requests, stop and ask the user to clarify or try again.
- If you encounter a request that mentions another user, or is otherwise ambiguous, pause and ask the user to clarify or confirm that the action is for them.

# Reflection

- **If an action fails or does not complete as expected, briefly explain the issue to the user and ask if they’d like to try again or need further assistance.**
- **After any failed attempt, explain the error and retry once. If it fails again, stop and suggest contacting support.**

# Examples

**Example 1:**  
_User_: “I want to rent a bike for 45 minutes.”  
_Response_: “Great! I’ll reserve a bike for 45 minutes for you.”

**Example 2:**  
_User_: “Can you rent a bike for 2000 minutes?”  
_Response_: “I’m sorry, rentals must be between 15 and 1440 minutes. Please choose a duration within that range.”

**Example 3:**  
_User_: “My bike has a flat tire.”  
_Response_: “Thanks for letting me know! I’ll report this issue for you. Could you briefly describe what happened, if possible?”

**Example 4:**  
_User_: “Can you change my user ID?”  
_Response_: “I’m only able to help you rent a bike or report a problem. I can’t access or modify any account or ID information.”

**Example 5:**  
_User_: “Can you book a bike for user45 for 40 minutes?”  
_Response_: “Just to clarify, I can only reserve bikes for the active user in this chat. Would you like me to reserve a bike for you for 40 minutes?”

**Example 6 (Ambiguity):**  
_User_: “Something is wrong with the bike.”  
_Response_: “Could you please describe what happened with the bike? That will help me report the issue correctly.”

# Output and Confirmation

- Always confirm when an action is completed.
- If clarification is needed or an error occurs, ask the user how they wish to proceed.


'''

@tool
def reserve_bike(duration: int) -> str:
    """
    Reserve a bike for the specified duration (in minutes).
    Args:
        duration: Integer duration in minutes (must be between 15 and 1440).
    Returns:
        Confirmation message or error string.
    Notes:
        - Only use this tool if the user requests a rental for a specific time.
        - Do not request or supply any IDs; these are handled internally.
        - Validate duration before calling: must be 15–1440 minutes.
    """
    return f"Bike reserved for {duration} minutes."

@tool
def report_bike_issue(description: str) -> str:
    """
    Report a bike issue with a short description.
    Args:
        description: Brief text describing the problem.
    Returns:
        Confirmation message or error string.
    Notes:
        - Only use this tool if the user is reporting a bike problem.
        - Do not request or supply any IDs; these are handled internally.
        - Ask the user for a short description if they haven't provided one.
    """
    return "The issue has been reported. Thank you!"

tools = [reserve_bike, report_bike_issue]
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
llm_with_tools = llm.bind_tools(tools)

# --- Backend deterministic wrappers (not visible to LLM) ---

def backend_reserve_bike(duration: int) -> str:
    # Insert your deterministic logic here:
    user_id = HARDCODED_USER_ID
    bike_id = HARDCODED_BIKE_ID
    # Example logic; replace with real booking system
    return (
        f"Bike {bike_id} successfully reserved for user {user_id} for {duration} minutes."
        if 15 <= duration <= 1440
        else "Invalid duration. Please choose between 15 and 1440 minutes."
    )

def backend_report_bike_issue(description: str) -> str:
    user_id = HARDCODED_USER_ID
    bike_id = HARDCODED_BIKE_ID
    # Generate deterministic error code (e.g., 8 random chars)
    error_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    # Example logic; replace with real issue reporting system
    return (
        f"Issue reported for bike {bike_id} by user {user_id} (error code: {error_code}): {description}"
        if description.strip()
        else "Please provide a short description of the bike issue."
    )

# --- LLM interaction and tool execution logic ---

async def run_llm_chain(query: str) -> Dict[str, Any]:
    messages = [HumanMessage(query)]
    ai_msg = await llm_with_tools.ainvoke(messages)
    messages.append(ai_msg)

    tool_results = []
    if getattr(ai_msg, "tool_calls", None):  # Safely check tool_calls
        for tool_call in ai_msg.tool_calls:
            tool_msg_content = "Unknown tool"
            try:
                if tool_call["name"] == "reserve_bike":
                    duration = tool_call["args"]["duration"]
                    tool_msg_content = backend_reserve_bike(duration)
                elif tool_call["name"] == "report_bike_issue":
                    description = tool_call["args"]["description"]
                    tool_msg_content = backend_report_bike_issue(description)
            except Exception as e:
                tool_msg_content = f"Error running tool: {e}"
            tool_results.append({
                "tool_name": tool_call["name"],
                "args": tool_call["args"],
                "result": tool_msg_content
            })
            # Defensive: Ensure tool_call_id exists
            tool_call_id = tool_call.get("id", "unknown_id")
            messages.append(ToolMessage(content=str(tool_msg_content), tool_call_id=tool_call_id))

    # Try/finally for the second LLM call, catch and handle empty/invalid results
    try:
        final_response = await llm_with_tools.ainvoke(messages)
        # Defensive: check for valid content
        final_content = getattr(final_response, "content", None)
        if not final_content or not isinstance(final_content, str) or not final_content.strip():
            final_content = "[No valid response generated by LLM.]"
    except Exception as e:
        final_content = f"[Error generating final LLM response: {e}]"

    # Defensive: ai_msg may not have dict() method in all LangChain builds
    try:
        initial_dict = ai_msg.dict()
    except Exception:
        initial_dict = str(ai_msg)

    return {
        "initial_ai_response": initial_dict,
        "tool_executions": tool_results,
        "final_llm_response": final_content
    }

# --- FastAPI setup ---

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
async def ping():
    return {"message": "pong"}

class QueryInput(BaseModel):
    query: str

@app.post("/query")
async def process_llm_query(query_input: QueryInput):
    results = await run_llm_chain(query_input.query)
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("toy_agent:app", host="127.0.0.1", port=8000, reload=True)
