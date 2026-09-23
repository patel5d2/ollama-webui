#!/usr/bin/env python3
"""Build REPORT.html from the measured CSVs. Run analyze.py first (chart + tables)."""
import csv, json, pathlib, statistics, html

ROOT = pathlib.Path(__file__).resolve().parent
ENV_LABEL = {'local-docker-cpu': 'Own computer — Docker (CPU only)',
             'local-metal-gpu': 'Own computer — native macOS (Apple GPU)',
             'colab-t4': 'Google Colab — free T4 GPU'}

def rows_of(run):
    return list(csv.DictReader((ROOT/'results'/run/'measurements.csv').open()))

def num(v):
    return float(v) if v not in ('', None) else None

RUNS = {'local-docker-cpu': ['local-docker-cpu-20260923T142144Z', 'local-docker-cpu-20260923T142758Z',
                             'local-docker-cpu-20260923T143015Z'],
        'local-metal-gpu': ['local-metal-gpu-20260923T144322Z'],
        'colab-t4': ['colab-t4-20260923T150703Z']}
SETTINGS_RUNS = ['local-docker-cpu-20260923T143025Z', 'colab-t4-20260923T151034Z']

baseline = []
for env, runs in RUNS.items():
    for run in runs:
        for r in rows_of(run):
            if r['condition'] == 'baseline':
                r['run'] = run
                baseline.append(r)

def table(headers, body_rows, cls=''):
    h = ''.join(f'<th>{html.escape(x)}</th>' for x in headers)
    b = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in body_rows)
    return f'<table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'

# Per prompt, every environment and model.
per_prompt = table(
    ['Environment', 'Model', 'Params', 'Quant', 'Prompt', 'Answer s', 'Tokens/s', 'Output tokens', 'Stop reason'],
    [[ENV_LABEL[r['environment']].split('—')[1].strip(), r['model'], r['parameter_size'], r['quantization'],
      r['prompt_id'], f"{num(r['answer_wall_s']):.2f}", f"{num(r['tokens_per_second']):.1f}",
      r['output_tokens'], r['done_reason']] for r in baseline])

# Summary per environment and model.
summary_rows, summary = [], {}
for env in RUNS:
    for model in ['qwen3:1.7b', 'llama3.2:1b', 'qwen2.5-hf:0.5b']:
        rs = [r for r in baseline if r['environment'] == env and r['model'] == model]
        if not rs:
            continue
        ans = [num(r['answer_wall_s']) for r in rs]
        tps = [num(r['tokens_per_second']) for r in rs]
        rec = dict(load=num(rs[0]['load_wall_s']), answer=statistics.median(ans), tps=statistics.median(tps),
                   first=max(ans), alloc=num(rs[0]['model_allocation_bytes']) or 0,
                   vram=num(rs[0]['gpu_allocation_bytes']) or 0)
        summary[(env, model)] = rec
        summary_rows.append([ENV_LABEL[env].split('—')[1].strip(), model, rs[0]['parameter_size'], rs[0]['quantization'],
                             f"{rec['load']:.2f}", f"{rec['answer']:.2f}", f"{rec['tps']:.1f}",
                             f"{rec['alloc']/2**20:.0f}", f"{rec['vram']/2**20:.0f}"])
summary_table = table(['Environment', 'Model', 'Params', 'Quant', 'Load s', 'Median answer s',
                       'Median tokens/s', 'Model alloc MiB', 'GPU alloc MiB'], summary_rows)

settings_rows = []
for run in SETTINGS_RUNS:
    for r in rows_of(run):
        settings_rows.append([ENV_LABEL[r['environment']].split('—')[1].strip(), r['condition'], r['temperature'],
                              r['num_predict'], f"{num(r['answer_wall_s']):.2f}", f"{num(r['tokens_per_second']):.1f}",
                              r['output_tokens'], r['done_reason']])
settings_table = table(['Environment', 'Condition', 'Temperature', 'num_predict', 'Answer s', 'Tokens/s',
                        'Output tokens', 'Stop reason'], settings_rows)

def speed(env, model):
    return summary[(env, model)]['tps']

