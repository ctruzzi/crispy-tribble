"""
LangChain Weather App using MCP Server

This application uses LangChain with the MCP weather service to answer
weather-related questions using natural language.
"""

import asyncio
import json
from typing import Any, Optional
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate
from langchain.tools import StructuredTool
from langchain_anthropic import ChatAnthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field


# Pydantic models for tool inputs
class WeatherInput(BaseModel):
    city: str = Field(description="The city name (e.g., 'New York', 'London', 'Tokyo')")


class EmptyInput(BaseModel):
    pass


class WeatherApp:
    """LangChain-based weather application using MCP."""

    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022"):
        """Initialize the weather app."""
        self.model_name = model_name
        self.session: Optional[ClientSession] = None
        self.agent_executor: Optional[AgentExecutor] = None

    async def connect_to_mcp(self):
        """Connect to the MCP weather server."""
        server_params = StdioServerParameters(
            command="python",
            args=["mcp_server.py"],
            env=None
        )

        # Create MCP client connection
        self.stdio_transport = stdio_client(server_params)
        self.stdio, self.write = await self.stdio_transport.__aenter__()
        self.session = ClientSession(self.stdio, self.write)
        await self.session.__aenter__()

        # Initialize the session
        await self.session.initialize()

        print("✓ Connected to MCP weather service")

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.session:
            await self.session.__aexit__(None, None, None)
        if hasattr(self, 'stdio_transport'):
            await self.stdio_transport.__aexit__(None, None, None)

    async def get_mcp_tools(self):
        """Get available tools from MCP server."""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")

        response = await self.session.list_tools()
        return response.tools

    async def call_mcp_tool(self, tool_name: str, arguments: dict) -> str:
        """Call an MCP tool and return the result."""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")

        result = await self.session.call_tool(tool_name, arguments)
        return result.content[0].text

    def create_langchain_tools(self, mcp_tools):
        """Convert MCP tools to LangChain tools."""
        langchain_tools = []

        for mcp_tool in mcp_tools:
            if mcp_tool.name == "get_current_weather":
                async def get_current_weather(city: str) -> str:
                    """Get current weather for a city."""
                    result = await self.call_mcp_tool("get_current_weather", {"city": city})
                    return result

                tool = StructuredTool.from_function(
                    coroutine=get_current_weather,
                    name="get_current_weather",
                    description=mcp_tool.description,
                    args_schema=WeatherInput
                )
                langchain_tools.append(tool)

            elif mcp_tool.name == "get_forecast":
                async def get_forecast(city: str) -> str:
                    """Get 5-day forecast for a city."""
                    result = await self.call_mcp_tool("get_forecast", {"city": city})
                    return result

                tool = StructuredTool.from_function(
                    coroutine=get_forecast,
                    name="get_forecast",
                    description=mcp_tool.description,
                    args_schema=WeatherInput
                )
                langchain_tools.append(tool)

            elif mcp_tool.name == "list_available_cities":
                async def list_cities() -> str:
                    """List all available cities."""
                    result = await self.call_mcp_tool("list_available_cities", {})
                    return result

                tool = StructuredTool.from_function(
                    coroutine=list_cities,
                    name="list_available_cities",
                    description=mcp_tool.description,
                    args_schema=EmptyInput
                )
                langchain_tools.append(tool)

        return langchain_tools

    async def setup_agent(self):
        """Set up the LangChain agent with MCP tools."""
        # Get MCP tools
        mcp_tools = await self.get_mcp_tools()
        print(f"✓ Loaded {len(mcp_tools)} tools from MCP server")

        # Convert to LangChain tools
        langchain_tools = self.create_langchain_tools(mcp_tools)

        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful weather assistant. You have access to weather data
for various cities through the available tools. When users ask about weather, use the
appropriate tools to fetch the information and provide clear, conversational responses.

Available cities: New York, London, Tokyo, Paris, Sydney

If a user asks about a city not in the list, politely inform them and suggest available cities."""),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        # Initialize the LLM
        llm = ChatAnthropic(model=self.model_name)

        # Create the agent
        agent = create_tool_calling_agent(llm, langchain_tools, prompt)
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=langchain_tools,
            verbose=True,
            handle_parsing_errors=True
        )

        print("✓ LangChain agent initialized")

    async def ask(self, question: str) -> str:
        """Ask the agent a weather-related question."""
        if not self.agent_executor:
            raise RuntimeError("Agent not initialized")

        response = await self.agent_executor.ainvoke({"input": question})
        return response["output"]

    async def run_interactive(self):
        """Run the app in interactive mode."""
        print("\n" + "="*60)
        print("🌤️  LangChain Weather App (powered by MCP)")
        print("="*60)
        print("\nType 'quit' or 'exit' to close the app.\n")

        while True:
            try:
                user_input = input("\nYou: ").strip()

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye! 👋")
                    break

                if not user_input:
                    continue

                print("\nAssistant: ", end="", flush=True)
                response = await self.ask(user_input)
                print(response)

            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")


async def main():
    """Main entry point."""
    app = WeatherApp()

    try:
        # Connect to MCP server
        await app.connect_to_mcp()

        # Setup the agent
        await app.setup_agent()

        # Run interactive mode
        await app.run_interactive()

    finally:
        # Cleanup
        await app.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
