/**
 * 🎯 批量互动 v2 — 导入链接 → 按百分比执行多动作
 *
 * 动作（每项带 0-100% 滑条）:
 *   👍 点赞视频  |  ⭐ 收藏视频  |  💬 评论回复  |  👤 关注作者
 *   🎬 浏览其他作品（含仅浏览 / 互动操作 两种模式）
 *
 * API: POST /api/ops/run {type:'interact', accounts, params:{urls, actions, interval, corpus}}
 */

import { apiRequest, confirmExecute } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

let _selector = null;
let _parsedItems = [];  // [{title, url}]

export async function loadView(container) {
  const uid = (container.id || 'interact').replace(/-/g, '_');
  const data = await apiRequest('/v2/accounts');
  const allAccts = Array.isArray(data) ? data : (data.accounts || []);

  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:4px">🎯 批量互动 <span style="font-size:10px;color:var(--text2);font-weight:400">导入链接 → 按百分比执行多动作</span></div>

        <!-- 账号选择器 -->
        <div id="acctList_${uid}" style="margin-bottom:6px"></div>

        <!-- 导入区 -->
        <div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:8px">
          <div style="font-size:11px;color:var(--text2);margin-bottom:4px">📋 粘贴标题+链接（每对两行，自动识别）</div>
          <textarea id="ia_input_${uid}" placeholder="${'例如:\n标题: 这个视频太有趣了\nhttps://www.douyin.com/video/xxx\n标题: 又一个好视频\nhttps://www.douyin.com/video/yyy'}"
            rows="4" style="width:100%;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px;font-family:monospace;resize:vertical">${'例如:\n标题: 这个视频太有趣了\nhttps://www.douyin.com/video/xxx\n标题: 又一个好视频\nhttps://www.douyin.com/video/yyy'}</textarea>
          <div style="display:flex;gap:4px;margin-top:4px;flex-wrap:wrap;align-items:center">
            <button onclick="window._ia_parse_${uid}()" style="background:var(--primary);color:#fff;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">🔍 解析</button>
            <button onclick="window._ia_fetchTitles_${uid}()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px" title="获取无标题链接的页面标题">🏷️ 获取标题</button>
            <span id="ia_parsedCount_${uid}" style="font-size:10px;color:var(--text2)"></span>
            <span id="ia_listToggle_${uid}" style="display:none;font-size:9px;color:var(--text2);cursor:pointer" onclick="window._ia_toggleList_${uid}()">展开列表 ▼</span>
          </div>
          <div id="ia_parsedList_${uid}" style="display:none;font-size:10px;margin-top:4px;max-height:120px;overflow-y:auto"></div>
        </div>

        <!-- 动作滑条 -->
        <div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:8px">
          <div style="font-size:11px;color:var(--text2);margin-bottom:6px">🎚️ 互动动作（滑条=执行概率，100%=每条都做，0%=不做）</div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;font-size:11px">
            <div style="display:flex;align-items:center;gap:4px">
              <span style="width:14px">👍</span>
              <span style="width:50px">点赞</span>
              <input type="range" id="ia_rate_like_${uid}" min="0" max="100" value="80" style="flex:1;height:4px"
                oninput="document.getElementById('ia_val_like_${uid}').textContent=this.value+'%'">
              <span id="ia_val_like_${uid}" style="width:36px;text-align:right;font-size:10px;color:var(--text2);font-family:monospace">80%</span>
            </div>
            <div style="display:flex;align-items:center;gap:4px">
              <span style="width:14px">⭐</span>
              <span style="width:50px">收藏</span>
              <input type="range" id="ia_rate_collect_${uid}" min="0" max="100" value="100" style="flex:1;height:4px"
                oninput="document.getElementById('ia_val_collect_${uid}').textContent=this.value+'%'">
              <span id="ia_val_collect_${uid}" style="width:36px;text-align:right;font-size:10px;color:var(--text2);font-family:monospace">100%</span>
            </div>
            <div style="display:flex;align-items:center;gap:4px">
              <span style="width:14px">💬</span>
              <span style="width:50px">评论</span>
              <input type="range" id="ia_rate_comment_${uid}" min="0" max="100" value="30" style="flex:1;height:4px"
                oninput="document.getElementById('ia_val_comment_${uid}').textContent=this.value+'%'">
              <span id="ia_val_comment_${uid}" style="width:36px;text-align:right;font-size:10px;color:var(--text2);font-family:monospace">30%</span>
            </div>
            <div style="display:flex;align-items:center;gap:4px">
              <span style="width:14px">👤</span>
              <span style="width:50px">关注</span>
              <input type="range" id="ia_rate_follow_${uid}" min="0" max="100" value="20" style="flex:1;height:4px"
                oninput="document.getElementById('ia_val_follow_${uid}').textContent=this.value+'%'">
              <span id="ia_val_follow_${uid}" style="width:36px;text-align:right;font-size:10px;color:var(--text2);font-family:monospace">20%</span>
            </div>
          </div>

          <!-- 浏览其他作品（可折叠） -->
          <div style="margin-top:6px;border-top:1px solid var(--border);padding-top:6px">
            <div onclick="window._ia_toggleBrowse_${uid}()" style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:11px;user-select:none">
              <span id="ia_browseArrow_${uid}">▶</span>
              <span>🎬 浏览作者其他作品</span>
              <span id="ia_browseSummary_${uid}" style="font-size:9px;color:var(--text2)"></span>
            </div>
            <div id="ia_browseBody_${uid}" style="display:none;margin-top:4px;padding-left:16px">
              <div style="display:flex;align-items:center;gap:4px;margin-bottom:4px;font-size:10px">
                <span>触发概率</span>
                <input type="range" id="ia_rate_browse_${uid}" min="0" max="100" value="40" style="flex:1;height:4px;max-width:120px"
                  oninput="window._ia_updateBrowseSummary_${uid}()">
                <span id="ia_val_browse_${uid}" style="width:36px;font-family:monospace">40%</span>
                <span style="margin-left:8px">浏览篇数</span>
                <input id="ia_browseCount_${uid}" type="number" min="1" max="20" value="3" style="width:40px;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px">
              </div>
              <div style="font-size:10px;color:var(--text2);margin-bottom:2px">操作模式</div>
              <div style="display:flex;gap:8px;font-size:10px">
                <label style="cursor:pointer"><input type="radio" name="ia_browseMode_${uid}" value="view" onchange="window._ia_updateBrowseSummary_${uid}()"> 仅浏览</label>
                <label style="cursor:pointer"><input type="radio" name="ia_browseMode_${uid}" value="interact" checked onchange="window._ia_updateBrowseSummary_${uid}()"> 互动操作（复用上方百分数）</label>
              </div>
            </div>
          </div>
        </div>

        <!-- 执行区 -->
        <div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap;margin-bottom:6px">
          <span style="font-size:10px;color:var(--text2)">执行间隔</span>
          <input id="ia_interval_${uid}" type="text" value="300-600" style="width:70px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px" title="每步间隔(秒)">
          <span style="font-size:9px;color:var(--text2)">秒</span>
          <span style="flex:1"></span>
          <button onclick="window._ia_exec_${uid}()" style="background:#22c55e;color:#000;border:none;padding:5px 16px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 执行所选互动</button>
        </div>

        <!-- 📊 互动策略（防封号） -->
        <div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:8px">
          <div style="font-size:11px;color:var(--text2);margin-bottom:6px">📊 互动策略 <span style="font-size:9px;color:var(--text2)">（账号轮动 + 评论配额 + 限流，模拟真人防封号）</span></div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;font-size:11px">
            <div style="display:flex;align-items:center;gap:4px">
              <span>💬 每视频评论上限</span>
              <input type="number" id="ia_cpv_${uid}" min="0" max="20" value="5" style="width:44px;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px" title="每条视频最多 N 条评论，超出则随机跳过（0=不评论）">
              <span style="font-size:9px;color:var(--text2)">条</span>
            </div>
            <div style="display:flex;align-items:center;gap:4px">
              <span>📮 每账号评论日上限</span>
              <input type="number" id="ia_cdl_${uid}" min="1" max="100" value="12" style="width:44px;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px" title="每个评论账号每天最多评论 N 条（防封号）">
              <span style="font-size:9px;color:var(--text2)">条</span>
            </div>
            <div style="display:flex;align-items:center;gap:4px">
              <span>👍 点赞组账号数</span>
              <input type="number" id="ia_glk_${uid}" min="0" max="100" value="30" style="width:44px;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px">
            </div>
            <div style="display:flex;align-items:center;gap:4px">
              <span>💬 评论组账号数</span>
              <input type="number" id="ia_gcm_${uid}" min="0" max="100" value="5" style="width:44px;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px">
            </div>
            <div style="display:flex;align-items:center;gap:4px">
              <span>⭐ 收藏组账号数</span>
              <input type="number" id="ia_gcl_${uid}" min="0" max="100" value="5" style="width:44px;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px">
            </div>
            <div style="display:flex;align-items:center;gap:4px">
              <span>🏃 执行节奏</span>
              <select id="ia_pace_${uid}" style="background:var(--bg);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px">
                <option value="loose">🐢 宽松（慢，安全）</option>
                <option value="compact">⚡ 紧凑（快，风险高）</option>
              </select>
            </div>
          </div>
        </div>

        <!-- 日志 -->
        <div id="log_${uid}" style="font-size:10px;background:var(--bg);border-radius:6px;padding:6px;max-height:200px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;

  // ── 账号选择器 ──
  _selector = createAccountSelector(document.getElementById(`acctList_${uid}`), {
    accounts: allAccts,
    checkAll: false,
    height: '200px',
  });

  // ── 注册全局函数 ──
  const self = uid;
  window[`_ia_parse_${self}`] = () => _ia_parse(self);
  window[`_ia_fetchTitles_${self}`] = () => _ia_fetchTitles(self);
  window[`_ia_toggleList_${self}`] = () => _ia_toggleList(self);
  window[`_ia_toggleBrowse_${self}`] = () => _ia_toggleBrowse(self);
  window[`_ia_updateBrowseSummary_${self}`] = () => _ia_updateBrowseSummary(self);
  window[`_ia_exec_${self}`] = () => _ia_exec(self);
}

