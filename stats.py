def build_stats(model, data):
    prompt_tokens = data.get("prompt_eval_count", 0) or 0
    generated_tokens = data.get("eval_count", 0) or 0

    total_tokens = prompt_tokens + generated_tokens

    prompt_duration = (
        data.get("prompt_eval_duration", 0) or 0
    ) / 1_000_000_000

    generation_duration = (
        data.get("eval_duration", 0) or 0
    ) / 1_000_000_000

    total_duration = (
        data.get("total_duration", 0) or 0
    ) / 1_000_000_000

    tokens_per_second = (
        generated_tokens / generation_duration
        if generation_duration > 0
        else 0
    )

    return {
        "type": "stats",
        "model": model,
        "prompt_tokens": prompt_tokens,
        "generated_tokens": generated_tokens,
        "total_tokens": total_tokens,
        "prompt_duration": round(prompt_duration, 2),
        "generation_duration": round(generation_duration, 2),
        "total_duration": round(total_duration, 2),
        "tokens_per_second": round(tokens_per_second, 2),
    }