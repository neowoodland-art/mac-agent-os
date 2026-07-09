/**
 * comment-workbench.js — 评论工作台 v4
 *
 * 批量视频 × 批量账号 × 角色化评论
 *
 * 流程:
 *   ① 导入视频（粘贴URL / 导入热帖API）
 *   ② 选择账号
 *   ③ 按视频调角色比例 → 生成评论
 *   ④ 预览编排（视频→评论→账号映射）
 *   ⑤ 一键分发
 *
 * 后端:
 *   GET  /api/comment-workbench/roles
 *   POST /api/comment-workbench/generate
 *   POST /api/ops/run {type:"smart_comment"}
 */

import { apiRequest } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

let _selector = null;
let _allRoles = [];
let _rolePcts = {};
let _videos = [];           // {url, title, tags, checked}
let _generatedComments = [];// [{video_idx, account_idx, account_id, text, role, role_label, is_long}]
let _resultText = '';
let _uid = '';

// ── 角色中文标签 ──
const ROLE_LABELS = {
  sharer: '分享型', questioner: '提问型', sympathizer: '共情型',
  skeptic: '质疑型', sufferer: '患者型', filler: '灌水型',
  expert_ref: '推荐型',
};

// ── 主入口 ──
export async function loadView(container) {
  _uid = container.id || 'cw';
  _videos = [];
  _generatedComments = [];
  _resultText = '';

  container.innerHTML = `
    <div style="padding:16px;max-width:960px">

      <!-- ═══ 标题 ═══ -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">💬 评论工作台</h2>
        <span style="font-size:10px;color:var(--text2)">批量视频 × 批量账号 × 角色化评论</span>
      </div>

      <!-- ═══ 自动更新总计 ═══ -->
      <span id="cwPctStatus_${_uid}" style="display:none"></span>

      <!-- ═══ 第一步：导入视频 ═══ -->
      <div class="cw-section" style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-bottom:10px">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">📥 第一步：导入视频</div>
        <div style="display:flex;gap:6px;margin-bottom:6px">
          <textarea id="cwUrls_${_uid}" placeholder="视频链接（每行一个，支持多个）" rows="3"
                    style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
          <div style="display:flex;flex-direction:column;gap:4px;width:180px">
            <button onclick="window._cwParseUrls('${_uid}')"
                    style="background:var(--primary);color:#fff;border:none;padding:5px 8px;border-radius:4px;cursor:pointer;font-size:11px">📋 解析链接</button>
            <button onclick="window._cwShowApiImport('${_uid}')"
                    style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;cursor:pointer;font-size:11px">📡 导入热帖</button>
          </div>
        </div>
        <!-- 导入热帖面板（折叠） -->
        <div id="cwImportPanel_${_uid}" style="display:none;background:var(--bg3);border-radius:6px;padding:8px;margin-bottom:6px">
          <div style="display:flex;gap:4px;align-items:center;margin-bottom:4px">
            <input id="cwApiUrl_${_uid}" type="text"
                   placeholder="API 地址" value="https://wx.tyhtak.com/api/biz/activity/api/v1/activity/recordswx1"
                   style="flex:1;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:3px;font-size:10px">
            <input id="cwApiPages_${_uid}" type="number" value="3" min="1" max="10"
                   style="width:40px;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:4px;border-radius:3px;font-size:10px;text-align:center">
            <span style="font-size:9px;color:var(--text2)">页</span>
            <button onclick="window._cwApiImport('${_uid}')"
                    style="background:#2563eb;color:#fff;border:none;padding:4px 10px;border-radius:3px;cursor:pointer;font-size:10px">导入</button>
            <span id="cwApiImportStatus_${_uid}" style="font-size:9px;color:var(--text2)"></span>
          </div>
        </div>
        <!-- 视频列表 -->
        <div id="cwVideoList_${_uid}" style="display:none;background:var(--bg3);border-radius:6px;padding:6px;max-height:240px;overflow-y:auto"></div>
      </div>

      <!-- ═══ 第二步：选择账号 ═══ -->
      <div class="cw-section" style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-bottom:10px">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">👥 第二步：选择账号</div>
        <div id="cwAcctList_${_uid}"><div class="loading">⏳ 加载账号列表...</div></div>
      </div>

      <!-- ═══ 第三步：角色比例 ═══ -->
      <div id="cwRoleSection_${_uid}" style="display:none;background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-bottom:10px">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">🎭 第三步：角色比例（所有视频通用）</div>
        <div id="cwRoleSliders_${_uid}" style="display:grid;gap:6px"></div>
        <div style="display:flex;gap:10px;align-items:center;margin-top:8px;flex-wrap:wrap">
          <label style="font-size:11px;display:flex;align-items:center;gap:4px">
            每条视频生成
            <input id="cwPerVideo_${_uid}" type="number" value="15" min="3" max="60"
                   style="width:50px;padding:3px 6px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:11px;text-align:center">
            条评论
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px">
            长评占比
            <input id="cwLongRatio_${_uid}" type="range" min="0" max="100" value="20"
                   oninput="document.getElementById('cwLongVal_${_uid}').textContent=this.value+'%'"
                   style="width:80px">
            <span id="cwLongVal_${_uid}" style="font-size:11px;color:var(--text2);min-width:35px">20%</span>
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px">
            <input type="checkbox" id="cwAiEnhance_${_uid}" checked>
            🧠 AI 改写
          </label>
          <button id="cwGenerateBtn_${_uid}" onclick="window._cwGenerate('${_uid}')"
                  style="background:var(--primary);color:#fff;border:none;padding:6px 16px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600">🚀 生成评论</button>
        </div>
      </div>

      <!-- ═══ 第四步：预览 ═══ -->
      <div id="cwPreview_${_uid}" style="display:none;background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-bottom:10px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="font-weight:600;font-size:13px">📝 第四步：预览编排</span>
          <div style="display:flex;gap:6px">
            <span id="cwPreviewCount_${_uid}" style="font-size:11px;color:var(--text2)"></span>
            <button onclick="window._cwRegenerate('${_uid}')"
                    style="background:var(--bg3);border:1px solid var(--border);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">🔄 重新生成</button>
            <button onclick="window._cwDispatch('${_uid}')"
                    style="background:var(--primary);color:#fff;border:none;padding:3px 12px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600">✅ 分发</button>
          </div>
        </div>
        <div id="cwCommentList_${_uid}" style="display:grid;gap:4px;max-height:500px;overflow-y:auto"></div>
      </div>

      <!-- ═══ 第五步：结果 ═══ -->
      <div id="cwResult_${_uid}" style="display:none;background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-top:10px">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">📊 分发结果</div>
        <div id="cwResultContent_${_uid}" style="font-size:11px;line-height:1.6"></div>
      </div>

    </div>
  `;

  // 初始化角色
  _rolePcts = {};
  ROLES_CONFIG.forEach(r => { _rolePcts[r.id] = r.pct; });
  renderRoleSliders();

  // 加载账号
  try {
    const acctRes = await apiRequest('/matrix/accounts');
    const accts = Array.isArray(acctRes) ? acctRes : (acctRes.accounts || []);
    const listEl = document.getElementById(`cwAcctList_${_uid}`);
    if (listEl) {
      _selector = createAccountSelector(listEl, {
        accounts: accts, checkAll: true, height: '160px',
        showBlueprint: false, showCollectTime: false,
      });
    }
  } catch (e) {
    const el = document.getElementById(`cwAcctList_${_uid}`);
    if (el) el.innerHTML = `<div class="error">❌ ${e.message}</div>`;
  }
}

