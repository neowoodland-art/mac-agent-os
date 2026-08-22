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
let _commentMap = {};   // {url: [{text, role, role_label}]} — 用户设定的评论内容

// 评论内容设置的 13 个角色（数字=生成条数）
const IA_ROLES = [
  { id: 'filler', label: '灌水', group: '灌水/搞怪' },
  { id: 'funny', label: '搞怪', group: '灌水/搞怪' },
  { id: 'sympathizer', label: '感同身受', group: '情感' },
  { id: 'sharer', label: '喜欢赞扬', group: '情感' },
  { id: 'angry', label: '愤世嫉俗', group: '情感' },
  { id: 'oppose', label: '坚决抵制', group: '情感' },
  { id: 'questioner', label: '提问', group: '疑问问答' },
  { id: 'answerer', label: '回答', group: '疑问问答' },
  { id: 'guide_analyze', label: '客观分析引导', group: '引导' },
  { id: 'guide_share', label: '经验分享引导', group: '引导' },
  { id: 'guide_agree', label: '赞同博主引导', group: '引导' },
  { id: 'guide_benefit', label: '薅羊毛推荐引导', group: '引导' },
  { id: 'guide_compare', label: '对比反证引导', group: '引导' },
];

// 无标题视频兜底用的灌水/搞怪池
const IA_FILLER_POOL = [
  '路过看看', '学到了', '不错', '支持一下', '挺有意思的', '点个赞走了',
  '哈哈哈哈', '这操作绝了', '笑死我了', '666', '离谱但真实', '我直接好家伙',
];

