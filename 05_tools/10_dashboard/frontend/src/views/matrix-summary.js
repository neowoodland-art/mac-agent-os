/**
 * 多机总览视图（已迁移）
 */
export async function loadView(container) {
  const uid = 'ms_' + Math.random().toString(36).slice(2, 6);
  container.innerHTML = `
    <div style="padding:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">📊 多机总览</h2>
        <span id="meta_${uid}" style="font-size:12px;color:var(--text2)"></span>
      </div>
      <div id="grid_${uid}" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:14px">
        <div class="loading">加载矩阵状态...</div>
      </div>
    </div>`;

  loadData(uid);
}

async function loadData(uid) {
  const gridEl = document.getElementById(`grid_${uid}`);
  const metaEl = document.getElementById(`meta_${uid}`);
  if (!gridEl) return;

  try {
    const r = await fetch('/api/matrix/cross-machines');
    const d = await r.json();

    // 获取身份目录统计
    let identityCount = 0;
    try {
      const ir = await fetch('/api/matrix/system-info');
      const id = await ir.json();
      identityCount = id.identity_dirs || 0;
    } catch(e) {}

    if (metaEl) metaEl.textContent = `${d.total_machines} 机器 · ${d.total_accounts} 账号 · 🪪 ${identityCount} 身份目录`;

    // 检测重复
    const allIds = {};
    const duplicates = [];
    d.machines.forEach(m => {
      (m.accounts || []).forEach(a => {
        if (allIds[a.id] && allIds[a.id] !== m.hostname) {
          duplicates.push({ id: a.id, m1: allIds[a.id], m2: m.hostname });
        }
        allIds[a.id] = m.hostname;
      });
    });

    gridEl.innerHTML = d.machines.map(m => {
      const accts = m.accounts || [];
      const localAccts = accts.filter(a => a.owner_machine === m.hostname || a.is_local);
      const remoteAccts = accts.filter(a => a.owner_machine !== m.hostname && !a.is_local);
      const loginAccts = accts.filter(a => a._status === 'logged_in');
      const isLocal = m.hostname === 'chengzigedeAir' || m.is_local;

      return `<div style="background:var(--bg2);border-radius:var(--radius);padding:16px;border:1px solid var(--border)">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
          <span style="width:10px;height:10px;border-radius:50%;background:${m.online ? 'var(--green)' : 'var(--red)'};display:inline-block"></span>
          <span style="font-weight:600;font-size:14px">${isLocal ? '🖥️' : '☁️'} ${m.hostname}</span>
          <span style="font-size:11px;color:var(--text2)">${accts.length} 账号 | ${loginAccts.length} 已登录</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;margin-bottom:8px">
          <div><span style="color:var(--text2)">本机声明:</span> ${localAccts.length}</div>
          <div><span style="color:var(--text2)">远程读取:</span> ${remoteAccts.length}</div>
          <div><span style="color:var(--text2)">登录:</span> <span style="color:var(--green)">${loginAccts.length}</span></div>
          <div><span style="color:var(--text2)">蓝图:</span> ${m.blueprint_count || 0}</div>
        </div>
        ${accts.length ? `<div style="font-size:10px;color:var(--text2);max-height:120px;overflow-y:auto">
          ${accts.slice(0, 20).map(a =>
            `<div style="display:flex;gap:6px;padding:1px 0">
              <span>${a.platform === 'douyin' ? '🎵' : '📕'}</span>
              <span>${a.id}</span>
              <span style="color:${a._status === 'logged_in' ? 'var(--green)' : 'var(--text2)'}">${a._status || '-'}</span>
            </div>`
          ).join('')}
          ${accts.length > 20 ? `<div style="color:var(--text2);margin-top:2px">... 还有 ${accts.length - 20} 个</div>` : ''}
        </div>` : '<div style="font-size:11px;color:var(--text2)">暂无账号</div>'}
        ${duplicates.filter(dp => dp.m1 === m.hostname || dp.m2 === m.hostname).map(dp =>
          `<div style="margin-top:6px;padding:3px 6px;background:rgba(245,158,11,.1);border-radius:4px;font-size:10px;color:var(--amber)">⚠ 重复: ${dp.id} (${dp.m1} / ${dp.m2})</div>`
        ).join('')}
      </div>`;
    }).join('');
  } catch(e) {
    gridEl.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}
