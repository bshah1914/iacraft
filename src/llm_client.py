"""Universal LLM client for message-to-iaac.

Supports 11 providers: Groq, Gemini, OpenAI, Claude, Ollama,
AWS Bedrock, Azure OpenAI, Mistral, DeepSeek, Cohere, Together AI.
Auto-fallback on rate limits.
"""

import os
import json
import httpx
from typing import Optional, Callable


# Model context window sizes (approximate)
MODEL_CONTEXT_SIZES = {
    "qwen2.5-coder:1.5b": 4096,
    "qwen2.5-coder:3b": 4096,
    "qwen2.5-coder:7b": 8192,
    "qwen2.5-coder:14b": 8192,
    "qwen2.5-coder:72b": 32768,
    "phi3:mini": 4096,
    "llama3:8b": 8192,
    "codellama:7b": 4096,
    "deepseek-coder:6.7b": 8192,
}

DEFAULT_CONTEXT_SIZE = 4096


def _get_context_size(model: str) -> int:
    return MODEL_CONTEXT_SIZES.get(model, DEFAULT_CONTEXT_SIZE)


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _cap_max_tokens(model: str, system_prompt: str, user_prompt: str, requested_max: int) -> int:
    ctx = _get_context_size(model)
    input_tokens = _estimate_tokens(system_prompt) + _estimate_tokens(user_prompt)
    available = ctx - input_tokens - 100
    return max(256, min(requested_max, available))


def _repair_truncated_json(text: str) -> str:
    first_brace = text.find('{')
    first_bracket = text.find('[')
    if first_brace == -1 and first_bracket == -1:
        return text
    start = min(x for x in [first_brace, first_bracket] if x != -1)
    json_text = text[start:]
    in_string = False
    escape_next = False
    stack = []
    for ch in json_text:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ('{', '['):
            stack.append(ch)
        elif ch == '}' and stack and stack[-1] == '{':
            stack.pop()
        elif ch == ']' and stack and stack[-1] == '[':
            stack.pop()
    repaired = json_text
    if in_string:
        repaired += '"'
    repaired = repaired.rstrip().rstrip(',')
    for opener in reversed(stack):
        repaired += '}' if opener == '{' else ']'
    return repaired


def _extract_json(raw: str) -> dict:
    cleaned = raw.strip()
    if "```json" in cleaned:
        start = cleaned.index("```json") + 7
        try:
            end = cleaned.index("```", start)
            cleaned = cleaned[start:end].strip()
        except ValueError:
            cleaned = cleaned[start:].strip()
    elif "```" in cleaned:
        start = cleaned.index("```") + 3
        try:
            end = cleaned.index("```", start)
            cleaned = cleaned[start:end].strip()
        except ValueError:
            cleaned = cleaned[start:].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        first = cleaned.find(start_char)
        last = cleaned.rfind(end_char)
        if first != -1 and last > first:
            try:
                return json.loads(cleaned[first:last + 1])
            except json.JSONDecodeError:
                continue
    repaired = _repair_truncated_json(cleaned)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    raise ValueError(f"Failed to parse JSON from LLM response. Response starts with: {raw[:200]}...")


# =============================================================================
# Provider Implementations
# =============================================================================

class GroqClient:
    """Groq — FREE, ultra-fast inference."""

    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY not set. Get free key: https://console.groq.com/keys")
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2) -> str:
        r = self.client.chat.completions.create(
            model=self.model, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        )
        return r.choices[0].message.content

    def generate_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192) -> dict:
        return _extract_json(self.generate(system_prompt, user_prompt, max_tokens))

    def generate_streaming(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2, callback: Optional[Callable] = None) -> str:
        full = ""
        for chunk in self.client.chat.completions.create(
            model=self.model, max_tokens=max_tokens, temperature=temperature, stream=True,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        ):
            text = chunk.choices[0].delta.content or ""
            full += text
            if callback and text: callback(text)
        return full


class GeminiClient:
    """Google Gemini — free tier available."""

    def __init__(self, model: str = "gemini-2.0-flash"):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY not set. Get free key: https://aistudio.google.com/apikey")
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2) -> str:
        from google.genai import types
        r = self.client.models.generate_content(
            model=self.model, contents=user_prompt,
            config=types.GenerateContentConfig(system_instruction=system_prompt, max_output_tokens=max_tokens, temperature=temperature),
        )
        return r.text

    def generate_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192) -> dict:
        enhanced = system_prompt + "\n\nIMPORTANT: Respond with ONLY valid JSON."
        return _extract_json(self.generate(enhanced, user_prompt, max_tokens))

    def generate_streaming(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2, callback: Optional[Callable] = None) -> str:
        from google.genai import types
        full = ""
        for chunk in self.client.models.generate_content_stream(
            model=self.model, contents=user_prompt,
            config=types.GenerateContentConfig(system_instruction=system_prompt, max_output_tokens=max_tokens, temperature=temperature),
        ):
            text = chunk.text or ""
            full += text
            if callback and text: callback(text)
        return full


