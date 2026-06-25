/**
 * 评论互动视图 - 三Tab合一
 * 💬 定向评论 | ❤️ 点赞互动 | 📚 语料库
 *
 * Tab 切换不丢失账号选择状态，共用顶部选择器.
 *
 * 调用规范:
 *   POST /api/ops/run {type:'interact', accounts, params}
 *   POST /api/ops/run {type:'like', accounts, params}
 */

import { apiRequest, confirmExecute } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

let _selector = null;
let _activeTab = 'comment';

export async function loadView(container) {
  const uid = container.id || 'interact';
  const data = await apiRequest('/matrix/accounts');
  const allAccts = Array.isArray(data) ? data : (data.accounts || []);

  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:4px">💬 评论互动 <span style="font-size:10px;color:var(--text2);font-weight:400">定向评论 / 三级接力 / 点赞 / 语料库</span></div>
        <div id="acctList_${uid}" style="margin-bottom:6px"></div>
        <div id="selBar_${uid}" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:6px">
          <span id="selCount_${uid}" style="font-size:10px;color:var(--text2)">已选 0 个</span>
          <button onclick="window._ia_selAll_${uid}()" style="background:var(--bg3);border:1px solid var(--border);padding:2px 8px;border-radius:3px;cursor:pointer;font-size:10px">全选</button>
          <button onclick="window._ia_selNone_${uid}()" style="background:var(--bg3);border:1px solid var(--border);padding:2px 8px;border-radius:3px;cursor:pointer;font-size:10px">清空</button>
        </div>
        <!-- 三个 Tab -->
        <div style="display:flex;gap:0;border-bottom:1px solid var(--border);margin-bottom:8px">
          <button class="ia_tab" data-tab="comment" onclick="window._ia_switchTab_${uid}('comment')"
            style="padding:6px 16px;font-size:12px;cursor:pointer;border:none;border-bottom:2px solid var(--primary);background:transparent;color:var(--primary);font-weight:600">💬 定向评论</button>
          <button class="ia_tab" data-tab="like" onclick="window._ia_switchTab_${uid}('like')"
            style="padding:6px 16px;font-size:12px;cursor:pointer;border:none;border-bottom:2px solid transparent;background:transparent;color:var(--text2)">❤️ 点赞互动</button>
          <button class="ia_tab" data-tab="corpus" onclick="window._ia_switchTab_${uid}('corpus')"
            style="padding:6px 16px;font-size:12px;cursor:pointer;border:none;border-bottom:2px solid transparent;background:transparent;color:var(--text2)">📚 语料库</button>
        </div>
        <!-- Tab 内容容器 -->
        <div id="tabBody_${uid}"></div>
        <!-- 日志（跨 Tab 共享） -->
        <div id="log_${uid}" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:200px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;

  // 账号选择器（所有 Tab 共享）
  _selector = createAccountSelector(document.getElementById(`acctList_${uid}`), {
    accounts: allAccts,
    checkAll: false,
    height: '200px',
  });

  const updateCount = () => {
    document.getElementById(`selCount_${uid}`).textContent = '已选 ' + (_selector?.getCount() || 0) + ' 个';
  };
  updateCount();

  // 注册全局函数
  window[`_ia_selAll_${uid}`] = () => { _selector?.selectAll(true); updateCount(); };
  window[`_ia_selNone_${uid}`] = () => { _selector?.selectAll(false); updateCount(); };
  window[`_ia_switchTab_${uid}`] = (tab) => {
    _activeTab = tab;
    // 切换 Tab 高亮
    document.querySelectorAll(`#${container.id} .ia_tab`).forEach(b => {
      const active = b.dataset.tab === tab;
      b.style.borderBottomColor = active ? 'var(--primary)' : 'transparent';
      b.style.color = active ? 'var(--primary)' : 'var(--text2)';
      b.style.fontWeight = active ? '600' : '400';
    });
    renderTab(uid, tab);
  };

  // 默认加载第一个 Tab
  renderTab(uid, 'comment');
}

// ── Tab 渲染 ────────────────────────────────────────────