// ═══ 角色滑条 ═══

function renderRoleSliders() {
  const wrap = document.getElementById(`cwRoleSliders_${_uid}`);
  if (!wrap) return;
  const groups = [
    { key: 'filler', label: '灌水/搞怪', items: ROLES_CONFIG.filter(r => r.group === 'filler' || r.group === 'funny') },
    { key: 'emotion', label: '情感类', items: ROLES_CONFIG.filter(r => r.group === 'emotion') },
    { key: 'guide', label: '引导类（穿插埋入）', items: ROLES_CONFIG.filter(r => r.group === 'guide') },
  ];
  wrap.innerHTML = groups.map(g => `
    <div style="font-size:9px;color:var(--text2);margin:5px 0 2px 0;font-weight:500;border-top:1px solid var(--border);padding-top:4px">${g.label}</div>
    ${g.items.map(r => {
      const pct = (_rolePcts[r.id] || 0) * 100;
      return `
      <div style="display:flex;align-items:center;gap:6px;font-size:10px">
        <span style="min-width:80px;font-weight:400">${r.label}</span>
        <input type="range" min="0" max="50" value="${Math.round(pct)}"
               data-role="${r.id}"
               oninput="window._cwRolePct('${_uid}','${r.id}',this.value)"
               style="flex:1;height:5px;accent-color:${_sliderColor(r.id)}">
        <span id="cwPct_${r.id}_${_uid}" style="min-width:30px;text-align:right;color:var(--text2)">${Math.round(pct)}%</span>
      </div>`;
    }).join('')}
  `).join('');
  document.getElementById(`cwRoleSection_${_uid}`).style.display = 'block';
}

