import json
d = json.load(open('/tmp/accts.json'))
for a in d:
    if 'douyin_test' in a['id'] or '15370103682' in str(a):
        print(f'id={a["id"]} identity_dir={a.get("identity_dir","?")} phone={a.get("phone","?")} platform={a.get("platform","?")}')