export async function loadView(container) {
  const uid = (container.id || 'interact').replace(/-/g, '_');
  const data = await apiRequest('/v2/accounts');
  const allAccts = Array.isArray(data) ? data : (data.accounts || []);

  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:4px">🎯 批量互动 <span style="font-size:10px;color:var(--text2);font-weight:400">账号全量 × 视频按比例 × 多动作连做</span></div>

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
            <button onclick="window._ia_toggleMd_${uid}()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px" title="粘贴 Markdown 表格（| 标题 | 链接 | 评论数 |），自动提取标题+链接">📋 MD表格</button>
            <span id="ia_parsedCount_${uid}" style="font-size:10px;color:var(--text2)"></span>
            <span id="ia_listToggle_${uid}" style="display:none;font-size:9px;color:var(--text2);cursor:pointer" onclick="window._ia_toggleList_${uid}()">展开列表 ▼</span>
          </div>
          <div id="ia_parsedList_${uid}" style="display:none;font-size:10px;margin-top:4px;max-height:120px;overflow-y:auto"></div>
          <!-- MD 表格提取（可折叠） -->
          <div id="ia_mdPanel_${uid}" style="display:none;margin-top:6px;border-top:1px dashed var(--border);padding-top:6px">
            <div style="font-size:10px;color:var(--text2);margin-bottom:4px">📋 粘贴 Markdown 表格（格式：<code>| 标题 | 链接 | 评论数 |</code>），自动提取「标题+链接」对填入上方导入框</div>
            <textarea id="ia_mdInput_${uid}" rows="5" placeholder="| 标题 | https://www.douyin.com/jingxuan?modal_id=xxx | 0 |&#10;| 标题2 | https://www.douyin.com/video/yyy | 12 |"
              style="width:100%;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:10px;font-family:monospace;resize:vertical"></textarea>
            <div style="display:flex;gap:4px;margin-top:4px;align-items:center">
              <button onclick="window._ia_parseMd_${uid}()" style="background:var(--primary);color:#fff;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">✅ 提取并解析</button>
              <span id="ia_mdResult_${uid}" style="font-size:10px;color:var(--text2)"></span>
            </div>
          </div>
        </div>

        <!-- 动作设置（账号全量 × 视频按比例） -->
        <div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:8px">
          <div style="font-size:11px;color:var(--text2);margin-bottom:6px">🎚️ 互动动作 <span style="font-size:9px;color:var(--text2)">（所有账号全量执行；比例 = 多少比例的视频执行该动作，0-100）</span></div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;font-size:11px">
            <div style="display:flex;align-items:center;gap:4px">
              <span style="width:14px">👍</span>
              <span style="width:60px">点赞</span>
              <span style="font-size:9px;color:var(--text2)">视频比例</span>
              <input type="number" id="ia_ratio_like_${uid}" min="0" max="100" step="5" value="90" style="width:48px;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px" title="0-100，90 = 90% 的视频被全部账号点赞">
              <span style="font-size:9px;color:var(--text2)">%</span>
            </div>
            <div style="display:flex;align-items:center;gap:4px">
              <span style="width:14px">⭐</span>
              <span style="width:60px">收藏</span>
              <span style="font-size:9px;color:var(--text2)">视频比例</span>
              <input type="number" id="ia_ratio_collect_${uid}" min="0" max="100" step="5" value="30" style="width:48px;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px" title="0-100，30 = 30% 的视频被全部账号收藏">
              <span style="font-size:9px;color:var(--text2)">%</span>
            </div>
            <div style="display:flex;align-items:center;gap:4px">
              <span style="width:14px">💬</span>
              <span style="width:60px">评论</span>
              <span style="font-size:9px;color:var(--text2)">视频比例</span>
              <input type="number" id="ia_ratio_comment_${uid}" min="0" max="100" step="5" value="60" style="width:48px;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px" title="0-100，60 = 60% 的视频有评论（每视频随机挑账号，受下方闸门控制）">
              <span style="font-size:9px;color:var(--text2)">%</span>
            </div>
          </div>
          <div style="font-size:9px;color:var(--text2);margin-top:4px">💡 评论还受下方闸门控制：每视频最多 N 条（随机挑账号）、每账号每天最多 N 条（到限自动降级为只赞藏）。未命中任何动作的视频直接跳过。</div>
        </div>

          <!-- 评论内容设置（可折叠） -->
          <div style="margin-top:6px;border-top:1px solid var(--border);padding-top:6px">
            <div onclick="window._ia_toggleCommentCfg_${uid}()" style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:11px;user-select:none">
              <span id="ia_cfgArrow_${uid}">▶</span>
              <span>⚙️ 评论内容设置</span>
              <span id="ia_cfgSummary_${uid}" style="font-size:9px;color:var(--text2)"></span>
            </div>
            <div id="ia_cfgBody_${uid}" style="display:none;margin-top:4px;padding-left:16px">
              <div style="font-size:10px;color:var(--text2);margin-bottom:4px">按角色设定评论内容（数字=该角色生成几条；默认引导类各1条）。生成的评论执行时直接使用，不再随机取语料。</div>
              <div id="ia_roleGrid_${uid}" style="display:grid;grid-template-columns:1fr 1fr;gap:3px 10px;font-size:10px"></div>
              <div style="display:flex;gap:4px;margin-top:6px;align-items:center;flex-wrap:wrap">
                <span id="ia_roleTotal_${uid}" style="font-size:10px;color:var(--text2)">合计 0 条</span>
                <button onclick="window._ia_genComments_${uid}()" style="background:var(--primary);color:#fff;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">🚀 为所有视频生成评论</button>
                <button onclick="window._ia_clearComments_${uid}()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">🗑 清空</button>
              </div>
              <!-- 引导内容（引导类/回答型评论按比例结合） -->
              <div style="margin-top:6px;border-top:1px dashed var(--border);padding-top:6px">
                <div style="font-size:10px;color:var(--text2);margin-bottom:3px">🎯 引导内容（引导类/回答型评论按比例结合）</div>
                <textarea id="ia_guidePoints_${uid}" rows="2" placeholder="如: 引导关注公众号约号 / 推荐朱晓光主任（不填=不结合引导）"
                  style="width:100%;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:10px;resize:vertical"></textarea>
                <div style="display:flex;align-items:center;gap:4px;margin-top:3px;font-size:10px">
                  <span style="color:var(--text2)">引导引用比例</span>
                  <input type="number" id="ia_guideRatio_${uid}" min="0" max="100" step="5" value="80" style="width:48px;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px" title="0-100，引导类/回答型评论中多少比例结合引导内容">
                  <span style="font-size:9px;color:var(--text2)">%</span>
                  <span style="font-size:9px;color:var(--text2);margin-left:4px">（引导类 + 回答型按此比例结合，其他角色 AI 生成但自然不带引导）</span>
                  <span style="flex:1"></span>
                  <label style="display:flex;align-items:center;gap:3px;cursor:pointer" title="勾选 = 强制 AI 生成评论（更自然）；不勾选但填了引导内容 = 自动 AI">
                    <input type="checkbox" id="ia_aiEnhance_${uid}"> <span style="font-size:10px">🧠 AI 改写</span>
                  </label>
                </div>
              </div>
              <div id="ia_cfgResult_${uid}" style="margin-top:6px;max-height:320px;overflow-y:auto;display:grid;gap:4px"></div>
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

        <!-- 📊 互动策略（评论闸门 + 节奏，防封号） -->
        <div style="background:var(--bg3);border-radius:6px;padding:8px;border:1px solid var(--border);margin-bottom:8px">
          <div style="font-size:11px;color:var(--text2);margin-bottom:6px">📊 评论闸门与节奏 <span style="font-size:9px;color:var(--text2)">（评论两道硬闸门 + 执行节奏，模拟真人防封号）</span></div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;font-size:11px">
            <div style="display:flex;align-items:center;gap:4px">
              <span>💬 每视频评论上限</span>
              <input type="number" id="ia_cpv_${uid}" min="0" max="20" value="5" style="width:44px;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px" title="0-20，每条视频最多 N 条评论（随机挑 N 个账号评；0=不评论）">
              <span style="font-size:9px;color:var(--text2)">条</span>
            </div>
            <div style="display:flex;align-items:center;gap:4px">
              <span>📮 每账号评论日上限</span>
              <input type="number" id="ia_cdl_${uid}" min="1" max="100" value="20" style="width:44px;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px" title="1-100，每个账号每天最多评论 N 条，到限自动降级为只赞藏">
              <span style="font-size:9px;color:var(--text2)">条</span>
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
  window[`_ia_toggleMd_${self}`] = () => _ia_toggleMd(self);
  window[`_ia_parseMd_${self}`] = () => _ia_parseMd(self);
  window[`_ia_exec_${self}`] = () => _ia_exec(self);
  window[`_ia_toggleCommentCfg_${self}`] = () => _ia_toggleCommentCfg(self);
  window[`_ia_updateRoleTotal_${self}`] = () => _ia_updateRoleTotal(self);
  window[`_ia_genComments_${self}`] = () => _ia_genComments(self);
  window[`_ia_clearComments_${self}`] = () => _ia_clearComments(self);
  window[`_ia_editComment_${self}`] = (el, ui, ci) => _ia_editComment(el, ui, ci);
  window[`_ia_delComment_${self}`] = (ui, ci) => _ia_delComment(ui, ci);
  window[`_ia_delVideo_${self}`] = (ui) => _ia_delVideo(ui);
  window[`_ia_regenVideo_${self}`] = (ui) => _ia_regenVideo(ui);
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

// ── MD 表格提取（| 标题 | 链接 | 评论数 |）──

function _ia_toggleMd(uid) {
  const panel = document.getElementById(`ia_mdPanel_${uid}`);
  if (!panel) return;
  panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

function _ia_parseMd(uid) {
  const text = document.getElementById(`ia_mdInput_${uid}`)?.value || '';
  const resultEl = document.getElementById(`ia_mdResult_${uid}`);
  if (!text.trim()) { if (resultEl) resultEl.textContent = '❌ 请粘贴 MD 表格'; return; }

  // 提取表格行: | 标题 | 链接 | 评论数 |（正则：标题 + 抖音链接 + 数字）
  const out = [];
  for (const line of text.split('\n')) {
    const m = line.trim().match(/^\|\s*(.*?)\s*\|\s*(https?:\/\/[^\s|]+)\s*\|\s*\d+\s*\|$/);
    if (m) {
      out.push('标题: ' + m[1].trim());
      out.push(m[2].trim());
    }
  }
  if (!out.length) { if (resultEl) resultEl.textContent = '❌ 未提取到「标题|链接」行（格式: | 标题 | URL | 评论数 |）'; return; }

  // 填入导入框并自动解析
  const inputEl = document.getElementById(`ia_input_${uid}`);
  if (inputEl) inputEl.value = out.join('\n');
  // 新的一组视频 → 清空旧的评论内容设定，避免错配
  _commentMap = {};
  _ia_renderCommentResults(uid);
  _ia_renderCommentSummary(uid);
  _ia_parse(uid);
  if (resultEl) resultEl.textContent = `✅ 提取 ${out.length / 2} 条，已填入并解析`;
}

// ── 评论内容设置（角色数字输入 → 按视频生成/编辑） ──

function _ia_toggleCommentCfg(uid) {
  const body = document.getElementById(`ia_cfgBody_${uid}`);
  const arrow = document.getElementById(`ia_cfgArrow_${uid}`);
  if (!body || !arrow) return;
  const isHidden = body.style.display === 'none';
  body.style.display = isHidden ? 'block' : 'none';
  arrow.textContent = isHidden ? '▼' : '▶';
  if (isHidden) {
    _ia_renderRoleGrid(uid);
    _ia_updateRoleTotal(uid);
    _ia_renderCommentResults(uid);
  }
}

function _ia_renderRoleGrid(uid) {
  const grid = document.getElementById(`ia_roleGrid_${uid}`);
  if (!grid) return;
  const groups = ['灌水/搞怪', '情感', '疑问问答', '引导'];
  grid.innerHTML = groups.map(g => `
    <div style="grid-column:1/-1;font-size:9px;color:var(--text2);margin-top:3px;font-weight:500;border-top:1px solid var(--border);padding-top:3px">${g}</div>
    ${IA_ROLES.filter(r => r.group === g).map(r => `
      <div style="display:flex;align-items:center;gap:4px">
        <span style="flex:1;min-width:64px">${r.label}</span>
        <input type="number" id="ia_role_${r.id}_${uid}" min="0" max="20" value="${r.id.startsWith('guide_') ? 1 : 0}"
               oninput="window._ia_updateRoleTotal_${uid}()"
               style="width:44px;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px;font-size:10px">
      </div>`).join('')}
  `).join('');
}

function _ia_collectRoleCounts(uid) {
  const counts = {};
  IA_ROLES.forEach(r => {
    const el = document.getElementById(`ia_role_${r.id}_${uid}`);
    const v = el ? parseInt(el.value || '0', 10) : 0;
    if (v > 0) counts[r.id] = v;
  });
  return counts;
}

function _ia_updateRoleTotal(uid) {
  const counts = _ia_collectRoleCounts(uid);
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const el = document.getElementById(`ia_roleTotal_${uid}`);
  if (el) el.textContent = `合计 ${total} 条`;
  return total;
}

function _ia_escapeHtml(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function _ia_genComments(uid) {
  if (!_parsedItems.length) { alert('请先解析内容链接'); return; }
  const roleCounts = _ia_collectRoleCounts(uid);
  if (!Object.keys(roleCounts).length) { alert('请至少填一个角色的评论条数'); return; }
  const perVideo = Object.values(roleCounts).reduce((a, b) => a + b, 0);

  // 校验：角色合计 vs 每视频评论上限（评论池建议 = 上限，保证每个视频恰好领满）
  const cpv = parseInt(document.getElementById(`ia_cpv_${uid}`)?.value || '5');
  if (perVideo !== cpv) {
    if (!confirm(`角色合计 ${perVideo} 条 ≠ 每视频评论上限 ${cpv} 条。\n建议评论池条数 = 每视频评论上限（${cpv} 条），这样每个视频恰好能领满，不会缺评论。\n仍按 ${perVideo} 条生成？（不足的视频评论数会少于上限）`)) return;
  }

  const resultEl = document.getElementById(`ia_cfgResult_${uid}`);
  if (resultEl) resultEl.innerHTML = '<div style="font-size:10px;color:var(--text2)">⏳ 生成中...</div>';
  _commentMap = {};

  let noTitleCount = 0;
  for (let i = 0; i < _parsedItems.length; i++) {
    const item = _parsedItems[i];
    const title = (item.title || '').trim();
    let comments = [];
    if (title) {
      try {
        const _gp = (document.getElementById(`ia_guidePoints_${uid}`)?.value || '').trim();
        const r = await fetch('/api/comment-workbench/generate', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            video_title: title,
            role_counts: roleCounts,
            ai_enhance: document.getElementById(`ia_aiEnhance_${uid}`)?.checked || !!_gp,  // AI改写勾选 或 有引导内容 → 自动 AI 生成
            long_ratio: 0,
            guide_points: _gp,
            guide_ratio: Math.min(100, Math.max(0, parseInt(document.getElementById(`ia_guideRatio_${uid}`)?.value || '80'))) / 100,
          }),
        });
        const d = await r.json();
        comments = (d.comments || []).map(c => ({
          text: c.text || '', role: c.role || 'filler', role_label: c.role_label || c.role || '灌水',
        }));
      } catch (e) {
        comments = [];
      }
    } else {
      // 无标题视频：用灌水/搞怪池填充（条数 = 角色合计）
      noTitleCount++;
      const pool = [...IA_FILLER_POOL];
      for (let k = 0; k < perVideo && pool.length; k++) {
        const idx = Math.floor(Math.random() * pool.length);
        comments.push({ text: pool.splice(idx, 1)[0], role: 'filler', role_label: '灌水/搞怪' });
      }
    }
    if (comments.length) _commentMap[item.url] = comments;
  }

  _ia_renderCommentResults(uid);
  _ia_renderCommentSummary(uid);
  if (noTitleCount) alert(`⚠️ ${noTitleCount} 个视频无标题，已用灌水/搞怪评论填充`);
}

