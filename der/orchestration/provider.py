import json
from typing import Any, Dict, Optional, Tuple

from google import genai
from google.genai import types

from anthropic import Anthropic

from openai import OpenAI


def invoke_openai(invoke_payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:

    client = OpenAI()

    model_id = invoke_payload.get("provider_model", "gpt-4.1")
    system_text = invoke_payload.get("system_text", "")
    user_text = invoke_payload.get("user_text", "")
    params = invoke_payload.get("params", {})

    temperature = params.get("temperature", 0.0)
    if not isinstance(temperature, (int, float)):
        temperature = 0.0

    try:
        response = client.responses.create(
            model=model_id,
            temperature=float(temperature),
            input=[
                {
                    "role": "system",
                    "content": system_text,
                },
                {
                    "role": "user",
                    "content": user_text,
                },
            ],
        )
    except Exception as e:
        return "", {"error": f"{type(e).__name__}: {e}"}

    output = ""
    try:
        output = response.output_text
    except Exception:
        output = ""

    output = output.strip() if isinstance(output, str) else ""

    tokens: Dict[str, Any] = {}
    usage = getattr(response, "usage", None)
    if usage:
        prompt_tokens = getattr(usage, "input_tokens", None)
        completion_tokens = getattr(usage, "output_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)

        if isinstance(prompt_tokens, int):
            tokens["prompt_tokens"] = prompt_tokens
        if isinstance(completion_tokens, int):
            tokens["completion_tokens"] = completion_tokens
        if isinstance(total_tokens, int):
            tokens["total_tokens"] = total_tokens

    return output, tokens

def invoke_gemini(invoke_payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:

    client = genai.Client()

    model_id = invoke_payload.get("provider_model")
    system_text = invoke_payload.get("system_text", "")
    user_text = invoke_payload.get("user_text", "")
    params = invoke_payload.get("params", {})

    config: Dict[str, Any] = {}

    if isinstance(model_id, str):
        model_id = model_id.strip()
    else:
        model_id = "gemini-2.5-pro"

    temperature = params.get("temperature", 0.0)
    if not isinstance(temperature, (int, float)):
        temperature = 0.0
    config["temperature"] = float(temperature)

    if system_text.strip():
        config["system_instruction"] = system_text.strip()

    try:
        gemini_config = types.GenerateContentConfig(**config)
    except Exception:
        gemini_config = types.GenerateContentConfig(temperature=float(config.get("temperature", 0.0)))

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=user_text,
            config=gemini_config,
        )
    except Exception as e:
        return "", {"error": f"{type(e).__name__}: {e}"}

    output = getattr(response, "text", "")
    if not isinstance(output, str):
        output = ""
    else:
        output = output.strip()

    tokens: Dict[str, Any] = {}
    usage = getattr(response, "usage_metadata", None)
    if usage is not None:
        prompt_tokens = getattr(usage, "prompt_token_count", None)
        completion_tokens = getattr(usage, "candidates_token_count", None)
        total_tokens = getattr(usage, "total_token_count", None)

        if isinstance(prompt_tokens, int):
            tokens["prompt_tokens"] = prompt_tokens
        if isinstance(completion_tokens, int):
            tokens["completion_tokens"] = completion_tokens
        if isinstance(total_tokens, int):
            tokens["total_tokens"] = total_tokens

    return output, tokens

def invoke_anthropic(invoke_payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:

    client = Anthropic()

    system_text = invoke_payload.get("system_text", "")
    user_text = invoke_payload.get("user_text", "")
    model = invoke_payload.get("provider_model")
    params = invoke_payload.get("params", {})

    if isinstance(model, str):
        model = model.strip()
    else:
        model = "claude-sonnet-4-5-20250929"

    temperature = params.get("temperature", 0.0)
    if not isinstance(temperature, (int, float)):
        temperature = 0.0

    max_tokens = 15000

    try:
        response = client.messages.create(
            model=model,
            system=system_text.strip(),
            messages=[
                {
                    "role": "user",
                    "content": user_text,
                }
            ],
            temperature=float(temperature),
            max_tokens=max_tokens,
        )

    except Exception as e:
        return "", {"error": f"{type(e).__name__}: {e}"}

    output_chunks = []
    for block in response.content:
        if block.type == "text":
            output_chunks.append(block.text)

    output_text = "\n".join(output_chunks).strip()

    tokens: Dict[str, Any] = {}
    usage = getattr(response, "usage", None)
    if usage:
        if isinstance(usage.input_tokens, int):
            tokens["prompt_tokens"] = usage.input_tokens
        if isinstance(usage.output_tokens, int):
            tokens["completion_tokens"] = usage.output_tokens
        if isinstance(usage.input_tokens, int) and isinstance(usage.output_tokens, int):
            tokens["total_tokens"] = usage.input_tokens + usage.output_tokens

    return output_text, tokens