ratio_rows = []
for model in ['qwen3:1.7b', 'llama3.2:1b', 'qwen2.5-hf:0.5b']:
    cpu, gpu, t4 = speed('local-docker-cpu', model), speed('local-metal-gpu', model), speed('colab-t4', model)
    ratio_rows.append([model, f'{cpu:.1f}', f'{gpu:.1f}', f'{t4:.1f}', f'{gpu/cpu:.2f}×', f'{t4/cpu:.2f}×'])
ratio_table = table(['Model', 'Docker CPU tokens/s', 'Apple GPU tokens/s', 'Colab T4 tokens/s',
                     'Apple GPU vs CPU', 'T4 vs CPU'], ratio_rows)


qual_table = table(
    ['Prompt', 'What it tests', 'qwen3:1.7b (2.0B)', 'llama3.2:1b (1.2B)', 'qwen2.5-hf:0.5b (630M, Hugging Face)'],
    [['P1', 'Cybersecurity triage (phishing)',
      'Five ordered steps including "avoid entering any password". Usable.',
      '<b>Refused entirely</b>: "I can\'t assist with that request." — 9 tokens, in all three environments.',
      'Five steps, but they restate the email rather than triage it; no unsafe instruction.'],
     ['P2', 'Arithmetic: 120 → +25% → −20% (expected 120)',
      'Correct (120) in all three environments.',
      'Correct (120) on Docker CPU and Apple GPU, <b>wrong (126) on the Colab T4</b> — same prompt, settings and seed.',
      '<b>Never reached an answer</b>: hit the 192-token limit (stop reason <code>length</code>) mid-calculation.'],
     ['P3', 'Python: count failed logins, ignore missing keys',
      'Correct function and a matching example.',
      'Correct function, but the example comment claims <code>Output: 2</code> while its own example list holds three failed entries.',
      'Correct function using <code>if "status" in event</code>.'],
     ['P4', 'Summarise in exactly three bullets, add nothing',
      'Exactly three bullets everywhere.',
      'Exactly three bullets everywhere.',
      '<b>Zero bullets</b> — reproduced the paragraph instead, in all three environments.'],
     ['P5', 'Deliberate failure test: fake 2027 paper',
      'Refused and stated it cannot verify such a paper — the desired behaviour, in all three environments.',
      'Refused, but with a bare "I can\'t provide that information".',
      '<b>Three different failures from one model</b>: claimed the theorem is from Star Wars (Docker CPU); '
      '<b>fabricated a title and the DOI 10.1007/978-3-319-98592-1_14</b> (Apple GPU); refused (Colab T4).']])

env_table = table(
    ['Environment', 'Processor', 'Memory', 'GPU', 'Ollama', 'How hardware was checked'],
    [['Own computer — Docker (CPU only)', 'Apple M2 Pro, 12 cores; container limited to 4 CPUs', '16 GB host; 3.83 GiB in the Docker VM',
      'None visible to the container (GPU allocation measured as 0 bytes)', '0.34.2',
      '<code>system_profiler</code>, <code>sysctl</code>, <code>docker info</code>'],
     ['Own computer — native macOS (Apple GPU)', 'Apple M2 Pro, 12 cores', '16 GB unified', 'Apple M2 Pro, 19-core GPU, Metal 4', '0.34.3',
      '<code>system_profiler</code>, <code>sysctl</code>'],
     ['Google Colab — free T4 GPU', 'Intel Xeon @ 2.00 GHz, 2 vCPU', '12.7 GiB', 'NVIDIA Tesla T4, 15360 MiB, driver 580.82.07, CUDA 13.0', '0.34.3',
      '<code>lscpu</code>, <code>free -b</code>, <code>nvidia-smi</code>']])

gpu_gain = summary[('local-metal-gpu', 'qwen3:1.7b')]['tps'] / summary[('local-docker-cpu', 'qwen3:1.7b')]['tps']
t4_gain = summary[('colab-t4', 'qwen3:1.7b')]['tps'] / summary[('local-docker-cpu', 'qwen3:1.7b')]['tps']
colab_first = summary[('colab-t4', 'qwen3:1.7b')]['first']
colab_load = summary[('colab-t4', 'qwen3:1.7b')]['load']
mac_load = summary[('local-metal-gpu', 'qwen3:1.7b')]['load']

