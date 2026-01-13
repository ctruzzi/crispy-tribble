"""
Example script demonstrating programmatic usage of the Weather App
"""

import asyncio
from weather_app import WeatherApp


async def run_examples():
    """Run example queries against the weather app."""
    app = WeatherApp()

    try:
        print("Setting up Weather App...")
        await app.connect_to_mcp()
        await app.setup_agent()

        # Example queries
        examples = [
            "What's the weather in Tokyo?",
            "Give me a 5-day forecast for Paris",
            "Compare the weather in New York and London",
            "Which city has the best weather right now?",
        ]

        print("\n" + "="*60)
        print("Running Example Queries")
        print("="*60 + "\n")

        for i, query in enumerate(examples, 1):
            print(f"\n--- Example {i} ---")
            print(f"Query: {query}")
            print(f"\nResponse:")

            response = await app.ask(query)
            print(response)
            print("\n" + "-"*60)

    finally:
        await app.disconnect()


if __name__ == "__main__":
    asyncio.run(run_examples())
