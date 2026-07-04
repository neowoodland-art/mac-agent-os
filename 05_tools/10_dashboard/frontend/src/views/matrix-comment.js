/**
 * 智能评论视图（v2）— 支持 smart_comment 预分析+预览+修改+分发
 *
 * 流程: 选账号 → 填链接 → 分析视频 → 预览可编辑 → 确认分发
 * 后端: POST /api/ops/run {type:"smart_comment", ...}
 *       GET  /api/matrix/corpus      — 语料分类列表
 *       GET  /api/matrix/accounts    — 账号列表
 */

import { apiRequest, confirmExecute } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

let _selector = null;
let _previewData = {};  // {url: {title, industry, comment}}
let _uid = '';
let _allCorpusCategories = [];

export async function loadView(container, params) {
  _uid = container.id || 'sc';
  _previewData = {};

  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border)">
        <!-- 标题 -->
        <div style="font-weight:600;font-size:14px;margin-bottom:10px">
          💬 定向评论
          <span style="font-size:10px;color:var(--text2);font-weight:400">分析预览后手动分发，或一键分析+自动分发</span>
        </div>

        <!-- 账号选择 -->
        <div id="acctList_${_uid}" style="margin-bottom:8px"><div class="loading">⏳ 加载账号列表...</div></div>

        <!-- 参数输入 -->
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
          <textarea id="urls_${_uid}" placeholder="视频链接（每行一个，支持多个）" rows="3"
                    style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
          <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:160px">
            <select id="dir_${_uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
              <option value="praise">👍 称赞</option>
              <option value="question">🤔 提问</option>
              <option value="empathy">💗 共鸣</option>
              <option value="agree">✅ 认同</option>
            </select>
            <select id="corpus_${_uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
              <option value="">🌐 自动匹配</option>
            </select>
            <div style="display:flex;gap:4px">
              <button id="btn_analyze_${_uid}" onclick="window._sc_analyze('${_uid}')"
                      style="flex:1;background:var(--primary);color:#fff;border:none;padding:5px 8px;border-radius:4px;cursor:pointer;font-size:11px">🔍 分析预览</button>
              <button id="btn_go_${_uid}" onclick="window._sc_go('${_uid}')"
                      style="flex:1;background:#16a34a;color:#fff;border:none;padding:5px 8px;border-radius:4px;cursor:pointer;font-size:11px">🚀 一键执行</button>
            </div>
          </div>
        </div>

        <!-- 状态/结果 -->
        <div id="result_${_uid}" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>

      <!-- 分析结果预览区 -->
      <div id="preview_${_uid}" style="display:none;margin-top:10px"></div>
    </div>`;

  // 加载账号 + 语料分类
  try {
    const [acctRes, corpRes] = await Promise.all([
      apiRequest('/matrix/accounts'),
      apiRequest('/matrix/corpus').catch(() => ({ categories: [] })),
    ]);
    const accts = Array.isArray(acctRes) ? acctRes : (acctRes.accounts || []);
    _allCorpusCategories = corpRes.categories || [];

    const listEl = document.getElementById(`acctList_${_uid}`);
    if (listEl) {
      _selector = createAccountSelector(listEl, {
        accounts: accts,
        checkAll: false,
        height: '180px',
        showBlueprint: false,
        showCollectTime: false,
      });
    }
  } catch (e) {
    const el = document.getElementById(`acctList_${_uid}`);
    if (el) el.innerHTML = `<div class="error">❌ ${e.message}</div>`;
  }

  // 填充语料分类下拉
  const corpusSel = document.getElementById(`corpus_${_uid}`);
  if (corpusSel) {
    const corpusCats = _allCorpusCategories;
    corpusCats.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.name;
      opt.textContent = `${c.name} (${(c.accessible||[]).join(',')||'通用'})`;
      corpusSel.appendChild(opt);
    });
  }

  // 如果是从账号中心带过来的账号参数
  if (params && params.accounts && _selector) {
    setTimeout(() => {
      const accts = params.accounts;
      const cbs = document.querySelectorAll(`#acctList_${_uid} .acct-cb`);
      cbs.forEach(cb => { if (accts.includes(cb.value)) cb.checked = true; });
    }, 300);
  }

  registerGlobals(_uid);
}

