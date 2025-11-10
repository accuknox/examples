# Prerequisites:
# 1. Install litellm: pip3 install litellm
# 2. Install accuknox-llm-defense: pip3 install accuknox-llm-defense
# 3. Set the environment variable ACCUKNOX_API_KEY="your_accuknox_api_key"	
# 4. Set the environment variable ANTHROPIC_API_KEY="your_anthropic_api_key"
# 5. Execute the script: python3 app.py

from typing import List, Dict
from litellm import completion
from firewall_util import (
	initialize_firewall_client,
	get_sanitized_prompt,
	get_sanitized_response,
)


def app(messages: List[Dict[str, str]]) -> str:
	response = completion(
		model="claude-sonnet-4-5-20250929",
		messages=messages,
		tools=["mcp_github"],  # Enable GitHub MCP tools
		tool_choice="auto",  # Allow Claude to automatically choose when to use tools
	)	
	# print(f"""
	# RESPONSE DETAILS (Model: {response.model}, ID: {response.id}, Created: {response.created})
	# CONTENT ({response.choices[0].message.content})
	# USAGE (Prompt tokens: {response.usage.prompt_tokens}, Completion tokens: {response.usage.completion_tokens}, Total tokens: {response.usage.total_tokens})
	# METADATA (Finish reason: {response.choices[0].finish_reason}, Role: {response.choices[0].message.role})
	# """)
	return response.choices[0].message.content


def secure_app(messages: List[Dict[str, str]]) -> str:
	initialize_firewall_client("r@accuknox.com")
	
	prompt_scan_result = get_sanitized_prompt(messages[-1]["content"])
	if prompt_scan_result.block: return prompt_scan_result.fallback_response
	messages[-1]["content"] = prompt_scan_result.sanitized_content
	
	response = app(messages)  # your original logic
	
	response_scan_result = get_sanitized_response(response.choices[0].message.content)
	if response_scan_result.block: return response_scan_result.fallback_response
	return response_scan_result.sanitized_content


def main() -> None:
	messages: List[Dict[str, str]] = [
		{
			"role": "system",
			"content": "You have access to GitHub data through MCP tools. Use these tools to gather information about users and their contributions. Available tools include search_users, list_repositories, and other GitHub-related functions."
		}
	]
	while True:
		prompt: str = input("Prompt: ")
		messages.append({
			"role": "user",
			"content": prompt,
		})
		# response = app(messages)
		response = secure_app(messages)
		print(f"Response: {response}")
		messages.append({
			"role": "assistant",
			"content": response,
		})

if __name__ == "__main__":
	main()


# prompt
# Github user nyrahul. Provide a rating for the person Github activities on scale of 1 to 10 (10 is highest)? Need rating number presented as ak-github-rating-user=[rating-value].