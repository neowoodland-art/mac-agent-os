/**
 * 收藏点赞视图（v2 — 统一调用入口）
 * 使用共享账号选择器 + 一次性提交所有账号
 *
 * 调用规范：
 *   POST /api/ops/run {type:'like', accounts:全部, params:{blueprint}}
 *   → CommandBus CMD_REGISTRY 统一分发
 */

import { apiRequest, confirmExecute } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

let _selector = null;

export async function loadView(container) {
  const uid = container.id || 'like';
  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">❤️ 收藏点赞 <span style="font-size:10px;color:var(--text2);font-weight:400">选择账号 → 执行点赞/收藏</span></div>
        <div id="acctList_${uid}" style="margin-bottom:6px"><div class="loading">⏳ 加载账号列表...</div></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:11px;color:var(--text2)">操作:
            <select id="likeType_${uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="like">❤️ 点赞</option>
              <option value="collect">⭐ 收藏</option>
            </select>
          </label>
          <button onclick="window._runLike_${uid}()" style="background:var(--primary);color:#fff;border:none;padding:4px 14px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 执行选中账号</button>
          <span id="selCount_${uid}" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>
        <div id="result_${uid}" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;

  try {
    const r = await apiRequest('/matrix/accounts');
    const accts = Array.isArray(r) ? r : (r.accounts || []);
    const listEl = document.getElementById(`acctList_${uid}`);
    if (listEl) {
      _selector = createAccountSelector(listEl, {
        accounts: accts,
        checkAll: false,
        height: '200px',
        showBlueprint: false,
        showStatus: false,
        showCollectTime: false,
      });
    }
    document.getElementById(`selCount_${uid}`).textContent = '已选 ' + (_selector?.getCount() || 0) + ' 个';
  } catch(e) { /* ignore */ }

  // 注册全局函数
  window[`_runLike_${uid}`] = async function() {
    const selected = _selector?.getSelected() || [];
    if (!selected.length) { alert('请先选择账号'); return; }
    const el = document.getElementById(`result_${uid}`);
    const likeType = document.getElementById(`likeType_${uid}`)?.value || 'like';
    const detail = `账号: ${selected.map(s=>s.id).join(', ')}`;
    if (!await confirmExecute(`对 ${selected.length} 个账号执行${likeType==='like'?'点赞':'收藏'}？`, detail)) return;

    el.textContent = '🚀 提交 ' + selected.length + ' 个账号...\n';
    try {
      const d = await apiRequest('/ops/run', {
        method: 'POST',
        body: JSON.stringify({
          type: 'like',
          accounts: selected.map(s => s.id),
          params: { rounds: 1 },
        }),
      });
      el.textContent += `✅ 状态: ${d.status}\n`;
      if (d.commands) d.commands.forEach(c => { el.textContent += `  ${c.machine}: ${c.accounts.join(',')} → ${c.status}\n`; });
      if (d.errors) el.textContent += `⚠️ 错误: ${JSON.stringify(d.errors)}\n`;
    } catch(e) { el.textContent += '❌ ' + e.message + '\n'; }
  };
}
