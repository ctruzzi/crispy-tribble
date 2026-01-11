# LangChain Weather App with MCP

A demonstration application that combines LangChain with the Model Context Protocol (MCP) to create an intelligent weather assistant. The app uses mock weather data exposed through MCP endpoints and leverages LangChain's agent capabilities for natural language interactions.

## Features

- **MCP Server**: Mock weather service exposing three tools via MCP:
  - `get_current_weather`: Get current weather conditions for a city
  - `get_forecast`: Get a 5-day weather forecast
  - `list_available_cities`: List all cities with available weather data

- **LangChain Integration**: Intelligent agent that:
  - Understands natural language weather queries
  - Automatically selects and uses appropriate MCP tools
  - Provides conversational responses

- **Mock Data**: Pre-configured weather data for:
  - New York
  - London
  - Tokyo
  - Paris
  - Sydney

## Architecture

```
┌─────────────────────┐
│   User Input        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  LangChain Agent    │
│  (weather_app.py)   │
└──────────┬──────────┘
           │
           │ MCP Protocol
           ▼
┌─────────────────────┐
│   MCP Server        │
│  (mcp_server.py)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Mock Weather Data  │
└─────────────────────┘
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd crispy-tribble
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your Anthropic API key:
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
# On Windows: set ANTHROPIC_API_KEY=your-api-key-here
```

5. (Optional) Check available models and set your preferred model:
```bash
# Check which Claude models are available on your account
python check_models.py

# Optionally set a specific model (defaults to claude-3-5-sonnet-20241022)
export CLAUDE_MODEL='claude-3-5-sonnet-20241022'
# On Windows: set CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

## Usage

### Running the Weather App

Simply run the main application:

```bash
python weather_app.py
```

This will:
1. Start the MCP server in the background
2. Connect the LangChain agent to the MCP server
3. Launch an interactive chat interface

### Example Interactions

```
You: What's the weather like in New York?
Assistant: The current weather in New York is partly cloudy with a
temperature of 72°F. The humidity is at 65% and winds are blowing
at 8 mph.

You: Give me the forecast for London
Assistant: Here's the 5-day forecast for London:
- Monday: Rainy
- Tuesday: Cloudy
- Wednesday: Cloudy
- Thursday: Partly Cloudy
- Friday: Sunny

You: Which cities can you give me weather for?
Assistant: I can provide weather information for the following cities:
New York, London, Tokyo, Paris, and Sydney.
```

## Project Structure

```
crispy-tribble/
├── mcp_server.py        # MCP server with mock weather endpoints
├── weather_app.py       # LangChain application
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## How It Works

### MCP Server (`mcp_server.py`)

The MCP server implements the Model Context Protocol to expose weather tools using a clean, modular architecture:

- **Decorator-based Tool Registration**: Each tool is defined with the `@mcp_tool` decorator, which registers both the tool definition and its handler
- **Individual Tool Handlers**: Each tool has its own dedicated async function, making it easy to add new tools
- **Tool Registry**: A central registry maps tool names to their handlers for clean dispatch
- **Stdio-based Server**: Uses the `mcp` Python library to communicate via stdin/stdout
- **Mock Data**: Returns weather data from an in-memory dictionary

**Adding a new tool is simple:**
```python
@mcp_tool(
    name="get_temperature",
    description="Get just the temperature for a city",
    input_schema={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name"}
        },
        "required": ["city"]
    }
)
async def get_temperature(arguments: dict) -> list[TextContent]:
    city = arguments.get("city", "").lower()
    # ... your implementation
    return [TextContent(type="text", text=json.dumps(result))]
```

The decorator automatically:
- Registers the tool in the tool registry
- Adds it to the list of available tools
- Wires up the handler for dispatch

### LangChain App (`weather_app.py`)

The LangChain application orchestrates the weather assistant with a dynamic tool conversion system:

