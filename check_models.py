"""
Script to check available Claude models on your Anthropic API account.
"""

import anthropic
import os

def check_available_models():
    """Check which Claude models are available."""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("\nPlease set your API key:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        return

    print("Checking available Claude models...\n")

    # List of common Claude models to test
    models_to_test = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    client = anthropic.Anthropic(api_key=api_key)

    print("Testing model availability:\n")
    available_models = []

    for model in models_to_test:
        try:
            # Try a minimal API call to test if model exists
            response = client.messages.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            print(f"✓ {model} - AVAILABLE")
            available_models.append(model)
        except anthropic.NotFoundError:
            print(f"✗ {model} - NOT FOUND (404)")
        except anthropic.PermissionDeniedError:
            print(f"⚠ {model} - PERMISSION DENIED")
        except Exception as e:
            print(f"? {model} - ERROR: {str(e)[:50]}")

    print(f"\n{'='*60}")
    if available_models:
        print(f"\nAvailable models ({len(available_models)}):")
        for model in available_models:
            print(f"  • {model}")

        print(f"\nTo use a specific model, set the CLAUDE_MODEL environment variable:")
        print(f"  export CLAUDE_MODEL='{available_models[0]}'")
    else:
        print("\n❌ No models available. Please check:")
        print("  1. Your ANTHROPIC_API_KEY is correct")
        print("  2. Your API key has the necessary permissions")
        print("  3. Your account has access to Claude models")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    check_available_models()
