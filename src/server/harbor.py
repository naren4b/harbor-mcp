import os
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import httpx
from harborapi import HarborAsyncClient
from harborapi.exceptions import NotFound
from mcp.server.fastmcp import FastMCP
import asyncio
import rich

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

# Constants
HARBOR_API_BASE = os.getenv("HARBOR_URL")
USER_AGENT = "harbor-app/1.0"
USER_NAME = os.getenv("HARBOR_USERNAME")
SECRET = os.getenv("HARBOR_PASSWORD")
INSECURE_SKIP_TLS_VERIFY=os.getenv("INSECURE_SKIP_TLS_VERIFY", "false").lower() == "true"

client = HarborAsyncClient(
    url=f"{HARBOR_API_BASE}/api/v2.0",
    username=USER_NAME,
    secret=SECRET,
    verify=not INSECURE_SKIP_TLS_VERIFY,
)


async def get_projects() -> None:
    # Get all projects
    projects = await client.get_projects(page_size=100)
    print(f"Found {len(projects)} projects")    
    return projects

async def get_repositories(project_name: str) -> None:
    # Get repositories for a specific project
    repositories = await client.get_repositories(project_name, page_size=100)
    print(
        f"Found {len(repositories)} repositories in project '{project_name}'"
    )
    # for repository in repositories:
    #     rich.print(repository)
    return repositories    


async def get_artifacts(project_name: str, repository_name: str) -> None:   
    # Get artifacts for a specific repository in a project
    artifacts = await client.get_artifacts(project_name, repository_name, page_size=100)
    print(
        f"Found {len(artifacts)} artifacts in repository '{repository_name}' of project '{project_name}'"
    )
    return artifacts
    # for artifact in artifacts:
    #     rich.print(artifact)

async def main():
    project_name = None
    repository_name = None
    for arg in sys.argv:
        if arg.startswith("--project-name="):
            project_name = arg.split("=", 1)[1]
        if arg.startswith("--repository-name="):
            repository_name = arg.split("=", 1)[1]
    if project_name:
        repositories = await get_repositories(project_name)
        # print(repositories )        
        if repository_name:
            repository= next((repo for repo in repositories if repo.name == f"{project_name}/{repository_name}"), None)
            if not repository:
                print(f"Repository '{repository_name}' not found in project '{project_name}'.")
                return
            else:               
                artifacts = await get_artifacts(project_name, repository_name)  
                print(f"Artifact,Digest,Size (bytes),Pull Count,Pull Time,Push Time,Tags")                                  
                for artifact in artifacts:
                    # rich.print(artifact)                    
                    
                    tags=[]
                    for tag in artifact.tags:
                        if tag.name:
                            tags.append(tag.name)
                    print(f"{artifact.repository_name} {artifact.digest} {artifact.size} {repository.pull_count} {artifact.pull_time} {artifact.push_time} {tags} ")                   
        else:
            for repository in repositories:
                rich.print(repository)
    else:    
        projects = await get_projects()
        for project in projects:
            rich.print(project)       

if __name__ == "__main__":     
    asyncio.run(main())
    
    