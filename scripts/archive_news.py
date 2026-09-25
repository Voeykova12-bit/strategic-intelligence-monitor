"""Preserve every existing ID before collectors apply their rolling window."""
import json
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]

def main():
    path=ROOT/'data/archive.json'
    old=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'items':[]}
    items={x['id']:x for x in old['items']}
    for name in ['news','social']:
        source=ROOT/'data'/f'{name}.json'
        if source.exists():
            for x in json.loads(source.read_text(encoding='utf-8')).get('items',[]):items[x['id']]=x
    payload={'updated_at':datetime.now(timezone.utc).isoformat(),'items':list(items.values())}
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Preserved',len(items),'archive records')

if __name__=='__main__':main()
