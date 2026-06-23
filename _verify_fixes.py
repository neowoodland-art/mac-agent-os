import py_compile
cwd = '/Users/chengzige/workbuddy-agent-os/agent-sync'
files = [
    '05_tools/07_matrix/scripts/mc/engine.py',
    '05_tools/07_matrix/scripts/douyin_ops.py',
    '05_tools/10_dashboard/services/command_bus.py',
    '05_tools/10_dashboard/routes/matrix.py',
]
for f in files:
    py_compile.compile(cwd + '/' + f, doraise=True)
    print('OK:', f)
print('全部通过')