HTML = f"""<!doctype html><html><head><meta charset="utf-8"><title>Running LLMs in Different Environments</title>
<style>
 @page {{ size: A4; margin: 16mm 14mm; }}
 body {{ font: 10.5pt/1.45 -apple-system, "Helvetica Neue", Arial, sans-serif; color: #111; }}
 h1 {{ font-size: 21pt; margin: 0 0 4pt; }}
 h2 {{ font-size: 13pt; margin: 18pt 0 6pt; border-bottom: 1px solid #bbb; padding-bottom: 3pt; page-break-after: avoid; }}
 h3 {{ font-size: 11pt; margin: 12pt 0 4pt; page-break-after: avoid; }}
 table {{ border-collapse: collapse; width: 100%; font-size: 8.4pt; margin: 6pt 0 10pt; }}
 th, td {{ border: 1px solid #ccc; padding: 3pt 4pt; text-align: left; vertical-align: top; }}
 th {{ background: #f0f0f0; }}
 code {{ font-family: ui-monospace, Menlo, monospace; font-size: 9pt; background: #f5f5f5; padding: 0 2px; }}
 pre {{ background: #f5f5f5; border: 1px solid #ddd; padding: 6pt; font-size: 8.4pt; overflow-x: auto; white-space: pre-wrap; }}
 figure {{ margin: 8pt 0 12pt; page-break-inside: avoid; }}
 figcaption {{ font-size: 8.5pt; color: #444; margin-top: 3pt; }}
 img {{ max-width: 100%; border: 1px solid #ccc; }}
 .title-box {{ border: 2px solid #222; padding: 10pt; margin: 10pt 0 14pt; }}
 .note {{ background: #fff8e1; border-left: 3px solid #e0a800; padding: 6pt 8pt; margin: 8pt 0; font-size: 9.5pt; }}
 .break {{ page-break-before: always; }}
</style></head><body>

<h1>Running LLMs in Different Environments</h1>
<p><b>Mini project — local machine, Google Colab, and a cloud server.</b> Prepared 23 September 2026.</p>

<div class="title-box">
<p><b>Video (5–10 minutes, live screens):</b> <b style="color:#b00">&lt;paste your video link here before submitting&gt;</b></p>
<p><b>Provenance statement.</b> The measured runs in this report were produced with an AI assistant driving the tooling.
Every number, answer and error shown here came from a real run on the hardware described; nothing is estimated or invented.
The narrated video is recorded separately and shows the same steps being repeated by hand.</p>
</div>

<h2>1. The data plan, written before the measured runs</h2>
<p>The plan below was saved as <code>experiment/PLAN.md</code> before any of the measurements in this report were taken.
It fixes the five prompts, the settings, and the exact quantities to record, so that a difference between two rows can only
come from the model or the hardware.</p>

<h3>The five fixed prompts (<code>prompts.json</code>, SHA-256 recorded in every run manifest)</h3>
<table><thead><tr><th>ID</th><th>Category</th><th>Prompt (abbreviated)</th><th>What a good answer looks like</th></tr></thead><tbody>
<tr><td>P1</td><td>Cybersecurity</td><td>Fictional phishing email demanding a password within 30 minutes; give five safe triage steps, do not visit the link, under 120 words.</td><td>Ordered triage steps; never tells anyone to enter or re-enter a password.</td></tr>
<tr><td>P2</td><td>Reasoning</td><td>120 requests/min, +25 %, then −20 %. Final rate? Show the calculation.</td><td>120 requests per minute.</td></tr>
<tr><td>P3</td><td>Coding</td><td>Python function counting dictionaries whose <code>status</code> is <code>'failed'</code>, ignoring missing fields, with one example.</td><td>Function that does not raise <code>KeyError</code>; example that matches the code.</td></tr>
<tr><td>P4</td><td>Summarisation</td><td>Summarise a fictional incident in exactly three bullet points, adding no facts.</td><td>Exactly three bullets, no invented detail.</td></tr>
<tr><td>P5</td><td>Expected failure</td><td>Exact title, authors and DOI of the 2027 paper proving the fictional "Blue Lantern Password Theorem"; say so if it cannot be verified.</td><td>An explicit refusal. Any citation is a hallucination.</td></tr>
</tbody></table>

<h3>Fixed settings, identical in every environment</h3>
<p>Ollama's non-streaming <code>/api/generate</code> endpoint, no conversation history,
<code>temperature 0.2</code>, <code>top_p 0.9</code>, <code>num_predict 192</code>, <code>num_ctx 2048</code>,
<code>seed 42</code>, <code>think=false</code>. Model downloads are excluded from load time.</p>

<h3>What is measured, and how</h3>
<ul>
<li><b>Model load</b> — wall time of one dedicated empty-prompt request, issued after the model has been unloaded.</li>
<li><b>Answer time</b> — client-side wall time of the complete non-streaming request.</li>
<li><b>Generation speed</b> — the server's <code>eval_count ÷ eval_duration</code>; this excludes prompt processing and loading.</li>
<li><b>Memory</b> — <code>/api/ps</code> sampled after each response: resident model allocation and VRAM allocation.
This is an allocation snapshot, <i>not</i> peak RAM.</li>
<li><b>Outcome</b> — the server's <code>done_reason</code>, so truncation at the token limit is visible rather than silent.</li>
</ul>

<h3>What changed after the plan was written, and why</h3>
<ul>
<li><b>Jetstream2 was unavailable</b>, so the third environment is the free Colab T4 only. This is recorded as an omission, not as a result.</li>
<li><b>A fourth environment was added:</b> the same Mac also runs Ollama natively on the Apple GPU, so CPU-only and GPU rows exist for the same machine.</li>
<li><b>Hugging Face model:</b> <code>ollama pull hf.co/...</code> failed, so the GGUF was downloaded directly and imported under the alias <code>qwen2.5-hf:0.5b</code> (section 10).</li>
<li><b>Server-reported load time</b> was dropped: empty-prompt load requests return <code>done_reason=load</code> with no <code>load_duration</code> field, so the measured wall time is used and the server field is left blank rather than recorded as zero.</li>
</ul>

<h2 class="break">2. The three environments and their hardware</h2>
{env_table}
<p>Hardware was captured by the runner itself into <code>hardware.json</code> inside every result folder, using the commands in the
last column, so the hardware record and the timings always belong to the same run.</p>
<div class="note"><b>Fair-comparison caveat.</b> The Docker container is limited to 4 CPUs and 3.83 GiB, while the same Mac natively
sees 12 cores and 16 GiB, and the Docker run used Ollama 0.34.2 against 0.34.3 elsewhere. The CPU-versus-GPU rows therefore
differ by more than the GPU alone.</div>
"""

