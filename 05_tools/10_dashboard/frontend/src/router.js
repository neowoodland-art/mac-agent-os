/**
 * AgentOS Dashboard — 路由模块
 * 
 * 职责：
 * - 管理已迁移视图的动态加载
 * - 提供工具函数供已迁移视图使用
 * - 与 index.html 内联代码共存（暴露到 window 供电线函数调用）
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

// ── 全局接口（供 inline.js 调用）─────────────────────────

/**
 * 尝试加载已迁移视图。供电线函数 switchView() 使用。
 * 内部检查视图是否已注册，已注册则加载到 #view-dynamic。
 * 
 * @param {string} viewName
 * @returns {boolean} 是否找到并开始加载
 */
export function tryLoadView(viewName) {
  if (!_migrated.has(viewName)) return false;

  const container = document.getElementById('view-dynamic');
  if (!container) return false;

  // 隐藏所有旧视图（class + inline style 双重保障，防内联 display 覆盖）
  document.querySelectorAll('[id^="view-"]').forEach(el => { el.classList.add('hidden'); el.style.display = 'none'; });
  document.querySelectorAll('[id^="plugin-view-"]').forEach(el => { el.classList.add('hidden'); el.style.display = 'none'; });

  // 显示动态容器（必须先清除 inline style，因为上方的 querySelectorAll 对 view-dynamic 也设置了 style.display='none'）
  container.classList.remove('hidden');
  container.style.removeProperty('display');
  container.style.display = 'block';
  container.innerHTML = '<div class="loading">⏳ 加载中...</div>';

  // 异步加载（不阻塞 switchView 返回）
  loadMigratedView(viewName, container).catch(err => {
    console.error(`[router] tryLoadView failed:`, err);
  });

  return true;
}

// 暴露到 window，供电线函数 switchView() 使用
window.tryLoadView = tryLoadView;

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
