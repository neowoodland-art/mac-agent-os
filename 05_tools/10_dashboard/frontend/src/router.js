/**
 * AgentOS Dashboard — 路由模块
 * 
 * 职责：
 * - 管理已迁移视图的动态加载
 * - 提供工具函数供已迁移视图使用
 * - 与 index.html 内联代码共存
 */

let _migrated = new Set();

export function registerMigrated(viewName) {
  _migrated.add(viewName);
}

export function isMigrated(viewName) {
  return _migrated.has(viewName);
}

/**
 * 动态加载已迁移视图
 * @param {string} viewName - 视图名称（对应 views/{viewName}.js）
 * @param {HTMLElement} container - 渲染容器
 * @returns {Promise<boolean>} 是否成功
 */
export async function loadMigratedView(viewName, container) {
  if (!container) return false;
  try {
    const mod = await import(`./views/${viewName}.js`);
    if (mod && typeof mod.loadView === 'function') {
      await mod.loadView(container);
      return true;
    }
  } catch (err) {
    console.error(`[router] Failed to load view "${viewName}":`, err.message);
    container.innerHTML = `<div class="error">❌ 加载视图失败: ${err.message}</div>`;
  }
  return false;
}

// ── 工具函数 ──

export function showLoading(el, msg = '⏳ 加载中...') {
  if (el) el.innerHTML = `<div class="loading">${msg}</div>`;
}

export function showError(el, msg) {
  if (el) el.innerHTML = `<div class="error">❌ ${msg}</div>`;
}

const BASE = '/api';
export async function apiRequest(path, options = {}) {
  const url = `${BASE}${path}`;
  const config = {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  };
  if (!config.method || config.method === 'GET' || config.method === 'HEAD') {
    delete config.headers['Content-Type'];
  }
  const r = await fetch(url, config);
  if (!r.ok) {
    const text = await r.text().catch(() => '');
    throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`);
  }
  return r.json();
}

/**
 * 通用执行前确认弹窗
 * @param {string} message - 确认信息
 * @param {string} detail - 详情（可选）
 * @returns {Promise<boolean>} 是否确认
 */
export async function confirmExecute(message, detail = '') {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:99999;display:flex;align-items:center;justify-content:center';
    overlay.innerHTML = `
      <div style="background:var(--bg2);border-radius:12px;padding:20px;max-width:420px;width:90%;box-shadow:0 8px 30px rgba(0,0,0,0.2)">
        <div style="font-size:15px;font-weight:600;margin-bottom:8px">⚠️ 确认执行</div>
        <div style="font-size:12px;color:var(--text2);margin-bottom:4px">${message}</div>
        ${detail ? `<div style="font-size:11px;color:var(--text2);margin-bottom:12px;background:var(--bg3);padding:8px;border-radius:6px;font-family:monospace">${detail}</div>` : '<div style="margin-bottom:12px"></div>'}
        <div style="display:flex;gap:8px;justify-content:flex-end">
          <button id="confirmCancel" style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">取消</button>
          <button id="confirmOk" style="background:#22c55e;color:#000;border:none;border-radius:6px;padding:6px 16px;font-size:12px;font-weight:600;cursor:pointer">✅ 确认执行</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    document.getElementById('confirmOk').onclick = () => { overlay.remove(); resolve(true); };
    document.getElementById('confirmCancel').onclick = () => { overlay.remove(); resolve(false); };
    overlay.onclick = (e) => { if (e.target === overlay) { overlay.remove(); resolve(false); } };
  });
}
