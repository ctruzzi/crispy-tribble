"""
LangChain Weather App using MCP Server

This application uses LangChain with the MCP weather service to answer
weather-related questions using natural language.
"""

import asyncio
import json
import os
from typing import Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
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

    def __init__(self, model_name: str = None):
        """Initialize the weather app.

        Args:
            model_name: Claude model to use. If not specified, reads from
                       CLAUDE_MODEL env var, or defaults to claude-3-5-sonnet-20241022
        """
        self.model_name = model_name or os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self.session: Optional[ClientSession] = None
        self.llm = None
        self.tools = []

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

    def _create_tool_handler(self, tool_name: str):
        """Factory function to create a tool handler with proper closure."""
        async def handler(**kwargs) -> str:
            """Dynamic tool handler that calls the MCP tool."""
            result = await self.call_mcp_tool(tool_name, kwargs)
            return result
        return handler

    def _get_args_schema(self, mcp_tool):
        """Determine the appropriate args schema based on the tool's input schema."""
        properties = mcp_tool.inputSchema.get("properties", {})
        required = mcp_tool.inputSchema.get("required", [])

        # If the tool has a "city" parameter, use WeatherInput
        if "city" in properties:
            return WeatherInput

        # If the tool has no parameters, use EmptyInput
        if not properties:
            return EmptyInput

        # For other cases, dynamically create a Pydantic model
        # This handles future tools with different parameters
        fields = {}
        for prop_name, prop_schema in properties.items():
            field_type = str  # Default to string type
            field_description = prop_schema.get("description", "")
            is_required = prop_name in required

            if is_required:
                fields[prop_name] = (field_type, Field(description=field_description))
            else:
                fields[prop_name] = (field_type, Field(default=None, description=field_description))

        # Create a dynamic Pydantic model
        return type(f"{mcp_tool.name}_input", (BaseModel,), {"__annotations__": {k: v[0] for k, v in fields.items()}, **{k: v[1] for k, v in fields.items()}})

    def create_langchain_tools(self, mcp_tools):
        """Convert MCP tools to LangChain tools dynamically.

        This method automatically converts any MCP tool to a LangChain tool
        without requiring hard-coded handlers for each tool.
        """
        langchain_tools = []

        for mcp_tool in mcp_tools:
            # Create a handler function for this specific tool
            handler = self._create_tool_handler(mcp_tool.name)

            # Determine the appropriate args schema
            args_schema = self._get_args_schema(mcp_tool)

            # Create the LangChain tool
            tool = StructuredTool.from_function(
                coroutine=handler,
                name=mcp_tool.name,
                description=mcp_tool.description,
                args_schema=args_schema
            )
            langchain_tools.append(tool)

        return langchain_tools

    async def setup_agent(self):
        """Set up the LangChain agent with MCP tools."""
        # Get MCP tools
        mcp_tools = await self.get_mcp_tools()
        print(f"✓ Loaded {len(mcp_tools)} tools from MCP server")

        # Convert to LangChain tools
        self.tools = self.create_langchain_tools(mcp_tools)

        # Initialize the LLM with tool binding
        print(f"✓ Using model: {self.model_name}")
        self.llm = ChatAnthropic(model=self.model_name).bind_tools(self.tools)

        print("✓ LangChain agent initialized")

    async def ask(self, question: str) -> str:
        """Ask the agent a weather-related question."""
        if not self.llm:
            raise RuntimeError("Agent not initialized")

        # System message
        system_msg = """You are a helpful weather assistant. You have access to weather data
for various cities through the available tools. When users ask about weather, use the
appropriate tools to fetch the information and provide clear, conversational responses.

Available cities: New York, London, Tokyo, Paris, Sydney

If a user asks about a city not in the list, politely inform them and suggest available cities."""

        # Start conversation
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": question}
        ]

        # Agent loop - max 10 iterations to prevent infinite loops
        for _ in range(10):
            # Get response from LLM
            response = await self.llm.ainvoke(messages)

            # Add assistant response to messages
            messages.append(response)

            # Check if there are tool calls
            if not response.tool_calls:
                # No more tool calls, return the final answer
                return response.content

            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # Find and execute the tool
                tool_result = None
                for tool in self.tools:
                    if tool.name == tool_name:
                        try:
                            tool_result = await tool.ainvoke(tool_args)
                        except Exception as e:
                            tool_result = f"Error executing tool: {str(e)}"
                        break

                if tool_result is None:
                    tool_result = f"Tool {tool_name} not found"

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "content": str(tool_result),
                    "tool_call_id": tool_call["id"]
                })

        return "Sorry, I couldn't process your request. Please try again."

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
