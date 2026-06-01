#!/usr/bin/env python3
"""Fix douyin_05 phone"""
import yaml
from pathlib import Path

AGENT_SYNC = Path.home() / 'workbuddy-agent-os/agent-sync'
AGENT_LOCAL = Path.home() / 'workbuddy-agent-os/agent-local'

# Registry
reg_path = AGENT_SYNC / '05_tools/07_matrix/accounts_registry.yaml'
txt = reg_path.read_text()
txt = txt.replace('133****4284', '185****9224')
reg_path.write_text(txt)
print('Registry: 133****4284 -> 185****9224')

# Override  
ovr_path = AGENT_LOCAL / 'tools/matrix/config/accounts.override.yaml'
txt = ovr_path.read_text()
txt = txt.replace('13382504284', '18550099224')
ovr_path.write_text(txt)
print('Override: 13382504284 -> 18550099224')
