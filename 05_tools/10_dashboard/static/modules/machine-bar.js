// ── Machine Status Bar ──
// 全局机器状态条 — 所有视图顶部显示三台机器在线/离线/忙碌

let _machineStatusTimer = null;
const MACHINE_NAMES = {
  'chengzigedeAir': { label: '本机', icon: '🖥️' },
  '5kechengdeAir': { label: '5kecheng', icon: '🖥️' },
  '7kecheng': { label: '7kecheng', icon: '🖥️' },
};

async function loadMachineBar() {
  const bar = document.getElementById('machineBar');
  if (!bar) return;
  try {
    const rh = await fetch('/api/federation/health');
    const health = await rh.json();
    const rm = await fetch('/api/machines');
    const machines = await rm.json();
    const machineList = machines.machines || [];

    // 构建状态卡
    let html = '<div class="machines-bar">';
    for (const [name, info] of Object.entries(MACHINE_NAMES)) {
      const h = health[name] || {};
      const isOnline = h.status === 'ok';
      const mData = machineList.find(m => m.hostname === name || m.hostname === h.hostname);

      // 状态颜色
      let statusClass = 'offline';
      let statusText = '离线';
      if (isOnline) {
        statusClass = 'online';
        statusText = '在线';
        // 如果有 guardd 数据且正在运行任务
        if (mData && mData.current_task) {
          statusClass = 'busy';
          statusText = '忙碌: ' + (mData.current_task || '');
        }
      }

      html += '<div class="machine-status-card ' + statusClass + '">' +
        '<span class="status-dot"></span>' +
        '<span class="machine-name">' + name + '</span>' +
        '<span class="machine-label">' + info.label + '</span>' +
        '<span class="machine-status">' + statusText + '</span>' +
        '</div>';
    }
    html += '</div>';
    bar.innerHTML = html;
  } catch(e) {
    bar.innerHTML = '<div class="machines-bar"><span style="font-size:11px;color:var(--text2)">⏳ 加载状态中...</span></div>';
  }
}

// 初始化 — 每30秒更新
function initMachineBar() {
  if (_machineStatusTimer) clearInterval(_machineStatusTimer);
  loadMachineBar();
  _machineStatusTimer = setInterval(loadMachineBar, 30000);
}