function _ia_renderCommentSummary(uid) {
  const el = document.getElementById(`ia_cfgSummary_${uid}`);
  if (!el) return;
  const n = Object.keys(_commentMap).length;
  const total = Object.values(_commentMap).reduce((a, cs) => a + cs.length, 0);
  el.textContent = n ? `已设定 ${n} 个视频 / ${total} 条评论` : '';
}

function _ia_renderCommentResults(uid) {
  const el = document.getElementById(`ia_cfgResult_${uid}`);
  if (!el) return;
  const urls = Object.keys(_commentMap);
  if (!urls.length) { el.innerHTML = ''; return; }
  el.innerHTML = urls.map((url, ui) => {
    const item = _parsedItems.find(p => p.url === url) || {};
    const title = (item.title || url).slice(0, 34);
    const comments = _commentMap[url];
    return `
      <div style="border:1px solid var(--border);border-radius:6px;padding:6px;background:var(--bg3)">
        <div style="display:flex;align-items:center;gap:4px;font-size:10px;margin-bottom:4px">
          <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600">${_ia_escapeHtml(title)}</span>
          <span style="font-size:9px;color:var(--text2)">${comments.length} 条</span>
          <button onclick="window._ia_regenVideo_${uid}(${ui})" title="重新生成此视频评论" style="font-size:9px;background:var(--bg);border:1px solid var(--border);color:var(--text);border-radius:3px;cursor:pointer;padding:1px 5px">🔄</button>
          <button onclick="window._ia_delVideo_${uid}(${ui})" title="删除此视频全部评论" style="font-size:9px;background:var(--bg);border:1px solid var(--border);color:var(--text);border-radius:3px;cursor:pointer;padding:1px 5px">🗑</button>
        </div>
        ${comments.map((c, ci) => `
          <div style="display:flex;gap:4px;align-items:center;margin-bottom:2px">
            <span style="font-size:9px;color:var(--text2);width:52px;flex-shrink:0">${_ia_escapeHtml(c.role_label)}</span>
            <input type="text" value="${_ia_escapeHtml(c.text)}"
                   onchange="window._ia_editComment_${uid}(this, ${ui}, ${ci})"
                   style="flex:1;font-size:10px;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:2px 4px;border-radius:3px">
            <button onclick="window._ia_delComment_${uid}(${ui}, ${ci})" title="删除此条" style="font-size:9px;background:var(--bg);border:1px solid var(--border);color:var(--text);border-radius:3px;cursor:pointer;padding:1px 5px">✕</button>
          </div>`).join('')}
      </div>`;
  }).join('');
}

