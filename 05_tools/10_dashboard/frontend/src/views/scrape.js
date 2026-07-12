/**
 * 内容抓取视图 v1（已迁移 Vite 构建）
 *
 * 对应后端：
 *   POST   /api/scrape/run        — 执行抓取
 *   POST   /api/scrape/resolve    — 批量解析 URL
 *   GET    /api/scrape/tasks      — 任务列表
 *   GET    /api/scrape/items      — 内容列表
 *   GET    /api/scrape/items/{id} — 单条详情（含评论）
 *   GET    /api/scrape/stats      — 统计
 *   POST   /api/scrape/sources    — 创建抓取源
 *   GET    /api/scrape/sources    — 抓取源列表
 *   DELETE /api/scrape/sources/{id} — 删除抓取源
 *
 * 设计原则：
 *   ⛔ 绝不使用 Camoufox（养号专用）
 *   ✅ OpenCLI → Chrome 降级
 *   ✅ L1 轻量 / L2 深度 分层
 */

import { apiRequest, showLoading, showError } from '../router.js';

let _currentTab = 'run';
let _pollTimer = null;

// ── 视图入口 ──

export async function loadView(container) {
  container.innerHTML = renderLayout();
  bindEvents(container);
  loadStats();
  loadSources();
  loadHistory();
}

// ── HTML 渲染 ──

function renderLayout() {
  return `
  <div style="padding:12px;font-size:12px;color:var(--text)">
    <!-- Tab 栏 -->
    <div style="display:flex;gap:0;margin-bottom:10px;border-bottom:1px solid var(--border)">
      <div class="collect-tab active" data-tab="run" style="padding:6px 14px;cursor:pointer;border-bottom:2px solid #6366f1;font-weight:600;font-size:12px">📡 新建抓取</div>
      <div class="collect-tab" data-tab="sources" style="padding:6px 14px;cursor:pointer;color:var(--text2);font-size:12px">📋 抓取源</div>
      <div class="collect-tab" data-tab="history" style="padding:6px 14px;cursor:pointer;color:var(--text2);font-size:12px">📜 历史</div>
      <div style="flex:1"></div>
      <div id="collectStats" style="padding:6px 14px;font-size:10px;color:var(--text2);font-family:monospace"></div>
    </div>

    <!-- Tab: 新建抓取 -->
    <div id="collectTabRun" class="collect-tab-content">

      <!-- 输入区 -->
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border);margin-bottom:8px">
        <div style="display:flex;gap:6px;margin-bottom:6px;flex-wrap:wrap;align-items:center">
          <input id="ciTarget" type="text" placeholder="输入 sec_uid / URL / 关键词" style="flex:1;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:12px">
          <button id="ciBatchBtn" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 8px;border-radius:4px;cursor:pointer;font-size:10px">📋 批量导入</button>
          <button id="ciResolveBtn" style="background:var(--bg3);color:var(--text2);border:1px solid var(--border);padding:4px 8px;border-radius:4px;cursor:pointer;font-size:10px">🔍 解析</button>
        </div>
        <textarea id="ciBatchInput" style="display:none;width:100%;height:60px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:4px;font-size:11px;font-family:monospace;margin-bottom:4px" placeholder="每行一个 URL / sec_uid"></textarea>

        <!-- 选项行 -->
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:10px;color:var(--text2)">
            工具:
            <select id="ciToolLevel" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px">
              <option value="1">Level 1: OpenCLI</option>
              <option value="2" selected>Level 2: OpenCLI → Chrome</option>
              <option value="3">Level 3: OpenCLI → Chrome → Web</option>
            </select>
          </label>
          <label style="font-size:10px;color:var(--text2)">
            <input type="checkbox" id="ciDeep"> 深度分析(L2)
          </label>
          <label style="font-size:10px;color:var(--text2)">
            机器:
            <select id="ciMachine" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px">
              <option value="">本机</option>
              <option value="all">所有机器</option>
              <!-- 远程机器由 API 动态填充 -->
            </select>
          </label>
          <button id="ciExecBtn" style="background:#22c55e;color:#000;border:none;padding:4px 14px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 执行</button>
          <span id="ciStatus" style="font-size:10px;color:var(--text2);font-family:monospace"></span>
        </div>
      </div>

      <!-- 日志区 -->
      <div id="ciLog" style="background:var(--bg2);border-radius:8px;padding:6px;border:1px solid var(--border);max-height:200px;overflow-y:auto;font-family:monospace;font-size:10px;white-space:pre-wrap;margin-bottom:8px;display:none"></div>

      <!-- 结果区 -->
      <div id="ciResults" style="background:var(--bg2);border-radius:8px;padding:8px;border:1px solid var(--border);display:none">
        <div id="ciResultMeta" style="font-size:10px;color:var(--text2);margin-bottom:6px"></div>
        <div id="ciResultTable" style="overflow-x:auto"></div>
      </div>
    </div>

    <!-- Tab: 抓取源 -->
    <div id="collectTabSources" class="collect-tab-content" style="display:none">
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border)">
        <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;align-items:center">
          <input id="csTarget" type="text" placeholder="sec_uid / URL" style="flex:1;min-width:150px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
          <select id="csPlatform" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 4px;border-radius:3px;font-size:10px">
            <option value="douyin">🎵 抖音</option>
            <option value="xiaohongshu">📕 小红书</option>
          </select>
          <select id="csType" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 4px;border-radius:3px;font-size:10px">
            <option value="user">用户主页</option>
            <option value="keyword">关键词</option>
          </select>
          <input id="csName" type="text" placeholder="显示名称" style="width:120px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
          <button id="csAddBtn" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">➕ 添加</button>
        </div>
        <div id="csList" style="font-size:11px"></div>
      </div>
    </div>

    <!-- Tab: 历史 -->
    <div id="collectTabHistory" class="collect-tab-content" style="display:none">
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border)">
        <div id="chList" style="font-size:11px"></div>
      </div>
    </div>
  </div>`;
}