// ── 解析标题+链接 ──

function _ia_parse(uid) {
  const text = document.getElementById(`ia_input_${uid}`)?.value || '';
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  const items = [];
  let currentTitle = '';

  for (const line of lines) {
    // 标题行
    if (line.startsWith('标题:') || line.startsWith('标题：') ||
        line.startsWith('title:') || line.startsWith('Title:')) {
      currentTitle = line.replace(/^标题[：:]\s*/i, '').replace(/^title[：:]\s*/i, '').trim();
      continue;
    }
    // 链接行
    if (line.match(/^https?:\/\//)) {
      items.push({ title: currentTitle || '无标题', url: line.split(/[?\s]/)[0] });
      currentTitle = '';
      continue;
    }
    // 其他格式：可能是标题本身
    if (!line.startsWith('http') && line.length > 2) {
      currentTitle = line;
      continue;
    }
    if (line.match(/^https?:\/\//)) {
      items.push({ title: currentTitle || '无标题', url: line.split(/[?\s]/)[0] });
      currentTitle = '';
    }
  }

  _parsedItems = items;
  const countEl = document.getElementById(`ia_parsedCount_${uid}`);
  const listEl = document.getElementById(`ia_parsedList_${uid}`);
  const toggleEl = document.getElementById(`ia_listToggle_${uid}`);

  if (countEl) countEl.textContent = `✅ 解析到 ${items.length} 条内容`;
  if (toggleEl) {
    toggleEl.style.display = items.length ? 'inline' : 'none';
    toggleEl.textContent = `展开列表 ▼`;
  }
  if (listEl) {
    listEl.style.display = 'none';
    listEl.innerHTML = items.map((item, i) =>
      `<div style="padding:2px 4px;border-bottom:1px solid var(--border);display:flex;gap:4px">
        <span style="color:var(--text2);width:20px;flex-shrink:0">${i+1}.</span>
        <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${item.title}</span>
        <span style="color:var(--text2);font-size:9px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:200px">${item.url}</span>
      </div>`
    ).join('');
  }
}

// ── 获取标题 ──

async function _ia_fetchTitles(uid) {
  const countEl = document.getElementById(`ia_parsedCount_${uid}`);
  if (!_parsedItems.length) { if (countEl) countEl.textContent = '⚠️ 请先解析链接'; return; }

  // 找出没有标题的条目
  const noTitle = _parsedItems.filter(item => !item.title || item.title === '无标题');
  if (!noTitle.length) { if (countEl) countEl.textContent = '✅ 已有标题，无需获取'; return; }

  if (countEl) countEl.textContent = `⏳ 获取 ${noTitle.length} 个标题...`;
  let fetched = 0;

  for (const item of noTitle) {
    try {
      const r = await fetch(`/api/scrape/title?url=${encodeURIComponent(item.url)}`);
      const d = await r.json();
      if (d.title) {
        item.title = d.title;
        fetched++;
      }
    } catch (e) { /* 忽略单个失败 */ }
  }

  // 刷新列表显示
  const listEl = document.getElementById(`ia_parsedList_${uid}`);
  if (listEl) {
    listEl.innerHTML = _parsedItems.map((item, i) =>
      `<div style="padding:2px 4px;border-bottom:1px solid var(--border);display:flex;gap:4px">
        <span style="color:var(--text2);width:20px;flex-shrink:0">${i+1}.</span>
        <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${item.title}</span>
        <span style="color:var(--text2);font-size:9px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:200px">${item.url}</span>
      </div>`
    ).join('');
  }

  if (countEl) countEl.textContent = `✅ 获取 ${fetched}/${noTitle.length} 个标题`;
}

function _ia_toggleList(uid) {
  const el = document.getElementById(`ia_parsedList_${uid}`);
  const toggle = document.getElementById(`ia_listToggle_${uid}`);
  if (!el || !toggle) return;
  const isHidden = el.style.display === 'none';
  el.style.display = isHidden ? 'block' : 'none';
  toggle.textContent = isHidden ? '收起列表 ▲' : '展开列表 ▼';
}

// ── 浏览设置展开/收起 ──

function _ia_toggleBrowse(uid) {
  const body = document.getElementById(`ia_browseBody_${uid}`);
  const arrow = document.getElementById(`ia_browseArrow_${uid}`);
  if (!body || !arrow) return;
  const isHidden = body.style.display === 'none';
  body.style.display = isHidden ? 'block' : 'none';
  arrow.textContent = isHidden ? '▼' : '▶';
  if (isHidden) _ia_updateBrowseSummary(uid);
}

function _ia_updateBrowseSummary(uid) {
  const rate = parseInt(document.getElementById(`ia_rate_browse_${uid}`)?.value || '0');
  const count = document.getElementById(`ia_browseCount_${uid}`)?.value || '3';
  const modeEl = document.querySelector(`input[name="ia_browseMode_${uid}"]:checked`);
  const mode = modeEl?.value || 'interact';
  const summary = document.getElementById(`ia_browseSummary_${uid}`);
  const val = document.getElementById(`ia_val_browse_${uid}`);
  if (val) val.textContent = rate + '%';
  if (summary) {
    const modeLabel = mode === 'view' ? '仅浏览' : '互动操作';
    summary.textContent = ` ${rate}% × ${count}篇 (${modeLabel})`;
  }
}

// ── 执行 ──

async function _ia_exec(uid) {
  const log = document.getElementById(`log_${uid}`);
  const selected = _selector?.getSelected() || [];

  if (!_parsedItems.length) { log.textContent = '❌ 请先解析内容链接\n'; return; }
  if (!selected.length) { log.textContent = '❌ 请选择账号\n'; return; }

  // 收集参数
  const urls = _parsedItems;
  const actions = {
    like: parseInt(document.getElementById(`ia_rate_like_${uid}`)?.value || '0'),
    collect: parseInt(document.getElementById(`ia_rate_collect_${uid}`)?.value || '0'),
    comment: parseInt(document.getElementById(`ia_rate_comment_${uid}`)?.value || '0'),
    follow: parseInt(document.getElementById(`ia_rate_follow_${uid}`)?.value || '0'),
    browse: {
      rate: parseInt(document.getElementById(`ia_rate_browse_${uid}`)?.value || '0'),
      count: parseInt(document.getElementById(`ia_browseCount_${uid}`)?.value || '3'),
      mode: document.querySelector(`input[name="ia_browseMode_${uid}"]:checked`)?.value || 'interact',
    },
  };
  const interval = document.getElementById(`ia_interval_${uid}`)?.value?.trim() || '300-600';

  // 互动策略参数（防封号）
  const strategy = {
    comment_per_video: parseInt(document.getElementById(`ia_cpv_${uid}`)?.value || '5'),
    comment_daily_limit: parseInt(document.getElementById(`ia_cdl_${uid}`)?.value || '12'),
    group_like: parseInt(document.getElementById(`ia_glk_${uid}`)?.value || '30'),
    group_comment: parseInt(document.getElementById(`ia_gcm_${uid}`)?.value || '5'),
    group_collect: parseInt(document.getElementById(`ia_gcl_${uid}`)?.value || '5'),
    pace: document.getElementById(`ia_pace_${uid}`)?.value || 'loose',
  };

  // 确认
  let detail = `链接: ${urls.length} 条\n`;
  const actionLabels = [];
  for (const [k, v] of Object.entries(actions)) {
    if (k === 'browse') {
      if (v.rate > 0) actionLabels.push(`🎬 浏览 ${v.rate}%×${v.count}篇 (${v.mode==='view'?'仅浏览':'互动'})`);
    } else if (v > 0) {
      actionLabels.push(`${ {like:'👍点赞',collect:'⭐收藏',comment:'💬评论',follow:'👤关注'}[k] || k } ${v}%`);
    }
  }
  detail += `动作: ${actionLabels.join(' | ')}\n`;
  detail += `策略: 每视频评论≤${strategy.comment_per_video}条 | 每账号评论≤${strategy.comment_daily_limit}条/天 | 分组 ${strategy.group_like}赞/${strategy.group_comment}评/${strategy.group_collect}藏 | ${strategy.pace==='compact'?'⚡紧凑':'🐢宽松'}\n`;
  detail += `间隔: ${interval}s`;

  if (!await confirmExecute(`🎯 ${selected.length} 个账号 × ${urls.length} 条链接`, detail)) return;

  log.textContent = `🚀 提交互动计划: ${selected.length} 个账号 × ${urls.length} 条链接\n`;
  log.textContent += `   策略: 每视频评论≤${strategy.comment_per_video}条 | 每账号≤${strategy.comment_daily_limit}条 | ${strategy.group_like}赞/${strategy.group_comment}评/${strategy.group_collect}藏\n`;

  try {
    const d = await apiRequest('/ops/run', {
      method: 'POST',
      body: JSON.stringify({
        type: 'interact',
        accounts: selected.map(s => s.id),
        params: {
          urls,            // 所有视频一次性提交，由后端计划生成器分配
          actions,
          strategy,
          interval,
        },
      }),
    });
    if (d.status === 'ok' || d.status === 'accepted') {
      log.textContent += `\n✅ 计划已提交: ${d.total_tasks || d.tasks?.length || '?'} 个互动任务\n`;
      if (d.summary) log.textContent += `   评论≈${d.summary.comment} | 点赞≈${d.summary.like} | 收藏≈${d.summary.collect}\n`;
      if (d.errors?.length) log.textContent += `⚠️ ${d.errors.length} 个错误: ${d.errors[0].message}\n`;
    } else {
      log.textContent += `\n❌ 提交失败: ${d.message || d.detail || '未知错误'}\n`;
      if (d.errors?.length) log.textContent += `   ${d.errors.map(e => e.message).join('; ')}\n`;
    }
  } catch(e) {
    log.textContent += `\n❌ 网络错误: ${e.message}\n`;
  }
}