function _ia_editComment(el, ui, ci) {
  const url = Object.keys(_commentMap)[ui];
  if (!url || !_commentMap[url] || !_commentMap[url][ci]) return;
  const v = (el.value || '').trim();
  if (v) _commentMap[url][ci].text = v;
  else el.value = _commentMap[url][ci].text;  // 空值还原
}

function _ia_delComment(uid, ui, ci) {
  const url = Object.keys(_commentMap)[ui];
  if (!url || !_commentMap[url]) return;
  _commentMap[url].splice(ci, 1);
  if (!_commentMap[url].length) delete _commentMap[url];
  _ia_renderCommentResults(uid);
  _ia_renderCommentSummary(uid);
}

function _ia_delVideo(uid, ui) {
  const url = Object.keys(_commentMap)[ui];
  if (!url) return;
  delete _commentMap[url];
  _ia_renderCommentResults(uid);
  _ia_renderCommentSummary(uid);
}

async function _ia_regenVideo(uid, ui) {
  const url = Object.keys(_commentMap)[ui];
  const item = _parsedItems.find(p => p.url === url);
  if (!item || !url) return;
  const roleCounts = _ia_collectRoleCounts(uid);
  if (!Object.keys(roleCounts).length) { alert('请至少填一个角色的评论条数'); return; }
  const title = (item.title || '').trim();
  let comments = [];
  if (title) {
    try {
      const _gp = (document.getElementById(`ia_guidePoints_${uid}`)?.value || '').trim();
      const r = await fetch('/api/comment-workbench/generate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_title: title, role_counts: roleCounts,
          ai_enhance: document.getElementById(`ia_aiEnhance_${uid}`)?.checked || !!_gp,  // AI改写勾选 或 有引导内容 → 自动 AI 生成
          long_ratio: 0,
          guide_points: _gp,
          guide_ratio: Math.min(100, Math.max(0, parseInt(document.getElementById(`ia_guideRatio_${uid}`)?.value || '80'))) / 100,
        }),
      });
      const d = await r.json();
      comments = (d.comments || []).map(c => ({
        text: c.text || '', role: c.role || 'filler', role_label: c.role_label || c.role || '灌水',
      }));
    } catch (e) { comments = []; }
  }
  if (comments.length) _commentMap[url] = comments;
  _ia_renderCommentResults(uid);
  _ia_renderCommentSummary(uid);
}