class OpenAIClient:
    """OpenAI — GPT-4o, GPT-4o-mini."""

    def __init__(self, model: str = "gpt-4o-mini"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY not set.")
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2) -> str:
        r = self.client.chat.completions.create(
            model=self.model, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        )
        return r.choices[0].message.content

    def generate_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192) -> dict:
        return _extract_json(self.generate(system_prompt, user_prompt, max_tokens))

    def generate_streaming(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2, callback: Optional[Callable] = None) -> str:
        full = ""
        for chunk in self.client.chat.completions.create(
            model=self.model, max_tokens=max_tokens, temperature=temperature, stream=True,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        ):
            text = chunk.choices[0].delta.content or ""
            full += text
            if callback and text: callback(text)
        return full


class ClaudeClient:
    """Anthropic Claude API."""

    def __init__(self, model: str = "claude-sonnet-4-6-20250514"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY not set.")
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2) -> str:
        r = self.client.messages.create(
            model=self.model, max_tokens=max_tokens, temperature=temperature,
            system=system_prompt, messages=[{"role": "user", "content": user_prompt}],
        )
        return r.content[0].text

    def generate_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192) -> dict:
        return _extract_json(self.generate(system_prompt, user_prompt, max_tokens))

    def generate_streaming(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2, callback: Optional[Callable] = None) -> str:
        full = ""
        with self.client.messages.stream(
            model=self.model, max_tokens=max_tokens, temperature=temperature,
            system=system_prompt, messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for text in stream.text_stream:
                full += text
                if callback: callback(text)
        return full


class AWSBedrockClient:
    """AWS Bedrock — Claude, Llama, Mistral on AWS."""

    def __init__(self, model: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0"):
        import boto3
        self.client = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2) -> str:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens, "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": [{"type": "text", "text": user_prompt}]}],
        })
        r = self.client.invoke_model(modelId=self.model, body=body)
        result = json.loads(r["body"].read())
        return result["content"][0]["text"]

    def generate_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192) -> dict:
        return _extract_json(self.generate(system_prompt, user_prompt, max_tokens))

    def generate_streaming(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2, callback: Optional[Callable] = None) -> str:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens, "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": [{"type": "text", "text": user_prompt}]}],
        })
        r = self.client.invoke_model_with_response_stream(modelId=self.model, body=body)
        full = ""
        for event in r["body"]:
            chunk = json.loads(event["chunk"]["bytes"])
            if chunk.get("type") == "content_block_delta":
                text = chunk.get("delta", {}).get("text", "")
                full += text
                if callback and text: callback(text)
        return full


class AzureOpenAIClient:
    """Azure OpenAI — GPT models on Azure."""

    def __init__(self, model: str = "gpt-4o-mini"):
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not endpoint or not api_key:
            raise EnvironmentError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set.")
        from openai import AzureOpenAI
        self.client = AzureOpenAI(azure_endpoint=endpoint, api_key=api_key, api_version="2024-10-21")
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2) -> str:
        r = self.client.chat.completions.create(
            model=self.model, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        )
        return r.choices[0].message.content

    def generate_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192) -> dict:
        return _extract_json(self.generate(system_prompt, user_prompt, max_tokens))

    def generate_streaming(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2, callback: Optional[Callable] = None) -> str:
        full = ""
        for chunk in self.client.chat.completions.create(
            model=self.model, max_tokens=max_tokens, temperature=temperature, stream=True,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        ):
            text = chunk.choices[0].delta.content or ""
            full += text
            if callback and text: callback(text)
        return full


class MistralClient:
    """Mistral AI — Mistral Large, Codestral."""

    def __init__(self, model: str = "mistral-large-latest"):
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise EnvironmentError("MISTRAL_API_KEY not set. Get key: https://console.mistral.ai/api-keys")
        from mistralai import Mistral
        self.client = Mistral(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2) -> str:
        r = self.client.chat.complete(
            model=self.model, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        )
        return r.choices[0].message.content

    def generate_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192) -> dict:
        return _extract_json(self.generate(system_prompt, user_prompt, max_tokens))

    def generate_streaming(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2, callback: Optional[Callable] = None) -> str:
        full = ""
        for chunk in self.client.chat.stream(
            model=self.model, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        ):
            text = chunk.data.choices[0].delta.content or ""
            full += text
            if callback and text: callback(text)
        return full


