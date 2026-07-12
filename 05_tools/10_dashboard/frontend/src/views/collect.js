/**
 * collect-view.js — 采集视图页面 v1
 *
 * 功能：
 *   - 批量输入 URL / sec_uid
 *   - URL 解析预览
 *   - 执行采集（L1轻量）
 *   - 展示结果表格
 *   - 采集历史
 */
import { registerMigrated, apiRequest, showLoading, showError } from '../router.js';

registerMigrated('collect');

export async function loadView(container) {
  container.innerHTML = `
    <div style="padding:20px;max-width:1200px;margin:0 auto">
      <h2 style="margin-bottom:16px">📡 内容采集</h2>

      <!-- 采集输入 -->
      <div style="background:var(--bg2);border-radius:10px;padding:16px;margin-bottom:16px">
        <div style="font-size:13px;font-weight:600;margin-bottom:8px">新建采集任务</div>
        <textarea id="collectTargets" rows="4"
          placeholder="输入 URL / sec_uid / 关键词，每行一个&#10;支持抖音视频链接、用户主页链接、短链等"
          style="width:100%;padding:8px;border-radius:6px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:12px;resize:vertical"></textarea>

        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:10px;align-items:center">
          <label style="font-size:12px">深度:
            <select id="collectDepth" style="margin-left:4px;padding:4px 8px;border-radius:4px;background:var(--bg3);color:var(--text);border:1px solid var(--border);font-size:12px">
              <option value="light">轻量采集（L1）</option>
              <option value="deep">深度分析（L2）</option>
            </select>
          </label>
          <label style="font-size:12px">工具:
            <select id="collectToolLevel" style="margin-left:4px;padding:4px 8px;border-radius:4px;background:var(--bg3);color:var(--text);border:1px solid var(--border);font-size:12px">
              <option value="1">Level 1: OpenCLI 仅</option>
              <option value="2" selected>Level 2: OpenCLI → 浏览器</option>
              <option value="3">Level 3: OpenCLI → 浏览器 → 网页抓取</option>
            </select>
          </label>
          <label style="font-size:12px">
            <input type="checkbox" id="collectMultiMachine" style="margin-right:4px">多机协同
          </label>
          <label style="font-size:12px">
            <input type="checkbox" id="collectAsyncMode" style="margin-right:4px">异步执行（大量目标）
          </label>
          <button id="collectResolveBtn" class="btn btn-secondary" style="font-size:12px">🔍 解析</button>
          <button id="collectRunBtn" class="btn btn-primary" style="font-size:12px">🚀 执行采集</button>
        </div>
      </div>

      <!-- 解析预览 -->
      <div id="collectResolvePreview" style="display:none;background:var(--bg2);border-radius:10px;padding:16px;margin-bottom:16px">
        <div style="font-size:13px;font-weight:600;margin-bottom:8px">解析结果</div>
        <div id="collectResolveTable"></div>
      </div>

      <!-- 执行结果 -->
      <div id="collectResult" style="display:none;background:var(--bg2);border-radius:10px;padding:16px;margin-bottom:16px">
        <div style="font-size:13px;font-weight:600;margin-bottom:8px">采集结果</div>
        <div id="collectResultContent"></div>
      </div>

      <!-- 采集历史 -->
      <div style="background:var(--bg2);border-radius:10px;padding:16px">
        <div style="font-size:13px;font-weight:600;margin-bottom:8px">
          最近采集
          <button id="collectRefreshHistory" style="margin-left:8px;padding:2px 8px;border-radius:4px;background:var(--bg3);border:1px solid var(--border);cursor:pointer;font-size:11px">⟳ 刷新</button>
        </div>
        <div id="collectHistoryList"><div class="loading">加载中...</div></div>
      </div>
    </div>
  `;

  // 绑定事件
  document.getElementById('collectResolveBtn').onclick = handleResolve;
  document.getElementById('collectRunBtn').onclick = handleRun;
  document.getElementById('collectRefreshHistory').onclick = loadHistory;

  // 加载历史
  loadHistory();
}

// ── 解析 ──

