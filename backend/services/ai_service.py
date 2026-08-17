import time
import httpx
import json
from typing import Generator, Optional, List
from backend.core.config import settings
from backend.services.model_manager import (
    model_manager,
    STATE_LOADING,
    STATE_ACTIVE,
    STATE_IDLE,
    STATE_ERROR
)

OLLAMA_URL = "http://localhost:11434/api/generate"


def call_model(
    prompt: str, 
    model: Optional[str] = None, 
    keep_alive: Optional[str] = None,
    images: Optional[list] = None
) -> str:
    """
    Executes a single non-streaming completion call to an Ollama model with telemetry tracking.
    """
    model = model or settings.MODEL_DEFAULT
    keep_alive = keep_alive if keep_alive is not None else settings.MODEL_KEEP_ALIVE_SESSION

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": keep_alive
    }
    
    if images:
        payload["images"] = images

    model_manager.set_model_state(model, STATE_LOADING)
    start_time = time.time()

    try:
        model_manager.set_model_state(model, STATE_ACTIVE)
        response = httpx.post(
            OLLAMA_URL,
            json=payload,
            timeout=300.0
        )
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        if response.status_code == 200:
            data = response.json()
            reply_text = data.get("response", "").strip()
            
            # Extract real token counts from Ollama response if provided
            input_tokens = data.get("prompt_eval_count", len(prompt.split()))
            output_tokens = data.get("eval_count", len(reply_text.split()))
            total_duration_s = max(0.001, end_time - start_time)
            tok_per_sec = output_tokens / total_duration_s

            model_manager.record_telemetry(
                model=model,
                mode="direct_call",
                latency_ms=latency_ms,
                first_token_latency=total_duration_s * 0.4,
                tokens_per_second=tok_per_sec,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            model_manager.set_model_state(model, STATE_IDLE)
            return reply_text
        else:
            model_manager.set_model_state(model, STATE_ERROR)
            return f"Error: Ollama returned status code {response.status_code}"
    except Exception as e:
        model_manager.set_model_state(model, STATE_ERROR)
        return f"Error calling Ollama API: {str(e)}"


def call_model_with(model: str, prompt: str, keep_alive: Optional[str] = None) -> str:
    """Custom model helper wrapper."""
    return call_model(prompt, model=model, keep_alive=keep_alive)


def stream_model(
    prompt: str, 
    model: Optional[str] = None, 
    keep_alive: Optional[str] = None,
    images: Optional[list] = None
) -> Generator[str, None, None]:
    """
    Streams a completion from Ollama line-by-line with real first-token and tok/s telemetry.
    """
    model = model or settings.MODEL_DEFAULT
    keep_alive = keep_alive if keep_alive is not None else settings.MODEL_KEEP_ALIVE_SESSION

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "keep_alive": keep_alive
    }

    if images:
        payload["images"] = images

    model_manager.set_model_state(model, STATE_LOADING)
    start_time = time.time()
    first_token_time: Optional[float] = None
    output_tokens_count = 0
    prompt_tokens_est = len(prompt.split())

    try:
        model_manager.set_model_state(model, STATE_ACTIVE)
        with httpx.stream(
            "POST",
            OLLAMA_URL,
            json=payload,
            timeout=httpx.Timeout(timeout=300.0, connect=10.0)
        ) as r:
            for line in r.iter_lines():
                if line:
                    data = json.loads(line)
                    chunk = data.get("response", "")
                    if chunk:
                        if first_token_time is None:
                            first_token_time = time.time()
                        output_tokens_count += len(chunk.split()) or 1
                        yield chunk

                    # If Ollama sent the final evaluation object in stream
                    if data.get("done", False):
                        final_prompt_tokens = data.get("prompt_eval_count", prompt_tokens_est)
                        final_eval_tokens = data.get("eval_count", output_tokens_count)
                        end_time = time.time()
                        latency_ms = (end_time - start_time) * 1000
                        first_tok_s = (first_token_time - start_time) if first_token_time else 0.5
                        gen_duration = max(0.001, end_time - (first_token_time or start_time))
                        tok_per_sec = final_eval_tokens / gen_duration

                        model_manager.record_telemetry(
                            model=model,
                            mode="streaming",
                            latency_ms=latency_ms,
                            first_token_latency=first_tok_s,
                            tokens_per_second=tok_per_sec,
                            input_tokens=final_prompt_tokens,
                            output_tokens=final_eval_tokens
                        )

        model_manager.set_model_state(model, STATE_IDLE)
    except Exception as e:
        model_manager.set_model_state(model, STATE_ERROR)
        yield f"Error in stream: {str(e)}"


def unload_model(model_name: str) -> bool:
    """Instructs model_manager to immediately unload the specified model."""
    return model_manager.unload_model(model_name)