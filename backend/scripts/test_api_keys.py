"""
Auditex -- API key smoke test.
Tests both Anthropic and OpenAI keys with a minimal 1-token call.
Run from the backend directory:
  python scripts/test_api_keys.py
Or via run.ps1:
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/test_api_keys.py"
"""
import asyncio
import os
import sys


async def test_anthropic():
    import anthropic
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key or key.startswith("placeholder"):
        print("  ANTHROPIC: SKIP -- key is placeholder")
        return False

    try:
        client = anthropic.AsyncAnthropic(api_key=key, timeout=15.0)
        msg = await client.messages.create(
            model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
            max_tokens=16,
            messages=[{"role": "user", "content": "Reply with just the word PONG"}],
        )
        text = msg.content[0].text.strip()
        print(f"  ANTHROPIC: PASS -- response='{text}' tokens_used={msg.usage.input_tokens+msg.usage.output_tokens}")
        return True
    except Exception as exc:
        print(f"  ANTHROPIC: FAIL -- {exc}")
        return False


async def test_openai():
    import openai
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key or key.startswith("placeholder"):
        print("  OPENAI:    SKIP -- key is placeholder")
        return False

    try:
        client = openai.AsyncOpenAI(api_key=key, timeout=15.0)
        resp = await client.chat.completions.create(
            model=os.environ.get("GPT4O_MODEL", "gpt-4o"),
            max_tokens=16,
            messages=[{"role": "user", "content": "Reply with just the word PONG"}],
        )
        text = resp.choices[0].message.content.strip()
        tokens = resp.usage.total_tokens
        print(f"  OPENAI:    PASS -- response='{text}' tokens_used={tokens}")
        return True
    except Exception as exc:
        print(f"  OPENAI:    FAIL -- {exc}")
        return False


async def main():
    print("=" * 48)
    print("Auditex -- API Key Smoke Test")
    print("=" * 48)

    ok_anthropic = await test_anthropic()
    ok_openai = await test_openai()

    print("=" * 48)
    if ok_anthropic and ok_openai:
        print("RESULT: BOTH KEYS VALID -- ready for MT-004")
    elif ok_anthropic:
        print("RESULT: Anthropic OK, OpenAI FAILED -- check OpenAI key")
        sys.exit(1)
    elif ok_openai:
        print("RESULT: OpenAI OK, Anthropic FAILED -- check Anthropic key")
        sys.exit(1)
    else:
        print("RESULT: BOTH FAILED -- check .env and restart containers")
        sys.exit(1)
    print("=" * 48)


if __name__ == "__main__":
    asyncio.run(main())
