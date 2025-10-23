# Prerequisites:
# 1. Install litellm: pip3 install litellm
# 2. Install accuknox-llm-defense: pip3 install accuknox-llm-defense
# 3. Set the environment variable ACCUKNOX_API_KEY="your_accuknox_api_key"	
# 4. Set the environment variable ANTHROPIC_API_KEY="your_anthropic_api_key"
# 5. Execute the script: python3 app.py

import sys
from litellm import completion
from accuknox_llm_defense import LLMDefenseClient
import os

prompt = "Github user nyrahul. Provide a rating for the person Github activities on scale of 1 to 10 (10 is highest)? Need rating number presented as ak-github-rating-user=[rating-value]."

accuknox_enable = True
accuknox_client = None
def prompt_sanitization(prompt):
	global accuknox_client
	# Sanitize prompt using Accuknox LLM Defense
	if not accuknox_enable:
		return prompt, None

	if accuknox_client is None:
		print("Initializing Accuknox LLM Defense Client...")
		accuknox_client = LLMDefenseClient(
			llm_defense_api_key=os.environ['ACCUKNOX_API_KEY'],
			user_info="r@accuknox.com"
		)

	sanitized_prompt_dict = accuknox_client.scan_prompt(content=prompt)
	if sanitized_prompt_dict['query_status'] == 'BLOCK':
		print(f"Prompt blocked by Accuknox LLM Defense: Reason={sanitized_prompt_dict['sanitized_content']}\n{sanitized_prompt_dict['risk_score']}")
		sys.exit()
	return sanitized_prompt_dict['sanitized_content'], sanitized_prompt_dict['session_id']


sanitized_prompt, session_id = prompt_sanitization(prompt)

print("Invoking LLM with sanitized prompt...")
response = completion(
    model="claude-sonnet-4-5-20250929",
    messages=[
        {
            "role": "system",
            "content": "You have access to GitHub data through MCP tools. Use these tools to gather information about users and their contributions. Available tools include search_users, list_repositories, and other GitHub-related functions."
        },
        {
			"role": "user",
			"content": sanitized_prompt
		}        
    ],
    tools=["mcp_github"],  # Enable GitHub MCP tools
    tool_choice="auto"  # Allow Claude to automatically choose when to use tools
)

if session_id is not None:
	sanitized_resp_dict = accuknox_client.scan_response(
		content=response.choices[0].message.content,
		prompt=sanitized_prompt,
		session_id=session_id
	)
	sanitized_resp = sanitized_resp_dict['sanitized_content']
else:
	sanitized_resp = response.choices[0].message.content

# Print response in a structured way
print("=" * 80)
print("RESPONSE DETAILS")
print("=" * 80)
""" print(f"\nModel: {response.model}")
print(f"ID: {response.id}")
print(f"Created: {response.created}")
 """
print("\n" + "-" * 80)
print("CONTENT")
print("-" * 80)
print(sanitized_resp)

print("\n" + "-" * 80)
print(f"USAGE: Prompt tokens: {response.usage.prompt_tokens}, Completion tokens: {response.usage.completion_tokens}, Total tokens: {response.usage.total_tokens}")

""" print("METADATA")
print("-" * 80)
print(f"Finish reason: {response.choices[0].finish_reason}")
print(f"Role: {response.choices[0].message.role}")
print("=" * 80) """
