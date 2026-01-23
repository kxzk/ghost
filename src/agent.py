import os
import sys
import json
import urllib.request
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk import create_sdk_mcp_server
from claude_agent_sdk import tool

LINEAR_API_URL = "https://api.linear.app/graphql"


def get_api_key() -> str:
    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        raise ValueError("LINEAR_API_KEY environment variable not set")
    return api_key


def execute_query(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {"Authorization": get_api_key(), "Content-Type": "application/json"}
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(LINEAR_API_URL, data=data, headers=headers, method="POST")

    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode("utf-8"))

    if "errors" in result:
        errors = [e.get("message", str(e)) for e in result["errors"]]
        raise RuntimeError(f"GraphQL errors: {'; '.join(errors)}")

    return result["data"]


def get_backlog_state_id(team_id: str) -> str:
    query = """
    query TeamStates($teamId: String!) {
        team(id: $teamId) {
            states {
                nodes {
                    id
                    name
                    type
                }
            }
        }
    }
    """
    data = execute_query(query, {"teamId": team_id})
    if not data.get("team"):
        raise ValueError(f"Team '{team_id}' not found")

    states = data["team"]["states"]["nodes"]
    for state in states:
        if state["type"] == "backlog":
            return state["id"]

    raise ValueError("No Backlog state found for team")


@tool(
    "list_issues",
    "List my assigned Linear issues. Optionally filter to issues created in the last N minutes.",
    {"recent_minutes": int},
)
async def list_issues(args: dict[str, Any]) -> dict[str, Any]:
    recent = args.get("recent_minutes")

    if recent:
        created_after = (datetime.now(UTC) - timedelta(minutes=recent)).isoformat()
        query = """
        query ListMyIssues($createdAfter: DateTimeOrDuration!) {
            viewer {
                assignedIssues(first: 50, orderBy: updatedAt, filter: { createdAt: { gte: $createdAfter } }) {
                    nodes {
                        identifier
                        title
                        state { name }
                    }
                }
            }
        }
        """
        data = execute_query(query, {"createdAfter": created_after})
    else:
        query = """
        query ListMyIssues {
            viewer {
                assignedIssues(first: 50, orderBy: updatedAt) {
                    nodes {
                        identifier
                        title
                        state { name }
                    }
                }
            }
        }
        """
        data = execute_query(query)

    issues = data["viewer"]["assignedIssues"]["nodes"]
    if not issues:
        return {"content": [{"type": "text", "text": "No issues found"}]}

    lines = [f"[{i['identifier']}] {i['title']} ({i['state']['name']})" for i in issues]
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


@tool(
    "get_issue",
    "Get details of a specific Linear issue by its identifier (e.g., 'ENG-123').",
    {"issue_id": str},
)
async def get_issue(args: dict[str, Any]) -> dict[str, Any]:
    issue_id = args["issue_id"]
    query = """
    query GetIssue($id: String!) {
        issue(id: $id) {
            identifier
            title
            description
            branchName
            state { name }
        }
    }
    """
    data = execute_query(query, {"id": issue_id})

    if not data.get("issue"):
        return {"content": [{"type": "text", "text": f"Issue '{issue_id}' not found"}]}

    issue = data["issue"]
    lines = [
        f"Issue: {issue['identifier']} - {issue['title']}",
        f"State: {issue['state']['name']}",
        f"Branch: {issue.get('branchName') or 'N/A'}",
        f"Description: {issue.get('description') or 'No description'}",
    ]
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


@tool(
    "create_issue",
    "Create a new Linear issue in the backlog.",
    {"team_id": str, "title": str, "description": str, "project_id": str},
)
async def create_issue(args: dict[str, Any]) -> dict[str, Any]:
    team_id = args["team_id"]
    title = args["title"]
    description = args.get("description", "")
    project_id = args.get("project_id")

    backlog_state_id = get_backlog_state_id(team_id)

    query = """
    mutation IssueCreate($input: IssueCreateInput!) {
        issueCreate(input: $input) {
            success
            issue {
                identifier
                title
                state { name }
            }
        }
    }
    """
    input_data: dict[str, Any] = {"title": title, "teamId": team_id, "stateId": backlog_state_id}
    if description:
        input_data["description"] = description
    if project_id:
        input_data["projectId"] = project_id

    data = execute_query(query, {"input": input_data})

    if not data["issueCreate"]["success"]:
        return {"content": [{"type": "text", "text": "Failed to create issue"}]}

    issue = data["issueCreate"]["issue"]
    return {
        "content": [
            {
                "type": "text",
                "text": f"Created: [{issue['identifier']}] {issue['title']} ({issue['state']['name']})",
            }
        ]
    }


@tool("list_teams", "List all Linear teams with their IDs.", {})
async def list_teams(_args: dict[str, Any]) -> dict[str, Any]:
    query = """
    query Teams {
        teams {
            nodes {
                id
                name
                key
            }
        }
    }
    """
    data = execute_query(query)
    teams = data["teams"]["nodes"]

    if not teams:
        return {"content": [{"type": "text", "text": "No teams found"}]}

    lines = [f"{t['name']} ({t['key']}): {t['id']}" for t in teams]
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


@tool("list_projects", "List all Linear projects. Optionally filter by team ID.", {"team_id": str})
async def list_projects(args: dict[str, Any]) -> dict[str, Any]:
    team_id = args.get("team_id")

    if team_id:
        query = """
        query Projects($teamId: String!) {
            team(id: $teamId) {
                projects {
                    nodes {
                        id
                        name
                    }
                }
            }
        }
        """
        data = execute_query(query, {"teamId": team_id})
        if not data.get("team"):
            return {"content": [{"type": "text", "text": f"Team '{team_id}' not found"}]}
        projects = data["team"]["projects"]["nodes"]
    else:
        query = """
        query Projects {
            projects {
                nodes {
                    id
                    name
                }
            }
        }
        """
        data = execute_query(query)
        projects = data["projects"]["nodes"]

    if not projects:
        return {"content": [{"type": "text", "text": "No projects found"}]}

    lines = [f"{p['name']}: {p['id']}" for p in projects]
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


linear_server = create_sdk_mcp_server(
    name="linear",
    version="1.0.0",
    tools=[list_issues, get_issue, create_issue, list_teams, list_projects],
)


async def run_agent(prompt: str) -> None:
    options = ClaudeAgentOptions(
        mcp_servers={"linear": linear_server},
        allowed_tools=[
            "mcp__linear__list_issues",
            "mcp__linear__get_issue",
            "mcp__linear__create_issue",
            "mcp__linear__list_teams",
            "mcp__linear__list_projects",
        ],
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        async for msg in client.receive_response():
            print(msg)


if __name__ == "__main__":
    import asyncio

    prompt = sys.argv[1] if len(sys.argv) > 1 else "List my Linear issues"
    asyncio.run(run_agent(prompt))
