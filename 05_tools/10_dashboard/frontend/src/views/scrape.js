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

  // 自动切换到指定Tab（从导航栏 crawl-sources/crawl-history 跳转时）
  if (window._scrapeTab) {
    const tab = window._scrapeTab;
    window._scrapeTab = null; // 消费后清除
    const tabEl = container.querySelector('.collect-tab[data-tab="' + tab + '"]');
    if (tabEl) tabEl.click();
  }
}

// ── HTML 渲染 ──

function renderLayout() {
  return `
  <div style="padding:12px;font-size:12px;color:var(--text)">
    <!-- Tab 栏 -->
    <div style="display:flex;gap:0;margin-bottom:10px;border-bottom:1px solid var(--border)">
      <div class="collect-tab active" data-tab="run" style="padding:6px 14px;cursor:pointer;border-bottom:2px solid #6366f1;font-weight:600;font-size:12px">📡 新建抓取</div>
      <div class="collect-tab" data-tab="sources" style="padding:6px 14px;cursor:pointer;color:var(--text2);font-size:12px">📋 抓取源</div>
      <div class="collect-tab" data-tab="dy-track" style="padding:6px 14px;cursor:pointer;color:var(--text2);font-size:12px">🎵 抖追踪</div>
      <div class="collect-tab" data-tab="dy-tracking" style="padding:6px 14px;cursor:pointer;color:var(--text2);font-size:12px">📡 跟踪中</div>
      <div class="collect-tab" data-tab="dy-authors" style="padding:6px 14px;cursor:pointer;color:var(--text2);font-size:12px">👥 博主监控</div>
      <div class="collect-tab" data-tab="history" style="padding:6px 14px;cursor:pointer;color:var(--text2);font-size:12px">📜 历史</div>
      <div style="flex:1"></div>
      <div id="collectStats" style="padding:6px 14px;font-size:10px;color:var(--text2);font-family:monospace"></div>
    </div>

    <!-- 抖音登录状态栏（采集不需要 Chrome 保持运行） -->
    <div id="loginBar" style="display:flex;align-items:center;gap:6px;padding:4px 8px;margin-bottom:6px;background:var(--bg2);border-radius:6px;border:1px solid var(--border);font-size:10px;color:var(--text2)">
      <span>🎵 抖音</span>
      <span id="loginStatusIcon" title="抖音登录状态">⚪</span>
      <span id="loginStatusText" style="font-size:9px;color:var(--text2)">检测中...</span>
      <span style="flex:1"></span>
      <button id="loginOpenBtn" style="display:none;background:#6366f1;color:#fff;border:none;padding:2px 8px;border-radius:4px;cursor:pointer;font-size:9px">📱 打开抖音登录</button>
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

    <!-- Tab: 跟踪中 -->
    <div id="collectTabDy-tracking" class="collect-tab-content" style="display:none">
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border)">
        <div id="dtTrackingList" style="font-size:11px"></div>
      </div>
    </div>

    <!-- Tab: 博主监控 -->
    <div id="collectTabDy-authors" class="collect-tab-content" style="display:none">
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border)">
        <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;align-items:center">
          <input id="daUrlInput" type="text" placeholder="粘贴视频链接或博主主页链接，跟踪博主" 
                 style="flex:1;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
          <button id="daAddBtn" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">👤 跟踪博主</button>
          <button id="daRefreshAllBtn" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">🔄 刷新全部</button>
          <span id="daStatus" style="font-size:10px;color:var(--text2);font-family:monospace"></span>
        </div>
        <div id="daAuthorList" style="font-size:11px"></div>
      </div>
    </div>

    <!-- Tab: 历史 -->
    <div id="collectTabHistory" class="collect-tab-content" style="display:none">
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border)">
        <div id="chList" style="font-size:11px"></div>
      </div>
    </div>

    <!-- Tab: 抖追踪 -->
    <div id="collectTabDy-track" class="collect-tab-content" style="display:none">
      <div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border)">
        <!-- 导入区 -->
        <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;align-items:center">
          <input id="dtApiUrl" type="text" placeholder="https://wx.tyhtak.com/api/biz/activity/api/v1/activity/recordswx1" 
                 style="flex:1;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px"
                 value="https://wx.tyhtak.com/api/biz/activity/api/v1/activity/recordswx1">
          <button id="dtImportBtn" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">📥 导入</button>
          <button id="dtNextPageBtn" style="display:none;background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">📄 下一页</button>
          <button id="dtBatchCollectBtn" style="display:none;background:#f97316;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600">⚡ 全部采集</button>
          <button id="dtCollectSelectedBtn" style="display:none;background:#22c55e;color:#000;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">✅ 采集选中</button>
          <button id="dtTrackSelectedBtn" style="display:none;background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">📌 跟踪选中</button>
          <span id="dtPageInfo" style="display:none;font-size:10px;color:var(--text2);font-family:monospace"></span>
          <span id="dtStatus" style="font-size:10px;color:var(--text2);font-family:monospace"></span>
        </div>
        <!-- 结果区：视频卡片列表 -->
        <div id="dtVideoList" style="font-size:11px;"></div>
        <!-- 日志 -->
        <div id="dtLog" style="display:none;background:var(--bg3);border-radius:6px;padding:6px;margin-top:6px;border:1px solid var(--border);max-height:150px;overflow-y:auto;font-family:monospace;font-size:10px;white-space:pre-wrap"></div>
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

  // 抖追踪事件
  const dtImportBtn = document.getElementById('dtImportBtn');
  if (dtImportBtn) dtImportBtn.addEventListener('click', () => doImportDyTopics(true));
  const dtNextPageBtn = document.getElementById('dtNextPageBtn');
  if (dtNextPageBtn) dtNextPageBtn.addEventListener('click', () => doImportDyTopics(false));
  const dtBatchBtn = document.getElementById('dtBatchCollectBtn');
  if (dtBatchBtn) dtBatchBtn.addEventListener('click', doBatchCollect);
  const dtCollectSelBtn = document.getElementById('dtCollectSelectedBtn');
  if (dtCollectSelBtn) dtCollectSelBtn.addEventListener('click', doCollectSelected);
  const dtTrackSelBtn = document.getElementById('dtTrackSelectedBtn');
  if (dtTrackSelBtn) dtTrackSelBtn.addEventListener('click', doTrackSelected);

  // ── 登录按钮事件 ──
  const loginBtn = document.getElementById('loginOpenBtn');
  if (loginBtn) {
    loginBtn.addEventListener('click', async () => {
      loginBtn.textContent = '⏳ 打开中...';
      loginBtn.disabled = true;
      document.getElementById('loginStatusText').textContent = '正在打开登录页...';
      try {
        const r = await fetch('/api/scrape/open-login', { method: 'POST' });
        const d = await r.json();
        if (d.success) {
          document.getElementById('loginStatusText').textContent = d.message || '请在 Chrome 窗口登录';
          document.getElementById('loginStatusIcon').textContent = '⏳';
          loginBtn.textContent = '已打开 ✅';
          // 10 秒后开始检测登录状态
          setTimeout(checkLoginStatus, 10000);
          // 如果 60 秒后还没登录，继续检测
          setTimeout(checkLoginStatus, 60000);
        } else {
          document.getElementById('loginStatusText').textContent = '❌ ' + (d.error || '打开失败');
        }
      } catch(e) {
        document.getElementById('loginStatusText').textContent = '❌ ' + e.message;
      }
      loginBtn.textContent = '📱 打开抖音登录';
      loginBtn.disabled = false;
    });
  }

  // ── 登录状态首次检测 ──
  setTimeout(checkLoginStatus, 1000);

}

// ── 抖音登录状态检测（无需浏览器，直接读 cookie 文件）──

async function checkLoginStatus() {
  const icon = document.getElementById('loginStatusIcon');
  const text = document.getElementById('loginStatusText');
  const btn = document.getElementById('loginOpenBtn');
  if (!icon || !text) return;
  try {
    const r = await fetch('/api/scrape/check-login');
    const d = await r.json();
    if (d.logged_in) {
      icon.textContent = '🟢';
      text.textContent = '抖音已登录';
      text.style.color = 'var(--green, #22c55e)';
      if (btn) btn.style.display = 'none';
    } else {
      icon.textContent = '🔴';
      text.textContent = '抖音未登录';
      text.style.color = '#ef4444';
      if (btn) btn.style.display = 'inline-block';
    }
  } catch(e) {
    icon.textContent = '⚪';
    text.textContent = '登录检测失败';
    text.style.color = 'var(--text2)';
    if (btn) btn.style.display = 'none';
  }
}

// 每 60 秒检查一次登录状态
setInterval(checkLoginStatus, 60000);

// ── Tab 切换 ──

async function switchTab(tab) {
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
  if (tab === 'history') {
    await loadHistory();
    loadDyHistory();
  }
  if (tab === 'dy-track') loadDyTrack();
  if (tab === 'dy-tracking') loadDyTracking();
  if (tab === 'dy-authors') loadDyAuthors();
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


// ═══════════════════════════════════════════════════════════
// 🎵 抖音追踪功能（与养号隔离，独立于 Camoufox）
// ═══════════════════════════════════════════════════════════

let _dyVideos = [];
let _dyTracked = new Set();
let _dyPage = 1;
let _dyTotal = 0;
let _dyApiUrl = '';

async function loadDyTrack() {
  const listEl = document.getElementById('dtVideoList');
  if (!listEl) return;
  const statusEl = document.getElementById('dtStatus');
  if (statusEl) statusEl.textContent = '';
  // 恢复缓存中的视频列表
  if (_dyVideos.length) {
    renderDyVideos(listEl);
  } else {
    listEl.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text2);font-size:12px">⬆️ 在上方输入 API 地址后点击「导入列表」</div>';
  }
}

function dtLog(msg) {
  const el = document.getElementById('dtLog');
  if (!el) return;
  el.style.display = 'block';
  el.textContent += msg + '\n';
  el.scrollTop = el.scrollHeight;
}

async function doImportDyTopics(reset = true) {
  const apiUrl = document.getElementById('dtApiUrl')?.value.trim();
  if (!apiUrl) { alert('请输入 API URL'); return; }
  const statusEl = document.getElementById('dtStatus');
  const pageInfoEl = document.getElementById('dtPageInfo');
  const nextBtnEl = document.getElementById('dtNextPageBtn');
  if (statusEl) statusEl.textContent = '⏳ 导入中...';
  
  const page = reset ? 1 : (_dyPage + 1);
  
  try {
    const r = await fetch('/api/scrape/import-topics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_url: apiUrl, page, page_size: 100 }),
    });
    const d = await r.json();
    if (d.status !== 'ok') {
      dtLog('❌ 导入失败: ' + (d.message || ''));
      if (statusEl) statusEl.textContent = '❌ 失败';
      return;
    }
    const items = d.items || [];
    if (reset) {
      _dyVideos = items;
      _dyPage = 1;
      _dyApiUrl = apiUrl;
      _dyTotal = d.total || items.length;
    } else {
      _dyVideos = _dyVideos.concat(items);
      _dyPage = page;
      _dyTotal = d.total || (_dyVideos.length + items.length);
    }
    
    if (statusEl) statusEl.textContent = `✅ ${reset ? '已导入' : '已追加'} ${_dyVideos.length} 条视频`;
    if (pageInfoEl) {
      pageInfoEl.style.display = 'inline';
      pageInfoEl.textContent = `📄 第 ${_dyPage} 页 / 共 ${_dyTotal} 条`;
    }
    if (nextBtnEl) {
      nextBtnEl.style.display = items.length >= 5 ? 'inline-block' : 'none';
    }
    dtLog(`✅ ${reset ? '导入' : '追加'} ${items.length} 条视频（第${_dyPage}页）`);
    const listEl = document.getElementById('dtVideoList');
    if (listEl) renderDyVideos(listEl);
  } catch (e) {
    dtLog('❌ 导入异常: ' + e.message);
    if (statusEl) statusEl.textContent = '❌ 异常';
  }
}

function renderDyVideos(container) {
  if (!_dyVideos.length) {
    container.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text2);font-size:12px">无视频数据</div>';
    return;
  }
    let html = '<div style="display:flex;align-items:center;gap:4px;padding:2px 8px;margin-bottom:2px;font-size:9px;color:var(--text2)">'
    + '<input type="checkbox" id="dtSelAll" style="flex-shrink:0" onchange="var x=document.querySelectorAll(\'.dt-sel-cb\');for(var j=0;j<x.length;j++){x[j].checked=this.checked}updateSelButtons()">'
    + '<span>全选</span>'
    + '<button id="dtTrackAllBtn" style="background:var(--bg3);color:var(--text2);border:1px solid var(--border);padding:1px 5px;border-radius:3px;cursor:pointer;font-size:9px">📌 全选跟踪</button>'
    + '<span style="flex:1"></span>'
    + '<button id="dtCopySelectedBtn" style="background:#6366f1;color:#fff;border:none;padding:2px 6px;border-radius:3px;cursor:pointer;font-size:9px">📋 复制选中</button>'
    + '<span>共 ' + _dyVideos.length + ' 条</span>'
    + '</div>';
  html += '<div style="display:flex;flex-direction:column;gap:6px">';
  _dyVideos.forEach((v, i) => {
    const tracked = _dyTracked.has(v.id);
    html += `<div style="background:var(--bg3);border-radius:6px;padding:6px 8px;border:1px solid var(--border)">
      <div style="display:flex;align-items:center;gap:3px;flex-wrap:nowrap">
        <input type="checkbox" class="dt-sel-cb" data-idx="${i}" style="flex-shrink:0">
        <button class="dt-collect-btn" data-idx="${i}" style="background:#22c55e;color:#000;border:none;padding:0 5px;border-radius:3px;cursor:pointer;font-size:9px;font-weight:600;flex-shrink:0">🔍</button>
        <label style="display:flex;align-items:center;gap:1px;font-size:9px;color:var(--text2);cursor:pointer;flex-shrink:0;white-space:nowrap">
          <input type="checkbox" class="dt-track-cb" data-id="${v.id}" ${tracked ? 'checked' : ''}>跟
        </label>
        <span style="font-size:10px;font-weight:600;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${v.title || ''}">${v.title || '无标题'}</span>
        <span style="font-size:8px;color:var(--text2);flex-shrink:0">${String(v.author || '?')?.slice(0,10) || '?'}</span>
        <a href="${v.url || '#'}" target="_blank" style="font-size:8px;color:var(--primary);flex-shrink:0">🔗</a>
      </div>
      <!-- 采集结果 -->
      <div id="dtResult_${i}" style="display:none;margin-top:4px;padding-top:4px;border-top:1px solid var(--border)">
        <div id="dtStats_${i}" style="font-size:10px;color:var(--text2)">⏳ 采集数据中...</div>
        <div id="dtComments_${i}" style="display:none;margin-top:4px;padding:4px;background:var(--bg2);border-radius:4px;font-size:10px;max-height:200px;overflow-y:auto"></div>
      </div>
    </div>`;
  });
  html += '</div>';
  container.innerHTML = html;

  // 绑定采集按钮
  container.querySelectorAll('.dt-collect-btn').forEach(btn => {
    btn.addEventListener('click', () => doCollectVideo(parseInt(btn.dataset.idx)));
  });
  // 绑定跟踪复选框
  container.querySelectorAll('.dt-track-cb').forEach(cb => {
    cb.addEventListener('change', (e) => {
      e.preventDefault();
      const id = cb.dataset.id;
      if (cb.checked) {
        _dyTracked.add(id);
        // 如果已采集过，立即跟踪
        const idx = _dyVideos.findIndex(v => v.id === id);
        if (idx >= 0 && document.getElementById('dtStats_' + idx)?.dataset?.collected) {
          trackVideo(idx);
        }
      } else {
        _dyTracked.delete(id);
      }
    });
  });
  updateBatchBtn();
  document.querySelectorAll('.dt-sel-cb').forEach(cb => cb.addEventListener('change', updateSelButtons));
  
  // 全选跟踪按钮
  const trackAllBtn = document.getElementById('dtTrackAllBtn');
  if (trackAllBtn && !trackAllBtn._bound) {
    trackAllBtn._bound = true;
    trackAllBtn.addEventListener('click', () => {
      const allChecked = document.querySelectorAll('.dt-track-cb:checked').length === document.querySelectorAll('.dt-track-cb').length;
      document.querySelectorAll('.dt-track-cb').forEach(cb => cb.checked = !allChecked);
      trackAllBtn.textContent = allChecked ? '📌 全选跟踪' : '✅ 已全选';
      setTimeout(() => trackAllBtn.textContent = '📌 全选跟踪', 1500);
    });
  }

  // 复制选中按钮（无勾选时复制全部）
  const copyBtn = document.getElementById('dtCopySelectedBtn');
  if (copyBtn && !copyBtn._bound) {
    copyBtn._bound = true;
    copyBtn.addEventListener('click', () => {
      const indices = getSelectedIndices();
      const items = indices.length ? indices.map(i => _dyVideos[i]).filter(Boolean) : _dyVideos;
      if (!items.length) return;
      const lines = items.map(v => ((v.title || '').replace(/\n/g, ' ') || '无标题') + '\n' + (v.url || '')).filter(Boolean);
      if (!lines.length) return;
      navigator.clipboard.writeText(lines.join('\n\n')).then(() => {
        const orig = copyBtn.textContent;
        copyBtn.textContent = '✅ 已复制';
        setTimeout(() => copyBtn.textContent = orig, 2000);
      });
    });
  }
}

async function doCollectVideo(idx) {
  const v = _dyVideos[idx];
  if (!v) return;
  const statsEl = document.getElementById('dtStats_' + idx);
  const commentEl = document.getElementById('dtComments_' + idx);
  const resultEl = document.getElementById('dtResult_' + idx);
  if (!statsEl || !resultEl) return;
  
  resultEl.style.display = 'block';
  statsEl.textContent = '⏳ 采集数据中...';
  statsEl.dataset.collected = '';
  
  try {
    const r = await fetch('/api/scrape/douyin-stats', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: v.url }),
    });
    const d = await r.json();
    if (d.status !== 'ok') {
      statsEl.textContent = '❌ ' + (d.message || '采集失败');
      return;
    }
    statsEl.textContent = `👍 ${d.likes || '?'} | 💬 ${d.comments || '?'} | ⭐ ${d.collects || '?'} | 更新时间: ${d.collected_at || '?'}`;
    statsEl.dataset.collected = 'true';
    statsEl.dataset.likes = d.likes || 0;
    statsEl.dataset.comments = d.comments || 0;
    statsEl.dataset.collects = d.collects || 0;
    
    // 如果有关联复选框且已勾选，自动跟踪
    const cb = document.querySelector('.dt-track-cb[data-id="' + v.id + '"]');
    if (cb?.checked) {
      trackVideo(idx, d);
    }

    // 显示评论
    if (d.comment_texts && d.comment_texts.length) {
      showDyComments(idx, commentEl, d.comment_texts);
    }
  } catch (e) {
    statsEl.textContent = '❌ 异常: ' + e.message;
  }
}

async function trackVideo(idx, data) {
  const v = _dyVideos[idx];
  if (!v) return;
  dtLog('📌 跟踪视频: ' + (v.title || '').slice(0, 40));
  // 如果已有采集结果，带上
  const statsEl = document.getElementById('dtStats_' + idx);
  if (data || statsEl?.dataset?.collected) {
    const likes = data?.likes || statsEl?.dataset?.likes || 0;
    const comments = data?.comments || statsEl?.dataset?.comments || 0;
    const collects = data?.collects || statsEl?.dataset?.collects || 0;
    
    try {
      await fetch('/api/scrape/track-video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: v.url,
          title: v.title,
          author: v.author,
          tracked_at: new Date().toLocaleString('zh-CN'),
        }),
      });
      dtLog('✅ 已跟踪');
    } catch (e) {
      dtLog('❌ 跟踪失败: ' + e.message);
    }
  } else {
    dtLog('⚠️ 请先采集再跟踪');
  }
}

async function loadDyHistory() {
  // 在历史 Tab 中加载跟踪列表
  const chList = document.getElementById('chList');
  if (!chList) return;
  
  // 先清除旧的跟踪列表
  let dySection = document.getElementById('dyTrackedSection');
  if (!dySection) {
    dySection = document.createElement('div');
    dySection.id = 'dyTrackedSection';
    chList.appendChild(dySection);
  }
  
  try {
    const r = await fetch('/api/scrape/tracked-videos');
    const d = await r.json();
    if (d.status !== 'ok') return;
    
    const items = d.items || [];
    if (!items.length) { dySection.innerHTML = ''; return; }
    
    let html = '<div style="margin-top:8px"><strong style="font-size:11px">🎵 抖音跟踪列表</strong></div>';
    html += '<div style="display:flex;flex-direction:column;gap:4px;margin-top:4px">';
    items.forEach(item => {
      html += '<div style="background:var(--bg3);border-radius:4px;padding:6px;border:1px solid var(--border)">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:2px">'
        + '<span style="font-size:10px;font-weight:600;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + (item.title || item.url?.slice(0, 40) || '?') + '</span>'
        + '<span style="font-size:9px;color:var(--text2)">' + (item.stats?.likes || '?') + '👍</span>'
        + '<span style="font-size:9px;color:var(--text2)">' + (item.stats?.comments || '?') + '💬</span>'
        + '<span style="font-size:9px;color:var(--text2)">' + (item.collected_at || '').slice(0, 16) + '</span>'
        + '<div style="display:flex;gap:2px">'
        + '<button class="dt-refresh-btn" data-id="' + item.id + '" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:1px 5px;border-radius:3px;cursor:pointer;font-size:9px">🔄</button>'
        + '<button class="dt-del-btn" data-id="' + item.id + '" style="background:#ef4444;color:#fff;border:none;padding:1px 5px;border-radius:3px;cursor:pointer;font-size:9px">✕</button>'
        + '</div>'
        + '</div>'
        + '<div class="dt-history-comments" id="dtHc_' + item.id + '" style="display:none;margin-top:4px;padding:4px;background:var(--bg2);border-radius:4px;font-size:9px;max-height:150px;overflow-y:auto"></div>'
        + '</div>';
    });
    html += '</div>';
    chList.innerHTML += html;
    
    // 绑定刷新按钮
    document.querySelectorAll('.dt-refresh-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.id;
        btn.textContent = '⏳';
        try {
          const r = await fetch('/api/scrape/refresh-video/' + id, { method: 'POST' });
          const d = await r.json();
          if (d.status === 'ok') {
            btn.textContent = '✅';
            setTimeout(() => btn.textContent = '🔄', 2000);
            // 刷新父元素显示
            const parent = btn.closest('[style*="background"]');
            if (parent) {
              const spans = parent.querySelectorAll('span');
              if (spans.length >= 3) {
                spans[1].textContent = d.item.stats.likes + '👍';
                spans[2].textContent = d.item.stats.comments + '💬';
                if (spans[3]) spans[3].textContent = (d.item.collected_at || '').slice(0, 16);
              }
            }
            // 显示评论
            const hc = document.getElementById('dtHc_' + id);
            if (hc && d.item.comment_texts?.length) {
              hc.style.display = 'block';
              hc.innerHTML = d.item.comment_texts.map(c => {
                const t = typeof c === 'string' ? c : (c.text || c.content || '');
                return '<div style="padding:2px 0">💬 ' + t + '</div>';
              }).join('');
            }
          } else {
            btn.textContent = '❌';
          }
        } catch(e) {
          btn.textContent = '❌';
        }
      });
    });
    // 绑定删除按钮
    document.querySelectorAll('.dt-del-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('确认删除这条跟踪记录？')) return;
        const id = btn.dataset.id;
        btn.textContent = '⏳';
        try {
          const r = await fetch('/api/scrape/delete-tracked/' + id, { method: 'POST' });
          const d = await r.json();
          if (d.status === 'ok') {
            btn.closest('[style*="background"]')?.remove();
          } else {
            btn.textContent = '✕';
          }
        } catch(e) {
          btn.textContent = '✕';
        }
      });
    });
  } catch (e) {
    // 静默失败，不影响原历史
    console.warn('抖追踪历史加载失败:', e.message);
  }
}


// ═══════════════════════════════════════════════════════════
// 🎵 抖追踪增强功能
// ═══════════════════════════════════════════════════════════

function updateBatchBtn() {
  const btn = document.getElementById('dtBatchCollectBtn');
  if (btn) btn.style.display = _dyVideos.length > 0 ? 'inline-block' : 'none';
}

async function doBatchCollect() {
  const btn = document.getElementById('dtBatchCollectBtn');
  if (btn) { btn.textContent = '⏳ 采集中...'; btn.disabled = true; }
  
  for (let i = 0; i < _dyVideos.length; i++) {
    const statsEl = document.getElementById('dtStats_' + i);
    // 跳过已采集的
    if (statsEl?.dataset?.collected) continue;
    await doCollectVideo(i);
    // 小延迟避免请求过快
    await new Promise(r => setTimeout(r, 1500));
  }
  
  if (btn) { btn.textContent = '⚡ 全部采集'; btn.disabled = false; }
  dtLog('✅ 全部采集完成');
}

function showCommentModal(title, comments) {
  // 移除旧弹窗
  const old = document.getElementById('dtCommentModal');
  if (old) old.remove();
  
  const overlay = document.createElement('div');
  overlay.id = 'dtCommentModal';
  overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:99999;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center';
  
  let commentHtml = '';
  if (comments && comments.length) {
    comments.forEach(c => {
      const text = typeof c === 'string' ? c : (c.text || c.content || '');
      const author = typeof c === 'string' ? '' : (c.nickname || c.author || '');
      const likes = typeof c === 'string' ? '' : (c.likes || c.digg_count || '');
      commentHtml += '<div style="padding:6px 0;border-bottom:1px solid var(--border)">'
        + (author ? '<span style="font-size:9px;color:var(--text2)">👤 ' + author + '</span>' : '')
        + (likes ? '<span style="font-size:9px;color:var(--text2);float:right">👍 ' + likes + '</span>' : '')
        + '<div style="font-size:11px;margin-top:2px;word-break:break-word">' + text + '</div>'
        + '</div>';
    });
  } else {
    commentHtml = '<div style="text-align:center;padding:20px;color:var(--text2)">暂无评论数据</div>';
  }
  
  overlay.innerHTML = '<div style="background:var(--bg2);border-radius:12px;padding:16px;max-width:500px;width:90%;max-height:80vh;display:flex;flex-direction:column;box-shadow:0 8px 30px rgba(0,0,0,0.3)">'
    + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
    + '<span style="font-size:13px;font-weight:600;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">💬 ' + (title || '评论') + '</span>'
    + '<span style="font-size:10px;color:var(--text2)">共 ' + (comments?.length || 0) + ' 条</span>'
    + '<button id="dtCommentClose" style="background:transparent;border:none;color:var(--text2);cursor:pointer;font-size:14px;padding:2px 6px">✕</button>'
    + '</div>'
    + '<div style="overflow-y:auto;flex:1;font-size:11px">' + commentHtml + '</div>'
    + '</div>';
  
  document.body.appendChild(overlay);
  document.getElementById('dtCommentClose').onclick = () => overlay.remove();
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
}

// 重写 showDyComments — 改为弹窗
function showDyComments(idx, container, comments) {
  if (!container) return;
  const v = _dyVideos[idx];
  const title = v?.title || '';
  
  container.innerHTML = '<span style="color:var(--primary);cursor:pointer;font-size:9px">💬 查看 ' + (comments?.length || 0) + ' 条评论 →</span>';
  container.style.display = 'block';
  container.onclick = () => showCommentModal(title, comments);
}

// 重写 renderDyVideos — 增加状态显示和全部采集按钮
function updateRenderDyVideos() {
  const listEl = document.getElementById('dtVideoList');
  if (listEl) renderDyVideos(listEl);
  updateBatchBtn();
  document.querySelectorAll('.dt-sel-cb').forEach(cb => cb.addEventListener('change', updateSelButtons));
  
  // 全选跟踪按钮
  const trackAllBtn = document.getElementById('dtTrackAllBtn');
  if (trackAllBtn && !trackAllBtn._bound) {
    trackAllBtn._bound = true;
    trackAllBtn.addEventListener('click', () => {
      const allChecked = document.querySelectorAll('.dt-track-cb:checked').length === document.querySelectorAll('.dt-track-cb').length;
      document.querySelectorAll('.dt-track-cb').forEach(cb => cb.checked = !allChecked);
      trackAllBtn.textContent = allChecked ? '📌 全选跟踪' : '✅ 已全选';
      setTimeout(() => trackAllBtn.textContent = '📌 全选跟踪', 1500);
    });
  }

  // 复制选中按钮（无勾选时复制全部）
  const copyBtn = document.getElementById('dtCopySelectedBtn');
  if (copyBtn && !copyBtn._bound) {
    copyBtn._bound = true;
    copyBtn.addEventListener('click', () => {
      const indices = getSelectedIndices();
      const items = indices.length ? indices.map(i => _dyVideos[i]).filter(Boolean) : _dyVideos;
      if (!items.length) return;
      const lines = items.map(v => ((v.title || '').replace(/\n/g, ' ') || '无标题') + '\n' + (v.url || '')).filter(Boolean);
      if (!lines.length) return;
      navigator.clipboard.writeText(lines.join('\n\n')).then(() => {
        const orig = copyBtn.textContent;
        copyBtn.textContent = '✅ 已复制';
        setTimeout(() => copyBtn.textContent = orig, 2000);
      });
    });
  }
}

// 将 renderDyVideos 末尾加上 updateBatchBtn
// 修改 renderDyVideos 的最后一行





// ═══════════════════════════════════════════════════════════
// 🎵 增强功能：采集选中 / 跟踪选中 / 跟踪专项页
// ═══════════════════════════════════════════════════════════

function getSelectedIndices() {
  const cbs = document.querySelectorAll('.dt-sel-cb:checked');
  return Array.from(cbs).map(cb => parseInt(cb.dataset.idx)).filter(i => !isNaN(i));
}

function updateSelButtons() {
  const hasSel = getSelectedIndices().length > 0;
  const sel1 = document.getElementById('dtCollectSelectedBtn');
  const sel2 = document.getElementById('dtTrackSelectedBtn');
  const copyBtn = document.getElementById('dtCopySelectedBtn');
  if (sel1) sel1.style.display = hasSel && _dyVideos.length > 0 ? 'inline-block' : 'none';
  if (sel2) sel2.style.display = hasSel && _dyVideos.length > 0 ? 'inline-block' : 'none';
  if (copyBtn) copyBtn.style.display = hasSel && _dyVideos.length > 0 ? 'inline-block' : 'none';
  
  // 全选勾选框同步
  const allCb = document.getElementById('dtSelAll');
  const total = document.querySelectorAll('.dt-sel-cb').length;
  const checked = document.querySelectorAll('.dt-sel-cb:checked').length;
  if (allCb) {
    allCb.checked = total > 0 && checked === total;
    allCb.indeterminate = checked > 0 && checked < total;
  }
}

async function doCollectSelected() {
  const indices = getSelectedIndices();
  if (!indices.length) { alert('请先勾选视频'); return; }
  for (const i of indices) {
    await doCollectVideo(i);
    await new Promise(r => setTimeout(r, 1500));
  }
  dtLog('✅ 选中采集完成: ' + indices.length + ' 条');
}

async function doTrackSelected() {
  const indices = getSelectedIndices();
  if (!indices.length) { alert('请先勾选视频'); return; }
  let count = 0;
  for (const i of indices) {
    const v = _dyVideos[i];
    if (!v) continue;
    _dyTracked.add(v.id);
    const cb = document.querySelector('.dt-track-cb[data-id="' + v.id + '"]');
    if (cb) cb.checked = true;
    const statsEl = document.getElementById('dtStats_' + i);
    if (statsEl?.dataset?.collected) {
      await trackVideo(i);
      count++;
    }
  }
  dtLog('✅ 已跟踪 ' + count + ' 条视频');
}

async function loadDyTracking() {
  const listEl = document.getElementById('dtTrackingList');
  if (!listEl) return;
  
  // 清除旧的刷新状态
  if (window._dtRefreshing) return;
  
  try {
    const r = await fetch('/api/scrape/tracked-videos');
    const d = await r.json();
    if (d.status !== 'ok') { listEl.innerHTML = '❌ 加载失败'; return; }
    
    const items = d.items || [];
    if (!items.length) {
      listEl.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text2);font-size:12px">暂无跟踪数据</div>';
      return;
    }
    
    let html = '<div style="display:flex;flex-direction:column;gap:4px">';
    
    // 头部：统计 + 一键刷新
    html += '<div style="display:flex;align-items:center;gap:6px;padding:4px 0;margin-bottom:2px;font-size:10px;color:var(--text2)">'
      + '<span>共 ' + items.length + ' 条</span>'
      + '<button id="dtRefreshAllBtn" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">🔄 刷新全部</button>'
      + '<button id="dtCopySelectedBtn" style="display:none;background:#6366f1;color:#fff;border:none;padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">📋 复制已选</button>'
      + '<button id="dtRefreshSelectedBtn" style="display:none;background:#f97316;color:#fff;border:none;padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">🔄 更新选中</button>'
      + '<button id="dtCopyAllBtn" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">📋 复制全部</button>'
      + '<span id="dtRefreshStatus" style="font-size:9px;font-family:monospace"></span>'
      + '</div>'
      + '<div id="dtRefreshRecovery" style="display:none"></div>';  // F5 恢复提示占位
    
    items.forEach((item, idx) => {
      const stats = item.stats || {};
      const prev = item.prev_stats || null;
      const itemId = item.id || idx;
      const vUrl = item.url || '';
      
      // 变化标记
      function diffHtml(label, key) {
        const cur = stats[key] || 0;
        if (!prev) return `<span style="font-size:9px;color:var(--text2)">${label} ${cur}</span>`;
        const old = prev[key] || 0;
        const diff = cur - old;
        let color = '#6b7280', arrow = '➡️', curColor = 'var(--text)';
        if (diff > 0) { color = '#22c55e'; arrow = '📈'; curColor = '#22c55e'; }
        if (diff < 0) { color = '#ef4444'; arrow = '📉'; curColor = '#ef4444'; }
        return `<span style="font-size:9px;color:var(--text2);white-space:nowrap">
          <span style="color:#9ca3af">${label}</span>
          <span style="color:#9ca3af;font-size:8px">${old}</span>
          <span style="font-size:8px;color:#9ca3af">→</span>
          <span style="font-weight:600;color:${curColor}">${cur}</span>
          <span style="color:${color};font-size:8px">${arrow}${diff > 0 ? '+' : ''}${diff}</span>
        </span>`;
      }
      
      html += '<div id="dtTrack_' + itemId + '" style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border)">'
        + '<div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap">'
        + '<input type="checkbox" class="dt-trk-sel" data-idx="' + idx + '" style="flex-shrink:0;cursor:pointer">'
        + (item.author ? '<span style="font-size:9px;color:var(--text2);white-space:nowrap">👤 ' + item.author + '</span>' : '')
        + '<button class="dt-track-author-btn" data-url="' + vUrl + '" style="background:#6366f1;color:#fff;border:none;padding:0 6px;border-radius:3px;cursor:pointer;font-size:8px;line-height:16px" title="跟踪这个博主">👤 跟踪</button>'
        + '<a href="' + vUrl + '" target="_blank" style="font-size:10px;font-weight:600;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--primary);text-decoration:none" title="' + (item.title || '') + '">' + (item.title || '?') + '</a>'
        + '<button class="dt-copy-link-btn" data-url="' + vUrl + '" data-title="' + (item.title || '').replace(/"/g,'&quot;') + '" style="background:var(--bg3);color:var(--text2);border:1px solid var(--border);padding:0 5px;border-radius:3px;cursor:pointer;font-size:8px">📋</button>'
        + diffHtml('👍', 'likes')
        + diffHtml('💬', 'comments')
        + diffHtml('⭐', 'collects')
        + (prev
          ? `<span style="font-size:8px;color:#9ca3af">⏱ ${(item.prev_collected_at||'').slice(5,16)}→${(item.collected_at||'').slice(5,16)}</span>`
          : `<span style="font-size:8px;color:var(--text2)">⏱ ${(item.collected_at||'').slice(5,16)}</span>`)
        + '<button class="dt-refresh-btn" data-id="' + item.id + '" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:0 5px;border-radius:3px;cursor:pointer;font-size:9px">🔄</button>'
        + '<button class="dt-del-btn" data-id="' + item.id + '" style="background:#ef4444;color:#fff;border:none;padding:0 5px;border-radius:3px;cursor:pointer;font-size:9px">✕</button>'
        + '</div>';
      
      // 评论区（默认展开前5条，点「展开全部」看全部）
      if (item.comment_texts?.length) {
        const allText = item.comment_texts.map(c => {
          const t = typeof c === 'string' ? c : (c.text || '');
          const n = typeof c === 'string' ? '' : (c.nickname || '');
          return (n ? '👤' + n + ': ' : '💬') + t;
        });
        const preview = allText.slice(0, 5).join('<br>');
        html += '<div class="dt-cmt-area" id="dtCmt_' + item.id + '" style="margin-top:4px;padding:4px;background:var(--bg2);border-radius:4px;font-size:9px;max-height:400px;overflow-y:auto">'
          + '<div class="dt-cmt-collapsed">' + preview + '</div>'
          + '<div class="dt-cmt-full" style="display:none">' + allText.join('<br>') + '</div>'
          + '</div>';
        if (allText.length > 5) {
          html += '<div style="font-size:8px;margin-top:1px"><span class="dt-cmt-toggle" data-id="' + item.id + '" style="color:var(--primary);cursor:pointer">💬 展开全部 ' + allText.length + ' 条</span></div>';
        }
      }
      
      html += '</div>';
    });
    html += '</div>';
    listEl.innerHTML = html;
    
    // 绑定刷新按钮（单条）
    listEl.querySelectorAll('.dt-refresh-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        btn.textContent = '⏳';
        const statusEl = document.getElementById('dtRefreshStatus');
        try {
          const r = await fetch('/api/scrape/refresh-video/' + btn.dataset.id, { method: 'POST' });
          const d = await r.json();
          if (d.status === 'ok') {
            btn.textContent = '✅';
            if (statusEl) statusEl.textContent = '';
            setTimeout(() => btn.textContent = '🔄', 1500);
            loadDyTracking();
          } else {
            btn.textContent = '❌';
            if (statusEl) statusEl.textContent = '❌ ' + (d.message || '采集失败');
            setTimeout(() => btn.textContent = '🔄', 3000);
            // 如果是登录过期，立即刷新登录状态
            if (d.login_expired) {
              setTimeout(checkLoginStatus, 500);
            }
          }
        } catch(e) {
          btn.textContent = '❌';
          if (statusEl) statusEl.textContent = '❌ 网络错误: ' + e.message;
          setTimeout(() => btn.textContent = '🔄', 3000);
        }
      });
    });
    
    // 绑定复制单条链接按钮
    listEl.querySelectorAll('.dt-copy-link-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const url = btn.dataset.url;
        const title = btn.dataset.title;
        const text = title + '\n' + url;
        navigator.clipboard.writeText(text).then(() => {
          const orig = btn.textContent;
          btn.textContent = '✅';
          setTimeout(() => btn.textContent = orig, 1500);
        });
      });
    });
    
    // 绑定复制全部按钮
    const copyAllBtn = document.getElementById('dtCopyAllBtn');
    if (copyAllBtn) {
      copyAllBtn.addEventListener('click', () => {
        const lines = items.map(it => {
          const title = (it.title || '无标题').replace(/\n/g, ' ');
          return title + '\n' + (it.url || '');
        }).join('\n\n');
        navigator.clipboard.writeText(lines).then(() => {
          const orig = copyAllBtn.textContent;
          copyAllBtn.textContent = '✅ 已复制';
          setTimeout(() => copyAllBtn.textContent = orig, 2000);
        });
      });
    }
    
    // 勾选框事件：显示/隐藏「复制已选」按钮
    function updateTrkSelBtn() {
      const checked = document.querySelectorAll('.dt-trk-sel:checked').length;
      const show = checked > 0 ? 'inline-block' : 'none';
      const selBtn = document.getElementById('dtCopySelectedBtn');
      if (selBtn) selBtn.style.display = show;
      const refBtn = document.getElementById('dtRefreshSelectedBtn');
      if (refBtn) refBtn.style.display = show;
    }
    listEl.querySelectorAll('.dt-trk-sel').forEach(cb => {
      cb.addEventListener('change', updateTrkSelBtn);
    });
    
    // 绑定复制已选按钮
    const copySelBtn = document.getElementById('dtCopySelectedBtn');
    if (copySelBtn) {
      copySelBtn.addEventListener('click', () => {
        const data = [];
        listEl.querySelectorAll('.dt-trk-sel:checked').forEach(cb => {
          const idx = parseInt(cb.dataset.idx);
          const item = items[idx];
          if (item) {
            data.push(((item.title || '无标题').replace(/\n/g, ' ')) + '\n' + (item.url || ''));
          }
        });
        if (!data.length) return;
        navigator.clipboard.writeText(data.join('\n\n')).then(() => {
          copySelBtn.textContent = '✅ 已复制';
          setTimeout(() => copySelBtn.textContent = '📋 复制已选', 2000);
        });
      });
    }
    
    // 绑定更新选中按钮
    const refSelBtn = document.getElementById('dtRefreshSelectedBtn');
    if (refSelBtn) {
      refSelBtn.addEventListener('click', async () => {
        const selected = listEl.querySelectorAll('.dt-trk-sel:checked');
        if (!selected.length) return;
        const statusEl = document.getElementById('dtRefreshStatus');
        refSelBtn.textContent = '⏳ 更新中...';
        let ok = 0, fail = 0, total = selected.length;
        for (const cb of selected) {
          const idx = parseInt(cb.dataset.idx);
          const item = items[idx];
          if (!item) { fail++; continue; }
          if (statusEl) statusEl.textContent = '更新中 ' + (ok+fail+1) + '/' + total;
          try {
            const r = await fetch('/api/scrape/refresh-video/' + item.id, { method: 'POST' });
            const d = await r.json();
            if (d.status === 'ok') ok++; else fail++;
            // 登录过期 → 立即停止
            if (d.login_expired) {
              if (statusEl) statusEl.textContent = '⛔ 登录已过期，已停止。请先登录';
              refSelBtn.textContent = '🔄 更新选中';
              checkLoginStatus();
              return;  // 跳出整个循环
            }
          } catch(e) { fail++; }
          await new Promise(r => setTimeout(r, 3000));
        }
        if (statusEl) statusEl.textContent = '✅ ' + ok + '成功 ' + fail + '失败';
        refSelBtn.textContent = '🔄 更新选中';
        loadDyTracking();
      });
    }
    
    // 绑定删除按钮
    listEl.querySelectorAll('.dt-del-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('确认删除？')) return;
        btn.textContent = '⏳';
        const r = await fetch('/api/scrape/delete-tracked/' + btn.dataset.id, { method: 'POST' });
        if (r.ok) {
          const el = document.getElementById('dtTrack_' + btn.dataset.id);
          if (el) el.remove();
        } else {
          btn.textContent = '✕';
        }
      });
    });
    
    // 绑定展开评论
    listEl.querySelectorAll('.dt-cmt-toggle').forEach(el => {
      el.addEventListener('click', () => {
        const id = el.dataset.id;
        const area = document.getElementById('dtCmt_' + id);
        if (!area) return;
        const collapsed = area.querySelector('.dt-cmt-collapsed');
        const full = area.querySelector('.dt-cmt-full');
        if (collapsed && full) {
          collapsed.style.display = 'none';
          full.style.display = 'block';
        }
        el.textContent = '💬 收起';
        el.onclick = () => {
          collapsed.style.display = 'block';
          full.style.display = 'none';
          el.textContent = '💬 展开全部';
        };
      });
    });
    
    // 绑定「跟踪博主」按钮
    listEl.querySelectorAll('.dt-track-author-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        btn.textContent = '⏳';
        btn.disabled = true;
        try {
          const r = await fetch('/api/scrape/track-author', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: btn.dataset.url }),
          });
          const d = await r.json();
          if (d.status === 'ok') {
            btn.textContent = '✓ 已跟踪';
            btn.style.background = '#22c55e';
          } else {
            btn.textContent = '❌ ' + (d.message || '失败');
            btn.style.background = '#ef4444';
          }
        } catch(e) {
          btn.textContent = '❌ ' + e.message;
          btn.style.background = '#ef4444';
        }
        setTimeout(() => { btn.textContent = '👤 跟踪'; btn.style.background = '#6366f1'; btn.disabled = false; }, 3000);
      });
    });
    
    // 绑定「刷新全部」按钮
    const refreshAllBtn = document.getElementById('dtRefreshAllBtn');
    if (refreshAllBtn) {
      refreshAllBtn.onclick = doRefreshAllTracking;
      // 更新按钮显示（如果正在刷新，改为停止按钮）
      if (window._dtRefreshing) {
        refreshAllBtn.textContent = '⏹ 停止';
        refreshAllBtn.style.background = '#ef4444';
        refreshAllBtn.style.color = '#fff';
      } else {
        refreshAllBtn.textContent = '🔄 刷新全部';
        refreshAllBtn.style.background = '';
        refreshAllBtn.style.color = '';
      }
    }
    
    // 检查 F5 恢复提示
    showRefreshRecovery();
    
  } catch (e) {
    listEl.innerHTML = '❌ 加载失败: ' + e.message;
  }
}

// ── 博主监控（跟踪博主列表 + 刷新 + 趋势） ──

async function loadDyAuthors() {
  const listEl = document.getElementById('daAuthorList');
  if (!listEl) return;
  listEl.innerHTML = '<div style="padding:12px;text-align:center;color:var(--text2);font-size:11px">⏳ 加载博主列表...</div>';

  // 绑定添加按钮
  const addBtn = document.getElementById('daAddBtn');
  const urlInput = document.getElementById('daUrlInput');
  if (addBtn) addBtn.onclick = async () => {
    const url = (urlInput?.value || '').trim();
    if (!url) { alert('请粘贴视频链接或博主主页链接'); return; }
    addBtn.textContent = '⏳';
    addBtn.disabled = true;
    try {
      const r = await fetch('/api/scrape/track-author', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      const d = await r.json();
      if (d.status === 'ok') {
        urlInput.value = '';
        alert('✅ ' + (d.message || '已跟踪'));
        loadDyAuthors();
      } else {
        alert('❌ ' + (d.message || '失败'));
      }
    } catch(e) { alert('❌ ' + e.message); }
    addBtn.textContent = '👤 跟踪博主';
    addBtn.disabled = false;
  };

  // 绑定刷新全部按钮
  const refreshAllBtn = document.getElementById('daRefreshAllBtn');
  const statusEl = document.getElementById('daStatus');
  if (refreshAllBtn) refreshAllBtn.onclick = async () => {
    refreshAllBtn.textContent = '⏳ 刷新中...';
    refreshAllBtn.disabled = true;
    if (statusEl) statusEl.textContent = '正在刷新全部博主（3秒/个）...';
    try {
      const r = await fetch('/api/scrape/refresh-all-authors', { method: 'POST' });
      const d = await r.json();
      if (statusEl) statusEl.textContent = '✅ 完成: ' + (d.results || []).map(x => x.nickname + (x.status === 'ok' ? '✓' : '✗')).join(' ');
    } catch(e) {
      if (statusEl) statusEl.textContent = '❌ ' + e.message;
    }
    refreshAllBtn.textContent = '🔄 刷新全部';
    refreshAllBtn.disabled = false;
    loadDyAuthors();
  };

  try {
    const r = await fetch('/api/scrape/tracked-authors');
    const d = await r.json();
    const authors = d.items || [];
    if (!authors.length) {
      listEl.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text2);font-size:12px">暂无跟踪博主<br><span style="font-size:10px">在上方粘贴视频链接，或到「跟踪中」列表点视频行的「👤 跟踪」按钮</span></div>';
      return;
    }

    let html = '';
    for (const a of authors) {
      const fansDelta = a.fans_delta || 0;
      const deltaColor = fansDelta > 0 ? '#22c55e' : (fansDelta < 0 ? '#ef4444' : '#6b7280');
      const deltaArrow = fansDelta > 0 ? '📈' : (fansDelta < 0 ? '📉' : '➡️');
      const collected = a.today_collected ? '<span style="color:#22c55e;font-size:9px">✅ 今日已采集</span>' : '<span style="color:#f59e0b;font-size:9px">⏳ 今日未采集</span>';

      // 最新3条视频（标题+点赞/评论/收藏）
      const latestVideos = a.latest_videos || [];
      const videoBlock = latestVideos.length
        ? '<div style="margin-top:6px;display:flex;flex-direction:column;gap:2px">' + latestVideos.map(v => {
            const title = (v.title || '?').slice(0, 30);
            return `<div style="display:flex;align-items:center;gap:6px;font-size:9px;color:var(--text2);padding:2px 6px;background:var(--bg2);border-radius:3px;overflow:hidden;white-space:nowrap">
              <a href="${v.url}" target="_blank" style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--primary);text-decoration:none" title="${title.replace(/"/g,'&quot;')}">${title}</a>
              <span style="flex-shrink:0">👍 ${v.likes ?? 0}</span>
              <span style="flex-shrink:0">💬 ${v.comments ?? 0}</span>
              <span style="flex-shrink:0">⭐ ${v.collects ?? 0}</span>
            </div>`;
          }).join('') + '</div>'
        : '';

      html += `<div class="da-author-row" data-id="${a.author_id}" style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:4px">
        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
          <span style="font-size:11px;font-weight:600">👤 ${a.nickname || a.uid}</span>
          ${a.unique_id ? `<span style="font-size:9px;color:var(--text2)">@${a.unique_id}</span>` : ''}
          <span style="font-size:9px;color:var(--text2)">⭐ ${a.works || 0} 作品</span>
          <span style="font-size:10px">👥 ${a.fans || 0} <span style="font-size:9px;color:${deltaColor}">${deltaArrow}${fansDelta > 0 ? '+' : ''}${fansDelta}</span></span>
          ${collected}
          <span style="flex:1"></span>
          <button class="da-refresh-btn" data-id="${a.author_id}" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:0 6px;border-radius:3px;cursor:pointer;font-size:9px">🔄</button>
          <button class="da-history-btn" data-id="${a.author_id}" style="background:#6366f1;color:#fff;border:none;padding:0 8px;border-radius:3px;cursor:pointer;font-size:9px">📈 趋势</button>
          <button class="da-del-btn" data-id="${a.author_id}" style="background:#ef4444;color:#fff;border:none;padding:0 6px;border-radius:3px;cursor:pointer;font-size:9px">✕</button>
        </div>
        ${videoBlock}
        <div class="da-history-area" id="daHistory_${a.author_id}" style="display:none;margin-top:6px;padding:6px;background:var(--bg2);border-radius:4px;font-size:10px"></div>
      </div>`;
    }
    listEl.innerHTML = html;

    // 绑定刷新单个
    listEl.querySelectorAll('.da-refresh-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        btn.textContent = '⏳';
        const r = await fetch('/api/scrape/refresh-author/' + btn.dataset.id, { method: 'POST' });
        const d = await r.json();
        btn.textContent = d.status === 'ok' ? '✅' : '❌';
        if (d.status === 'ok' && d.item?.new_video_count > 0) alert(`✅ ${d.item.nickname} 发现 ${d.item.new_video_count} 个新视频，已加入跟踪`);
        setTimeout(() => loadDyAuthors(), 1500);
      });
    });

    // 绑定删除
    listEl.querySelectorAll('.da-del-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('取消跟踪该博主？')) return;
        const r = await fetch('/api/scrape/tracked-authors/' + btn.dataset.id, { method: 'DELETE' });
        if (r.ok) loadDyAuthors();
      });
    });

    // 绑定趋势展开
    listEl.querySelectorAll('.da-history-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.id;
        const area = document.getElementById('daHistory_' + id);
        if (!area) return;
        if (area.style.display === 'block') { area.style.display = 'none'; return; }
        area.style.display = 'block';
        area.innerHTML = '⏳ 加载趋势...';
        try {
          const r = await fetch('/api/scrape/author-history/' + id);
          const d = await r.json();
          const snaps = d.item?.snapshots || [];
          if (!snaps.length) { area.innerHTML = '暂无数据'; return; }
          // 趋势行
          const rows = snaps.map(s => {
            const prev = null;
            const fans = s.fans || 0;
            return `<div style="display:flex;gap:8px;align-items:center;padding:2px 0;border-bottom:1px dashed var(--border)">
              <span style="font-size:9px;color:var(--text2);width:70px">${s.date || ''}</span>
              <span style="font-size:10px;width:80px">👥 ${fans}</span>
              <span style="font-size:9px;color:var(--text2);width:60px">⭐ ${s.works || 0}</span>
              <span style="font-size:9px">${(s.new_videos || []).length ? '🆕 ' + s.new_videos.length + '个新视频' : ''}</span>
            </div>`;
          }).join('');
          area.innerHTML = '<div style="font-size:10px;font-weight:600;margin-bottom:4px">📈 历史快照 (' + snaps.length + ' 天)</div>' + rows;
        } catch(e) {
          area.innerHTML = '❌ ' + e.message;
        }
      });
    });
  } catch (e) {
    listEl.innerHTML = '❌ 加载失败: ' + e.message;
  }
}


function showRefreshRecovery() {
  const raw = sessionStorage.getItem('dt_refresh_progress');
  if (!raw) return;
  try {
    const prog = JSON.parse(raw);
    // 超过 5 分钟的不提示
    if (Date.now() - prog.started_at > 300000) { sessionStorage.removeItem('dt_refresh_progress'); return; }
    // 已完成的直接清掉
    if (prog.status === 'completed') { sessionStorage.removeItem('dt_refresh_progress'); return; }
    
    const elapsed = Math.round((Date.now() - prog.started_at) / 1000);
    const recoveryEl = document.getElementById('dtRefreshRecovery');
    if (!recoveryEl) return;
    recoveryEl.style.display = 'block';
    recoveryEl.innerHTML = `<div style="display:flex;align-items:center;gap:6px;padding:6px 10px;margin-bottom:4px;background:#fffbeb;border:1px solid #fde68a;border-radius:6px;font-size:11px">
      <span>⏸️</span>
      <span style="flex:1">上次全部更新中断（${prog.done||0}/${prog.total||'?'}，已完成${elapsed}秒前），<strong>✅${prog.success||0} ❌${prog.fail||0}</strong></span>
      <button onclick="sessionStorage.removeItem('dt_refresh_progress');this.closest('#dtRefreshRecovery').style.display='none'" style="background:none;border:1px solid var(--border);border-radius:4px;padding:2px 8px;cursor:pointer;font-size:10px">✕ 关闭</button>
    </div>`;
  } catch(e) {
    sessionStorage.removeItem('dt_refresh_progress');
  }
}

// ── 一键刷新全部（逐个刷新，间隔 3 秒） ──

async function doRefreshAllTracking() {
  // 清除之前的恢复提示
  sessionStorage.removeItem('dt_refresh_progress');
  const recoveryEl = document.getElementById('dtRefreshRecovery');
  if (recoveryEl) recoveryEl.style.display = 'none';
  // 如果正在刷新，点击即为停止
  if (window._dtRefreshing) {
    window._dtRefreshing = false;
    const statusEl = document.getElementById('dtRefreshStatus');
    if (statusEl) statusEl.textContent += ' ⏹ 已停止';
    const btn = document.getElementById('dtRefreshAllBtn');
    if (btn) { btn.textContent = '🔄 刷新全部'; btn.style.background = ''; btn.style.color = ''; }
    return;
  }
  
  window._dtRefreshing = true;
  
  const statusEl = document.getElementById('dtRefreshStatus');
  const btn = document.getElementById('dtRefreshAllBtn');
  if (btn) { btn.textContent = '⏹ 停止'; btn.style.background = '#ef4444'; btn.style.color = '#fff'; }
  
  const items = document.querySelectorAll('.dt-refresh-btn');
  let success = 0, fail = 0;
  const total = items.length;
  
  // 写入 sessionStorage（F5 不丢）
  sessionStorage.setItem('dt_refresh_progress', JSON.stringify({
    started_at: Date.now(),
    total, success, fail,
    done: 0, status: 'running'
  }));
  
  for (const refreshBtn of items) {
    if (!window._dtRefreshing) break; // 允许中断
    
    const id = refreshBtn.dataset.id;
    refreshBtn.textContent = '⏳';
    const done = success + fail;
    if (statusEl) statusEl.textContent = '正在刷新 ' + (done + 1) + '/' + total;
    
    try {
      const r = await fetch('/api/scrape/refresh-video/' + id, { method: 'POST' });
      const d = await r.json();
      if (d.status === 'ok') {
        refreshBtn.textContent = '✅';
        success++;
        // 逐条更新前端显示，不刷新整个列表
        updateTrackedRow(id, d.item);
      } else {
        refreshBtn.textContent = '❌';
        fail++;
      }
    } catch(e) {
      refreshBtn.textContent = '❌';
      fail++;
    }
    
    // 每完成一条更新 sessionStorage
    sessionStorage.setItem('dt_refresh_progress', JSON.stringify({
      started_at: Date.now(),
      total, success, fail,
      done: success + fail, status: 'running'
    }));
    
    // 等 3 秒再刷新下一条
    await new Promise(r => setTimeout(r, 3000));
  }
  
  // 完成标记
  sessionStorage.setItem('dt_refresh_progress', JSON.stringify({
    started_at: Date.now(),
    total, success, fail,
    done: success + fail, status: 'completed'
  }));
  
  if (statusEl) statusEl.textContent = '✅ 完成: ' + success + ' 成功, ' + fail + ' 失败';
  if (btn) { btn.textContent = '🔄 刷新全部'; btn.style.background = ''; btn.style.color = ''; }
  window._dtRefreshing = false;
  
  // 刷新列表显示
  loadDyTracking();
}

// Modify updateBtn to also show selection buttons
function updateSelBtnDisplay() {
  const cbs = document.querySelectorAll('.dt-sel-cb');
  if (cbs.length > 0) {
    updateSelButtons();
  }
}

// Patch renderDyVideos to add selection listener
// Override the dt-sel-cb change handler


// ═══════════════════════════════════════════════════════════
// 逐条更新跟踪行（刷新全部时，不重绘整个列表）
// ═══════════════════════════════════════════════════════════

function updateTrackedRow(id, item) {
  if (!item) return;
  const div = document.getElementById('dtTrack_' + id);
  if (!div) return;
  const stats = item.stats || {};
  // 更新点赞/评论/收藏/时间
  const spans = div.querySelectorAll('span');
  if (spans.length >= 3) {
    spans[1].textContent = (stats.likes || 0) + '👍';
    spans[2].textContent = (stats.comments || 0) + '💬';
    if (spans.length >= 4) spans[3].textContent = (stats.collects || 0) + '⭐';
  }
  const timeEl = div.querySelector('.dt-track-time');
  if (timeEl) timeEl.textContent = (item.collected_at || '').slice(0, 19);
}
