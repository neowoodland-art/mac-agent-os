import json, sys
d = json.load(sys.stdin)
for ri in d.get('results', []):
    if 'xhs' in ri.get('identity_dir', ''):
        xhs = ri.get('xiaohongshu', {})
        print(f'{ri["identity_dir"]}: nickname={xhs.get("nickname","?")} fans={xhs.get("fans","?")} likes={xhs.get("likes","?")}')
