# Copyright (c) Microsoft. All rights reserved.
# Multi-Agent Research Workflow - Azure Foundry Hosted Agent
# Adapted from Module 3 - OpenAI Agents SDK - Multi Agents notebook.
#
# Pipeline:  User Query → Researcher (Tavily) → Analyst → Writer → Final Report

import os
import requests

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import Field
from typing_extensions import Annotated

# Load .env when running locally; platform injects vars at runtime in production.
load_dotenv()


# ---------------------------------------------------------------------------
# Tavily search tool
# ---------------------------------------------------------------------------

@tool(approval_mode="never_require")
def tavily_search(
    query: Annotated[str, Field(description="The research query to search for.")],
    max_results: Annotated[int, Field(description="Maximum number of results to return (1–10).")] = 5,
) -> str:
    """
    Search the web using the Tavily API and return a summary of the top results.
    Use this tool whenever you need up-to-date information or external data.
    """
    tavily_api_key = os.environ.get("TAVILY_API_KEY", "")
    if not tavily_api_key:
        return "Tavily API key is not configured. Set the TAVILY_API_KEY environment variable."

    url = "https://api.tavily.com/search"
    headers = {"Content-Type": "application/json"}
    payload = {
        "api_key": tavily_api_key,
        "query": query,
        "max_results": max(1, min(max_results, 10)),
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            return "No relevant results found for the given query."
        return "\n".join(f"- {r['title']}: {r['content']}" for r in results)
    except requests.exceptions.Timeout:
        return "Tavily search timed out. Please try again."
    except requests.exceptions.RequestException as exc:
        return f"Tavily API error: {exc}"


# ---------------------------------------------------------------------------
# Agent instructions — orchestrates the full Researcher → Analyst → Writer
# pipeline in a single multi-step conversation turn.
# ---------------------------------------------------------------------------

AGENT_INSTRUCTIONS = """
You are a Senior Research Analyst that orchestrates a full research pipeline.
When a user provides a research question or topic, you MUST follow these steps
in order and show your work clearly:

## Step 1 – Research
Use the `tavily_search` tool (with max_results=5) to gather fresh, relevant
information on the topic. Summarise the key findings in 5 concise bullet points.

## Step 2 – Analysis
Analyse the research findings. Identify key trends, risks, or strategic insights
in no more than 2 paragraphs.

## Step 3 – Final Report
Synthesise everything into a structured executive report with:
- **Executive Summary** (2–3 sentences)
- **Detailed Report** (at least 400 words in Markdown, covering key findings,
  context, implications, and evidence)
- **Follow-Up Questions** (3–5 questions for further investigation)

Always label each section clearly with Markdown headings so the output is
easy to read.
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    model_name = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME") or os.getenv("FOUNDRY_MODEL_NAME")
    if not model_name:
        raise RuntimeError(
            "Model deployment name is not configured. "
            "Set AZURE_AI_MODEL_DEPLOYMENT_NAME or FOUNDRY_MODEL_NAME."
        )

    project_endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    if not project_endpoint:
        raise RuntimeError(
            "Foundry project endpoint is not configured. "
            "Set FOUNDRY_PROJECT_ENDPOINT."
        )

    client = FoundryChatClient(
        project_endpoint=project_endpoint,
        model=model_name,
        credential=DefaultAzureCredential(),
    )

    agent = Agent(
        client=client,
        instructions=AGENT_INSTRUCTIONS,
        tools=[tavily_search],
    )

    server = ResponsesHostServer(agent, default_fetch_history_count=0)
    server.run()


if __name__ == "__main__":
    main()