// ── 事件绑定 ──

function bindEvents(container) {
  // Tab 切换
  container.querySelectorAll('.collect-tab').forEach(el => {
    el.addEventListener('click', () => switchTab(el.dataset.tab));
  });

  // 批量导入按钮
  const batchBtn = document.getElementById('ciBatchBtn');
  if (batchBtn) {
    batchBtn.addEventListener('click', () => {
      const ta = document.getElementById('ciBatchInput');
      if (ta) ta.style.display = ta.style.display === 'none' ? 'block' : 'none';
    });
  }

  // 解析按钮
  const resolveBtn = document.getElementById('ciResolveBtn');
  if (resolveBtn) {
    resolveBtn.addEventListener('click', doResolve);
  }

  // 执行按钮
  const execBtn = document.getElementById('ciExecBtn');
  if (execBtn) {
    execBtn.addEventListener('click', doCollect);
  }

  // 抓取源添加按钮
  const addBtn = document.getElementById('csAddBtn');
  if (addBtn) {
    addBtn.addEventListener('click', addSource);
  }

  // 加载远程机器列表
  loadMachines();
}

// ── Tab 切换 ──

function switchTab(tab) {
  _currentTab = tab;
  document.querySelectorAll('.collect-tab').forEach(el => {
    el.style.borderBottom = el.dataset.tab === tab ? '2px solid #6366f1' : '2px solid transparent';
    el.style.fontWeight = el.dataset.tab === tab ? '600' : '400';
    el.style.color = el.dataset.tab === tab ? 'var(--text)' : 'var(--text2)';
  });
  document.querySelectorAll('.collect-tab-content').forEach(el => {
    el.style.display = 'none';
  });
  const contentEl = document.getElementById('collectTab' + tab.charAt(0).toUpperCase() + tab.slice(1));
  if (contentEl) contentEl.style.display = 'block';
  if (tab === 'sources') loadSources();
  if (tab === 'history') loadHistory();
}

// ── 日志 ──

function log(msg) {
  const el = document.getElementById('ciLog');
  if (!el) return;
  el.style.display = 'block';
  el.textContent += msg + '\n';
  el.scrollTop = el.scrollHeight;
}

function clearLog() {
  const el = document.getElementById('ciLog');
  if (el) { el.textContent = ''; el.style.display = 'none'; }
}

// ── 获取目标列表 ──

function getTargets() {
  const single = document.getElementById('ciTarget')?.value.trim();
  const batchInput = document.getElementById('ciBatchInput');
  const batch = batchInput?.value.trim();
  if (batch) {
    return batch.split('\n').map(s => s.trim()).filter(Boolean);
  }
  if (single) return [single];
  return [];
}

// ── 解析 URL ──

async function doResolve() {
  const targets = getTargets();
  if (!targets.length) { alert('请先输入目标'); return; }
  try {
    const r = await fetch('/api/scrape/resolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ targets }),
    });
    const d = await r.json();
    if (d.status !== 'ok') { alert('❌ ' + (d.message || '解析失败')); return; }
    const info = d.data.map(t =>
      `${t.status === 'resolved' ? '✅' : '❌'} ${t.input.slice(0, 40)} → ${t.platform}/${t.type}: ${t.target_id || '?'}`
    ).join('\n');
    log(info);
  } catch (e) {
    log('❌ 解析失败: ' + e.message);
  }
}

