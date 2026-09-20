/**
 * navigation.js — 侧边栏导航渲染
 *
 * 从 inline.js 提取。处理导航栏分组定义、渲染、折叠/展开。
 * 所有函数同时注册到 window，因为 HTML onclick 属性直接引用它们。
 */

// ── 导航分组定义 ──
// ✅ 菜单定义已单点化 → 见 src/nav-menu.js（新增/删除菜单只改那里）
import { NAV_GROUPS } from './nav-menu.js';
const groups = NAV_GROUPS;

// ── Sidebar toggle ──
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const btn = document.getElementById('sidebarToggleBtn');
  const isCollapsed = sb.classList.toggle('collapsed');
  btn.textContent = isCollapsed ? '▶' : '◀';
  btn.title = isCollapsed ? '展开侧边栏' : '折叠侧边栏';
}

// ── Nav group accordion ──
function toggleGroup(el) {
  const body = el.nextElementSibling;
  if (!body || !body.classList) return;
  // 手风琴: 关闭其他所有分组
  document.querySelectorAll('.nav-group-header').forEach(h => {
    if (h === el) return;
    const b = h.nextElementSibling;
    if (b && b.classList && !b.classList.contains('collapsed')) {
      b.classList.add('collapsed');
      h.dataset.collapsed = 'true';
      const arrow = h.querySelector('span:last-child');
      if (arrow) arrow.textContent = '▶';
    }
  });
  // 切换当前分组
  const isCollapsed = body.classList.toggle('collapsed');
  el.dataset.collapsed = isCollapsed ? 'true' : 'false';
  el.querySelector('span:last-child').textContent = isCollapsed ? '▶' : '▼';
}

function collapseAllGroups() {
  document.querySelectorAll('.nav-group-header').forEach(h => {
    const body = h.nextElementSibling;
    if (body && body.classList && !body.classList.contains('collapsed')) {
      body.classList.add('collapsed');
      h.dataset.collapsed = 'true';
      const arrow = h.querySelector('span:last-child');
      if (arrow) arrow.textContent = '▶';
    }
  });
}

// ── Status badge helper ──
const S = (label, status) => `<span style="font-size:9px;margin-left:4px;padding:1px 5px;border-radius:3px;background:rgba(217,119,6,.12);color:#d97706;font-weight:500">${status}</span>`;

// ── Render nav ──
function _renderNav() {
  const nav = document.getElementById('navBar');
  if (!nav) return;
  let html = '';
  for (const [gname, g] of Object.entries(groups)) {
    html += `<div class="nav-group-header" onclick="toggleGroup(this)" data-collapsed="true">${g.icon} ${gname} <span style="float:right;font-size:10px;opacity:.5">▶</span></div>`;
    html += `<div class="nav-group-body collapsed">`;
    for (const item of g.items) {
      if (item.sub) {
        html += `<div class="nav-item" data-view="${item.view}" onclick="switchView('${item.view}')">${item.label}</div>`;
        for (const sub of item.sub) {
          html += `<div class="nav-sub" data-group="${item.view.replace('plugin-','')}" data-view="${sub.view}" onclick="switchView('${sub.view}')" style="display:none">${sub.label}</div>`;
        }
      } else {
        html += `<div class="nav-item" data-view="${item.view}" onclick="switchView('${item.view}')">${item.label}</div>`;
      }
    }
    html += '</div>';
  }
  html += '<div class="nav-item" data-view="timeline" onclick="switchView(\'timeline\')" style="display:none">📈 时间线</div>';
  nav.innerHTML = html;
}

/**
 * renderNav() — 渲染侧边栏导航
 * 由 loadPlugins() 在 inline.js 中调用
 */
export function renderNav() {
  _renderNav();
  // 恢复当前视图的激活状态由调用方负责
}

// ── 暴露到 window（供 HTML onclick 使用）──
window.toggleSidebar = toggleSidebar;
window.toggleGroup = toggleGroup;
window.collapseAllGroups = collapseAllGroups;
window.renderNav = renderNav;

// 自动渲染（模块加载时 DOM 可能尚未就绪 → 就绪后再渲染一次）
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', _renderNav);
} else {
  _renderNav();
}

// 内部函数也 export 以便测试
export { toggleSidebar, toggleGroup, collapseAllGroups, _renderNav, groups };
