import json
d=json.load(open('/Users/chengzige/workbuddy-agent-os/agent-local/tools/matrix/recordings/recording_douyin_test_20260623_175216.json'))
s=d['steps'][4]  # 步骤5 (0-index = 4)
print('步骤5的所有click事件:')
for e in s.get('events',[]):
    if e.get('t')=='click':
        print(json.dumps(e, ensure_ascii=False))
print()
print('步骤5页面上所有含"登录/协议/同意"的元素:')
for x in s.get('page',{}).get('interactables',[]):
    txt=x.get('text','')
    if any(w in txt for w in ['登录','协议','同意','获取']):
        print(f'  tag={x["tag"]} text="{txt}" cls={x["cls"]} rect={x.get("rect","")}')
print()
# 步骤6的page信息
s6=d['steps'][5]  # 步骤6
print(f'步骤6: mode={s6["page"].get("page_mode","?")} 事件={len(s6.get("events",[]))}')
print('步骤6页面上所有元素(前20):')
for x in s6.get('page',{}).get('interactables',[])[:20]:
    print(f'  tag={x["tag"]} text="{x.get("text","")[:15]}" cls={x.get("cls","")[:20]}')
