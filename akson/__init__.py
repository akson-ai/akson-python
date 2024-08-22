"""Akson library for developing AI agents."""

import os
import time
import asyncio
from abc import ABC, abstractmethod
from textwrap import dedent
from contextlib import asynccontextmanager

import uvicorn
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

# Agent talks to this URL.
AKSON_API_URL = os.getenv("AKSON_API_URL", "https://api.akson.ai")

# Agent registers with this URL, which must be reachable by Akson.
# If not set, it will be constructed using AGENT_HOST and AGENT_PORT.
AGENT_URL = os.getenv("AGENT_URL")

# HTTP server listens on this address. AGENT_URL must point to this address.
# Default values are set to sensible defaults for local development.
AGENT_HOST = os.getenv("AGENT_HOST", "localhost")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8000"))


class AksonException(Exception):
    """Base class for all Akson exceptions."""

    message: str


class AgentNotReachable(AksonException):
    message = "Agent not reachable"


class AgentNotFound(AksonException):
    message = "Agent not found"


class AgentInput(BaseModel):
    """Type of argument that is sent to agent."""

    message: str
    session_id: str | None = None


class AgentOutput(BaseModel):
    """Type of return value from agent run."""

    message: str


class Agent(ABC):
    """Base class for all agents."""

    name: str
    """The name of the agent. Other agents uses this name to communicate with it."""

    description: str
    """A short description of the agent."""

    @abstractmethod
    async def handle_message(self, input: AgentInput) -> AgentOutput:
        """Handle incoming message from another agent."""
        ...

    def run(self):
        """Starts an HTTP server to run the agent."""
        run_agents(self)


def run_agents(*agents: Agent):
    """Run multiple agents together in a single HTTP server.
    Each agent will be registered under separate URLs (/<agent_name>)."""

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        asyncio.get_running_loop().set_debug(True)
        for agent in agents:
            asyncio.create_task(_register_agent(agent))
        yield

    app = FastAPI(lifespan=lifespan)

    for agent in agents:
        handler = _create_agent_handler(agent)
        app.router.post(f"/{agent.name}")(handler)

    uvicorn.run(app, host=AGENT_HOST, port=AGENT_PORT)


def _create_agent_handler(agent: Agent):
    async def handle_message(request: AgentInput):
        if request.message == "Akson-HealthCheck":
            return AgentOutput(message="OK")
        return await agent.handle_message(request)

    return handle_message


def _callback_url(agent_name: str) -> str:
    if AGENT_URL:
        return AGENT_URL
    return f"http://{AGENT_HOST}:{AGENT_PORT}/{agent_name}"


async def _register_agent(agent: Agent):
    while True:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{AKSON_API_URL}/register-agent",
                    json={
                        "name": agent.name,
                        "description": agent.description,
                        "callback_url": _callback_url(agent.name),
                    },
                )
                _check_response(response)
        except Exception as e:
            print(f"Failed to register agent: {e}")
            time.sleep(5)
        else:
            return


def _check_response(response: httpx.Response):
    """Check response from Akson API.
    Parses the response and raises AksonException if the response contains an error."""
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if not e.response.headers.get("Akson-Error"):
            raise
        for cls in AksonException.__subclasses__():
            if cls.__name__ == e.response.json()["name"]:
                raise cls(e.response.json()["message"])
        raise


async def send_message(agent: str | Agent, message: str, autoformat=True, session_id: str | None = None) -> str:
    """Send message to agent."""
    if autoformat:
        message = dedent(message)

    # Local agent communication
    if isinstance(agent, Agent):
        reply = await agent.handle_message(AgentInput(message=message, session_id=session_id))
        return reply.message

    endpoint = f"{AKSON_API_URL}/send-message"
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json={"agent": agent, "message": message, "session_id": session_id})
        _check_response(response)
        return response.json()["message"]