async function handleResolve() {
  const text = document.getElementById('collectTargets').value.trim();
  if (!text) return alert('请先输入目标');
  const targets = text.split('\n').filter(t => t.trim());

  try {
    const r = await apiRequest('/collect/resolve', {
      method: 'POST',
      body: JSON.stringify({ targets }),
    });
    if (r.status !== 'ok') return alert(r.message || '解析失败');

    const preview = document.getElementById('collectResolvePreview');
    preview.style.display = 'block';
    const table = document.getElementById('collectResolveTable');

    if (!r.data || r.data.length === 0) {
      table.innerHTML = '<div style="color:var(--red);font-size:12px">❌ 无法解析任何目标</div>';
      return;
    }

    let html = `<table style="width:100%;font-size:11px;border-collapse:collapse">
      <tr style="background:var(--bg3)">
        <th style="padding:6px 8px;text-align:left">输入</th>
        <th style="padding:6px 8px;text-align:left">平台</th>
        <th style="padding:6px 8px;text-align:left">类型</th>
        <th style="padding:6px 8px;text-align:left">目标ID</th>
        <th style="padding:6px 8px;text-align:left">状态</th>
      </tr>`;
    for (const r of r.data) {
      const status = r.status === 'resolved' ? '✅' : r.status === 'pending' ? '⏳' : '❌';
      html += `<tr>
        <td style="padding:4px 8px;max-width:200px;overflow:hidden;text-overflow:ellipsis">${esc(r.input)}</td>
        <td style="padding:4px 8px">${r.platform || '-'}</td>
        <td style="padding:4px 8px">${r.type || '-'}</td>
        <td style="padding:4px 8px;font-family:monospace">${r.target_id || '-'}</td>
        <td style="padding:4px 8px">${status}</td>
      </tr>`;
    }
    html += '</table>';
    table.innerHTML = html;
  } catch (e) {
    alert('解析失败: ' + e.message);
  }
}

// ── 执行 ──

async function handleRun() {
  const text = document.getElementById('collectTargets').value.trim();
  if (!text) return alert('请先输入目标');
  const targets = text.split('\n').filter(t => t.trim());

  const depth = document.getElementById('collectDepth').value;
  const toolLevel = parseInt(document.getElementById('collectToolLevel').value);
  const multiMachine = document.getElementById('collectMultiMachine').checked;
  const asyncMode = document.getElementById('collectAsyncMode').checked;

  const resultDiv = document.getElementById('collectResult');
  const resultContent = document.getElementById('collectResultContent');
  resultDiv.style.display = 'block';
  resultContent.innerHTML = '<div class="loading">⏳ 采集中...</div>';

  try {
    const r = await apiRequest('/collect/run', {
      method: 'POST',
      body: JSON.stringify({
        targets,
        depth,
        tool_level: toolLevel,
        multi_machine: multiMachine,
        async_mode: asyncMode,
      }),
    });
    if (r.status !== 'ok') {
      resultContent.innerHTML = `<div style="color:var(--red);font-size:12px">❌ ${r.message || '采集失败'}</div>`;
      return;
    }

    if (r.status === 'async') {
      resultContent.innerHTML = `<div style="font-size:12px">
        ✅ 异步任务已创建 (ID: ${r.run_id})<br>
        目标数: ${r.total}<br>
        <span style="color:var(--text2)">结果将稍后可用</span>
      </div>`;
      return;
    }

    renderResults(resultContent, r);
    loadHistory();
  } catch (e) {
    resultContent.innerHTML = `<div style="color:var(--red);font-size:12px">❌ ${e.message}</div>`;
  }
}

