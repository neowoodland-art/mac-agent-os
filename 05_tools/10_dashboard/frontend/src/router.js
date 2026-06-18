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