// ── 执行抓取 ──

async function doCollect() {
  const targets = getTargets();
  if (!targets.length) { alert('请先输入目标'); return; }

  const statusEl = document.getElementById('ciStatus');
  const toolLevel = parseInt(document.getElementById('ciToolLevel')?.value || '2');
  const depth = document.getElementById('ciDeep')?.checked ? 'deep' : 'light';
  const machine = document.getElementById('ciMachine')?.value || '';
  const isAsync = targets.length > 10;

  clearLog();
  log(`🚀 开始抓取: ${targets.length} 个目标 (L${toolLevel}, ${depth}, 机器:${machine || '本机'})`);
  if (statusEl) statusEl.textContent = '⏳ 执行中...';

  try {
    const r = await fetch('/api/scrape/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        targets,
        tool_level: toolLevel,
        depth,
        machine,
        async_mode: isAsync,
      }),
    });
    const d = await r.json();
    if (d.status === 'error') {
      log('❌ ' + d.message);
      if (statusEl) statusEl.textContent = '❌ 失败';
      return;
    }

    // 异步任务 → 轮询
    if (d.status === 'async') {
      if (statusEl) statusEl.textContent = `⏳ 异步任务 ${d.run_id} (${d.total} 个目标)`;
      log(`⏳ 异步任务已创建: ${d.run_id}`);
      pollAsyncResult(d.run_id, statusEl);
      return;
    }

    // 同步完成 → 展示结果
    if (statusEl) statusEl.textContent = `✅ 完成 (${d.duration}s, ${d.success}/${d.total})`;
    log(`✅ 抓取完成: ${d.duration}s, ${d.success} 成功, ${d.errors?.length || 0} 错误`);
    renderResults(d.data || [], d);
  } catch (e) {
    log('❌ ' + e.message);
    if (statusEl) statusEl.textContent = '❌ 异常';
  }
}

// ── 轮询异步结果 ──

async function pollAsyncResult(runId, statusEl) {
  if (_pollTimer) clearInterval(_pollTimer);
  let attempts = 0;

  _pollTimer = setInterval(async () => {
    attempts++;
    try {
      const r = await fetch(`/api/scrape/result?run_id=${runId}`);
      const d = await r.json();
      if (d.status !== 'ok') return;

      const data = d.data;
      if (!data || data.status === 'running') {
        if (statusEl) statusEl.textContent = `⏳ 进行中: ${data?.completed || 0}/${data?.total || '?'}`;
        return;
      }

      // 完成
      clearInterval(_pollTimer);
      _pollTimer = null;
      if (statusEl) statusEl.textContent = `✅ 完成 (${data.results?.length || 0}/${data.total})`;
      log(`✅ 异步任务完成: ${data.results?.length || 0} 成功, ${data.errors?.length || 0} 错误`);
      renderResults(data.results || [], data);
    } catch (e) {
      if (attempts > 30) {
        clearInterval(_pollTimer);
        _pollTimer = null;
        if (statusEl) statusEl.textContent = '❌ 轮询超时';
        log('❌ 异步任务轮询超时');
      }
    }
  }, 2000);
}

// ── 渲染结果表格 ──

