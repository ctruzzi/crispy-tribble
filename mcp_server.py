"""
MCP Server with Mock Weather Endpoints

This server exposes mock weather data endpoints via the Model Context Protocol (MCP).
"""

import json
from datetime import datetime
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio


# Mock weather data
MOCK_WEATHER_DATA = {
    "new york": {
        "temperature": 72,
        "condition": "Partly Cloudy",
        "humidity": 65,
        "wind_speed": 8,
        "forecast": ["Sunny", "Cloudy", "Rainy", "Partly Cloudy", "Sunny"]
    },
    "london": {
        "temperature": 58,
        "condition": "Rainy",
        "humidity": 80,
        "wind_speed": 12,
        "forecast": ["Rainy", "Cloudy", "Cloudy", "Partly Cloudy", "Sunny"]
    },
    "tokyo": {
        "temperature": 68,
        "condition": "Sunny",
        "humidity": 55,
        "wind_speed": 6,
        "forecast": ["Sunny", "Sunny", "Partly Cloudy", "Cloudy", "Rainy"]
    },
    "paris": {
        "temperature": 64,
        "condition": "Cloudy",
        "humidity": 70,
        "wind_speed": 10,
        "forecast": ["Cloudy", "Rainy", "Partly Cloudy", "Sunny", "Sunny"]
    },
    "sydney": {
        "temperature": 78,
        "condition": "Sunny",
        "humidity": 60,
        "wind_speed": 15,
        "forecast": ["Sunny", "Sunny", "Partly Cloudy", "Partly Cloudy", "Cloudy"]
    }
}


# Initialize MCP server
server = Server("weather-service")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available weather tools."""
    return [
        Tool(
            name="get_current_weather",
            description="Get the current weather for a specific city. Returns temperature, condition, humidity, and wind speed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name (e.g., 'New York', 'London', 'Tokyo')"
                    }
                },
                "required": ["city"]
            }
        ),
        Tool(
            name="get_forecast",
            description="Get a 5-day weather forecast for a specific city.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name (e.g., 'New York', 'London', 'Tokyo')"
                    }
                },
                "required": ["city"]
            }
        ),
        Tool(
            name="list_available_cities",
            description="List all cities with available weather data.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls for weather data."""

    if name == "get_current_weather":
        city = arguments.get("city", "").lower()

        if city not in MOCK_WEATHER_DATA:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Weather data not available for '{city}'. Available cities: {', '.join(MOCK_WEATHER_DATA.keys())}"
                })
            )]

        weather = MOCK_WEATHER_DATA[city]
        result = {
            "city": city.title(),
            "timestamp": datetime.now().isoformat(),
            "temperature": weather["temperature"],
            "temperature_unit": "Fahrenheit",
            "condition": weather["condition"],
            "humidity": weather["humidity"],
            "humidity_unit": "%",
            "wind_speed": weather["wind_speed"],
            "wind_speed_unit": "mph"
        }

        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    elif name == "get_forecast":
        city = arguments.get("city", "").lower()

        if city not in MOCK_WEATHER_DATA:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Weather data not available for '{city}'. Available cities: {', '.join(MOCK_WEATHER_DATA.keys())}"
                })
            )]

        weather = MOCK_WEATHER_DATA[city]
        forecast_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

        result = {
            "city": city.title(),
            "forecast": [
                {
                    "day": day,
                    "condition": condition
                }
                for day, condition in zip(forecast_days, weather["forecast"])
            ]
        }

        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    elif name == "list_available_cities":
        result = {
            "available_cities": [city.title() for city in MOCK_WEATHER_DATA.keys()]
        }

        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    else:
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"})
        )]


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
