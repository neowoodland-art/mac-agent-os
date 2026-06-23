import json
d=json.load(open('/Users/chengzige/workbuddy-agent-os/agent-local/tools/matrix/recordings/recording_douyin_test_20260623_174522.json'))
steps=d['steps']
print(f'共{len(steps)}步 耗时{d["meta"]["duration"]}s')
for i,s in enumerate(steps):
    print(f'\n=== 步骤{i+1} ({len(s.get("events",[]))}事件) mode={s["page"].get("page_mode","?")} ===')
    for e in s.get('events',[]):
        t=e.get('t','')
        if t=='click':
            print(f'  click: ({e.get("x")},{e.get("y")}) tag={e.get("tag")} cls="{e.get("cls","")[:40]}" e2e="{e.get("e2e","")}" text="{e.get("text","")[:20]}" rect={e.get("rect","")} ancestor={e.get("ancestorTag","")}.{e.get("ancestorCls","")[:20]}" parentTag={e.get("parentTag","")} parentCls="{e.get("parentCls","")[:20]}"')
        elif t=='key':
            k=e.get('k','')
            if k not in ('`','F4','Escape'):
                print(f'  key: "{k}"')