function _sliderColor(role) {
  const m = {
    filler:'#8b8fa3', funny:'#a78bfa',
    sympathizer:'#f59e0b', sharer:'#22c55e',
    angry:'#ef4444', oppose:'#dc2626',
    guide_analyze:'#3b82f6', guide_share:'#06b6d4',
    guide_agree:'#10b981', guide_benefit:'#f97316',
    guide_compare:'#8b5cf6',
  };
  return m[role] || '#3b82f6';
}

window._cwRolePct = (uid, roleId, val) => {
  _rolePcts[roleId] = parseInt(val) / 100;
  document.getElementById(`cwPct_${roleId}_${uid}`).textContent = `${val}%`;
  const total = Object.values(_rolePcts).reduce((a, b) => a + b, 0);
  const el = document.getElementById(`cwPctStatus_${uid}`);
  if (el) el.textContent = `总计 ${(total * 100).toFixed(0)}% ${Math.abs(total - 1) < 0.01 ? '✅' : '⚠️'}`;
};

// ═══ 导入视频 ═══

window._cwParseUrls = (uid) => {
  const raw = document.getElementById(`cwUrls_${uid}`)?.value?.trim();
  if (!raw) { alert('请先粘贴视频链接'); return; }
  const urls = raw.split('\n').map(s => s.trim()).filter(Boolean);
  if (!urls.length) { alert('没有有效的链接'); return; }

  urls.forEach(url => {
    if (!_videos.find(v => v.url === url)) {
      _videos.push({ url, title: '', tags: '', checked: true, industry: '', direction: 'auto' });
    }
  });
  _renderVideoList(uid);
};

window._cwShowApiImport = (uid) => {
  const panel = document.getElementById(`cwImportPanel_${uid}`);
  panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
};

window._cwApiImport = async (uid) => {
  const url = document.getElementById(`cwApiUrl_${uid}`)?.value?.trim();
  const pages = parseInt(document.getElementById(`cwApiPages_${uid}`)?.value || '3');
  if (!url) { alert('请输入 API 地址'); return; }

  const statusEl = document.getElementById(`cwApiImportStatus_${uid}`);
  statusEl.textContent = '⏳ 导入中...';

  let total = 0;
  for (let p = 1; p <= pages; p++) {
    try {
      const r = await apiRequest('/ops/import-topics', {
        method: 'POST',
        body: JSON.stringify({ api_url: url, page: p, page_size: 10 }),
      });
      if (r.status === 'ok' && r.items && r.items.length) {
        r.items.forEach(t => {
          const tUrl = t.url || t.link || t.title;
          if (!_videos.find(v => v.url === tUrl)) {
            _videos.push({
              url: tUrl,
              title: t.title || t.content || '',
              tags: Array.isArray(t.tags) ? t.tags.join(',') : (t.tags || ''),
              checked: true,
              industry: '',
              direction: 'auto',
            });
            total++;
          }
        });
      }
    } catch (e) {
      console.warn(`导入第${p}页失败:`, e);
    }
  }
  statusEl.textContent = total > 0 ? `✅ 导入 ${total} 条` : '⚠️ 未获取到视频';
  if (total > 0) _renderVideoList(uid);
};