function renderResults(items, meta) {
  const resultsEl = document.getElementById('ciResults');
  const metaEl = document.getElementById('ciResultMeta');
  const tableEl = document.getElementById('ciResultTable');
  if (!resultsEl || !metaEl || !tableEl) return;

  if (!items || !items.length) {
    metaEl.textContent = '⚠️ 没有抓取到任何内容';
    resultsEl.style.display = 'block';
    tableEl.innerHTML = '';
    return;
  }

  metaEl.textContent = `共 ${items.length} 条内容${meta?.duration ? ' | 耗时 ' + meta.duration + 's' : ''}`;
  resultsEl.style.display = 'block';

  let html = `<table style="width:100%;border-collapse:collapse;font-size:10px">
    <thead><tr style="background:var(--bg3);color:var(--text2);text-align:left">
      <th style="padding:3px 4px">#</th>
      <th style="padding:3px 4px">平台</th>
      <th style="padding:3px 4px">标题</th>
      <th style="padding:3px 4px">作者</th>
      <th style="padding:3px 4px">👍</th>
      <th style="padding:3px 4px">💬</th>
      <th style="padding:3px 4px">发布时间</th>
      <th style="padding:3px 4px">操作</th>
    </tr></thead><tbody>`;

  items.forEach((item, i) => {
    const platformIcon = item.platform === 'douyin' ? '🎵' : item.platform === 'xiaohongshu' ? '📕' : item.platform === 'bilibili' ? '📺' : '🌐';
    const itemId = item.item_id || item.id || i;
    const title = (item.title || '无标题').slice(0, 50);
    const author = item.author_name?.slice(0, 15) || '?';
    const likes = item.stats?.likes ?? item.likes ?? '?';
    const comments = item.stats?.comments ?? item.comment_count ?? item.comments ?? '?';
    const pubTime = (item.published_at || '').slice(0, 10);
    const link = item.url || '#';

    html += `<tr style="border-bottom:1px solid var(--border)">
      <td style="padding:3px 4px;color:var(--text2)">${i + 1}</td>
      <td style="padding:3px 4px">${platformIcon}</td>
      <td style="padding:3px 4px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${title}">
        <a href="${link}" target="_blank" style="color:var(--primary);text-decoration:none">${title}</a>
      </td>
      <td style="padding:3px 4px;color:var(--text2)">${author}</td>
      <td style="padding:3px 4px">${likes}</td>
      <td style="padding:3px 4px">${comments}</td>
      <td style="padding:3px 4px;color:var(--text2)">${pubTime}</td>
      <td style="padding:3px 4px">
        <button class="ci-comment-btn" data-item-id="${itemId}" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:1px 5px;border-radius:3px;cursor:pointer;font-size:9px">💬</button>
        ${item.media?.[0]?.url ? `<button class="ci-dl-btn" data-url="${item.media[0].url}" style="background:var(--bg3);color:var(--text2);border:1px solid var(--border);padding:1px 5px;border-radius:3px;cursor:pointer;font-size:9px">⬇</button>` : ''}
      </td>
    </tr>`;
  });

  html += '</tbody></table>';
  tableEl.innerHTML = html;

  // 评论按钮
  tableEl.querySelectorAll('.ci-comment-btn').forEach(btn => {
    btn.addEventListener('click', () => showComments(btn.dataset.itemId));
  });

  // 下载按钮
  tableEl.querySelectorAll('.ci-dl-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      navigator.clipboard?.writeText(btn.dataset.url);
      btn.textContent = '✅';
      setTimeout(() => { btn.textContent = '⬇'; }, 2000);
    });
  });
}

// ── 评论弹窗 ──

async function showComments(itemId) {
  // 如果 itemId 是纯数字，走详情 API
  try {
    const r = await fetch(`/api/scrape/items/${itemId}`);
    const d = await r.json();
    if (d.status !== 'ok') { alert('❌ 加载评论失败'); return; }
    const comments = d.data?.comments || [];
    if (!comments.length) { alert('暂无评论'); return; }

    let html = comments.map((c, i) =>
      `<div style="padding:4px 0;border-bottom:1px solid var(--border);font-size:11px">
        <b>${c.author_name || '匿名'}</b>
        <span style="color:var(--text2);float:right">👍 ${c.likes || 0}</span>
        <div style="color:var(--text);margin-top:2px">${c.text || ''}</div>
      </div>`
    ).join('');

    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center';
    overlay.innerHTML = `<div style="background:var(--bg2);border-radius:10px;padding:16px;max-width:500px;width:80%;max-height:80vh;overflow-y:auto;border:1px solid var(--border)"><div style="font-weight:600;font-size:13px;margin-bottom:8px">💬 评论区</div>${html}<div style="text-align:center;margin-top:8px"><button class="ci-close-overlay" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 12px;border-radius:4px;cursor:pointer">关闭</button></div></div>`;
    document.body.appendChild(overlay);
    overlay.querySelector('.ci-close-overlay').addEventListener('click', () => overlay.remove());
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
  } catch (e) {
    alert('❌ ' + e.message);
  }
}

// ── 统计 ──

async function loadStats() {
  const el = document.getElementById('collectStats');
  if (!el) return;
  try {
    const r = await fetch('/api/scrape/stats');
    const d = await r.json();
    if (d.total !== undefined) {
      el.textContent = `📊 ${d.total} 条内容 | 今日 +${d.today} | ${d.sources || 0} 源`;
    }
  } catch (e) { /* ignore */ }
}

// ── 远程机器列表 ──

