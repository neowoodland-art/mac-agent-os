/**
 * 远程控制视图 — C2 机器列表与命令下发
 */
export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
  try {
    const uid = Date.now().toString(36);
    const res = await fetch('/api/c2/machines');
    const data = res.ok ? await res.json() : { machines: [] };
    const machines = Array.isArray(data) ? data : (data.machines || []);

    container.innerHTML = `
      <div style="padding:16px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
          <h2 style="font-size:18px;margin:0">🖥️ 远程控制</h2>
          <span style="font-size:12px;color:var(--text2)">
            <strong>${machines.length}</strong> 台机器
            <span style="margin-left:8px;font-size:11px">🟢在线 <strong id="onlineCount_${uid}">0</strong></span>
            <span style="margin-left:4px;font-size:11px">🔴离线 <strong id="offlineCount_${uid}">0</strong></span>
          </span>
        </div>
        <div id="machineGrid_${uid}" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:10px"></div>
      </div>`;

    const gridEl = document.getElementById('machineGrid_' + uid);
    if (!gridEl) { container.innerHTML = '<div class="error">❌ 渲染错误: 容器丢失</div>'; return; }

    function renderMachines(list) {
      const online = list.filter(m => m.online !== false);
      const onlineEl = document.getElementById('onlineCount_' + uid);
      const offlineEl = document.getElementById('offlineCount_' + uid);
      if (onlineEl) onlineEl.textContent = online.length;
      if (offlineEl) offlineEl.textContent = list.length - online.length;

      if (!list.length) {
        gridEl.innerHTML = '<div style="font-size:12px;color:var(--text2);padding:40px;text-align:center">暂无机器数据</div>';
        return;
      }

      gridEl.innerHTML = list.map(m => {
        const isOnline = m.online !== false;
        return `<div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div style="display:flex;align-items:center;gap:6px">
              <span style="width:8px;height:8px;border-radius:50%;background:${isOnline ? 'var(--green, #22c55e)' : 'var(--red, #ef4444)'};display:inline-block"></span>
              <span style="font-weight:600;font-size:13px">${m.hostname || m.name || m.id}</span>
            </div>
            <span style="font-size:10px;color:var(--text2)">${m.ip || m.address || ''}</span>
          </div>
          <div style="font-size:11px;color:var(--text2);margin-bottom:8px">
            ${m.os ? `<span style="margin-right:8px">${m.os}</span>` : ''}
            ${m.platform ? `<span>${m.platform}</span>` : ''}
            ${m.version ? `<span style="margin-left:8px">v${m.version}</span>` : ''}
          </div>
          <div style="display:flex;gap:4px;flex-wrap:wrap">
            <button onclick="window._sendC2('${m.id || m.hostname || m.name}','shell','')" style="background:var(--bg3);border:1px solid var(--border);border-radius:4px;padding:3px 10px;font-size:10px;cursor:pointer">💻 Shell</button>
            <button onclick="window._sendC2('${m.id || m.hostname || m.name}','exec','')" style="background:var(--bg3);border:1px solid var(--border);border-radius:4px;padding:3px 10px;font-size:10px;cursor:pointer">⚡ 执行</button>
            <button onclick="window._sendC2('${m.id || m.hostname || m.name}','file','')" style="background:var(--bg3);border:1px solid var(--border);border-radius:4px;padding:3px 10px;font-size:10px;cursor:pointer">📁 文件</button>
            <button onclick="window._sendC2('${m.id || m.hostname || m.name}','ping','')" style="background:var(--bg3);border:1px solid var(--border);border-radius:4px;padding:3px 10px;font-size:10px;cursor:pointer">🏓 Ping</button>
            <button onclick="window._showCustomC2('${m.id || m.hostname || m.name}')" style="background:var(--primary);color:#fff;border:none;border-radius:4px;padding:3px 10px;font-size:10px;cursor:pointer">✏️ 自定义</button>
          </div>
          <div id="c2Result_${(m.id || m.hostname || m.name).replace(/[^a-zA-Z0-9]/g, '_')}" style="margin-top:6px;font-size:10px;color:var(--text2);min-height:0"></div>
        </div>`;
      }).join('');
    }

    renderMachines(machines);

    // 通用 C2 发送函数
    window._sendC2 = async (target, type, params) => {
      const resultId = 'c2Result_' + target.replace(/[^a-zA-Z0-9]/g, '_');
      const el = document.getElementById(resultId);
      if (el) el.innerHTML = '<span style="color:var(--amber)">⏳ 发送中...</span>';
      try {
        const r = await fetch('/api/c2/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target, type, params }),
        });
        const d = await r.json();
        if (el) {
          const output = d.output || d.result || d.message || JSON.stringify(d);
          el.innerHTML = `<span style="color:${r.ok ? 'var(--green)' : 'var(--red)'}">${r.ok ? '✅' : '❌'} ${output}</span>`;
        }
      } catch (e) {
        if (el) el.innerHTML = `<span style="color:var(--red)">❌ ${e.message}</span>`;
      }
    };

    // 自定义命令弹窗
    window._showCustomC2 = (target) => {
      const overlay = document.createElement('div');
      overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:99999;display:flex;align-items:center;justify-content:center';
      overlay.innerHTML = `
        <div style="background:var(--bg2);border-radius:12px;padding:20px;max-width:400px;width:90%">
          <div style="font-size:15px;font-weight:600;margin-bottom:12px">✏️ 发送命令 → ${target}</div>
          <div style="display:grid;gap:8px;font-size:12px">
            <label>类型
              <select id="customC2Type" style="width:100%;padding:4px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px">
                <option value="shell">💻 Shell</option>
                <option value="exec">⚡ 执行</option>
                <option value="file">📁 文件</option>
                <option value="ping">🏓 Ping</option>
                <option value="custom">🔧 自定义</option>
              </select>
            </label>
            <label>参数
              <textarea id="customC2Params" rows="4" placeholder='JSON 格式或文本参数' style="width:100%;padding:4px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:11px;resize:vertical"></textarea>
            </label>
          </div>
          <div style="display:flex;gap:6px;justify-content:flex-end;margin-top:12px">
            <button onclick="this.closest('div[style]').parentElement.remove()" style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">取消</button>
            <button onclick="window._doCustomC2('${target}')" style="background:var(--primary);color:#fff;border:none;border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">🚀 发送</button>
          </div>
        </div>`;
      document.body.appendChild(overlay);
    };

    window._doCustomC2 = (target) => {
      const type = document.getElementById('customC2Type')?.value || 'shell';
      const paramsRaw = document.getElementById('customC2Params')?.value || '';
      let params = paramsRaw;
      // 尝试解析 JSON
      try { params = JSON.parse(paramsRaw); } catch {}
      window._sendC2(target, type, params);
      document.querySelector('div[style*="position:fixed"]')?.remove();
    };

  } catch (e) {
    container.innerHTML = `<div class="error">❌ ${e.message || e}</div>`;
  }
}