function _renderVideoList(uid) {
  const wrap = document.getElementById(`cwVideoList_${uid}`);
  if (!wrap) return;
  if (!_videos.length) { wrap.style.display = 'none'; return; }

  wrap.style.display = 'block';
  wrap.innerHTML = `
    <div style="display:flex;align-items:center;gap:4px;margin-bottom:4px;font-size:10px;color:var(--text2)">
      <label style="display:flex;align-items:center;gap:2px;cursor:pointer">
        <input type="checkbox" onchange="window._cwToggleAllVideo('${uid}',this.checked)" ${_videos.every(v => v.checked) ? 'checked' : ''}>
        全选
      </label>
      <span>共 ${_videos.length} 个视频</span>
      <button onclick="window._cwClearVideos('${uid}')" style="margin-left:auto;background:none;border:none;cursor:pointer;font-size:10px;color:var(--red)">清空</button>
    </div>
    ${_videos.map((v, i) => {
      const indOpts = INDUSTRIES.map(ind => `<option value="${ind.id}" ${(v.industry||'')===ind.id?'selected':''}>${ind.label.replace(/^[^\s]+\s/,'')}</option>`).join('');
      const ctOpts = CONTENT_TYPES.map(ct => `<option value="${ct.id}" ${(v.content_type||'')===ct.id?'selected':''}>${ct.label.replace(/^[^\s]+\s/,'')}</option>`).join('');
      return `
      <div style="display:flex;align-items:center;gap:3px;padding:2px 4px;font-size:10px;background:var(--bg2);border-radius:3px;margin-bottom:2px">
        <input type="checkbox" ${v.checked ? 'checked' : ''} onchange="window._cwToggleVideo('${uid}',${i},this.checked)">
        <span style="flex:2;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:60px" title="${v.title || v.url}">${v.title ? v.title.slice(0, 18) : _shortenUrl(v.url, 25)}</span>
        <select onchange="window._cwSetVideoIndustry('${uid}',${i},this.value)" style="width:58px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:1px 2px;border-radius:2px;font-size:9px">${indOpts}</select>
        <select onchange="window._cwSetVideoContentType('${uid}',${i},this.value)" style="width:52px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:1px 2px;border-radius:2px;font-size:9px">${ctOpts}</select>
        <input type="text" placeholder="标签" value="${v.tags||''}" maxlength="16"
               onchange="window._cwSetVideoTag('${uid}',${i},this.value)"
               style="width:50px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:1px 2px;border-radius:2px;font-size:9px">
        <button onclick="window._cwRemoveVideo('${uid}',${i})"
                style="background:none;border:none;cursor:pointer;font-size:10px;opacity:.3;padding:0 2px">✕</button>
      </div>`}).join('')}
  `;
}

window._cwToggleVideo = (uid, idx, checked) => {
  if (_videos[idx]) _videos[idx].checked = checked;
};

window._cwToggleAllVideo = (uid, checked) => {
  _videos.forEach(v => v.checked = checked);
  _renderVideoList(uid);
};

window._cwClearVideos = (uid) => {
  _videos = [];
  _renderVideoList(uid);
};

window._cwSetVideoTag = (uid, idx, val) => {
  if (_videos[idx]) _videos[idx].tags = val;
};

window._cwRemoveVideo = (uid, idx) => {
  _videos.splice(idx, 1);
  _renderVideoList(uid);
};

window._cwSetVideoIndustry = (uid, idx, val) => {
  if (_videos[idx]) _videos[idx].industry = val;
};

window._cwSetVideoContentType = (uid, idx, val) => {
  if (_videos[idx]) _videos[idx].content_type = val;
};

