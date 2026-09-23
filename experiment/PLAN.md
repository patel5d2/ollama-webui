# Experiment plan — saved before new measured runs

Prepared 2026-09-23. Existing installation and model downloads predate this plan; do not claim this was written before installing tools. Measurements below are new, assistant-operated runs for the student to inspect and repeat.

Use the exact five prompts in prompts.json on every model and environment. P1 is cybersecurity; P5 deliberately requests an invented citation to test hallucination and uncertainty. Expected P2 answer is 120. Assess P3 missing-key handling and P4 unsupported additions.

Local baseline: existing Docker Ollama and Open WebUI. Models: existing qwen3:1.7b, llama3.2:1b, and hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M downloaded from Hugging Face. Two families, three parameter sizes. Attempt a larger Qwen model on Jetstream2 if access and memory permit. Also measure native macOS Ollama GPU if installation is available; label CPU/GPU separately.

Use Ollama's non-streaming /api/generate endpoint with no conversation history, temperature 0.2, top_p 0.9, num_predict 192, num_ctx 2048, seed 42, and think=false. Save exact settings, model metadata, version, answers and raw timings. A token limit may truncate answers; record done_reason. Downloads are excluded from model loading time.

Unload before each model suite, load with an empty prompt, then run five warm prompts sequentially. Model load = dedicated request wall time and server load_duration. Answer time = client request wall time. Generation speed = eval_count / (eval_duration / 1e9); this excludes prompt processing and loading. One run per prompt is exploratory, not a statistically robust benchmark. OS file caches are not cleared, so unloaded does not mean disk-cold.

Memory: sample /api/ps after each response, recording resident model allocation size and size_vram. This is an allocation snapshot, NOT peak RAM or whole-machine memory. Record host RAM and GPU separately, plus Docker VM RAM/CPU limits. Apply the same allocation measurement in every environment and mark unsupported measurements unavailable.

Settings experiment on qwen3:1.7b using P1: temperature 0.1 versus 1.2 at fixed top_p 0.9 and limit 192; then temperature 0.1 with token limit 64. Same seed, context and prompt. No causal claims from a single sample.

| Environment | Model / size / quantization | Load seconds | Prompt | Answer seconds | Tokens/s | Model allocation bytes | GPU allocation bytes | Outcome |
|---|---|---|---|---|---|---|---|---|
| pending | pending | | | | | | | |

Save hardware command output, errors and troubleshooting. Do not fabricate unavailable cloud results. Screenshots should show visible model names, prompts and outputs without account credentials. Cloud access and live student narration are required to finish all evidence.
