/**
 * 账号管理视图（v2 精简版 — 直接 fetch，不依赖组件）
 * 显示统一表格：机器 | 身份 | 账号ID | 平台 | 昵称 | 粉丝 | 关注 | 获赞 | 作品 | 状态
 */
export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
  try {
    const BASE = '/api';
    const [ar, hr] = await Promise.all([
      fetch(BASE + '/matrix/accounts').then(r => r.ok ? r.json() : { accounts: [] }).catch(() => ({ accounts: [] })),
      fetch(BASE + '/matrix/homepage-info').then(r => r.ok ? r.json() : { results: [] }).catch(() => ({ results: [] })),
    ]);
    const accounts = Array.isArray(ar) ? ar : (ar.accounts || []);
    const results = (hr.results || []);

    // 构建 hpIndex
    const hpIndex = {};
    results.forEach(r => {
      if (r.identity_dir) hpIndex[r.identity_dir] = r;
      if (r.phone) hpIndex[r.phone] = r;
    });

    // 机器排序
    const machineOrder = ['chengzigedeAir', '5kechengdeAir', '7kecheng'];
    const groups = {};
    accounts.forEach(a => {
      const m = a.owner_machine || 'unknown';
      if (!groups[m]) groups[m] = [];
      const hp = hpIndex[a.identity_dir] || hpIndex[a.phone];
      const hpAcc = hp ? (a.platform === 'douyin' ? hp.douyin : hp.xiaohongshu) : null;
      groups[m].push({
        id: a.id, platform: a.platform, phone: a.phone || '',
        identity_dir: (a.identity_dir || '').replace('identities/', ''),
        nickname: hpAcc?.nickname || a.nickname || '',
        fans: hpAcc?.fans || a.fans || '',
        following: hpAcc?.following || a.following || '',
        likes: hpAcc?.likes || a.likes || '',
        posts: hpAcc?.posts || a.posts || '',
        status: a._status || 'unknown',
        collected_at: hpAcc?.collected_at || '',
      });
    });

    let html = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px">👤 账号管理</h2>
        <div style="display:flex;gap:6px">
          <button onclick="window.showCreateAccount()" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">+ 新建账号</button>
          <button onclick="try{window.switchView('matrix-sms-proxy')}catch(e){}" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">📡 短信与代理</button>
        </div>
      </div>
      <div style="overflow-x:auto">
      <table style="width:100%;font-size:11px;border-collapse:collapse">
        <tr style="font-size:9px;color:var(--text2);border-bottom:1px solid var(--border)">
          <th style="padding:4px 6px;font-weight:400;text-align:left">机器</th>
          <th style="padding:4px 6px;font-weight:400;text-align:left">身份</th>
          <th style="padding:4px 6px;font-weight:400;text-align:left">账号ID</th>
          <th style="padding:4px 6px;font-weight:400;text-align:left">平台</th>
          <th style="padding:4px 6px;font-weight:400;text-align:left">昵称</th>
          <th style="padding:4px 6px;font-weight:400;text-align:right">👥</th>
          <th style="padding:4px 6px;font-weight:400;text-align:right">👍</th>
          <th style="padding:4px 6px;font-weight:400;text-align:right">❤️</th>
          <th style="padding:4px 6px;font-weight:400;text-align:right">📝</th>
          <th style="padding:4px 6px;font-weight:400;text-align:left">状态</th>
        </tr>`;

    machineOrder.filter(m => groups[m]).forEach(m => {
      groups[m].forEach(a => {
        const platIcon = a.platform === 'douyin' ? '🎵' : '📕';
        const statusIcons = {
          'logged_in': '🟢 已登录', 'remote': '🔵 远程', 'expired': '🟡 过期',
          'no_cookie': '🔴 无Cookie', 'disabled': '⚪ 禁用',
        };
        const statusIcon = statusIcons[a.status] || a.status;
        html += `<tr style="border-bottom:1px solid var(--border)">
          <td style="padding:3px 6px">${m === 'chengzigedeAir' ? '🖥️' : '☁️'}${m}</td>
          <td style="padding:3px 6px;font-size:10px;color:var(--text2)">📁${a.identity_dir}</td>
          <td style="padding:3px 6px"><strong>${a.id}</strong></td>
          <td style="padding:3px 6px">${platIcon}</td>
          <td style="padding:3px 6px">${a.nickname || '-'}</td>
          <td style="padding:3px 6px;text-align:right">${a.fans || '-'}</td>
          <td style="padding:3px 6px;text-align:right">${a.following || '-'}</td>
          <td style="padding:3px 6px;text-align:right">${a.likes || '-'}</td>
          <td style="padding:3px 6px;text-align:right">${a.posts || '-'}</td>
          <td style="padding:3px 6px;font-size:10px">${statusIcon}</td>
        </tr>`;
      });
    });

    html += '</table></div>';
    html += `<div style="padding:4px 6px;font-size:10px;color:var(--text2);margin-top:6px">共 ${accounts.length} 个账号 | 🎵 ${accounts.filter(a => a.platform === 'douyin').length} | 📕 ${accounts.filter(a => a.platform === 'xiaohongshu').length}</div>`;
    container.innerHTML = html;

  } catch (e) {
    container.innerHTML = `<div class="error">❌ ${e.message || e}</div>`;
  }
}