1. **Connection**: Establishes a connection to the MCP server using stdio transport
2. **Tool Discovery**: Queries the MCP server for available tools
3. **Dynamic Tool Conversion**: Automatically converts ANY MCP tool to LangChain format without hard-coding
   - Factory function creates handlers with proper closures for each tool
   - Automatic args schema detection from MCP tool's input schema
   - Supports tools with city parameters, no parameters, or custom parameters
4. **Agent Creation**: Creates a tool-calling agent with Claude (Anthropic)
5. **Interactive Loop**: Processes user queries and generates responses

**Key Feature**: When you add a new tool to the MCP server using the `@mcp_tool` decorator, the LangChain app automatically discovers and uses it - no code changes needed in `weather_app.py`!

## Customization

### Adding New Cities

Edit `mcp_server.py` and add entries to the `MOCK_WEATHER_DATA` dictionary:

```python
MOCK_WEATHER_DATA = {
    # ... existing cities ...
    "berlin": {
        "temperature": 60,
        "condition": "Partly Cloudy",
        "humidity": 68,
        "wind_speed": 9,
        "forecast": ["Cloudy", "Rainy", "Partly Cloudy", "Sunny", "Sunny"]
    }
}
```

### Changing the LLM

Modify the model name in `weather_app.py`:

```python
app = WeatherApp(model_name="claude-3-opus-20240229")
```

### Adding New Tools

Adding a new tool is incredibly simple - just add it to `mcp_server.py` and you're done!

**Define the tool in `mcp_server.py`:**
```python
@mcp_tool(
    name="get_humidity",
    description="Get humidity level for a specific city",
    input_schema={
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "The city name"
            }
        },
        "required": ["city"]
    }
)
async def get_humidity(arguments: dict) -> list[TextContent]:
    city = arguments.get("city", "").lower()
    if city not in MOCK_WEATHER_DATA:
        return [TextContent(type="text", text=json.dumps({"error": "City not found"}))]

    result = {
        "city": city.title(),
        "humidity": MOCK_WEATHER_DATA[city]["humidity"]
    }
    return [TextContent(type="text", text=json.dumps(result))]
```

**That's it!** The tool is automatically:
- Registered in the MCP server via the `@mcp_tool` decorator
- Discovered by the LangChain app when it connects
- Converted to a LangChain-compatible tool with proper args schema
- Made available to Claude for use in conversations

No changes needed to `weather_app.py` - the dynamic tool conversion handles everything automatically!

## Requirements

- Python 3.8+
- Anthropic API key (for Claude access)
- Dependencies listed in `requirements.txt`

## Troubleshooting

### Model 404 Error

If you get an error like `Error code: 404 - model not found`, this means the model isn't available on your Anthropic API account. To fix this:

1. **Check available models:**
   ```bash
   python check_models.py
   ```

2. **Set the correct model:**
   ```bash
   export CLAUDE_MODEL='model-name-from-check-script'
   ```

3. **Common model names to try:**
   - `claude-3-5-sonnet-20241022` (newest Claude 3.5 Sonnet)
   - `claude-3-5-sonnet-20240620` (older Claude 3.5 Sonnet)
   - `claude-3-opus-20240229` (Claude 3 Opus)
   - `claude-3-sonnet-20240229` (Claude 3 Sonnet)
   - `claude-3-haiku-20240307` (Claude 3 Haiku - fastest/cheapest)

4. **Verify your API key** has access to Claude models by checking your [Anthropic Console](https://console.anthropic.com/)

### Other Common Issues

- **MCP connection errors**: Make sure `mcp_server.py` is in the same directory
- **Import errors**: Run `pip install -r requirements.txt` to ensure all dependencies are installed
- **API key not found**: Ensure `ANTHROPIC_API_KEY` environment variable is set

## Model Context Protocol (MCP)

This project demonstrates the Model Context Protocol, which provides a standardized way to:

- Expose tools and resources to LLMs
- Create composable, interoperable AI systems
- Separate data/tool providers from LLM applications

Learn more about MCP at: https://modelcontextprotocol.io

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
