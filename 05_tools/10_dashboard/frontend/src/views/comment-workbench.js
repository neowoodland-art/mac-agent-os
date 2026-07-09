/**
 * comment-workbench.js — 评论工作台（v3 角色化评论）
 *
 * 流程:
 *   输入视频标题 → 调角色比例 → 一键生成 → 预览编排 → 分发
 * 后端:
 *   GET  /api/comment-workbench/roles
 *   POST /api/comment-workbench/generate
 *   POST /api/ops/run {type:"smart_comment", ...}
 */

const BASE = '/api';

// ── 角色中文标签（跟后端一致）──
const ROLE_LABELS = {
  sharer: '分享型', questioner: '提问型', sympathizer: '共情型',
  skeptic: '质疑型', sufferer: '患者型', filler: '灌水型',
  expert_ref: '推荐型',
};

let _roles = [];           // 从 API 加载的角色列表
let _rolePcts = {};        // {role_id: 当前百分比}
let _generatedComments = []; // 生成的评论列表
let _editIdx = -1;          // 正在编辑的评论索引

// ── 主入口 ──
export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载评论工作台...</div>';

  try {
    // 加载角色数据
    const rolesR = await fetch(`${BASE}/comment-workbench/roles`);
    const rolesD = await rolesR.json();
    _roles = rolesD.roles || [];
    // 初始化百分比
    _rolePcts = {};
    _roles.forEach(r => { _rolePcts[r.id] = r.default_pct; });

    render(container);
  } catch (e) {
    container.innerHTML = `<div class="error">❌ ${e.message || e}</div>`;
  }
}

function render(container) {
  const totalPct = Object.values(_rolePcts).reduce((a, b) => a + b, 0);
  const totalOk = Math.abs(totalPct - 1.0) < 0.01;

  container.innerHTML = `
    <div style="padding:16px;max-width:900px">

      <!-- ═══ 顶部：标题 + 操作按钮 ═══ -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">💬 评论工作台</h2>
        <div style="display:flex;gap:6px">
          <button onclick="window._cwLoadRoles()" style="background:var(--bg3);border:1px solid var(--border);padding:4px 10px;border-radius:6px;cursor:pointer;font-size:11px">🔄 刷新角色</button>
        </div>
      </div>

      <!-- ═══ 第一步：视频信息 ═══ -->
      <div style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-bottom:10px">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">📹 视频信息</div>
        <div style="display:flex;gap:6px">
          <input id="cwVideoTitle" type="text" placeholder="视频标题（必填）"
                 style="flex:1;padding:6px 10px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:12px">
          <input id="cwVideoTags" type="text" placeholder="标签（可选，逗号分隔）"
                 style="width:200px;padding:6px 10px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:12px">
        </div>
      </div>

      <!-- ═══ 第二步：角色比例滑条 ═══ -->
      <div style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-bottom:10px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="font-weight:600;font-size:13px">🎭 角色比例</span>
          <span id="cwPctStatus" style="font-size:11px;color:${totalOk ? 'var(--green)' : 'var(--red)'}">
            总计 ${(totalPct * 100).toFixed(0)}% ${totalOk ? '✅' : '⚠️ 需等于 100%'}
          </span>
        </div>
        <div id="cwRoleSliders" style="display:grid;gap:6px">
          ${_roles.map(r => renderRoleSlider(r)).join('')}
        </div>
      </div>

      <!-- ═══ 第三步：生成设置 ═══ -->
      <div style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-bottom:10px">
        <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
          <label style="font-size:11px;display:flex;align-items:center;gap:4px">
            生成条数
            <input id="cwTotal" type="number" value="30" min="5" max="100"
                   style="width:60px;padding:3px 6px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:11px;text-align:center">
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px">
            长评占比
            <input id="cwLongRatio" type="range" min="0" max="100" value="20"
                   oninput="document.getElementById('cwLongRatioVal').textContent=this.value+'%'"
                   style="width:100px">
            <span id="cwLongRatioVal" style="font-size:11px;color:var(--text2);min-width:35px">20%</span>
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px">
            <input type="checkbox" id="cwAiEnhance" checked>
            🧠 AI 增强改写
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px">
            <input type="checkbox" id="cwAutoDispatch" checked>
            ✅ 生成后自动分发
          </label>
          <button id="cwGenerateBtn" onclick="window._cwGenerate()"
                  style="background:var(--primary);color:#fff;border:none;padding:6px 16px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600">🚀 生成评论</button>
        </div>
      </div>

      <!-- ═══ 第四步：预览编排 ═══ -->
      <div id="cwPreview" style="display:none">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="font-weight:600;font-size:13px">📝 生成预览</span>
          <div style="display:flex;gap:6px">
            <span id="cwPreviewCount" style="font-size:11px;color:var(--text2)"></span>
            <button onclick="window._cwRegenerate()" style="background:var(--bg3);border:1px solid var(--border);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">🔄 重新生成</button>
            <button onclick="window._cwDispatch()" style="background:var(--primary);color:#fff;border:none;padding:3px 12px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600">✅ 确认分发</button>
          </div>
        </div>
        <div id="cwCommentList" style="display:grid;gap:4px"></div>
      </div>

      <!-- ═══ 第五步：分发结果 ═══ -->
      <div id="cwResult" style="display:none;background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-top:10px">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">📊 分发结果</div>
        <div id="cwResultContent" style="font-size:11px;line-height:1.6"></div>
      </div>

    </div>
  `;
}