const INDUSTRIES = [
  { id: '', label: '自动识别' },
  { id: 'medical', label: '🏥 医疗健康' },
  { id: 'suzhou', label: '📍 苏州本地' },
  { id: 'entertainment', label: '🎮 休闲娱乐' },
  { id: 'news', label: '📰 热点实讯' },
  { id: 'food', label: '🍜 吃喝玩乐' },
  { id: 'patriotic', label: '🇨🇳 家国情怀' },
  { id: 'misc', label: '📦 其他灌水' },
];

const CONTENT_TYPES = [
  { id: '', label: '自动' },
  { id: 'real_person', label: '🎭 真人出镜' },
  { id: 'ad', label: '📢 纯广告' },
  { id: 'knowledge', label: '📚 知识分享' },
  { id: 'experience', label: '💡 经验分享' },
  { id: 'explore', label: '🔍 探店' },
  { id: 'review', label: '📊 测评' },
  { id: 'other', label: '其他' },
];

// 角色定义：灌水 → 情感 → 引导，含 AI 用到的角色描述
const ROLES_CONFIG = [
  { id: 'filler', label: '灌水/路过', group: 'filler', pct: 0.30, desc: '路过灌水' },
  { id: 'funny', label: '😜 搞怪', group: 'funny', pct: 0.08, desc: '搞怪吐槽' },
  { id: 'sympathizer', label: '感同身受', group: 'emotion', pct: 0.12, desc: '共情感同身受' },
  { id: 'sharer', label: '喜欢赞扬', group: 'emotion', pct: 0.12, desc: '赞美赞扬' },
  { id: 'angry', label: '愤世嫉俗', group: 'emotion', pct: 0.08, desc: '愤怒吐槽现实' },
  { id: 'oppose', label: '坚决抵制', group: 'emotion', pct: 0.05, desc: '反对抵制' },
  { id: 'guide_analyze', label: '客观分析引导', group: 'guide', pct: 0.08, desc: '客观分析夸优点引导' },
  { id: 'guide_share', label: '经验分享引导', group: 'guide', pct: 0.06, desc: '相同经历经验分享引导' },
  { id: 'guide_agree', label: '赞同博主引导', group: 'guide', pct: 0.04, desc: '赞同博主引导' },
  { id: 'guide_benefit', label: '薅羊毛推荐引导', group: 'guide', pct: 0.04, desc: '利益分享薅羊毛引导' },
  { id: 'guide_compare', label: '对比反证引导', group: 'guide', pct: 0.03, desc: '对比其他差评反证引导' },
];

function _videoLabel(v) {
  let parts = [];
  if (v.title) parts.push(v.title.slice(0, 24));
  else parts.push(_shortenUrl(v.url, 30));
  const indLabel = INDUSTRIES.find(i => i.id === v.industry)?.label;
  if (indLabel && indLabel !== '自动识别') parts.push(`[${indLabel}]`);
  if (v.tags) parts.push(`#${v.tags}`);
  return parts.join(' ');
}

