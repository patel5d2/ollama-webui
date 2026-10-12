# Video script — about 5 minutes, live screens

The assignment asks for **5 to 10 minutes**. This script runs about 5:00 at a normal speaking pace, including the time the
models take to answer. Don't trim it below 5:00. Read the **SAY** lines in your own words; the **SHOW** lines tell you
what must be on screen.

## Before you press record (not part of the 5 minutes)

1. **Mac:** `docker compose up -d`, sign in to Open WebUI at <http://localhost:3000>, select `qwen3:1.7b`, and have P2 ready to paste.
2. **Colab:** open the notebook, choose Runtime → Change runtime type → **T4 GPU**, and run the setup cells (install and model pulls)
   until Ollama answers. Add one new cell, ready to run but not yet run:
   `!ollama run qwen3:1.7b --think=false --verbose "A server processes 120 requests per minute. Traffic increases by 25 percent, then decreases by 20 percent. What is the final requests-per-minute rate? Show the calculation briefly."`
3. **Jetstream2:** make sure the VM is running, open the web desktop, open Terminal and make the font bigger (Ctrl + +).
   Warm the GPU once so the 30-second CUDA start-up doesn't land in your video: `ollama run qwen3:14b --think=false "hi"`.
   Have this ready to paste:
   `ollama run qwen3:14b --think=false --verbose "A fictional employee receives an email saying their account will close in 30 minutes unless they enter their password at https://login.example.invalid. Give five safe triage steps for a security analyst. Do not visit the link. Keep your answer under 120 words."`
4. Open **REPORT.pdf** at the settings table (section 6), the chart (section 7) and the recommendations (section 9).
5. Hide passwords, tokens, the Exosphere login page and your email. Don't type your password while recording.

---

## 0:00 – 0:25 · Introduction

**SHOW:** REPORT.pdf, page 1 (the five prompts table).

**SAY:** "Hi, I'm [name]. For this project I ran the same five prompts on open-source LLMs in three places: my own Mac,
Google Colab, and a Jetstream2 cloud server. I measured speed, memory and answer quality, with the prompts and settings fixed
before measuring: temperature 0.2, a 192-token limit, the same seed, and one Python script recording everything. One prompt
is a phishing-triage question, and one is designed to make the model invent a fake research paper."

## 0:25 – 1:15 · Environment 1: my own computer, with a graphical interface

**SHOW:** Open WebUI. Paste P2 into the chat with `qwen3:1.7b` and let it generate.

**SAY:** "First, my own computer. This is Open WebUI, a graphical interface running in Docker. It talks to Ollama, which
actually runs the model. I'll ask Qwen3 1.7B the arithmetic question: 120 requests a minute, up 25 percent, then down
20 percent."

*(while it generates)* "The right answer is 120." *(If a 'Thinking' section appears:)* "In the GUI, Qwen thinks before it
answers by default; my script turned that off."

"Inside Docker the Mac gives Ollama no GPU, so this ran on the CPU at about 52 tokens a second. Running Ollama natively on the
Mac's Apple GPU got 88, about 1.7 times faster on the same laptop. I also used the command line, and a Python script calling
Ollama's API, which produced every number in my report."

## 1:15 – 2:00 · Environment 2: Google Colab

**SHOW:** The notebook's `nvidia-smi` output (Tesla T4), then run your prepared `ollama run` cell.

**SAY:** "Second, Google Colab's free tier. Here's nvidia-smi showing a Tesla T4 with 15 gigabytes. I'll run the same question
on the same model."

*(point at the eval rate at the bottom of the output)* "In my measured runs the T4 did about 119 tokens a second on this model.
Two catches: Ollama's official installer failed with a 404, so I installed the release file by hand, and when the
session ends everything here is deleted."

## 2:00 – 3:20 · Environment 3: Jetstream2, plus the biggest surprise

**SHOW:** Jetstream2 terminal. Run `nvidia-smi`, then paste the `qwen3:14b` command and let it generate. Then run `ollama ps`.

**SAY:** "Third, Jetstream2: a Linux server with a 20-gigabyte slice of an NVIDIA A100. I got access on Saturday. Here I
could try bigger models: this is Qwen3 14B, about eight times bigger than anything on my Mac, answering the phishing question."

*(when it finishes, point at "eval rate")* "That's about [read the eval rate, about 74 in your test run] tokens a second, close to the 88 my script measured, and `ollama ps`
confirms it's running 100 percent on the GPU."

**SHOW:** run `ls -l /dev/nvidia*` and `id ollama`.

**SAY:** "This was my biggest surprise. The first time, Ollama ran at 20 tokens a second, slower than my laptop, and gave no
error. `ollama ps` said 100 percent CPU. The GPU device files only allow the `vglusers` group, and the `ollama` service
account wasn't in it. You can see it's in the group now, because one `usermod` command fixed it, and the small model went from 20 to 315 tokens a second, about 16 times
faster. I also tried Qwen3 32B. It needs about 20 gigabytes, which is more than the GPU slice can hold, so part of it spilled
onto the CPU and it slowed to 11 tokens a second. The real limit is whether it fits in GPU memory."

## 3:20 – 3:55 · Task 4: changing the settings

**SHOW:** REPORT.pdf, section 6 (the settings table and the bullet points under it).

**SAY:** "For the settings task I ran the phishing prompt at temperature 0.1 and 1.2, and again with a 64-token limit. On my
Mac's CPU, the low temperature, the supposedly safe one, told the analyst to ask the employee to re-enter their password. That's
dangerous advice. The other three backends didn't say it, so one sample proves nothing. The 64-token answer simply stops mid-sentence
with no warning. In security work you have to check the stop reason and keep a human in the loop."

## 3:55 – 4:35 · The comparison and recommendations

**SHOW:** The chart in section 7, then scroll to the recommendations in section 9.

**SAY:** "Here's the comparison. The A100 was fastest on every model, Colab came second, and my Mac's GPU third. But quality
mattered more than speed. Only the 14B and 32B models answered all five prompts correctly. Llama 1B refused the phishing question
everywhere, and the small Hugging Face model made things up on some backends. And identical settings didn't give identical text: Llama got
the arithmetic wrong only on Colab.

My recommendations: for a security analyst's everyday work, a persistent GPU server running a 14B model. For confidential data,
my own machine, because the prompts never leave it. For a quick experiment that has to be done today, Colab. Jetstream2 took days
to get access to, and it silently ran on the CPU until I fixed it."

## 4:35 – 5:00 · What I'd do differently, and wrap-up

**SHOW:** The Jetstream2 terminal or the report's problems table (section 10).

**SAY:** "What I'd do differently: check `ollama ps` before trusting any number, repeat each prompt several times instead of
once, and test the 14B on my Mac, since it might fit in 16 gigabytes. I used an AI assistant for commands and debugging, which the
assignment allows, but everything here ran live. Last step: I'll shelve the Jetstream2 VM so it stops
using the class allocation. Thanks for watching."

---

After recording, upload the video, paste its link into the red placeholder on page 1 of the report (`report.py` line with
"paste your video link here"), rebuild the PDF, and **shelve the Jetstream2 instance in Exosphere**.
