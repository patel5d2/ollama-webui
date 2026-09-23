# Live recording outline (student narration required)

Aim for 7-9 minutes. Do not submit a silent automated recording as your personal walkthrough.

0:00-0:45: Explain the five fixed prompts, settings and measurement plan. Admit that existing local setup predates the new plan.

0:45-2:15: Open http://localhost:3000. Select Qwen3 and enter P2 from prompts.json. Show actual generation. Explain Open WebUI is the interface and Ollama runs the model. Show the Python runner and saved raw answer and timing.

2:15-3:45: Open the Colab notebook (https://colab.research.google.com/drive/1EDD1vaZj1z4kkD-GbKDRF1u2NWps7pkY). Show GPU hardware output and rerun a model prompt live. Explain downloaded session files disappear when runtime is deleted and save evidence first.

3:45-5:15: State plainly that Jetstream2 was unavailable, so the third environment is the free Colab T4, and show nvidia-smi plus one live prompt there. Mention the installer 404 you had to work around and that the free tier allows one session at a time.

5:15-6:30: Show low/high temperature answers and the truncated 64-token answer. Explain why the unsafe password-verification suggestion is a failure rather than advice to follow.

6:30-8:00: Show comparison.png and the REPORT.pdf tables and recommendations. Discuss small-model hallucination, incorrect code example comments, the Hugging Face redirect error, and what you would improve (repeat trials, fuller answer budget, stricter quality rubric).

Finish by saving cloud evidence and shutting down the class VM. Upload your recording using your course-approved service and put its accessible link on page one of the final report. Do not show passwords, tokens or keys.