// ── 渲染单个角色滑条 ──
function renderRoleSlider(r) {
  const pct = (_rolePcts[r.id] || 0) * 100;
  const color = _sliderColor(r.id);
  return `
    <div style="display:flex;align-items:center;gap:8px;font-size:11px">
      <span style="min-width:55px;font-weight:500">${r.label}</span>
      <input type="range" min="0" max="100" value="${Math.round(pct)}"
             data-role="${r.id}"
             oninput="window._cwUpdatePct('${r.id}', this.value)"
             style="flex:1;height:6px;accent-color:${color}">
      <span id="cwPct_${r.id}" style="min-width:35px;text-align:right;color:var(--text2)">${Math.round(pct)}%</span>
      <span style="font-size:9px;color:var(--text2)">${r.count}条</span>
    </div>
  `;
}

// 角色颜色
function _sliderColor(role) {
  const colors = {
    filler: '#8b8fa3', questioner: '#3b82f6', sharer: '#22c55e',
    sympathizer: '#f59e0b', sufferer: '#ef4444', skeptic: '#8b5cf6',
    expert_ref: '#06b6d4',
  };
  return colors[role] || '#3b82f6';
}

// ── 全局函数 ──

// 更新角色比例
window._cwUpdatePct = (roleId, val) => {
  _rolePcts[roleId] = parseInt(val) / 100;
  document.getElementById(`cwPct_${roleId}`).textContent = `${val}%`;
  // 更新总计状态
  const total = Object.values(_rolePcts).reduce((a, b) => a + b, 0);
  const ok = Math.abs(total - 1.0) < 0.01;
  const el = document.getElementById('cwPctStatus');
  if (el) el.textContent = `总计 ${(total * 100).toFixed(0)}% ${ok ? '✅' : '⚠️ 需等于 100%'}`;
};

// 重新加载角色
window._cwLoadRoles = async () => {
  const container = document.querySelector('#cwRoleSliders');
  if (!container) return;
  try {
    const r = await fetch(`${BASE}/comment-workbench/roles`);
    const d = await r.json();
    _roles = d.roles || [];
    _roles.forEach(r => {
      if (!(_r.id in _rolePcts)) _rolePcts[r.id] = r.default_pct;
    });
    container.innerHTML = _roles.map(r => renderRoleSlider(r)).join('');
  } catch(e) {
    alert('❌ 加载角色失败: ' + e.message);
  }
};

// 生成评论
window._cwGenerate = async () => {
  const title = document.getElementById('cwVideoTitle')?.value?.trim();
  if (!title) { alert('请填写视频标题'); return; }

  const btn = document.getElementById('cwGenerateBtn');
  btn.textContent = '⏳ 生成中...'; btn.disabled = true;

  const tags = document.getElementById('cwVideoTags')?.value?.trim() || '';
  const total = parseInt(document.getElementById('cwTotal')?.value || '30');
  const longRatio = parseInt(document.getElementById('cwLongRatio')?.value || '20') / 100;
  const aiEnhance = document.getElementById('cwAiEnhance')?.checked || false;

  try {
    const r = await fetch(`${BASE}/comment-workbench/generate`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_title: title,
        video_tags: tags ? tags.split(/[,，]/).map(s => s.trim()).filter(Boolean) : [],
        role_distribution: _rolePcts,
        total,
        ai_enhance: aiEnhance,
        long_ratio: longRatio,
      }),
    });
    const d = await r.json();
    _generatedComments = d.comments || [];

    renderPreview();
  } catch(e) {
    alert('❌ ' + e.message);
  }
  btn.textContent = '🚀 生成评论'; btn.disabled = false;
};

// 渲染预览
function renderPreview() {
  const wrap = document.getElementById('cwPreview');
  const list = document.getElementById('cwCommentList');
  const count = document.getElementById('cwPreviewCount');
  if (!wrap || !list) return;

  wrap.style.display = 'block';
  if (count) count.textContent = `共 ${_generatedComments.length} 条`;

  list.innerHTML = _generatedComments.map((c, i) => {
    const roleColor = _sliderColor(c.role);
    const longMark = c.is_long ? ' 📖' : '';
    return `
      <div style="display:flex;align-items:center;gap:6px;padding:4px 8px;background:var(--bg3);border-radius:4px;font-size:11px;border-left:3px solid ${roleColor}">
        <span style="font-size:9px;color:var(--text2);min-width:20px">#${i + 1}</span>
        <span style="font-size:9px;padding:1px 5px;border-radius:3px;background:${roleColor}20;color:${roleColor};min-width:45px;text-align:center">${c.role_label || ROLE_LABELS[c.role] || c.role}${longMark}</span>
        <span style="flex:1;color:var(--text)">${escapeHtml(c.text)}</span>
        <button onclick="window._cwEditComment(${i})" style="background:none;border:none;cursor:pointer;font-size:12px;opacity:.5" title="编辑">✏️</button>
        <button onclick="window._cwDeleteComment(${i})" style="background:none;border:none;cursor:pointer;font-size:12px;opacity:.3" title="删除">✕</button>
      </div>
    `;
  }).join('');
}