async function renderTab(uid, tab) {
  const body = document.getElementById(`tabBody_${uid}`);
  if (!body) return;

  if (tab === 'comment') renderCommentTab(uid, body);
  else if (tab === 'like') renderLikeTab(uid, body);
  else if (tab === 'corpus') renderCorpusTab(uid, body);
}

// ── Tab 1: 定向评论 ─────────────────────────────────────

function renderCommentTab(uid, body) {
  body.innerHTML = `
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
      <textarea id="ic_urls_${uid}" placeholder="视频链接（每行一个，支持多个）" rows="3"
        style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
      <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:140px">
        <div style="display:flex;gap:4px">
          <select id="ic_strategy_${uid}" style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
            <option value="comment">💬 定向评论</option>
            <option value="chain">🔗 三级接力</option>
            <option value="hot">🔥 热评互动</option>
          </select>
          <select id="ic_dir_${uid}" style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
            <option value="">自动方向</option>
            <option value="称赞">👍 称赞</option><option value="提问">🤔 提问</option>
            <option value="共鸣">💗 共鸣</option><option value="感慨">😌 感慨</option>
          </select>
        </div>
        <div style="display:flex;gap:4px">
          <select id="ic_corpus_${uid}" style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
            <option value="">🎲 随机语料</option>
            <option value="food">🍜 美食</option><option value="travel">✈️ 旅行</option>
            <option value="tech">💻 科技</option><option value="lifestyle">🌿 生活</option>
            <option value="emotion">💛 情感</option>
          </select>
          <input id="ic_comment_${uid}" placeholder="或手动写评论" style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
        </div>
        <button onclick="window._ia_runComment('${uid}')" style="background:var(--primary);color:#fff;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 执行评论</button>
        <button onclick="window._ia_previewComment('${uid}')" style="background:var(--bg3);border:1px solid var(--border);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">🔍 预检</button>
      </div>
    </div>`;
}

// ── Tab 2: 点赞互动 ─────────────────────────────────────

function renderLikeTab(uid, body) {
  body.innerHTML = `
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
      <div style="flex:1;min-width:200px">
        <div style="font-size:11px;color:var(--text2);margin-bottom:4px">操作类型</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <label style="font-size:11px;display:flex;align-items:center;gap:4px;cursor:pointer">
            <input type="checkbox" id="il_likeVideo_${uid}" checked> ❤️ 点赞视频
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px;cursor:pointer">
            <input type="checkbox" id="il_likeComment_${uid}"> 💬 点赞评论
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px;cursor:pointer">
            <input type="checkbox" id="il_follow_${uid}"> 👤 关注博主
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px;cursor:pointer">
            <input type="checkbox" id="il_collect_${uid}"> ⭐ 收藏视频
          </label>
        </div>
      </div>
      <div style="flex:1;min-width:200px">
        <div style="font-size:11px;color:var(--text2);margin-bottom:4px">视频链接（可选）</div>
        <input id="il_url_${uid}" placeholder="留空则浏览推荐页操作" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px">
        <button onclick="window._ia_runLike('${uid}')" style="margin-top:6px;background:var(--primary);color:#fff;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600;width:100%">🚀 执行选中账号</button>
      </div>
    </div>`;
}

// ── Tab 3: 语料库 ───────────────────────────────────────

