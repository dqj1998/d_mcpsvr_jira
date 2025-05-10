import os
import logging
import json
from typing import Any, List
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from mcp_client import call_tool

global ai_client

def init_ai_caller():
    """
    Initialize AI utilities by loading environment variables and setting up the Azure OpenAI client.
    """

    # Read Azure credentials from environment variables
    os.environ['AZURE_CLIENT_ID'] = os.getenv('AZURE_CLIENT_ID')
    os.environ['AZURE_CLIENT_SECRET'] = os.getenv('AZURE_CLIENT_SECRET')
    os.environ['AZURE_TENANT_ID'] = os.getenv('AZURE_TENANT_ID')

    default_credential = DefaultAzureCredential()

    token_provider = get_bearer_token_provider(default_credential, "https://cognitiveservices.azure.com/.default")

    global ai_client
    ai_client = AzureOpenAI(azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_ad_token_provider=token_provider,
        api_version="2023-12-01-preview")

async def generate_response(messages: list, tools: Any = None) -> str:
    logging.debug(f"Tools: {tools}")
    messages_for_processing = messages.copy()  # Operate on a copy to avoid modifying the caller's list

    if tools:
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema
        } for tool in tools]
        available_tools = [{"type": "function", "function": tool} for tool in available_tools]
    else:
        available_tools = []
    response = ai_client.chat.completions.create(model="gpt-4o",
        messages=messages_for_processing,
        temperature=0.7,
        max_tokens=4000,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        tools=available_tools,
        tool_choice="auto",
        stop=None)
    while response.choices[0].message.tool_calls:
        for tool_call in response.choices[0].message.tool_calls:
            # Extract tool name and arguments
            tool_name = tool_call.function.name
            if tool_call.function.arguments:
                # Parse JSON arguments
                tool_args = json.loads(tool_call.function.arguments)
            else:
                tool_args = {}

            # Execute tool call            
            result = await call_tool(tool_name, tool_args)
            logging.debug(f"Calling tool {tool_name} with args {tool_args}: {result}")
            result_txt = ""
            if isinstance(result, str) and result.startswith("Err"):
                logging.error(f"Error in tool call: {result}")
            elif isinstance(result, list) and len(result) > 0:
                result_txt = result[0].text
            messages_for_processing.append({
                "role": "assistant",
                "content": "Called tool",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        },
                        "type": "function"
                    }
                ]
            })
            messages_for_processing.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": tool_name,
                "content": result_txt,
            })
        response = ai_client.chat.completions.create(model="gpt-4o",
            messages=messages_for_processing,
            tools=available_tools,
            tool_choice="auto",
        )
        
    logging.debug("Return the AI response: ".format(response.choices[0].message.content))
    return response.choices[0].message.content

    

def process_message(message: list, history: list, tools) -> tuple:
    """
    Process user message and generate AI response.
    Returns:
      - ai response: str
      - conversation history: list
    """
    print(f"User: {message}")
    new_history = history.copy()

    new_history+= message

    # Validate and ensure the messages list is properly formatted
    for msg in new_history:
        if "role" not in msg or "content" not in msg:
            raise ValueError("Each message must include 'role' and 'content' fields.")

    # Generate AI response based on full conversation history
    ai_response = generate_response(new_history, tools)
    print(f"AI: {ai_response}")

    # Append AI response to history
    new_history.append({"role": "assistant", "content": ai_response})

    return ai_response, new_history
