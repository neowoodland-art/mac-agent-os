/**
 * 养号执行视图（已迁移）
 * 使用共享账号选择器 + 独立 API 调用
 */

import { apiRequest, confirmExecute } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

let _selector = null;

export async function loadView(container) {
  const uid = container.id || 'nurture';
  const data = await apiRequest('/v2/accounts');
  const allAccts = Array.isArray(data) ? data : (data.accounts || []);

  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">🌱 养号执行 <span style="font-size:10px;color:var(--text2);font-weight:400">预检 → 窗口定位 → 执行 → 验证</span></div>
        <div id="acctList_${uid}" style="margin-bottom:6px"></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:11px;color:var(--text2)">轮数:
            <select id="ndRounds" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="1">1 测试</option><option value="5">5</option>
              <option value="10" selected>10 默认</option>
              <option value="20">20</option><option value="30">30</option>
            </select>
          </label>
          <label style="font-size:11px;color:var(--text2)">蓝图:
            <select id="ndBlueprint" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="">自动匹配</option>
              <option value="douyin_daily_clean">🎵 纯净养号(无评论·无短信)</option>
              <option value="douyin_daily">🎵 douyin_daily</option>
              <option value="xhs_daily">📕 xhs_daily</option>
              <option value="douyin_active_v1">🎵 douyin_active_v1</option>
              <option value="xhs_active_v1">📕 xhs_active_v1</option>
            </select>
          </label>
          <button onclick="window._nurturePreflight('${uid}')" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔍 预检</button>
          <button onclick="window._nurtureExec('${uid}')" style="background:#22c55e;color:#000;border:none;padding:4px 14px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 执行选中</button>
          <button onclick="window._nurtureAll('${uid}')" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">📋 全部启用</button>
          <span id="selCount_${uid}" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>
        <div id="preflightInfo_${uid}" style="font-size:10px;color:var(--text2);margin-top:2px;font-family:monospace;white-space:pre-wrap"></div>
        <div id="log_${uid}" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:300px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;

  // 渲染账号选择器
  _selector = createAccountSelector(document.getElementById(`acctList_${uid}`), {
    accounts: allAccts,
    checkAll: false,
    height: '350px',
  });

  document.getElementById(`selCount_${uid}`).textContent = '已选 ' + (_selector?.getCount() || 0) + ' 个';

  // 注册全局函数（使按钮可以工作）
  if (!window._nurtureRegistered) {
    window._nurtureRegistered = true;

    window._nurturePreflight = async function(uid) {
      const log = document.getElementById(`log_${uid}`);
      const info = document.getElementById(`preflightInfo_${uid}`);
      if (log) log.textContent = '🔍 预检中...\n';
      if (info) info.textContent = '';
      try {
        const r = await apiRequest('/matrix/nurture/preflight');
        if (info) info.textContent = r.info || JSON.stringify(r, null, 2);
      } catch(e) {
        if (log) log.textContent += '❌ ' + e.message + '\n';
      }
    };

    window._nurtureExec = async function(uid) {
      const selected = _selector?.getSelected() || [];
      if (!selected.length) { alert('请先选择要执行的账号'); return; }
      const log = document.getElementById(`log_${uid}`);
      const rounds = document.getElementById('ndRounds')?.value || '10';
      const blueprint = document.getElementById('ndBlueprint')?.value || '';
      if (!await confirmExecute(`养号执行 ${selected.length} 个账号？`, `轮数: ${rounds}\n蓝图: ${blueprint || '自动匹配'}`)) return;
      if (log) log.textContent = '🚀 提交 ' + selected.length + ' 个账号到执行队列...\n';
      try {
        // 一次性提交所有账号，CommandBus 自动按机器分组和排队
        const d = await apiRequest('/ops/run', {
          method: 'POST',
          body: JSON.stringify({
            type: 'nurture',
            accounts: selected.map(s => s.id),
            params: { blueprint, rounds: parseInt(rounds) },
          }),
        });
        if (log) {
          log.textContent += `✅ 状态: ${d.status}\n`;
          if (d.commands) {
            d.commands.forEach(c => {
              log.textContent += `  ${c.machine}: ${c.accounts.join(',')} → ${c.status}\n`;
            });
          }
          if (d.errors) log.textContent += `⚠️ 错误: ${JSON.stringify(d.errors)}\n`;
          if (d.warnings) log.textContent += `⚠️ 警告: ${JSON.stringify(d.warnings)}\n`;
        }
      } catch(e) {
        if (log) log.textContent += '❌ ' + e.message + '\n';
      }
    };

    window._nurtureAll = async function(uid) {
      _selector?.selectAll(true);
      await window._nurtureExec(uid);
    };
  }
}