// 编辑评论
window._cwEditComment = (idx) => {
  const c = _generatedComments[idx];
  if (!c) return;
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:99999;display:flex;align-items:center;justify-content:center';
  overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };
  overlay.innerHTML = `
    <div style="background:var(--bg2);border-radius:12px;padding:20px;max-width:500px;width:90%">
      <div style="font-size:14px;font-weight:600;margin-bottom:8px">✏️ 编辑评论 #${idx + 1}</div>
      <div style="font-size:11px;color:var(--text2);margin-bottom:6px">角色：${c.role_label || ROLE_LABELS[c.role] || c.role}</div>
      <textarea id="cwEditText" style="width:100%;min-height:80px;padding:6px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;font-size:12px">${escapeHtml(c.text)}</textarea>
      <div style="display:flex;gap:6px;justify-content:flex-end;margin-top:8px">
        <button onclick="this.closest('div[style]').parentElement.remove()" style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">取消</button>
        <button onclick="window._cwSaveEdit(${idx})" style="background:var(--primary);color:#fff;border:none;border-radius:6px;padding:6px 16px;font-size:12px;cursor:pointer">✅ 保存</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
};

// 保存编辑
window._cwSaveEdit = (idx) => {
  const text = document.getElementById('cwEditText')?.value?.trim();
  if (!text) return;
  if (_generatedComments[idx]) {
    _generatedComments[idx].text = text;
  }
  document.querySelector('div[style*="position:fixed"]')?.remove();
  renderPreview();
};

// 删除评论
window._cwDeleteComment = (idx) => {
  _generatedComments.splice(idx, 1);
  renderPreview();
};

// 重新生成
window._cwRegenerate = () => {
  window._cwGenerate();
};

// 确认分发
window._cwDispatch = async () => {
  if (!_generatedComments.length) { alert('没有可分发的评论'); return; }
  if (!confirm(`确认分发 ${_generatedComments.length} 条评论？`)) return;

  const autoDispatch = document.getElementById('cwAutoDispatch')?.checked || false;
  const resultEl = document.getElementById('cwResult');
  const contentEl = document.getElementById('cwResultContent');
  resultEl.style.display = 'block';
  contentEl.innerHTML = '⏳ 处理中...';

  // 如果没有勾选自动分发，只显示评论列表供复制
  if (!autoDispatch) {
    contentEl.innerHTML = `
      <div style="margin-bottom:6px;color:var(--text2)">✅ 已生成 ${_generatedComments.length} 条评论（未分发）</div>
      <div style="font-size:10px;background:var(--bg3);padding:8px;border-radius:4px;white-space:pre-wrap;max-height:300px;overflow-y:auto">
        ${_generatedComments.map((c, i) => `#${i + 1} [${c.role_label || ROLE_LABELS[c.role] || c.role}] ${c.text}`).join('\n')}
      </div>
      <button onclick="navigator.clipboard.writeText(document.querySelector('#cwResultContent div:last-child').textContent)" style="margin-top:6px;background:var(--bg3);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">📋 复制全部</button>
    `;
    return;
  }

  // 自动分发模式：遍历评论执行
  let success = 0, fail = 0;
  const results = [];
  for (let i = 0; i < _generatedComments.length; i++) {
    const c = _generatedComments[i];
    contentEl.innerHTML = `⏳ 分发中 ${i + 1}/${_generatedComments.length}...`;
    try {
      const r = await fetch(`${BASE}/ops/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'smart_comment',
          accounts: [],
          params: {
            urls: [document.getElementById('cwVideoTitle')?.value?.trim() || ''],
            direction: 'praise',
            custom_comment: c.text,
          },
        }),
      });
      const d = await r.json();
      if (d.status === 'accepted' || d.status === 'ok') {
        success++;
        results.push(`#${i + 1} [${c.role_label || ROLE_LABELS[c.role] || c.role}] ✅`);
      } else {
        fail++;
        results.push(`#${i + 1} [${c.role_label || ROLE_LABELS[c.role] || c.role}] ❌ ${d.message || d.error || ''}`);
      }
    } catch(e) {
      fail++;
      results.push(`#${i + 1} ❌ ${e.message}`);
    }
  }

  contentEl.innerHTML = `
    <div style="margin-bottom:6px;font-weight:600">✅ 完成：成功 ${success} / 失败 ${fail}</div>
    <div style="font-size:10px;background:var(--bg3);padding:8px;border-radius:4px;max-height:300px;overflow-y:auto">
      ${results.join('<br>')}
    </div>
  `;
};

// ── 工具函数 ──
function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