async function loadMachines() {
  const sel = document.getElementById('ciMachine');
  if (!sel) return;
  try {
    const r = await fetch('/api/ops/machines');
    const d = await r.json();
    if (d.machines) {
      d.machines.forEach(m => {
        if (m.name && m.name !== 'local') {
          const opt = document.createElement('option');
          opt.value = m.name;
          opt.textContent = `🖥 ${m.name}`;
          sel.appendChild(opt);
        }
      });
    }
  } catch (e) { /* ignore */ }
}

// ── 抓取源管理 ──

async function addSource() {
  const target = document.getElementById('csTarget')?.value.trim();
  const platform = document.getElementById('csPlatform')?.value;
  const type = document.getElementById('csType')?.value;
  const name = document.getElementById('csName')?.value.trim() || target;
  if (!target) { alert('请填写目标'); return; }

  try {
    const r = await fetch('/api/scrape/sources', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform, source_type: type, target, display_name: name }),
    });
    const d = await r.json();
    if (d.status !== 'ok') { alert('❌ ' + (d.message || '添加失败')); return; }
    document.getElementById('csTarget').value = '';
    document.getElementById('csName').value = '';
    loadSources();
  } catch (e) {
    alert('❌ ' + e.message);
  }
}

async function loadSources() {
  const el = document.getElementById('csList');
  if (!el) return;
  try {
    const r = await fetch('/api/scrape/sources');
    const d = await r.json();
    if (d.status !== 'ok') { el.textContent = '❌ 加载失败'; return; }
    const sources = d.data || [];
    if (!sources.length) { el.innerHTML = '<div style="color:var(--text2);padding:10px;text-align:center">暂无抓取源</div>'; return; }

    let html = sources.map(s =>
      `<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 6px;border-bottom:1px solid var(--border)">
        <span>${s.display_name || s.target} <span style="color:var(--text2);font-size:9px">(${s.platform}/${s.source_type})</span></span>
        <span style="font-size:9px;color:var(--text2)">${s.last_collected ? '上次: ' + s.last_collected.slice(0, 10) : '未抓取'} <button class="cs-del-btn" data-id="${s.id}" style="background:var(--bg3);color:var(--red);border:1px solid var(--border);padding:1px 6px;border-radius:3px;cursor:pointer;font-size:9px">🗑</button></span>
      </div>`
    ).join('');
    el.innerHTML = html;

    el.querySelectorAll('.cs-del-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('删除此抓取源？')) return;
        try {
          await fetch(`/api/scrape/sources/${btn.dataset.id}`, { method: 'DELETE' });
          loadSources();
        } catch (e) { alert('❌ ' + e.message); }
      });
    });
  } catch (e) {
    el.textContent = '❌ ' + e.message;
  }
}

// ── 抓取历史 ──

async function loadHistory() {
  const el = document.getElementById('chList');
  if (!el) return;
  try {
    const r = await fetch('/api/scrape/tasks?limit=30');
    const d = await r.json();
    if (d.status !== 'ok') { el.textContent = '❌ 加载失败'; return; }
    const tasks = d.data || [];
    if (!tasks.length) { el.innerHTML = '<div style="color:var(--text2);padding:10px;text-align:center">暂无抓取历史</div>'; return; }

    let html = `<table style="width:100%;border-collapse:collapse;font-size:10px">
      <thead><tr style="background:var(--bg3);color:var(--text2);text-align:left">
        <th style="padding:3px 4px">时间</th>
        <th style="padding:3px 4px">类型</th>
        <th style="padding:3px 4px">目标</th>
        <th style="padding:3px 4px">状态</th>
        <th style="padding:3px 4px">结果</th>
      </tr></thead><tbody>`;

    tasks.forEach(t => {
      const statusIcon = t.status === 'completed' ? '✅' : t.status === 'failed' ? '❌' : t.status === 'running' ? '⏳' : '⏸';
      html += `<tr style="border-bottom:1px solid var(--border)">
        <td style="padding:3px 4px;color:var(--text2)">${(t.created_at || '').slice(0, 16)}</td>
        <td style="padding:3px 4px">${t.platform || 'auto'}</td>
        <td style="padding:3px 4px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${(t.target || '').slice(0, 40)}</td>
        <td style="padding:3px 4px">${statusIcon} ${t.status}</td>
        <td style="padding:3px 4px;color:var(--text2);font-size:9px">${t.completed_targets || 0}/${t.total_targets || 0}</td>
      </tr>`;
    });

    html += '</tbody></table>';
    el.innerHTML = html;
  } catch (e) {
    el.textContent = '❌ ' + e.message;
  }
}