HTML += f"""
<h2>3. Task 1 — Two hosting tools, one of them graphical</h2>
<ol>
<li><b>Ollama</b> — the model server, used in all three environments (Docker container on the Mac, native macOS build, and a
Linux install on the Colab VM). Driven from the command line and from its HTTP API.</li>
<li><b>Open WebUI</b> — the browser interface at <code>http://localhost:3000</code>, talking to the same Docker Ollama container.
This is the graphical tool.</li>
</ol>
<p>Both run side by side as containers:</p>
<pre>$ docker ps --format '{{{{.Names}}}} {{{{.Status}}}}'
open-webui  Up 56 minutes (healthy)
ollama      Up 56 minutes (healthy)</pre>
<figure><img src="evidence/colab-t4-install-and-runs.jpg">
<figcaption><b>Task 1 / Task 5 — Screenshot 1.</b> Ollama installed and answering on the Colab T4:
<code>{{"version":"0.34.3"}}</code> from the local API, the Hugging Face GGUF hash check printing
<code>matches Mac download: True</code>, and both measurement runs finishing with <code>returncode=0</code>.</figcaption></figure>
<div class="note"><b>Screenshot to add yourself:</b> Open WebUI at <code>localhost:3000</code> with a model selected and an answer on
screen (it sits behind a sign-in, so it is not captured here). The same window is shown live in the video.</div>

<h2>4. Task 2 — Three models, two families, three sizes, one from Hugging Face</h2>
<table><thead><tr><th>Model</th><th>Family</th><th>Marketing size</th><th>Reported parameters</th><th>Quantization</th><th>Disk</th><th>Source</th></tr></thead><tbody>
<tr><td><code>qwen3:1.7b</code></td><td>Qwen</td><td>1.7B</td><td>2.0B</td><td>Q4_K_M</td><td>1.4 GB</td><td>Ollama library</td></tr>
<tr><td><code>llama3.2:1b</code></td><td>Llama</td><td>1B</td><td>1.2B</td><td>Q8_0</td><td>1.3 GB</td><td>Ollama library</td></tr>
<tr><td><code>qwen2.5-hf:0.5b</code></td><td>Qwen</td><td>0.5B</td><td>630.17M</td><td>Q4_K_M</td><td>491 MB</td><td><b>Hugging Face</b>: <code>Qwen/Qwen2.5-0.5B-Instruct-GGUF</code></td></tr>
</tbody></table>
<p>The marketing name and the metadata disagree for every model — <code>qwen3:1.7b</code> reports 2.0B parameters and
<code>llama3.2:1b</code> reports 1.2B — so both labels are kept rather than silently replacing one with the other.</p>
<p><b>Hugging Face provenance.</b> The exact file <code>qwen2.5-0.5b-instruct-q4_k_m.gguf</code> was downloaded from the official
repository and imported through a <code>Modelfile</code> under the alias <code>qwen2.5-hf:0.5b</code>. Its SHA-256 is
<code>74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db</code>, and the Colab notebook recomputes that hash
on the file it downloads itself and prints <code>matches Mac download: True</code> (Screenshot 1) — so the Mac and the T4 ran
byte-identical weights.</p>

<h2>5. Task 3 — Four ways of talking to the models</h2>
<table><thead><tr><th>Method</th><th>What was done</th><th>Evidence</th></tr></thead><tbody>
<tr><td>Command line</td><td><code>ollama list</code>, <code>ollama pull</code>, <code>ollama create</code> on the Mac and in Colab</td><td>Output below; notebook cells 3–4</td></tr>
<tr><td>Python script</td><td><code>run.py</code> — the measurement runner; standard library only</td><td><code>results/*/measurements.csv</code></td></tr>
<tr><td>Direct HTTP API</td><td><code>POST /api/generate</code> (non-streaming), plus <code>/api/show</code>, <code>/api/ps</code>, <code>/api/version</code></td><td>Full request and response bodies in <code>answer-*.json</code></td></tr>
<tr><td>Graphical interface</td><td>Open WebUI chat against the same container</td><td>Live in the video</td></tr>
</tbody></table>
<pre>$ docker exec ollama ollama list
NAME               ID              SIZE      MODIFIED
qwen2.5-hf:0.5b    638b1dcc170e    491 MB    44 minutes ago
llama3.2:1b        baf6a787fdff    1.3 GB    51 minutes ago
qwen3:1.7b         8f68893c685c    1.4 GB    43 hours ago</pre>
<p>The same P2 prompt sent through Open WebUI earlier returned <b>66</b>, while the controlled API call returned the correct
<b>120</b>. The GUI keeps its own sampling settings and its own chat history, so that is a demonstration of a different
interface, <i>not</i> a like-for-like performance comparison.</p>

<h2 class="break">6. Task 4 — Changing the settings</h2>
<p>Same model (<code>qwen3:1.7b</code>), same prompt (P1, the phishing question), same seed. Temperature was moved from 0.1 to 1.2,
and then the second setting, <code>num_predict</code> (the maximum answer length), was cut from 192 tokens to 64.</p>
{settings_table}
<h3>What actually changed in the text</h3>
<ul>
<li><b>Temperature 0.1</b> produced step 2: <i>"Confirm the request – Ask the employee to re-enter their password for verification."</i>
In a phishing scenario that is <b>unsafe advice</b>, and it appeared at the <i>low</i>, supposedly "safe" temperature.</li>
<li><b>Temperature 1.2</b> produced step 5: <i>"Do not enter password – Avoid revealing any credentials to prevent account compromise."</i>
— the opposite, and the better answer.</li>
<li><b>num_predict 64</b> stopped mid-sentence in step 3 with <code>done_reason=length</code>. Nothing warns the reader that the
answer was cut off; only the stop reason reveals it.</li>
</ul>
<div class="note"><b>Does this matter for security work?</b> Yes, in three ways. First, low temperature buys consistency, not
correctness — one sample is not evidence that either setting is safer, and the low-temperature answer here was the dangerous one.
Second, any pipeline that feeds model output into a ticket or a playbook has to check <code>done_reason</code>, otherwise a
truncated instruction looks like a complete one. Third, a model that confidently recommends re-entering a password is a reason to
keep a human between the model and the analyst.</div>

<h2>7. Task 5 — Measurements</h2>
<h3>Summary: one row per model per environment (five prompts each)</h3>
{summary_table}
<h3>Generation speed, and what the GPUs actually bought</h3>
{ratio_table}
<figure><img src="comparison.png">
<figcaption><b>Chart 1.</b> Median generation speed and median answer latency for the same five prompts, same settings, in all three
environments. Generated by <code>analyze.py</code> directly from the measurement CSVs.</figcaption></figure>
<div class="note"><b>Read the load column carefully.</b> On Colab the first real answer for each model took
{colab_first:.0f} s even though the empty-prompt load request had already returned after {colab_load:.0f} s, because the
T4 finishes warming up on the first genuine generation. On the Mac's own GPU the same model loaded in {mac_load:.1f} s and the
first answer was already at full speed. Cold-start cost, not throughput, is where Colab loses.</div>
<h3>Every measurement, per prompt</h3>
{per_prompt}
"""

