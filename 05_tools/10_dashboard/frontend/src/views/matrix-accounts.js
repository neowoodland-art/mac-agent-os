/**
 * 账号管理视图（v2 — 合并主页信息）
 * 统一表格：机器 | 身份 | 账号ID | 平台 | 昵称 | 粉丝 | 关注 | 获赞 | 作品 | 采集时间 | 状态
 * 顶部操作：新建账号 + 短信与代理
 */

import { apiRequest } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

export async function loadView(container) {
  container.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h2 style="font-size:18px">👤 账号管理</h2>
      <div style="display:flex;gap:6px">
        <button onclick="window.showCreateAccount()" class="btn btn-primary btn-sm" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">+ 新建账号</button>
        <button onclick="window._goSmsProxy()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">📡 短信与代理</button>
      </div>
    </div>
    <div id="matrixAccountsContent"><div class="loading">⏳ 加载账号数据...</div></div>`;

  // 注册快捷方式
  window._goSmsProxy = () => { try { window.switchView('matrix-sms-proxy'); } catch(e) { /* ignore */ } };

  try {
    // 并行拉取账号数据 + 采集数据
    const [ar, hr] = await Promise.all([
      apiRequest('/matrix/accounts'),
      apiRequest('/matrix/homepage-info').catch(() => ({ results: [] })),
    ]);

    const accounts = Array.isArray(ar) ? ar : (ar.accounts || []);
    const el = document.getElementById('matrixAccountsContent');
    if (!el) return;

    if (!accounts.length) {
      el.innerHTML = '<div class="error">暂无账号</div>';
      return;
    }

    // 构建 hpIndex（按 identity_dir + phone 索引）
    const hpIndex = {};
    (hr.results || []).forEach(r => {
      if (r.identity_dir) hpIndex[r.identity_dir] = r;
      if (r.phone) hpIndex[r.phone] = r;
    });

    // 用共享账号选择器渲染统一表格
    const listContainer = document.createElement('div');
    el.innerHTML = '';
    el.appendChild(listContainer);
    createAccountSelector(listContainer, {
      accounts,
      hpIndex,
      checkAll: false,
      height: '500px',
      showBlueprint: true,
    });
  } catch (e) {
    const el = document.getElementById('matrixAccountsContent');
    if (el) el.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}
