import json
d=json.load(open('/Users/chengzige/workbuddy-agent-os/agent-local/tools/matrix/recordings/recording_douyin_test_20260623_181208.json'))
for i,s in enumerate(d['steps']):
    html=s.get('page_html','')
    if html and len(html)>50:
        print(f'=== 步骤{i+1} HTML ({len(html)}B) ===')
        # 只显示包含"登录/协议/btn_id"的部分
        for line in html.split('\\n'):
            if any(w in line for w in ['登录','协议','douyin_login','btn_id']):
                print(f'  {line[:200]}')