function _ia_clearComments(uid) {
  _commentMap = {};
  _ia_renderCommentResults(uid);
  _ia_renderCommentSummary(uid);
}

// ── 执行 ──

async function _ia_exec(uid) {
  const log = document.getElementById(`log_${uid}`);
  const selected = _selector?.getSelected() || [];

  if (!_parsedItems.length) { log.textContent = '❌ 请先解析内容链接\n'; return; }
  if (!selected.length) { log.textContent = '❌ 请选择账号\n'; return; }

  // 收集参数（账号全量 × 视频按比例）
  const urls = _parsedItems;
  const likeRatio = parseInt(document.getElementById(`ia_ratio_like_${uid}`)?.value || '90');
  const collectRatio = parseInt(document.getElementById(`ia_ratio_collect_${uid}`)?.value || '30');
  const commentRatio = parseInt(document.getElementById(`ia_ratio_comment_${uid}`)?.value || '60');
  const interval = document.getElementById(`ia_interval_${uid}`)?.value?.trim() || '300-600';

  // 策略参数（带范围保护：比例 0-100，上限 0-20 / 1-100）
  const strategy = {
    like_ratio: Math.min(100, Math.max(0, likeRatio)) / 100,
    collect_ratio: Math.min(100, Math.max(0, collectRatio)) / 100,
    comment_ratio: Math.min(100, Math.max(0, commentRatio)) / 100,
    comment_per_video: Math.min(20, Math.max(0, parseInt(document.getElementById(`ia_cpv_${uid}`)?.value || '5'))),
    comment_daily_limit: Math.min(100, Math.max(1, parseInt(document.getElementById(`ia_cdl_${uid}`)?.value || '20'))),
    pace: document.getElementById(`ia_pace_${uid}`)?.value || 'loose',
  };

  // 用户设定的评论内容 → comment_map（执行时直接取设定内容，不随机）
  const commentMap = {};
  for (const [u, cs] of Object.entries(_commentMap)) {
    const texts = (cs || []).map(c => (c.text || '').trim()).filter(Boolean);
    if (texts.length) commentMap[u] = texts;
  }
  const cmVideoCount = Object.keys(commentMap).length;
  const cmTotal = Object.values(commentMap).reduce((a, t) => a + t.length, 0);

  // 确认
  let detail = `链接: ${urls.length} 条\n`;
  detail += `动作(账号全量): 👍点赞 ${strategy.like_ratio*100}%视频 | ⭐收藏 ${strategy.collect_ratio*100}%视频 | 💬评论 ${strategy.comment_ratio*100}%视频\n`;
  detail += `评论闸门: 每视频≤${strategy.comment_per_video}条 | 每账号≤${strategy.comment_daily_limit}条/天 | ${strategy.pace==='compact'?'⚡紧凑':'🐢宽松'}\n`;
  detail += `评论内容: ${cmVideoCount ? `已设定 ${cmVideoCount} 个视频 / ${cmTotal} 条（按序分配，用完即止）` : '⚠️ 未设定（将随机取语料）'}\n`;
  detail += `间隔: ${interval}s`;

  if (!await confirmExecute(`🎯 ${selected.length} 个账号 × ${urls.length} 条链接`, detail)) return;

  log.textContent = `🚀 提交互动计划: ${selected.length} 个账号 × ${urls.length} 条链接\n`;
  log.textContent += `   动作: 点赞${Math.round(strategy.like_ratio*100)}%视频 | 收藏${Math.round(strategy.collect_ratio*100)}%视频 | 评论${Math.round(strategy.comment_ratio*100)}%视频\n`;
  log.textContent += `   评论闸门: 每视频≤${strategy.comment_per_video}条 | 每账号≤${strategy.comment_daily_limit}条/天 | ${strategy.pace==='compact'?'⚡紧凑':'🐢宽松'}\n`;
  log.textContent += `   评论内容: ${cmVideoCount ? `已设定 ${cmVideoCount} 个视频 / ${cmTotal} 条` : '⚠️ 未设定（随机语料）'}\n`;

  try {
    const d = await apiRequest('/ops/run', {
      method: 'POST',
      body: JSON.stringify({
        type: 'interact',
        accounts: selected.map(s => s.id),
        params: {
          urls,            // 所有视频一次性提交，由后端计划生成器分配
          strategy,
          interval,
          comment_map: cmVideoCount ? commentMap : undefined,  // 用户设定的评论内容
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
