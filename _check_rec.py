import json
base='/Users/chengzige/workbuddy-agent-os/agent-local/tools/matrix/recordings'
for name in ['recording_douyin_test_20260623_172258.json','recording_douyin_test_20260623_172608.json']:
    d=json.load(open(base+'/'+name))
    steps=d['steps']
    all_btns=set()
    for si in steps:
        for x in si.get('page',{}).get('interactables',[]):
            if x.get('tag') in ('button','a'):
                txt=x.get('text','').strip()
                cls=x.get('cls','').strip()
                e2e=x.get('e2e','')
                if txt or cls:
                    all_btns.add(f'tag={x["tag"]} text="{txt[:15]}" cls="{cls[:20]}" e2e="{e2e}"')
    print(f'\n=== {name} ===')
    for b in sorted(all_btns):
        print(f'  {b}')