function _shortenUrl(url, maxLen) {
  if (!url) return '';
  const s = url.replace(/^https?:\/\//, '').replace(/^www\./, '');
  return s.length > maxLen ? s.slice(0, maxLen) + '…' : s;
}

// ═══ 视频编辑弹窗 ═══

window._cwEditVideo = (uid, idx) => {
  const v = _videos[idx];
  if (!v) return;
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:99999;display:flex;align-items:center;justify-content:center';
  overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };

  const indOpts = INDUSTRIES.map(i =>
    `<option value="${i.id}" ${v.industry === i.id ? 'selected' : ''}>${i.label}</option>`
  ).join('');
  const dirOpts = DIRECTIONS.map(d =>
    `<option value="${d.id}" ${(v.direction || 'auto') === d.id ? 'selected' : ''}>${d.label}</option>`
  ).join('');

  overlay.innerHTML = `
    <div style="background:var(--bg2);border-radius:12px;padding:20px;max-width:450px;width:90%">
      <div style="font-size:14px;font-weight:600;margin-bottom:10px">✏️ 编辑视频</div>
      <div style="font-size:11px;color:var(--text2);margin-bottom:10px;word-break:break-all">${v.title || _shortenUrl(v.url, 50)}</div>

      <div style="margin-bottom:10px">
        <div style="font-size:11px;font-weight:500;margin-bottom:4px">行业</div>
        <select id="cwEditInd_${uid}" style="width:100%;padding:6px 8px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:12px">
          ${indOpts}
        </select>
      </div>

      <div style="margin-bottom:10px">
        <div style="font-size:11px;font-weight:500;margin-bottom:4px">标签（逗号分隔）</div>
        <input id="cwEditTags_${uid}" type="text" value="${v.tags || ''}" placeholder="如: 运动,健身,跑步"
               style="width:100%;padding:6px 8px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:12px">
      </div>

      <div style="margin-bottom:14px">
        <div style="font-size:11px;font-weight:500;margin-bottom:4px">情感方向（角色滑条仍生效，此为主方向）</div>
        <select id="cwEditDir_${uid}" style="width:100%;padding:6px 8px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:12px">
          ${dirOpts}
        </select>
      </div>

      <div style="display:flex;gap:6px;justify-content:flex-end">
        <button onclick="this.closest('[style*=\"position:fixed\"]').remove()"
                style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">取消</button>
        <button onclick="window._cwSaveVideoEdit('${uid}',${idx})"
                style="background:var(--primary);color:#fff;border:none;border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">✅ 确认</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
};

window._cwSaveVideoEdit = (uid, idx) => {
  const v = _videos[idx];
  if (!v) return;
  v.industry = document.getElementById(`cwEditInd_${uid}`)?.value || '';
  v.tags = document.getElementById(`cwEditTags_${uid}`)?.value?.trim() || '';
  v.direction = document.getElementById(`cwEditDir_${uid}`)?.value || 'auto';
  document.querySelector('[style*="position:fixed"]')?.remove();
  _renderVideoList(uid);
};

// ═══ 生成评论 ═══

window._cwGenerate = async (uid) => {
  const selectedVids = _videos.filter(v => v.checked);
  if (!selectedVids.length) { alert('请至少选择一个视频'); return; }

  const accts = _selector ? _selector.getSelected() : [];
  if (!accts || !accts.length) { alert('请至少选择一个账号'); return; }

  const perVideo = parseInt(document.getElementById(`cwPerVideo_${uid}`)?.value || '15');
  const longRatio = parseInt(document.getElementById(`cwLongRatio_${uid}`)?.value || '20') / 100;
  const aiEnhance = document.getElementById(`cwAiEnhance_${uid}`)?.checked || false;
  const totalNeeded = perVideo * selectedVids.length;

  // 检查：每个视频生成的评论数是否超过账号数
  // 如果 perVideo > 账号数，则每个视频会有多余的评论无处分配
  if (perVideo > accts.length) {
    const excess = perVideo - accts.length;
    if (!confirm(`每个视频生成 ${perVideo} 条评论，但只有 ${accts.length} 个账号。每视频多 ${excess} 条将不分配账号。继续？`)) return;
  }

  const btn = document.getElementById(`cwGenerateBtn_${uid}`);
  btn.textContent = '⏳ 生成中...'; btn.disabled = true;

  _generatedComments = [];

  // 一次 API 调用生成所有评论，然后按视频分组
  // 这样从语料池取出的每条评论全局唯一，各视频之间绝不撞车
  const allTitles = selectedVids.map(v => v.title || '').filter(Boolean).join(' | ');
  // 提取所有视频的标签去重，供后端行业分类使用
  const allTags = [...new Set(selectedVids.flatMap(v => (v.tags || '').split(/[,，]/).map(s => s.trim()).filter(Boolean)))];
  // 取多数视频的行业（如果所有视频行业不同，用通用）
  const industries = [...new Set(selectedVids.map(v => v.industry || '').filter(Boolean))];
  const batchIndustry = industries.length === 1 ? industries[0] : '';
  // 取多数视频的方向
  const dirs = [...new Set(selectedVids.map(v => v.direction || 'auto').filter(d => d !== 'auto'))];
  const batchDirection = dirs.length === 1 ? dirs[0] : 'auto';

  try {
    const r = await fetch('/api/comment-workbench/generate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_title: allTitles || '视频',
        video_tags: allTags,
        video_industry: batchIndustry,
        direction: batchDirection,
        role_distribution: _rolePcts,
        total: totalNeeded,
        ai_enhance: aiEnhance,
        long_ratio: longRatio,
      }),
    });
    const d = await r.json();
    const allComments = d.comments || [];

    // 按视频分组，每个视频分到 perVideo 条
    for (let vi = 0; vi < selectedVids.length; vi++) {
      const v = selectedVids[vi];
      const start = vi * perVideo;
      const end = Math.min(start + perVideo, allComments.length);
      const videoComments = allComments.slice(start, end);

      // 此视频的 keyword 替换
      const kw = _extractKeyword(v.title || '');
      let processed = videoComments;
      if (kw) {
        processed = videoComments.map(c => ({
          ...c,
          text: c.text ? c.text.replace(/\{keyword\}/g, kw) : c.text,
        }));
      }

      // 从此视频的评论池中，循环分配到各账号
      processed.forEach((c, ci) => {
        const acctIdx = ci % accts.length;
        _generatedComments.push({
          video_idx: vi,
          account_idx: acctIdx,
          account_id: accts[acctIdx]?.id || accts[acctIdx] || `account_${acctIdx}`,
          text: c.text,
          role: c.role,
          role_label: c.role_label || ROLE_LABELS[c.role] || c.role,
          is_long: !!c.is_long,
        });
      });
    }
  } catch (e) {
    console.error('生成评论失败:', e);
    alert('❌ 生成失败: ' + (e.message || e));
  }

  btn.textContent = '🚀 生成评论'; btn.disabled = false;
  _renderPreview(uid);
};

function _extractKeyword(title) {
  // 从标题提取短关键词用于 {keyword} 模板替换
  if (!title) return '';
  // 优先取行业关键词
  const m = title.match(/(?:关于|分享|推荐|说说|聊聊|如何|怎么|什么|为什么)(.{2,8})/);
  if (m) return m[1];
  // 取第一个有意义的词
  const words = title.replace(/[的在了是就都和与及、，。！？]/g, ' ').split(/\s+/).filter(Boolean);
  return words[0] || title.slice(0, 6);
}

// ═══ 预览 ═══

function _renderPreview(uid) {
  const wrap = document.getElementById(`cwPreview_${uid}`);
  const list = document.getElementById(`cwCommentList_${uid}`);
  const count = document.getElementById(`cwPreviewCount_${uid}`);
  if (!wrap || !list) return;

  if (!_generatedComments.length) {
    wrap.style.display = 'none';
    return;
  }

  wrap.style.display = 'block';
  count.textContent = `共 ${_generatedComments.length} 条 | ${_videos.filter(v=>v.checked).length} 个视频 | ${_selector?.getSelected()?.length || 0} 个账号`;

  const selectedVids = _videos.filter(v => v.checked);

  list.innerHTML = _generatedComments.map((c, i) => {
    const v = selectedVids[c.video_idx];
    const videoLabel = v ? (v.title ? v.title.slice(0, 20) : _shortenUrl(v.url, 20)) : `视频#${c.video_idx + 1}`;
    const roleColor = _sliderColor(c.role);
    return `
      <div style="display:flex;align-items:center;gap:4px;padding:4px 8px;background:var(--bg3);border-radius:4px;font-size:10px;border-left:3px solid ${roleColor}">
        <span style="font-size:9px;color:var(--text2);min-width:16px">#${i + 1}</span>
        <span style="font-size:9px;color:var(--text2);min-width:40px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${v ? (v.title||v.url) : ''}">📹 ${videoLabel}</span>
        <span style="font-size:9px;padding:1px 4px;border-radius:3px;background:${roleColor}20;color:${roleColor};min-width:35px;text-align:center">${c.role_label}${c.is_long ? '📖' : ''}</span>
        <span style="font-size:9px;color:var(--text2);min-width:60px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">👤 ${c.account_id}</span>
        <span style="flex:1;color:var(--text);min-width:0">${escapeHtml(c.text)}</span>
        <button onclick="window._cwEditComment(${i},'${uid}')" style="background:none;border:none;cursor:pointer;font-size:11px;opacity:.5" title="编辑">✏️</button>
        <button onclick="window._cwDeleteComment(${i},'${uid}')" style="background:none;border:none;cursor:pointer;font-size:11px;opacity:.3" title="删除">✕</button>
      </div>`;
  }).join('');
}