class DeepSeekClient:
    """DeepSeek — ultra cheap coding model."""

    def __init__(self, model: str = "deepseek-coder"):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise EnvironmentError("DEEPSEEK_API_KEY not set. Get key: https://platform.deepseek.com/api_keys")
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2) -> str:
        r = self.client.chat.completions.create(
            model=self.model, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        )
        return r.choices[0].message.content

    def generate_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192) -> dict:
        return _extract_json(self.generate(system_prompt, user_prompt, max_tokens))

    def generate_streaming(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2, callback: Optional[Callable] = None) -> str:
        full = ""
        for chunk in self.client.chat.completions.create(
            model=self.model, max_tokens=max_tokens, temperature=temperature, stream=True,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        ):
            text = chunk.choices[0].delta.content or ""
            full += text
            if callback and text: callback(text)
        return full


class CohereClient:
    """Cohere — Command R+, free trial available."""

    def __init__(self, model: str = "command-r-plus"):
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key:
            raise EnvironmentError("COHERE_API_KEY not set. Get key: https://dashboard.cohere.com/api-keys")
        import cohere
        self.client = cohere.ClientV2(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2) -> str:
        r = self.client.chat(
            model=self.model, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        )
        return r.message.content[0].text

    def generate_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192) -> dict:
        enhanced = system_prompt + "\n\nIMPORTANT: Respond with ONLY valid JSON."
        return _extract_json(self.generate(enhanced, user_prompt, max_tokens))

    def generate_streaming(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2, callback: Optional[Callable] = None) -> str:
        full = ""
        for event in self.client.chat_stream(
            model=self.model, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        ):
            if event.type == "content-delta":
                text = event.delta.message.content.text or ""
                full += text
                if callback and text: callback(text)
        return full


class TogetherClient:
    """Together AI — $25 free credit, Llama/Qwen/Mixtral."""

    def __init__(self, model: str = "Qwen/Qwen2.5-Coder-32B-Instruct"):
        api_key = os.getenv("TOGETHER_API_KEY")
        if not api_key:
            raise EnvironmentError("TOGETHER_API_KEY not set. Get key: https://api.together.ai/settings/api-keys")
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url="https://api.together.xyz/v1")
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2) -> str:
        r = self.client.chat.completions.create(
            model=self.model, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        )
        return r.choices[0].message.content

    def generate_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192) -> dict:
        return _extract_json(self.generate(system_prompt, user_prompt, max_tokens))

    def generate_streaming(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2, callback: Optional[Callable] = None) -> str:
        full = ""
        for chunk in self.client.chat.completions.create(
            model=self.model, max_tokens=max_tokens, temperature=temperature, stream=True,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        ):
            text = chunk.choices[0].delta.content or ""
            full += text
            if callback and text: callback(text)
        return full


class OllamaClient:
    """Ollama — local/remote, unlimited, free."""

    TIMEOUT = httpx.Timeout(connect=10.0, read=1800.0, write=10.0, pool=30.0)

    def __init__(self, model: str = "qwen2.5-coder:7b", base_url: str = None):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model
        self.context_size = _get_context_size(model)
        self._verify_connection()

    def _verify_connection(self):
        try:
            resp = httpx.get(f"{self.base_url}/", timeout=5.0)
            if resp.status_code != 200:
                raise ConnectionError(f"Ollama returned status {resp.status_code}")
        except httpx.ConnectError:
            raise ConnectionError(f"Cannot connect to Ollama at {self.base_url}. Run: ollama serve")

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2) -> str:
        return self.generate_streaming(system_prompt, user_prompt, max_tokens, temperature)

    def generate_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192) -> dict:
        enhanced = system_prompt + "\n\nIMPORTANT: Respond with ONLY valid JSON."
        return _extract_json(self.generate(enhanced, user_prompt, max_tokens))

    def generate_streaming(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2, callback: Optional[Callable] = None) -> str:
        safe_max = _cap_max_tokens(self.model, system_prompt, user_prompt, max_tokens)
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "stream": True,
            "options": {"num_ctx": self.context_size, "temperature": temperature, "num_predict": safe_max, "top_k": 40, "top_p": 0.9},
        }
        full = ""
        with httpx.stream("POST", f"{self.base_url}/api/chat", json=payload, timeout=self.TIMEOUT) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    chunk = json.loads(line)
                    text = chunk.get("message", {}).get("content", "")
                    full += text
                    if callback and text: callback(text)
        return full


