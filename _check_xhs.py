import json
d = json.load(open('/tmp/hp3.json'))
for ri in d.get('results', []):
    xhs = ri.get('xiaohongshu') or {}
    if xhs.get('nickname'):
        print(f'{ri.get("identity_dir","?"):20s} xhs_nickname={xhs.get("nickname","")} fans={xhs.get("fans","")} likes={xhs.get("likes","")}')