window._cwEditComment = (idx, uid) => {
  const c = _generatedComments[idx];
  if (!c) return;
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:99999;display:flex;align-items:center;justify-content:center';
  overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };
  overlay.innerHTML = `
    <div style="background:var(--bg2);border-radius:12px;padding:20px;max-width:500px;width:90%">
      <div style="font-size:14px;font-weight:600;margin-bottom:4px">✏️ 编辑评论 #${idx + 1}</div>
      <div style="font-size:10px;color:var(--text2);margin-bottom:6px">
        角色：${c.role_label} | 账号：${c.account_id} | 视频 #${c.video_idx + 1}
      </div>
      <textarea id="cwEditText_${uid}" style="width:100%;min-height:80px;padding:6px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:12px">${escapeHtml(c.text)}</textarea>
      <div style="display:flex;gap:6px;justify-content:flex-end;margin-top:8px">
        <button onclick="this.closest('[style*=\"position:fixed\"]').remove()" style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">取消</button>
        <button onclick="window._cwSaveEdit(${idx},'${uid}')" style="background:var(--primary);color:#fff;border:none;border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">✅ 保存</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
};

window._cwSaveEdit = (idx, uid) => {
  const text = document.getElementById(`cwEditText_${uid}`)?.value?.trim();
  if (!text) return;
  if (_generatedComments[idx]) _generatedComments[idx].text = text;
  document.querySelector('[style*="position:fixed"]')?.remove();
  _renderPreview(uid);
};

window._cwDeleteComment = (idx, uid) => {
  _generatedComments.splice(idx, 1);
  _renderPreview(uid);
};

window._cwRegenerate = (uid) => {
  _generatedComments = [];
  window._cwGenerate(uid);
};

// ═══ 分发 ═══

window._cwDispatch = async (uid) => {
  if (!_generatedComments.length) { alert('没有可分发的内容'); return; }
  if (!confirm(`确认分发 ${_generatedComments.length} 条评论？`)) return;

  const resultEl = document.getElementById(`cwResult_${uid}`);
  const contentEl = document.getElementById(`cwResultContent_${uid}`);
  resultEl.style.display = 'block';
  contentEl.innerHTML = '⏳ 分发中...';

  const selectedVids = _videos.filter(v => v.checked);
  const accts = _selector ? _selector.getSelected() : [];

  let success = 0, fail = 0;
  const results = [];

  for (let i = 0; i < _generatedComments.length; i++) {
    const c = _generatedComments[i];
    const v = selectedVids[c.video_idx];
    contentEl.innerHTML = `⏳ 分发中 ${i + 1}/${_generatedComments.length}...`;

    try {
      const r = await fetch('/api/ops/run', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'smart_comment',
          accounts: [c.account_id],
          params: {
            urls: [v ? v.url : ''],
            direction: 'praise',
            custom_comment: c.text,
            skip_analysis: true,
          },
        }),
      });
      const d = await r.json();
      if (d.status === 'accepted' || d.status === 'ok') {
        success++;
        results.push(`#${i + 1} ${c.account_id} [${c.role_label}] ✅`);
      } else {
        fail++;
        results.push(`#${i + 1} ${c.account_id} ❌ ${d.message || d.error || ''}`);
      }
    } catch (e) {
      fail++;
      results.push(`#${i + 1} ${c.account_id} ❌ ${e.message}`);
    }
  }

  contentEl.innerHTML = `
    <div style="margin-bottom:6px;font-weight:600">完成：成功 ${success} / 失败 ${fail} / 共 ${_generatedComments.length}</div>
    <div style="font-size:10px;background:var(--bg3);padding:8px;border-radius:4px;max-height:300px;overflow-y:auto">
      ${results.join('<br>')}
    </div>
  `;
};

// ═══ 工具 ═══

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