function registerGlobals(uid) {
  if (window[`_sc_ready_${uid}`]) return;
  window[`_sc_ready_${uid}`] = true;

  window[`_sc_modeChange`] = (u) => {
    const isSmart = document.querySelector(`input[name="mode_${u}"]:checked`).value === 'smart';
    document.getElementById(`btn_analyze_${u}`).style.display = isSmart ? '' : 'none';
    document.getElementById(`btn_go_${u}`).style.display = isSmart ? 'none' : '';
    if (!isSmart) {
      document.getElementById(`preview_${u}`).style.display = 'none';
    }
  };

  window[`_sc_analyze`] = async (u) => {
    const selected = _selector?.getSelected() || [];
    const urlsText = document.getElementById(`urls_${u}`)?.value;
    const direction = document.getElementById(`dir_${u}`)?.value || 'praise';
    const corpusCategory = document.getElementById(`corpus_${u}`)?.value || '';
    const resultEl = document.getElementById(`result_${u}`);
    const previewEl = document.getElementById(`preview_${u}`);

    if (!urlsText || !urlsText.trim()) { resultEl.textContent = '请填写至少一个视频链接'; return; }
    const urls = urlsText.split('\n').map(u => u.trim()).filter(u => u);
    if (!urls.length) { resultEl.textContent = '请填写有效的视频链接'; return; }
    if (!selected.length) { resultEl.textContent = '请先选择要执行的账号'; return; }

    resultEl.textContent = `⏳ 正在分析 ${urls.length} 个视频...`;
    previewEl.style.display = 'none';

    // 取第一个账号的 industry
    const firstAcctId = selected[0].id;

    try {
      const resp = await apiRequest('/ops/run', {
        method: 'POST',
        body: JSON.stringify({
          type: 'smart_comment',
          accounts: [firstAcctId],
          params: {
            urls,
            direction,
            corpus_category: corpusCategory || undefined,
            preview: true
          }
        })
      });
      // preview mode 返回 {status, preview: {url: {title, industry, comment}}}
      const preview = resp.preview || {};
      const items = Object.entries(preview);

      if (!items.length) {
        resultEl.textContent = '⚠️ 分析完成但没有返回结果';
        return;
      }

      _previewData = preview;

      // 渲染预览区
      previewEl.innerHTML = `
        <div style="font-weight:600;font-size:12px;margin-bottom:6px;color:var(--text)">📋 分析结果（共 ${items.length} 个视频）
          <span style="font-size:10px;color:var(--text2);font-weight:400"> — 可修改预评论后确认分发</span>
        </div>
        ${items.map(([url, data]) => `
          <div style="background:var(--bg2);border-radius:6px;padding:8px 10px;border:1px solid var(--border);margin-bottom:4px">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
              <span style="font-size:11px;color:var(--text2);max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(url.slice(0, 60))}</span>
              <span class="industry-tag" style="font-size:9px;padding:1px 6px;border-radius:3px;background:${data.industry === 'health' ? 'rgba(34,197,94,.15)' : 'var(--bg3)'};color:${data.industry === 'health' ? '#16a34a' : 'var(--text2)'}">${data.industry || 'general'}</span>
              <span style="font-size:10px;color:var(--text2)">${escapeHtml(data.title || '').slice(0, 30)}</span>
            </div>
            <div style="display:flex;gap:6px;align-items:center">
              <input class="sc-preview-input" data-url="${escapeHtml(url)}"
                     value="${escapeHtml(data.comment || '')}"
                     style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;font-size:11px">
              <span style="font-size:9px;color:var(--text2);cursor:pointer" onclick="navigator.clipboard.writeText(this.parentElement.querySelector('input').value)">📋</span>
            </div>
          </div>
        `).join('')}
        <div style="font-size:10px;color:var(--text2);margin-top:6px;text-align:center">
          当前选中 ${selected.length} 个账号，分发后将产生 ${items.length * selected.length} 条评论任务（P0）
        </div>
        <button onclick="window[\`_sc_confirmDistribute\`]('${u}')"
                style="background:#16a34a;color:#fff;border:none;padding:5px 20px;border-radius:4px;cursor:pointer;font-size:12px;margin-top:6px;float:right">✅ 确认并分发</button>
        <div style="clear:both"></div>
      `;

      previewEl.style.display = 'block';
      resultEl.textContent = `✅ 分析完成，${items.length} 个视频`;
    } catch (e) {
      resultEl.textContent = `❌ 分析失败: ${e.message}`;
    }
  };

  window[`_sc_confirmDistribute`] = async (u) => {
    const selected = _selector?.getSelected() || [];
    if (!selected.length) { alert('请选择账号'); return; }

    // 读取用户修改后的预评论
    const inputs = document.querySelectorAll('.sc-preview-input');
    const comments = {};
    inputs.forEach(inp => {
      const url = inp.getAttribute('data-url');
      comments[url] = inp.value;
    });

    if (!Object.keys(comments).length) { alert('没有可分发的评论'); return; }

    // 确认弹窗
    const count = selected.length * Object.keys(comments).length;
    const confirmed = await confirmExecute(
      `确认分发到 ${selected.length} 个账号`,
      `共 ${count} 条评论任务（P0 优先）\n${Object.entries(comments).slice(0, 3).map(([url, txt]) => `${url.slice(0, 30)} → ${txt.slice(0, 25)}`).join('\n')}${Object.keys(comments).length > 3 ? '\n...' : ''}`
    );
    if (!confirmed) return;

    const resultEl = document.getElementById(`result_${u}`);
    resultEl.textContent = `⏳ 正在分发 ${count} 条任务...`;

    try {
      const resp = await apiRequest('/ops/run', {
        method: 'POST',
        body: JSON.stringify({
          type: 'smart_comment',
          accounts: selected.map(s => s.id),
          params: {
            urls: Object.keys(comments),
            comments,
            direction: document.getElementById(`dir_${u}`)?.value || 'praise',
          }
        })
      });
      resultEl.textContent = `✅ 已分发 ${count} 条评论任务 (P0)`;
    } catch (e) {
      resultEl.textContent = `❌ 分发失败: ${e.message}`;
    }
  };

  // 一键执行模式：分析+自动分发（不预览）
  window[`_sc_go`] = async (u) => {
    const selected = _selector?.getSelected() || [];
    const urlsText = document.getElementById(`urls_${u}`)?.value;
    const dir = document.getElementById(`dir_${u}`)?.value;
    const corpus = document.getElementById(`corpus_${u}`)?.value || '';
    const resultEl = document.getElementById(`result_${u}`);

    if (!urlsText || !urlsText.trim()) { resultEl.textContent = '请填写至少一个视频链接'; return; }
    const urls = urlsText.split('\n').map(u => u.trim()).filter(u => u);
    if (!selected.length) { resultEl.textContent = '请先选择账号'; return; }

    const count = selected.length * urls.length;
    const details = `账号 ${selected.length} 个 · 视频 ${urls.length} 个\n方向: ${dir} · 语料: ${corpus || '自动'}`;
    const ok = await confirmExecute(`即将一键分析并分发 ${count} 条评论`, details);
    if (!ok) { resultEl.textContent = '已取消'; return; }

    resultEl.textContent = `⏳ 分析 ${urls.length} 个视频并分发到 ${selected.length} 个账号...`;

    try {
      const resp = await apiRequest('/ops/run', {
        method: 'POST',
        body: JSON.stringify({
          type: 'smart_comment',
          accounts: selected.map(s => s.id),
          params: {
            urls,
            direction: dir,
            corpus_category: corpus || undefined,
            preview: false
          }
        })
      });
      // 显示进度日志
      const machines = resp?.machines || {};
      let log = '';
      for (const [m, data] of Object.entries(machines)) {
        const okc = data?.success || 0;
        const failc = data?.failed || 0;
        log += `🖥 ${m}: ✅${okc} ❌${failc}\n`;
      }
      resultEl.textContent = log || `✅ 已分发 ${count} 条评论任务 (P0)`;
    } catch (e) {
      resultEl.textContent = `❌ 执行失败: ${e.message}`;
    }
  };
}

function escapeHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