async function renderCorpusTab(uid, body) {
  body.innerHTML = '<div class="loading">⏳ 加载语料库...</div>';
  try {
    const r = await apiRequest('/matrix/corpus');
    const d = r;
    const cats = d.categories || d.corpus || [];

    // 按平台分组
    const groups = {};
    cats.forEach(c => {
      const p = c.platform === 'xiaohongshu' ? '📕 小红书' : '🎵 抖音';
      if (!groups[p]) groups[p] = [];
      groups[p].push(c);
    });

    let html = `<div style="font-size:12px;color:var(--text2);margin-bottom:6px">共 ${cats.length} 个分类 · ${d.total_comments || 0} 条评论</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px">`;

    Object.entries(groups).forEach(([platform, items]) => {
      html += `<div style="background:var(--bg2);border-radius:6px;padding:10px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:12px;margin-bottom:6px">${platform}</div>
        <table style="width:100%;font-size:10px;border-collapse:collapse">
        <thead><tr><th style="text-align:left;padding:2px 4px;border-bottom:1px solid var(--border);color:var(--text2);font-weight:400">分类</th>
        <th style="padding:2px 4px;border-bottom:1px solid var(--border);color:var(--text2);font-weight:400;text-align:center">条数</th></tr></thead>
        <tbody>${items.map(c => `<tr>
          <td style="padding:2px 4px;border-bottom:1px solid var(--border)">${c.name || c.category || '?'}</td>
          <td style="padding:2px 4px;border-bottom:1px solid var(--border);text-align:center">${c.count || c.comment_count || 0}</td>
        </tr>`).join('')}</tbody></table>
      </div>`;
    });

    // 三级接力语料展示
    html += `<div style="background:var(--bg2);border-radius:6px;padding:10px;border:1px solid var(--border);grid-column:1/-1">
      <div style="font-weight:600;font-size:12px;margin-bottom:6px">🔗 三级接力语料</div>
      <div style="font-size:10px;color:var(--text2);margin-bottom:4px">评论→回复→再回复，5 个分类可用。在「定向评论」Tab 选择"三级接力"策略即可使用</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <span style="background:var(--bg3);padding:2px 8px;border-radius:3px;font-size:10px">🍜 美食 2组</span>
        <span style="background:var(--bg3);padding:2px 8px;border-radius:3px;font-size:10px">✈️ 旅行 2组</span>
        <span style="background:var(--bg3);padding:2px 8px;border-radius:3px;font-size:10px">💻 科技 1组</span>
        <span style="background:var(--bg3);padding:2px 8px;border-radius:3px;font-size:10px">🌿 生活 1组</span>
        <span style="background:var(--bg3);padding:2px 8px;border-radius:3px;font-size:10px">💛 情感 1组</span>
      </div>
    </div>`;

    html += '</div>';
    body.innerHTML = html;
  } catch (e) {
    body.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}

// ── 执行: 定向评论 ───────────────────────────────────────

window._ia_previewComment = async function(uid) {
  const log = document.getElementById(`log_${uid}`);
  const selected = _selector?.getSelected() || [];
  const urlsText = document.getElementById(`ic_urls_${uid}`)?.value;
  if (!urlsText?.trim()) { log.textContent = '❌ 请填写视频链接\n'; return; }
  if (!selected.length) { log.textContent = '❌ 请选择账号\n'; return; }
  log.textContent = '🔍 预检...\n';
  try {
    const d = await apiRequest('/ops/run', {
      method: 'POST',
      body: JSON.stringify({
        type: 'interact',
        accounts: selected.map(s => s.id),
        params: {
          url: urlsText.split('\n').map(u=>u.trim()).filter(Boolean)[0],
          strategy: document.getElementById(`ic_strategy_${uid}`)?.value || 'comment',
          corpus: document.getElementById(`ic_corpus_${uid}`)?.value || '',
          rounds: 1,
          dry_run: true,
        },
      }),
    });
    const cmds = d.commands || [];
    log.textContent = `✅ 预检完成 | 策略: ${document.getElementById(`ic_strategy_${uid}`)?.value || 'comment'}\n`;
    log.textContent += `   账号: ${selected.length} 个\n`;
    cmds.forEach(c => log.textContent += `   ${c.machine}: ${c.command || ''}\n`);
  } catch(e) { log.textContent += '❌ ' + e.message + '\n'; }
};

window._ia_runComment = async function(uid) {
  const log = document.getElementById(`log_${uid}`);
  const selected = _selector?.getSelected() || [];
  const urlsText = document.getElementById(`ic_urls_${uid}`)?.value;
  if (!urlsText?.trim()) { log.textContent = '❌ 请填写视频链接\n'; return; }
  if (!selected.length) { log.textContent = '❌ 请选择账号\n'; return; }
  const urls = urlsText.split('\n').map(u => u.trim()).filter(Boolean);
  const strategy = document.getElementById(`ic_strategy_${uid}`)?.value || 'comment';
  const dir = document.getElementById(`ic_dir_${uid}`)?.value || '';
  const corpus = document.getElementById(`ic_corpus_${uid}`)?.value || '';
  const customText = document.getElementById(`ic_comment_${uid}`)?.value?.trim() || '';

  const label = {comment:'定向评论', chain:'三级接力', hot:'热评互动'}[strategy] || strategy;
  const detail = `策略: ${label}\n链接: ${urls.join('\n')}\n方向: ${dir || '自动'}\n语料: ${corpus || '随机'}\n自定义: ${customText || '无'}`;
  if (!await confirmExecute(`${label} ${selected.length} 个账号 × ${urls.length} 个视频`, detail)) return;

  log.textContent = `🚀 ${label} ${selected.length} 个账号...\n`;
  // 按机器分组
  const byMachine = {};
  selected.forEach(s => {
    const m = s.machine || 'unknown';
    if (!byMachine[m]) byMachine[m] = [];
    byMachine[m].push(s.id);
  });

  let done = 0, total = Object.keys(byMachine).length, ok = 0;
  for (const [machine, ids] of Object.entries(byMachine)) {
    for (const url of urls) {
      try {
        const d = await apiRequest('/ops/run', {
          method: 'POST',
          body: JSON.stringify({
            type: 'interact',
            accounts: ids,
            params: { url, strategy, direction: dir, corpus, rounds: 1 },
          }),
        });
        done++; ok += d.status === 'accepted' ? 1 : 0;
        log.textContent += `📦 [${machine}/${url.slice(0,30)}] ${d.status || 'OK'} (${done}/${total*urls.length})\n`;
      } catch(e) { log.textContent += `❌ [${machine}] ${e.message}\n`; }
    }
  }
  log.textContent += `\n✅ ${ok}/${done} 提交完成\n`;
};

// ── 执行: 点赞互动 ──────────────────────────────────────

window._ia_runLike = async function(uid) {
  const log = document.getElementById(`log_${uid}`);
  const selected = _selector?.getSelected() || [];
  if (!selected.length) { log.textContent = '❌ 请选择账号\n'; return; }

  const likeVideo = document.getElementById(`il_likeVideo_${uid}`)?.checked;
  const likeComment = document.getElementById(`il_likeComment_${uid}`)?.checked;
  const follow = document.getElementById(`il_follow_${uid}`)?.checked;
  const collect = document.getElementById(`il_collect_${uid}`)?.checked;
  const url = document.getElementById(`il_url_${uid}`)?.value?.trim();

  const ops = [];
  if (likeVideo) ops.push('点赞视频');
  if (likeComment) ops.push('点赞评论');
  if (follow) ops.push('关注博主');
  if (collect) ops.push('收藏视频');
  if (!ops.length) { log.textContent = '❌ 请至少选择一种操作\n'; return; }

  const detail = `操作: ${ops.join(', ')}\n链接: ${url || '推荐页随机'}`;
  if (!await confirmExecute(`${selected.length} 个账号执行点赞互动`, detail)) return;

  log.textContent = `🚀 ${selected.length} 个账号执行 ${ops.join('/')}...\n`;

  // 按机器分组
  const byMachine = {};
  selected.forEach(s => {
    const m = s.machine || 'unknown';
    if (!byMachine[m]) byMachine[m] = [];
    byMachine[m].push(s.id);
  });

  const blueprint = likeComment ? 'interact_like' : (collect ? 'interact_like' : 'like');
  let done = 0, total = Object.keys(byMachine).length;
  for (const [machine, ids] of Object.entries(byMachine)) {
    try {
      const d = await apiRequest('/ops/run', {
        method: 'POST',
        body: JSON.stringify({
          type: url ? 'interact' : 'like',
          accounts: ids,
          params: { url, blueprint, rounds: 1 },
        }),
      });
      done++;
      log.textContent += `📦 [${machine}] ${d.status || 'OK'} (${done}/${total})\n`;
    } catch(e) { log.textContent += `❌ [${machine}] ${e.message}\n`; }
  }
  log.textContent += `\n✅ 完成\n`;
};
