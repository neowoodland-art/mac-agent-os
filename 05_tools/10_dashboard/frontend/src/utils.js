/**
 * utils.js — 通用工具函数（从 inline.js 提取）
 * 
 * 用途：视图渲染辅助、字符处理、DOM 操作
 * 注意：这些是纯函数，不依赖外部状态
 */

// ── Shell 视图渲染（用于尚未对接 API 的视图占位）──
export function renderShell(containerId, title, status, note) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.classList.remove('hidden');
  el.style.display = 'block';
  el.innerHTML = `
    <div style="padding:40px;text-align:center;color:var(--text2)">
      <div style="font-size:32px;margin-bottom:12px">🚧</div>
      <div style="font-size:16px;font-weight:600;margin-bottom:8px">${title}</div>
      <div style="font-size:12px;margin-bottom:4px">状态: ${status}</div>
      <div style="font-size:11px;opacity:.7">${note}</div>
    </div>`;
}

// ── HTML 转义 ──
export function esc(s) {
  if (typeof s !== 'string') return s ?? '';
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── 字符串截断 ──
export function trunc(s, n) {
  if (typeof s !== 'string') return s ?? '';
  return s.length > n ? s.slice(0, n) + '...' : s;
}

// ── 时间格式化 ──
export function formatTime(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch { return iso.slice(0, 16) || iso; }
}

// ── 数字格式化 ──
export function fmtNum(n) {
  const num = parseInt(n) || 0;
  if (num >= 10000) return (num / 10000).toFixed(1) + 'w';
  return num.toLocaleString();
}
