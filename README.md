# AccuKnox Examples

This repository contains various examples demonstrating the usage of AccuKnox tools and integrations. Each example is contained in its own directory with detailed documentation.

## Available Examples

### 1. Prompt Firewall

A demonstration of how to combine an LLM client (`litellm`) with AccuKnox's prompt/response scanning middleware (`accuknox-llm-defense`) and GitHub MCP tools. This example shows how to:

- Sanitize user prompts with Accuknox LLM Defense before sending to an LLM
- Invoke an LLM (via `litellm`) with GitHub MCP tools integration
- Scan model responses with Accuknox LLM Defense
- Generate structured output with usage details

[View Prompt Firewall Example →](./prompt-firewall)

## Getting Started

Each example directory contains its own README with specific setup instructions, prerequisites, and usage details. Choose an example that matches your use case and follow the instructions in its README file.

## License

This examples repository is licensed under the terms in the [LICENSE](./LICENSE) file.