function renderResults(container, r) {
  const items = r.data || [];
  const errors = r.errors || [];

  let html = `<div style="font-size:12px;margin-bottom:10px;color:var(--text2)">
    共 ${r.total} 个目标 | ✅ 成功 ${r.success} | ❌ 失败 ${errors.length} | ⏱ ${r.duration}s
  </div>`;

  if (items.length === 0) {
    html += '<div style="font-size:12px;color:var(--text2)">无采集结果</div>';
    container.innerHTML = html;
    return;
  }

  html += `<table style="width:100%;font-size:11px;border-collapse:collapse">
    <tr style="background:var(--bg3)">
      <th style="padding:6px 8px;text-align:left">#</th>
      <th style="padding:6px 8px;text-align:left">标题</th>
      <th style="padding:6px 8px;text-align:left">作者</th>
      <th style="padding:6px 8px;text-align:right">❤️</th>
      <th style="padding:6px 8px;text-align:right">评论</th>
      <th style="padding:6px 8px;text-align:left">时间</th>
      <th style="padding:6px 8px;text-align:left">操作</th>
    </tr>`;

  items.forEach((item, i) => {
    const stats = item.stats || {};
    html += `<tr>
      <td style="padding:4px 8px">${i + 1}</td>
      <td style="padding:4px 8px;max-width:250px;overflow:hidden;text-overflow:ellipsis" title="${esc(item.title)}">${esc(trunc(item.title, 40))}</td>
      <td style="padding:4px 8px">${esc(item.author_name || '-')}</td>
      <td style="padding:4px 8px;text-align:right">${stats.likes ?? '-'}</td>
      <td style="padding:4px 8px;text-align:right">${stats.comments ?? '-'}</td>
      <td style="padding:4px 8px;font-size:10px">${item.published_at ? item.published_at.slice(0, 10) : '-'}</td>
      <td style="padding:4px 8px">
        <button class="collect-view-detail" data-id="${item.item_id || ''}" style="padding:2px 6px;border-radius:4px;background:var(--bg3);border:1px solid var(--border);cursor:pointer;font-size:10px">详情</button>
      </td>
    </tr>`;
  });
  html += '</table>';
  container.innerHTML = html;

  // 绑定详情按钮
  container.querySelectorAll('.collect-view-detail').forEach(btn => {
    btn.onclick = () => {
      const id = btn.dataset.id;
      // 简单弹窗展示
      const item = items.find(i => i.item_id === id);
      if (item) {
        alert([
          `标题: ${item.title}`,
          `作者: ${item.author_name}`,
          `链接: ${item.url}`,
          `点赞: ${item.stats?.likes ?? '-'} 评论: ${item.stats?.comments ?? '-'}`,
          item.media?.length ? `下载链接: ${item.media[0]?.url || '-'}` : '',
        ].filter(Boolean).join('\n'));
      }
    };
  });
}

// ── 历史 ──

async function loadHistory() {
  const el = document.getElementById('collectHistoryList');
  if (!el) return;
  try {
    const r = await apiRequest('/collect/tasks?limit=20');
    if (r.status !== 'ok') { el.innerHTML = '<div style="font-size:12px;color:var(--red)">加载失败</div>'; return; }
    const tasks = r.data || [];
    if (tasks.length === 0) {
      el.innerHTML = '<div style="font-size:12px;color:var(--text2)">暂无采集记录</div>';
      return;
    }
    let html = '<table style="width:100%;font-size:11px;border-collapse:collapse">' +
      '<tr style="background:var(--bg3)"><th style="padding:6px 8px;text-align:left">时间</th><th style="padding:6px 8px;text-align:left">平台</th><th style="padding:6px 8px;text-align:left">目标</th><th style="padding:6px 8px;text-align:left">状态</th><th style="padding:6px 8px;text-align:right">数量</th></tr>';
    for (const t of tasks) {
      const s = t.status === 'completed' ? '✅' : t.status === 'running' ? '⏳' : '❌';
      html += `<tr>
        <td style="padding:4px 8px;font-size:10px">${t.created_at || '-'}</td>
        <td style="padding:4px 8px">${t.platform || '-'}</td>
        <td style="padding:4px 8px;max-width:150px;overflow:hidden;text-overflow:ellipsis">${esc(trunc(t.target, 30))}</td>
        <td style="padding:4px 8px">${s} ${t.status}</td>
        <td style="padding:4px 8px;text-align:right">${t.total_targets || '-'}</td>
      </tr>`;
    }
    html += '</table>';
    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = `<div style="font-size:12px;color:var(--red)">❌ ${e.message}</div>`;
  }
}

// ── 工具函数 ──

function esc(s) {
  if (typeof s !== 'string') return s ?? '';
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function trunc(s, n) {
  if (typeof s !== 'string') return s ?? '';
  return s.length > n ? s.slice(0, n) + '...' : s;
}
