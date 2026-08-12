import asyncio
import json
from openai import AsyncOpenAI
import config

OPENROUTER_KEY = config.OPENROUTER_API_KEY
GROQ_KEY = config.GROQ_API_KEY
GEMINI_KEY = config.GEMINI_API_KEY

with open("brain/prompts/tool_schemas.json", "r", encoding="utf-8") as f:
    tools = json.load(f)

async def test_openrouter_models():
    print("=== Testing OpenRouter Models ===")
    client = AsyncOpenAI(
        api_key=OPENROUTER_KEY,
        base_url="https://openrouter.ai/api/v1",
        default_headers={"HTTP-Referer": "https://github.com/ev-agent", "X-Title": "E.V. Agent"}
    )
    models_to_test = [
        "google/gemini-2.0-flash-001",
        "deepseek/deepseek-chat",
        "meta-llama/llama-3.3-70b-instruct",
        "deepseek/deepseek-r1"
    ]
    for m in models_to_test:
        try:
            res = await client.chat.completions.create(
                model=m,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=10
            )
            print(f"  [OK] OpenRouter model: {m} -> {res.choices[0].message.content}")
        except Exception as e:
            print(f"  [FAIL] OpenRouter model: {m} -> {e}")

async def test_groq_tools():
    print("=== Testing Groq with Tools ===")
    client = AsyncOpenAI(
        api_key=GROQ_KEY,
        base_url="https://api.groq.com/openai/v1"
    )
    groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8192", "qwen-2.5-32b"]
    for m in groq_models:
        try:
            res = await client.chat.completions.create(
                model=m,
                messages=[{"role": "user", "content": "Search GDP of Vietnam"}],
                tools=tools,
                tool_choice="auto",
                max_tokens=100
            )
            print(f"  [OK] Groq model {m}: tool_calls={res.choices[0].message.tool_calls}")
        except Exception as e:
            print(f"  [FAIL] Groq model {m} -> {e}")

async def test_gemini_models():
    print("=== Testing Gemini Models ===")
    client = AsyncOpenAI(
        api_key=GEMINI_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    gemini_models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    for m in gemini_models:
        try:
            res = await client.chat.completions.create(
                model=m,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=10
            )
            print(f"  [OK] Gemini model: {m} -> {res.choices[0].message.content}")
        except Exception as e:
            print(f"  [FAIL] Gemini model: {m} -> {e}")

async def main():
    await test_openrouter_models()
    await test_groq_tools()
    await test_gemini_models()

if __name__ == "__main__":
    asyncio.run(main())