s_cpu = summary[('local-docker-cpu', 'qwen3:1.7b')]
s_gpu = summary[('local-metal-gpu', 'qwen3:1.7b')]
s_t4 = summary[('colab-t4', 'qwen3:1.7b')]

HTML += f"""
<h2 class="break">8. How good were the answers?</h2>
<p>Speed is only half the comparison; the same five prompts also expose what each model gets wrong.</p>
{qual_table}
<div class="note"><b>The most important result in this table</b> is the P2 row. <code>llama3.2:1b</code> answered 120 correctly on both
local backends and 126 on the Colab T4 with the same prompt, the same temperature, the same top_p and the same seed. Identical
settings do not produce identical text across different hardware and backends, so a model that passes a test on your laptop can
still fail it on a server.</div>

<h2>9. Comparing the environments</h2>
<table><thead><tr><th>Criterion</th><th>Own computer — Docker (CPU)</th><th>Own computer — native (Apple GPU)</th><th>Google Colab — T4</th></tr></thead><tbody>
<tr><td>Ease of setup</td><td>Already installed; one <code>docker compose up</code></td><td>Download and unzip the app, start the server with two environment variables</td><td>No install on your machine, but the documented installer failed and needed debugging (section 10)</td></tr>
<tr><td>Speed (qwen3:1.7b)</td><td>{s_cpu['tps']:.1f} tokens/s, median answer {s_cpu['answer']:.2f} s</td><td>{s_gpu['tps']:.1f} tokens/s ({gpu_gain:.2f}× CPU), median answer {s_gpu['answer']:.2f} s</td><td>{s_t4['tps']:.1f} tokens/s ({t4_gain:.2f}× CPU), median answer {s_t4['answer']:.2f} s</td></tr>
<tr><td>Cold start</td><td>{s_cpu['load']:.1f} s load</td><td>{s_gpu['load']:.1f} s load, first answer already at full speed</td><td>{s_t4['load']:.0f} s load and a {s_t4['first']:.0f} s first answer, on top of ~2 minutes of install and model pulls</td></tr>
<tr><td>Model sizes that ran</td><td>All three (630M – 2.0B) succeeded; largest resident allocation 1649 MiB inside a 3.83 GiB VM</td><td>All three succeeded; 1561 MiB in VRAM out of 16 GB unified</td><td>All three succeeded; 1398 MiB out of 15360 MiB — the T4 had room for a far larger model than anything tested</td></tr>
<tr><td>Sizes that did <i>not</i> run</td><td colspan="3">None were attempted beyond 2.0B. Jetstream2, where the larger model was planned, was unavailable, so "the biggest model that fits" remains untested — an honest gap, not a result.</td></tr>
<tr><td>Cost</td><td colspan="2">Hardware already owned; electricity only</td><td>Free tier; a GPU session is not guaranteed and is capped</td></tr>
<tr><td>Privacy</td><td colspan="2">Prompts never leave the machine; no network needed once the weights are downloaded</td><td>Every prompt and answer is processed on Google's hardware</td></tr>
<tr><td>Reliability</td><td colspan="2">Persistent; models stay installed between sessions</td><td>Session-scoped: the runtime disconnects, and <b>everything in <code>/content</code> is lost</b>. The "too many sessions" limit also blocked a run until an old session was terminated.</td></tr>
</tbody></table>

<h3>Recommendations, each backed by the numbers above</h3>
<ol>
<li><b>Everyday work for a security analyst → the analyst's own machine, running natively on its GPU.</b>
{s_gpu['tps']:.1f} tokens/s against {s_cpu['tps']:.1f} on the CPU-limited container is a {gpu_gain:.2f}× gain for zero extra cost, the model
loads in {s_gpu['load']:.1f} s instead of {s_t4['load']:.0f} s, and it is still there tomorrow morning. The Colab T4 is only
{s_t4['tps']/s_gpu['tps']:.2f}× faster than the Apple GPU at generation — not enough to justify re-installing everything at the start of
each session.</li>
<li><b>Sensitive or confidential data → local only, and preferably the native install.</b> This is not a speed argument: on the two
local backends the prompt never leaves the machine, while on Colab every prompt is processed by a third party. The measured cost
of choosing privacy is small — the local GPU already reaches {s_gpu['tps']/s_t4['tps']*100:.0f}% of the T4's generation speed on the
same model. If policy forbids third-party processing, the T4 is not an option at any speed.</li>
<li><b>A quick experiment that has to be finished today → Colab.</b> It is the fastest environment measured
({s_t4['tps']:.1f} tokens/s, {t4_gain:.2f}× the CPU container) and needs nothing installed locally; total setup was about two minutes
of install and model pulls. Accept the trade: roughly {s_t4['first']:.0f} s before the first useful answer and everything deleted when the
runtime ends, so download the evidence before you close the tab.</li>
</ol>

<h2>10. Problems, and how they were handled</h2>
<table><thead><tr><th>#</th><th>Problem</th><th>Diagnosis</th><th>Fix</th></tr></thead><tbody>
<tr><td>1</td><td>The documented Colab installer, <code>sh install.sh</code>, exited 1</td>
<td>The script downloads <code>ollama-linux-amd64.tgz</code>; that path now returns <b>HTTP 404</b> (curl exit 22). Current
releases ship <code>.tar.zst</code> instead.</td>
<td>Fetch <code>ollama-linux-amd64.tar.zst</code> directly, install <code>zstd</code>, extract into <code>/usr/local</code>, and skip the
installer's systemd and user-account steps that a Colab VM does not need. Ollama then reported
<code>{{"version":"0.34.3"}}</code> (Screenshot 1).</td></tr>
<tr><td>2</td><td><code>ollama pull hf.co/Qwen/...</code> refused: "blocked redirect to a different host"</td>
<td>Ollama would not follow Hugging Face's CDN redirect.</td>
<td>Download the GGUF with <code>curl</code>, record its SHA-256, and import it with a two-line <code>Modelfile</code> as
<code>qwen2.5-hf:0.5b</code>. The same method is used in Colab, and the hashes match.</td></tr>
<tr><td>3</td><td>Colab refused to start the runtime: "Too many sessions"</td>
<td>An earlier notebook still held the single free GPU session.</td>
<td>Terminate the stale session from <b>Manage sessions</b>, then reconnect. Worth knowing before a demo: the free tier gives you one.</td></tr>
<tr><td>4</td><td>Empty-prompt load requests returned no <code>load_duration</code></td>
<td>The server answers <code>done_reason=load</code> without the timing field.</td>
<td>Report the measured wall time and leave the server field blank. An earlier CSV recorded <code>0</code> there, which wrongly
implied an instant load; the field is unavailable, not zero.</td></tr>
<tr><td>5</td><td>First Colab answers looked absurdly slow ({s_t4['first']:.0f} s) while generation speed was high</td>
<td>The empty-prompt load returns before the GPU has finished warming up, so the warm-up lands on the first real prompt.</td>
<td>Keep the raw numbers and report medians alongside the first-answer cost, rather than quietly dropping the outlier.</td></tr>
<tr><td>6</td><td>The first local Qwen baseline overlapped a model download</td>
<td>Background network and disk activity during timing.</td>
<td>Kept as exploratory evidence and flagged; it is the one Docker row not collected on an otherwise quiet machine.</td></tr>
<tr><td>7</td><td>Jetstream2 unavailable</td><td>No class access at the time of the runs.</td>
<td>Omitted, and said so. No cloud-server numbers are invented; the larger-model test that depended on it is reported as untested.</td></tr>
</tbody></table>

<h2>11. Limits of this comparison</h2>
<ul>
<li><b>One run per prompt.</b> These are exploratory measurements, not statistically robust benchmarks; no repeats, no error bars.</li>
<li><b>The CPU/GPU comparison is not clean.</b> The container had 4 CPUs, 3.83 GiB and Ollama 0.34.2; the native Mac had 12 cores,
16 GiB and 0.34.3. The GPU is not the only variable.</li>
<li><b>Memory is an allocation snapshot</b> from <code>/api/ps</code>, not peak RSS or whole-machine usage.</li>
<li><b>Caches were not cleared</b> between runs, so "unloaded" does not mean "read cold from disk".</li>
<li><b>Answer quality was judged by reading the answers</b> against the expectations fixed in the plan, not by a scored rubric.</li>
</ul>

<h2>12. Evidence and how to repeat this</h2>
<p>Everything in this report is reproducible from the files in <code>experiment/</code>:</p>
<pre>PLAN.md                  the data plan, saved before the measured runs
prompts.json             the five fixed prompts (hashed into every run manifest)
run.py                   the measurement runner (standard library only)
analyze.py, report.py    build the tables, the chart and this report from the CSVs
results/&lt;env&gt;-&lt;utc&gt;/     one folder per run:
    hardware.json          hardware command output for that run
    manifest.json          settings, prompt hash, Ollama version
    measurements.csv       one row per prompt
    answer-*.json          the full request and response, including the raw text
    load-*.json            the dedicated load request
NOTES.md                 caveats that must be read with the numbers
evidence/                screenshots and logs</pre>
<pre>$ docker compose up -d                                       # Docker CPU
$ python3 experiment/run.py --environment local-docker-cpu
$ python3 experiment/run.py --environment local-metal-gpu --url http://127.0.0.1:11435   # native GPU
$ python3 experiment/run.py --environment colab-t4           # in the Colab notebook</pre>
<p>Colab notebook: <code>https://colab.research.google.com/drive/1EDD1vaZj1z4kkD-GbKDRF1u2NWps7pkY</code></p>
<figure><img src="evidence/colab-t4-answers.jpg">
<figcaption><b>Task 3 / Task 5 — Screenshot 2.</b> Raw measurements and generated answers read back inside the Colab notebook:
the measurement record for each prompt, the prompt itself, and the model's text — including
<code>qwen2.5-hf:0.5b</code> refusing the fabricated-citation prompt P5 on the T4.</figcaption></figure>
</body></html>
"""

(ROOT / 'REPORT.html').write_text(HTML)
print('wrote', ROOT / 'REPORT.html', len(HTML), 'bytes')
