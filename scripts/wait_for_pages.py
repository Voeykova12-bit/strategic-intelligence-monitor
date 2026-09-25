"""Avoid racing the repository's existing branch-based Pages deployment.

Use that deployment when it succeeds. If Pages is configured for Actions only,
or the branch deployment failed, the workflow deploys its verified artifact.
"""
import json,os,subprocess,time
from urllib.request import Request,urlopen

def branch_state(runs,sha):
    matching=[r for r in runs if r.get('head_sha')==sha and r.get('name')=='pages build and deployment']
    if not matching:return 'missing'
    latest=max(matching,key=lambda r:r['id'])
    if latest['status']!='completed':return 'waiting'
    return 'deployed' if latest.get('conclusion')=='success' else 'fallback'

def main():
    repo=os.environ['GITHUB_REPOSITORY'];token=os.environ['GITHUB_TOKEN']
    sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    started=time.monotonic();state='missing'
    while time.monotonic()-started<180:
        request=Request(f'https://api.github.com/repos/{repo}/actions/runs?head_sha={sha}&per_page=30',headers={
          'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'StrategyRadar'})
        with urlopen(request,timeout=15) as response:runs=json.load(response)['workflow_runs']
        state=branch_state(runs,sha)
        if state in ('deployed','fallback'):break
        if state=='missing' and time.monotonic()-started>=60:break
        time.sleep(5)
    if state=='waiting':raise RuntimeError('Pages deployment still running; refusing a competing deployment')
    deployed=state=='deployed'
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as output:output.write(f'deployed={str(deployed).lower()}\n')
    print('Existing Pages deployment succeeded' if deployed else 'No successful branch deployment; using verified artifact')

if __name__=='__main__':main()