# =============================================================================
# Provider Registry & Unified Client
# =============================================================================

PROVIDER_MAP = {
    "groq": GroqClient,
    "gemini": GeminiClient,
    "openai": OpenAIClient,
    "claude": ClaudeClient,
    "bedrock": AWSBedrockClient,
    "azure_openai": AzureOpenAIClient,
    "mistral": MistralClient,
    "deepseek": DeepSeekClient,
    "cohere": CohereClient,
    "together": TogetherClient,
    "ollama": OllamaClient,
}

DEFAULT_MODELS_MAP = {
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-2.0-flash",
    "openai": "gpt-4o-mini",
    "claude": "claude-sonnet-4-6-20250514",
    "bedrock": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    "azure_openai": "gpt-4o-mini",
    "mistral": "mistral-large-latest",
    "deepseek": "deepseek-coder",
    "cohere": "command-r-plus",
    "together": "Qwen/Qwen2.5-Coder-32B-Instruct",
    "ollama": "qwen2.5-coder:7b",
}

FALLBACK_CHAIN = {
    "groq": ["gemini", "together", "ollama"],
    "gemini": ["groq", "together", "ollama"],
    "openai": ["groq", "gemini", "ollama"],
    "claude": ["groq", "gemini", "ollama"],
    "bedrock": ["groq", "gemini", "ollama"],
    "azure_openai": ["groq", "gemini", "ollama"],
    "mistral": ["groq", "gemini", "ollama"],
    "deepseek": ["groq", "gemini", "ollama"],
    "cohere": ["groq", "gemini", "ollama"],
    "together": ["groq", "gemini", "ollama"],
    "ollama": [],
}

# Env var required per provider
PROVIDER_ENV_KEYS = {
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "bedrock": None,  # Uses AWS credentials
    "azure_openai": "AZURE_OPENAI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "cohere": "COHERE_API_KEY",
    "together": "TOGETHER_API_KEY",
    "ollama": None,
}


def _create_backend(provider: str, model: str = None, ollama_url: str = None):
    provider = provider.lower()
    cls = PROVIDER_MAP.get(provider)
    if not cls:
        raise ValueError(f"Unsupported provider: {provider}. Available: {list(PROVIDER_MAP.keys())}")
    default_model = DEFAULT_MODELS_MAP.get(provider)
    if provider == "ollama":
        return cls(model=model or default_model, base_url=ollama_url)
    return cls(model=model or default_model)


class LLMClient:
    """Unified LLM client with automatic fallback on rate limits."""

    def __init__(self, provider: str = "groq", model: str = None, ollama_url: str = None):
        self.provider = provider.lower()
        self.model = model
        self.ollama_url = ollama_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._backend = _create_backend(self.provider, model, ollama_url)
        self._active_provider = self.provider
        self._on_fallback = None

    def _is_rate_limit(self, error: Exception) -> bool:
        err = str(error).lower()
        return any(kw in err for kw in ["429", "rate_limit", "resource_exhausted", "quota", "too many requests", "throttl"])

    def _get_fallback(self):
        chain = FALLBACK_CHAIN.get(self._active_provider, [])
        for fp in chain:
            try:
                env_key = PROVIDER_ENV_KEYS.get(fp)
                if env_key and not os.getenv(env_key):
                    continue
                if fp == "ollama":
                    try:
                        httpx.get(f"{self.ollama_url}/", timeout=3.0)
                    except Exception:
                        continue
                backend = _create_backend(fp, ollama_url=self.ollama_url)
                old = self._active_provider
                self._active_provider = fp
                if self._on_fallback:
                    self._on_fallback(old, fp, "rate limit")
                return backend
            except Exception:
                continue
        return None

    def _call_with_fallback(self, method_name: str, *args, **kwargs):
        try:
            return getattr(self._backend, method_name)(*args, **kwargs)
        except Exception as e:
            if self._is_rate_limit(e):
                fallback = self._get_fallback()
                if fallback:
                    self._backend = fallback
                    return getattr(self._backend, method_name)(*args, **kwargs)
            raise

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2) -> str:
        return self._call_with_fallback("generate", system_prompt, user_prompt, max_tokens, temperature)

    def generate_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192) -> dict:
        return self._call_with_fallback("generate_json", system_prompt, user_prompt, max_tokens)

    def generate_streaming(self, system_prompt: str, user_prompt: str, max_tokens: int = 8192, temperature: float = 0.2, callback: Optional[Callable] = None) -> str:
        return self._call_with_fallback("generate_streaming", system_prompt, user_prompt, max_tokens, temperature, callback)
