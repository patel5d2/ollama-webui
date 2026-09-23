#!/usr/bin/env python3
"""Standard-library Ollama experiment runner; retain raw evidence, never invent results."""
import argparse
import csv
import datetime as dt
import hashlib
import json
import pathlib
import platform
import subprocess
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent

def command(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=30)
        # Avoid machine identifiers in evidence.
        return '\n'.join(x for x in (p.stdout + p.stderr).splitlines()
                         if not any(s in x for s in ('Serial Number', 'Hardware UUID', 'Provisioning UDID')))
    except Exception as e:
        return str(e)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--environment', required=True)
    ap.add_argument('--url', default='http://127.0.0.1:11434')
    ap.add_argument('--models', nargs='+', default=['qwen3:1.7b','llama3.2:1b','qwen2.5-hf:0.5b'])
    ap.add_argument('--settings', action='store_true')
    args = ap.parse_args()
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = ROOT / 'results' / f'{args.environment}-{stamp}'
    out.mkdir(parents=True)
    def save(name, obj):
        (out / name).write_text(json.dumps(obj, indent=2) + '\n')
    def api(path, body=None):
        req = urllib.request.Request(args.url + '/api/' + path,
              data=None if body is None else json.dumps(body).encode(),
              headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req, timeout=1200) as r:
            return json.load(r)
    hw = {'platform':platform.platform(), 'machine':platform.machine()}
    cmds = ([['system_profiler','SPHardwareDataType','SPDisplaysDataType'],
             ['sysctl','hw.memsize','hw.ncpu'],
             ['docker','info','--format','CPUs={{.NCPU}} Memory={{.MemTotal}}']]
            if platform.system() == 'Darwin' else
            [['lscpu'],['free','-b'],['nvidia-smi']])
    for c in cmds:
        hw[' '.join(c)] = command(c)
    save('hardware.json', hw)
    prompts = json.loads((ROOT/'prompts.json').read_text())
    save('manifest.json', {'started_utc':stamp,'environment':args.environment,
         'models':args.models,'settings':args.settings,
         'prompts_sha256':hashlib.sha256((ROOT/'prompts.json').read_bytes()).hexdigest(),
         'ollama_version':api('version'),'prompts':prompts})
    fields = ['environment','model','parameter_size','quantization','prompt_id','condition',
              'load_wall_s','load_server_s','answer_wall_s','server_total_s','generation_s',
              'output_tokens','tokens_per_second','model_allocation_bytes','gpu_allocation_bytes',
              'temperature','top_p','num_predict','done_reason']
    with (out/'measurements.csv').open('w',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=fields); writer.writeheader(); f.flush()
        for mi, model in enumerate(args.models):
            try:
                meta = api('show',{'model':model}); save(f'model-{mi}.json',meta)
                for loaded in api('ps').get('models',[]):
                    api('generate',{'model':loaded['name'],'keep_alive':0})
                deadline = time.monotonic()+60
                while api('ps').get('models'):
                    if time.monotonic()>deadline:
                        raise RuntimeError('Model did not unload within 60 seconds')
                    time.sleep(.25)
                start = time.perf_counter()
                load = api('generate',{'model':model,'prompt':'','stream':False,'keep_alive':'10m',
                                      'options':{'num_ctx':2048}})
                load_wall = time.perf_counter()-start
                save(f'load-{mi}.json',{'wall_s':load_wall,'response':load})
                trials = [(p,'baseline',.2,192) for p in prompts]
                if args.settings:
                    trials = [(prompts[0],label,temp,limit) for label,temp,limit in
                              [('temp-low',.1,192),('temp-high',1.2,192),('tokens-64',.1,64)]]
                for pi,(p,label,temp,limit) in enumerate(trials):
                    body = {'model':model,'prompt':p['prompt'],'stream':False,'think':False,
                            'keep_alive':'10m','options':{'temperature':temp,'top_p':.9,
                            'num_predict':limit,'num_ctx':2048,'seed':42}}
                    start = time.perf_counter(); result = api('generate',body)
                    wall = time.perf_counter()-start
                    resident = api('ps')
                    alloc = next((m for m in resident.get('models',[])
                                  if m.get('name')==model or m.get('model')==model), {})
                    gen = result.get('eval_duration',0)/1e9
                    row = dict(environment=args.environment,model=model,
                        parameter_size=meta.get('details',{}).get('parameter_size',''),
                        quantization=meta.get('details',{}).get('quantization_level',''),
                        prompt_id=p['id'],condition=label,load_wall_s=load_wall,
                        load_server_s=load['load_duration']/1e9 if 'load_duration' in load else '',
                        answer_wall_s=wall,server_total_s=result.get('total_duration',0)/1e9,
                        generation_s=gen,output_tokens=result.get('eval_count',0),
                        tokens_per_second=result.get('eval_count',0)/gen if gen else '',
                        model_allocation_bytes=alloc.get('size',''),gpu_allocation_bytes=alloc.get('size_vram',''),
                        temperature=temp,top_p=.9,num_predict=limit,done_reason=result.get('done_reason',''))
                    save(f'answer-{mi}-{pi}.json',{'request':body,'response':result,'measurement':row,'resident':resident})
                    writer.writerow(row); f.flush()
                    print(f"{model} {p['id']} {label}: {wall:.2f}s, {row['tokens_per_second']:.2f} tokens/s",flush=True)
                api('generate',{'model':model,'keep_alive':0})
            except Exception as e:
                save(f'error-{mi}.json',{'model':model,'error':str(e)})
                print(f'{model}: ERROR {e}',flush=True)
    print(f'Evidence saved: {out}',flush=True)

if __name__ == '__main__':
    main()
