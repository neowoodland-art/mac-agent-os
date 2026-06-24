/**
 * 账号管理视图（已迁移）
 * 使用共享账号选择器 + 独立账号表格渲染
 */

import { apiRequest } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

export async function loadView(container) {
  container.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h2 style="font-size:18px">👤 账号管理</h2>
      <button onclick="window.showCreateAccount()" class="btn btn-primary btn-sm" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">+ 新建账号</button>
    </div>
    <div style="display:flex;gap:4px;margin-bottom:12px">
      <div class="acct-tab active" onclick="window.acctSwitchTab('list',this)" style="padding:6px 12px;cursor:pointer;font-size:12px;border-bottom:2px solid #6366f1;font-weight:600">📋 账号列表</div>
      <div class="acct-tab" onclick="window.acctSwitchTab('identity',this)" style="padding:6px 12px;cursor:pointer;font-size:12px;color:var(--text2)">🔑 身份管理</div>
    </div>
    <div id="acct-tab-list"><div id="matrixAccountsContent"><div class="loading">加载中...</div></div></div>
    <div id="acct-tab-identity" style="display:none"><div id="matrixIdentityContent"><div class="loading">加载中...</div></div></div>`;

  // 加载账号列表数据并渲染
  try {
    let machinesInfo = '';
    try {
      const mr = await apiRequest('/matrix/cross-machines');
      if (mr.total_machines) {
        machinesInfo = '<div style="display:flex;gap:12px;margin-bottom:12px;font-size:12px;color:var(--text2);background:var(--bg2);border-radius:var(--radius);padding:8px 12px;border:1px solid var(--border)">'+
          '<span>🖥️ 机器: <strong>'+mr.total_machines+'</strong></span>'+
          '<span>👤 账号: <strong>'+mr.total_accounts+'</strong></span>'+
          '<span>📡 在线: <strong style="color:var(--green)">'+mr.online_machines+'</strong></span>'+
        '</div>';
      }
    } catch(e) { /* ignore */ }

    const d = await apiRequest('/matrix/accounts');
    const accounts = Array.isArray(d) ? d : (d.accounts || []);
    const el = document.getElementById('matrixAccountsContent');
    if (!el) return;
    if (!accounts.length) { el.innerHTML = machinesInfo+'<div class="error">暂无账号</div>'; return; }

    // 用共享账号选择器渲染
    const listContainer = document.createElement('div');
    el.innerHTML = machinesInfo;
    el.appendChild(listContainer);
    createAccountSelector(listContainer, {
      accounts,
      checkAll: false,
      height: '400px',
      showBlueprint: true,
    });
  } catch(e) {
    const el = document.getElementById('matrixAccountsContent');
    if (el) el.innerHTML = '<span style="color:var(--red)">'+e.message+'</span>';
  }
}
