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
  const uid = (container.id || 'interact').replace(/-/g, '_');
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

// ── Tab 3: 语料库管理 ───────────────────────────────────────

async function renderCorpusTab(uid, body) {
  body.innerHTML = '<div class="loading">⏳ 加载语料库...</div>';
  try {
    const r = await apiRequest('/matrix/corpus');
    const cats = r.categories || [];
    const total = r.total_comments || 0;

    const platforms = { douyin: '🎵 抖音', xiaohongshu: '📕 小红书' };
    const groups = { douyin: [], xiaohongshu: [] };
    cats.forEach(c => { if (groups[c.platform]) groups[c.platform].push(c); });

    let html = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
      <span style="font-size:12px;color:var(--text2)">共 ${cats.length} 个分类 · ${total} 条评论</span>
      <span style="font-size:10px;color:var(--text2)">点分类行展开管理</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:8px" id="corpusGrid_${uid}">`;

    Object.entries(groups).forEach(([platKey, items]) => {
      if (!items.length) return;
      const platLabel = platforms[platKey] || platKey;
      html += `<div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:12px;margin-bottom:6px">${platLabel}</div>
        ${items.map((c, ci) => `
          <div style="border:1px solid var(--border);border-radius:4px;margin-bottom:3px;overflow:hidden">
            <div onclick="_ia_toggleCorpusCat_${uid}('${platKey}','${c.name}',${ci})"
              style="display:flex;align-items:center;gap:4px;padding:4px 6px;background:var(--bg3);cursor:pointer;font-size:10px;user-select:none">
              <span id="corpusArrow_${uid}_${platKey}_${ci}" style="font-size:8px;opacity:.6">▶</span>
              <span style="flex:1"><strong>${c.label || c.name}</strong></span>
              <span style="color:var(--text2)">${c.count}条</span>
              <span style="color:var(--text2);font-size:9px">权重${c.weight}</span>
            </div>
            <div id="corpusBody_${uid}_${platKey}_${ci}" style="display:none;padding:4px 6px"></div>
          </div>
        `).join('')}
        <!-- 新增批量导入 -->
        <div style="margin-top:4px;display:flex;gap:4px">
          <textarea id="corpusImport_${uid}_${platKey}" placeholder="批量导入评论（每行一条）" rows="2"
            style="flex:1;font-size:10px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;padding:3px 5px;resize:vertical"></textarea>
          <button onclick="_ia_batchImportCorpus_${uid}('${platKey}')"
            style="background:var(--primary);color:#fff;border:none;padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px;white-space:nowrap">📥 导入</button>
        </div>
      </div>`;
    });

    html += '</div>';

    // 三阶场景语料
    html += `<div style="margin-top:8px;background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border)">
      <div style="font-weight:600;font-size:12px;margin-bottom:6px">🔗 三阶接力语料 <span style="font-size:10px;color:var(--text2);font-weight:400">一阶(评论) → 二阶(回复) → 三阶(再回复)</span></div>
      <div style="font-size:10px;color:var(--text2);margin-bottom:4px">在「定向评论」Tab 选"三级接力"策略时使用</div>
      <div id="corpusScenes_${uid}" style="font-size:10px;color:var(--text2)">⏳ 加载场景数据...</div>
    </div>`;

    body.innerHTML = html;

    // 加载三阶数据
    try {
      const sr = await apiRequest('/matrix/corpus/scenes');
      const groups = sr.groups || {};
      const sceneEl = document.getElementById(`corpusScenes_${uid}`);
      if (sceneEl) {
        let sh = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px">';
        const labels = { first_comment: '💬 一阶(评论)', reply: '💬 二阶(回复)', re_reply: '💬 三阶(再回复)' };
        for (const [key, label] of Object.entries(labels)) {
          const items = groups[key] || [];
          sh += `<div style="background:var(--bg3);border-radius:6px;padding:6px">
            <div style="font-weight:600;font-size:11px;margin-bottom:3px">${label}</div>
            ${items.length ? items.map(s => `<span style="display:inline-block;background:var(--bg2);padding:1px 5px;border-radius:3px;margin:1px;font-size:9px">${s.persona}</span>`).join('') : '<span style="color:var(--text2);font-size:9px">暂无数据，可在 YAML 中配置</span>'}
          </div>`;
        }
        sh += '</div>';
        sceneEl.innerHTML = sh;
      }
    } catch(e) { /* ignore */ }

    // 注册展开/折叠函数
    window[`_ia_toggleCorpusCat_${uid}`] = async (platKey, catName, ci) => {
      const bodyEl = document.getElementById(`corpusBody_${uid}_${platKey}_${ci}`);
      const arrow = document.getElementById(`corpusArrow_${uid}_${platKey}_${ci}`);
      if (!bodyEl) return;
      if (bodyEl.style.display !== 'none') {
        bodyEl.style.display = 'none';
        if (arrow) arrow.textContent = '▶';
        return;
      }
      bodyEl.innerHTML = '<div style="font-size:10px;color:var(--text2)">⏳ 加载中...</div>';
      bodyEl.style.display = 'block';
      if (arrow) arrow.textContent = '▼';
      try {
        const detail = await apiRequest(`/matrix/corpus/category?platform=${platKey}&category=${encodeURIComponent(catName)}`);
        const comments = detail.comments || [];
        let dh = '<div style="font-size:10px">';
        if (!comments.length) {
          dh += '<div style="color:var(--text2);padding:2px 0">暂无评论，在下方批量导入</div>';
        } else {
          comments.forEach((text, idx) => {
            const display = text.length > 60 ? text.slice(0, 58) + '…' : text;
            dh += `<div style="display:flex;align-items:center;gap:4px;padding:2px 0;border-bottom:1px solid var(--border)">
              <span style="flex:1;word-break:break-all">${display}</span>
              <button onclick="_ia_delCorpus_${uid}('${platKey}','${catName.replace(/'/g,"\\'")}',${idx})" style="background:none;border:none;color:var(--red);cursor:pointer;font-size:10px;padding:0 2px" title="删除">✕</button>
            </div>`;
          });
        }
        // 单条新增
        dh += `<div style="display:flex;gap:4px;margin-top:4px">
          <input id="corpusAddInput_${uid}_${platKey}_${ci}" placeholder="输入新评论..."
            style="flex:1;font-size:10px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;padding:3px 5px">
          <button onclick="_ia_addCorpus_${uid}('${platKey}','${catName.replace(/'/g,"\\'")}',${ci})"
            style="background:var(--primary);color:#fff;border:none;padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">➕ 添加</button>
        </div>`;
        dh += '</div>';
        bodyEl.innerHTML = dh;
      } catch(e) {
        bodyEl.innerHTML = `<div style="color:var(--red);font-size:10px">❌ ${e.message}</div>`;
      }
    };

    // 单条添加
    window[`_ia_addCorpus_${uid}`] = async (platKey, catName, ci) => {
      const input = document.getElementById(`corpusAddInput_${uid}_${platKey}_${ci}`);
      const text = input?.value?.trim();
      if (!text) return;
      try {
        await apiRequest('/matrix/corpus/add', {
          method: 'POST',
          body: JSON.stringify({ platform: platKey, category: catName, text }),
        });
        input.value = '';
        // 刷新此分类
        const fn = window[`_ia_toggleCorpusCat_${uid}`];
        if (fn) fn(platKey, catName, ci);
      } catch(e) { alert('❌ ' + e.message); }
    };

    // 删除评论
    window[`_ia_delCorpus_${uid}`] = async (platKey, catName, idx) => {
      if (!confirm('确定删除这条评论？')) return;
      try {
        await apiRequest('/matrix/corpus/delete', {
          method: 'POST',
          body: JSON.stringify({ platform: platKey, category: catName, index: idx }),
        });
        renderCorpusTab(uid, body); // 刷新整个页面
      } catch(e) { alert('❌ ' + e.message); }
    };

    // 批量导入
    window[`_ia_batchImportCorpus_${uid}`] = async (platKey) => {
      const ta = document.getElementById(`corpusImport_${uid}_${platKey}`);
      const lines = ta?.value?.split('\n').map(l => l.trim()).filter(Boolean);
      if (!lines || !lines.length) { alert('请先在文本框中输入评论（每行一条）'); return; }
      // 弹窗让用户选分类
      const cats = groups[platKey] || [];
      if (!cats.length) { alert('该平台暂无分类'); return; }
      const catList = cats.map((c, i) => `${i+1}. ${c.label || c.name}`).join('\n');
      const choice = prompt(`选择导入到哪个分类？\n${catList}\n\n输入编号 (1-${cats.length}):`);
      const idx = parseInt(choice) - 1;
      if (isNaN(idx) || idx < 0 || idx >= cats.length) { alert('无效选择'); return; }
      const catName = cats[idx].name;
      if (!confirm(`向 ${platKey}/${catName} 导入 ${lines.length} 条评论？`)) return;
      try {
        const r = await apiRequest('/matrix/corpus/batch-add', {
          method: 'POST',
          body: JSON.stringify({ platform: platKey, category: catName, texts: lines }),
        });
        if (r.status === 'ok') {
          ta.value = '';
          renderCorpusTab(uid, body); // 刷新
        } else {
          alert('❌ ' + (r.error || '导入失败'));
        }
      } catch(e) { alert('❌ ' + e.message); }
    };
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
