import json
from pathlib import Path

root = Path(__file__).resolve().parent
cells = []
def md(s):
    cells.append({'cell_type':'markdown','metadata':{},'source':s.splitlines(True)})
def code(s):
    cells.append({'cell_type':'code','metadata':{},'source':s.splitlines(True),'outputs':[],'execution_count':None})
md('# LLM Hosting Experiment — Colab\nSelect Runtime → Change runtime type → T4 GPU (free). Run cells in order. The same saved prompts and runner are used on the Mac and in Colab. Download results before disconnecting. All input is fictional. These runs are assistant-assisted; inspect the code and repeat a live example for your video.')
md((root/'PLAN.md').read_text())
code("import pathlib, json\nroot = pathlib.Path('/content/llm-experiment')\nroot.mkdir(exist_ok=True)\n" +
     '\n'.join(f"(root/{name!r}).write_text({(root/name).read_text()!r})" for name in ['run.py','prompts.json','PLAN.md']))
code("""import subprocess, urllib.request, time, os, hashlib
subprocess.run(['nvidia-smi'], check=True)
# install.sh exited 1 on Colab: it fetches ollama-linux-amd64.tgz, and that path now
# returns 404. Current releases ship .tar.zst, so fetch and extract that directly and
# skip the installer's systemd and user-account steps, which a Colab VM does not need.
subprocess.run('apt-get -qq install -y zstd', shell=True, check=True)
subprocess.run('curl -fsSL https://ollama.com/download/ollama-linux-amd64.tar.zst -o /content/ollama.tar.zst', shell=True, check=True)
subprocess.run('tar --zstd -xf /content/ollama.tar.zst -C /usr/local', shell=True, check=True)
OLLAMA = '/usr/local/bin/ollama'
log = open('/content/ollama.log', 'w')
server = subprocess.Popen([OLLAMA, 'serve'], stdout=log, stderr=log,
                          env={**os.environ, 'OLLAMA_HOST': '127.0.0.1:11434'})
for attempt in range(60):
    try:
        print(urllib.request.urlopen('http://127.0.0.1:11434/api/version').read().decode())
        break
    except Exception:
        time.sleep(1)
else:
    print(open('/content/ollama.log').read())
    raise RuntimeError('Ollama failed to start; inspect /content/ollama.log')""")
code("""for model in ['qwen3:1.7b', 'llama3.2:1b']:
    subprocess.run([OLLAMA, 'pull', model], check=True)

# Same Hugging Face artifact and same local alias as the Mac runs, imported the same way:
# ollama's hf.co pull rejected the CDN redirect locally, so the file is fetched directly.
GGUF = '/content/qwen2.5-0.5b-instruct-q4_k_m.gguf'
subprocess.run('curl -fL https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/'
               'qwen2.5-0.5b-instruct-q4_k_m.gguf -o ' + GGUF, shell=True, check=True)
digest = hashlib.sha256(open(GGUF, 'rb').read()).hexdigest()
print(digest, 'matches Mac download:',
      digest == '74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db')
(root / 'Modelfile').write_text('FROM ' + GGUF + chr(10))
subprocess.run([OLLAMA, 'create', 'qwen2.5-hf:0.5b', '-f', str(root / 'Modelfile')], check=True)
models = ['qwen3:1.7b', 'llama3.2:1b', 'qwen2.5-hf:0.5b']""")
code("subprocess.run(['python',str(root/'run.py'),'--environment','colab-t4','--models',*models], check=True)")
code("subprocess.run(['python',str(root/'run.py'),'--environment','colab-t4','--models','qwen3:1.7b','--settings'], check=True)")
code("# Read actual answers and measurements in this notebook.\nfor path in sorted((root/'results').glob('*/answer-*.json')):\n    record=json.loads(path.read_text())\n    print(record['measurement'])\n    print(record['request']['prompt'])\n    print(record['response']['response'], '\\n')")
code("import shutil\nfrom google.colab import files\nshutil.make_archive('/content/colab-evidence','zip',root)\nfiles.download('/content/colab-evidence.zip')")
md('After saving evidence and recording your live example, choose Runtime → Disconnect and delete runtime to release resources.')
nb = {'nbformat':4,'nbformat_minor':5,'metadata':{'colab':{'name':'LLM_Hosting_Experiment.ipynb'},'kernelspec':{'display_name':'Python 3','name':'python3'},'accelerator':'GPU'},'cells':cells}
(root/'LLM_Hosting_Experiment.ipynb').write_text(json.dumps(nb,indent=2))
