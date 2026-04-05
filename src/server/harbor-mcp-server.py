from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
import harbor
import rich
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file


# Initialize FastMCP server
mcp = FastMCP("harbor-mcp-server")

# Constants
USER_AGENT = "harbor-mcp-server/1.0"

def _format_projects(projects: Any) -> list[str]:
    lines = []
    for project in projects:
        project_info = f"• {project.name}"
        if project.owner_name:
            project_info += f" (owner: {project.owner_name})"
        if project.repo_count is not None:
            project_info += f" [{project.repo_count} repos]"
        lines.append(project_info)
    return lines

@mcp.tool("getProjects", description="Get all projects in the Harbor registry")
async def getProjects() -> str:
    """Get All Projects in Harbor registry    
    """
    data = await harbor.get_projects()
    
    
    if not data or len(data) == 0:
        return "Unable to fetch projects or no projects found."
    project_data= _format_projects(data)    
    return "\n---\n".join(project_data)

@mcp.tool("getRepositories", description="Get all repositories in a Harbor project")    
async def getRepositories(project_name: str) -> str:
    """Get all repositories in a Harbor project
    Args:
        project_name (str): Name of the Harbor project
    """
    repositories = await harbor.get_repositories(project_name)
    
    if not repositories or len(repositories) == 0:
        return f"Unable to fetch repositories for project '{project_name}' or no repositories found."
    
    repo_data = []
    sorted_repositories = sorted(repositories, key=lambda r: r.id, reverse=False)
    slno=  1
    repo_data.append(f"{'SlNo':<5} {'ID':<10} {'Name':<30} {'Artifact Count':<15} {'Pull Count':<10}")
    for repository in sorted_repositories:
        repo_data.append(f"{slno:<5} {repository.id:<10} {repository.name:<30} {repository.artifact_count:<15} {repository.pull_count:<10}")
        slno += 1   
    
    return "\n---\n".join(repo_data)

@mcp.tool("getArtifacts", description="Get all artifacts details in a Harbor repository")
async def getArtifacts(project_name: str, repository_name: str) -> str:
    """Get all artifacts details in a Harbor repository
    Args:
        project_name (str): Name of the Harbor project
        repository_name (str): Name of the Harbor repository
    """
    repositories = await harbor.get_repositories(project_name)
    artifact_data = []
    repository= next((repo for repo in repositories if repo.name == f"{project_name}/{repository_name}"), None)
    if not repository:
        artifact_data.append(f"Repository '{repository_name}' not found in project '{project_name}'.")
        return "\n---\n".join(artifact_data)
    else:               
        artifacts = await harbor.get_artifacts(project_name, repository_name)  
        artifact_data.append(f"Artifact,Digest,Size (bytes),Pull Count,Pull Time,Push Time,Tags")                                  
        for artifact in artifacts:
            tags=[]
            for tag in artifact.tags:
                if tag.name:
                    tags.append(tag.name)
            artifact_data.append(f"{artifact.repository_name} {artifact.digest} {artifact.size} {repository.pull_count} {artifact.pull_time} {artifact.push_time} {tags} ")  
    
    return "\n---\n".join(artifact_data)


def main():
    # NOTE: do NOT print/log to stdout — stdio transport uses stdout exclusively for JSONRPC
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
