from ai_prompts import init_prompt_map
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.identity import ClientSecretCredential
from azure.identity import DefaultAzureCredential
from azure.identity import get_bearer_token_provider
from azure_ai_caller import generate_response, init_ai_caller
import os
import copy
import logging
import asyncio
from server import init_project
from sqlite import init_project_db
from util import init_logger

from mcp_client import list_tools  # Import the copy module for deep copying

load_dotenv()

init_ai_caller()

ai_prompts = init_prompt_map()

async def gen_vector_prompt(user_prompt):
    """
    Generate a prompt for the AI model based on user input.
    """
    new_prompts = replace_prompt("gen_vector_prompt", "{user_input}", user_prompt)
    
    # Generate response using the updated prompts
    response = await generate_response(new_prompts)

    return response

def replace_prompt(prompt_key, place_holder, user_prompt):
    """
    Replace the place_holder placeholder in the prompt with the actual user input.
    """
    prompts = copy.deepcopy(ai_prompts.get(prompt_key, []))  # Use deepcopy to avoid modifying the original map
    if not isinstance(prompts, list):
        raise TypeError(f"Expected 'ai_prompts[\"{prompt_key}\"]' to be a list")

    # Replace {place_holder} in the 'content' field of each dictionary in the list
    for prompt in prompts:
        if 'content' in prompt:
            prompt['content'] = prompt['content'].replace(f"{place_holder}", user_prompt)

    return prompts

def format_jira_result(result):
    """
    Format a Jira result dictionary into a human-readable string.
    """
    metadata = {item['name']: item['value'] for item in result.get('metadata', [])}
    formatted_result = (
        f"Ticket: {metadata.get('id', 'N/A')}\n"
        f"URL: {metadata.get('url', 'N/A')}\n"
        f"Issue Type: {metadata.get('issuetype', 'N/A')}\n"
        f"Project: {metadata.get('project', 'N/A')}\n"
        f"Reporter: {metadata.get('reporter', 'N/A')}\n"
        f"Assignee: {metadata.get('assignee', 'N/A')}\n"
        f"Priority: {metadata.get('priority', 'N/A')}\n"
        f"Status: {metadata.get('status', 'N/A')}\n"
        f"Description: {result.get('text', 'N/A')}\n"
    )
    return formatted_result

# Simple Chat Loop
async def chat_loop():
    print("Welcome to the Jira Information Chat ('exit' to quit)")
    output_count = 5  # Default output count for Jira tickets

    mcp_tools = await list_tools()
    logging.debug(f"Available tools: {mcp_tools}")
    
    cur_project = None

    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ["exit", "quit"]:
            break
        
        # Handle '?' or 'help' command to display available commands
        if user_input in ["?", "help"]:
            print("Bot: Available commands:")
            print("  p>xxxx   - Set the current project.")
            print("  c>N      - Set the output count of Jira tickets to N (e.g., c>3).")
            print("  !>xxxx   - Ignore the GenAI optimization and search AI Search directly with 'xxxx'.")
            print("  exit/quit - Exit the chat.")
            print("  ? or help - Display this help message.")
            continue
        
        # Handle 'c>N' command to set output count
        if user_input.startswith("c>"):
            try:
                output_count = int(user_input[2:])
                print(f"Bot: Output count set to {output_count}")
            except ValueError:
                print("Bot: Invalid count. Please use 'c>N' where N is a number.")
            continue
        
        # Handle 'p>xxxx' command to set current project
        if user_input.startswith("p>"):
            cur_project = user_input[2:]
            # Initialize the project in the database
            init_result = init_project(cur_project)
            if init_result.startswith("Err") and not init_result.startswith("Err001:"):
                print(f"Bot: Error initializing project '{cur_project}': {init_result}")
                cur_project = None
            else:
                print(f"Bot: Project '{cur_project}' initialized successfully.")
                print(f"Bot: Current project set to '{cur_project}'")
            continue

        # Handle '!>xxxx' command to bypass gen_vector_prompt
        if user_input.startswith("!>"):
            messages_for_ai = [{"role": "user", "content": user_input[2:]}]
            if cur_project:
                messages_for_ai.append({"role": "system", "content": "Current project is " + cur_project})
            jira_results = await generate_response(messages_for_ai, mcp_tools)
        else:
            gen_vector_prompt_response = await gen_vector_prompt(user_input)
            new_prompts = replace_prompt("query_tickets_with_mcptools", "{user_input}", gen_vector_prompt_response)
            if cur_project:
                new_prompts.append({"role": "system", "content": "Current project is " + cur_project})
            jira_results = await generate_response(new_prompts, mcp_tools)
        
        if not jira_results:
            print("Bot: No relevant Jira information found.")
        else:
            print("Bot: Relevant Jira information:")
            print("--------------------------------------------------")
            print(jira_results)
            #for idx, doc in enumerate(jira_results[:output_count]):  # Limit results to output_count
            #    print(f"{idx + 1}.\n{format_jira_result(doc)}")

# Execution
if __name__ == "__main__":
    init_logger()
    asyncio.run(chat_loop())
