/**
 * 智能评论视图（v3）— 导入热帖 + 跳过分析 + 执行记录
 *
 * 流程:
 *   导入模式: 点"导入热帖" → 选择视频 → 导入 → 一键执行（跳过分析）
 *   手动模式: 粘贴URL → 分析预览 → 确认分发
 * 后端: POST /api/ops/run {type:"smart_comment", ...}
 *       POST /api/ops/import-topics
 *       POST/GET /api/ops/batch-log
 */

import { apiRequest, confirmExecute } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

let _selector = null;
let _previewData = {};
let _uid = '';
let _allCorpusCategories = [];
let _importedTitles = {};     // {url: "标题文本"} — 导入热帖时存
let _apiUrl = localStorage.getItem('_sc_api_url') || 'https://wx.tyhtak.com/api/biz/activity/api/v1/activity/recordswx1';

/* ─── 加载视图 ─────────────────────────────────── */
export async function loadView(container, params) {
  _uid = container.id || 'sc';
  _previewData = {};
  _importedTitles = {};

  container.innerHTML = `
    <div style="padding:16px">
      <!-- 主面板 -->
      <div style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:14px;margin-bottom:10px">
          💬 定向评论
          <span style="font-size:10px;color:var(--text2);font-weight:400">导入热帖一键分发，或手动粘贴分析后分发</span>
        </div>

        <!-- ⚙ 数据源设置（可折叠） -->
        <details style="margin-bottom:8px;font-size:11px">
          <summary style="cursor:pointer;color:var(--text2)">⚙ 数据源设置</summary>
          <div style="margin-top:6px;display:flex;gap:6px;align-items:center">
            <input id="apiUrl_${_uid}" type="text" value="${escapeHtml(_apiUrl)}"
                   style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;font-size:11px">
            <button id="btn_testApi_${_uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px">测试连接</button>
            <span id="apiTestResult_${_uid}" style="font-size:10px;color:var(--text2)"></span>
          </div>
        </details>

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
            <details style="font-size:10px;margin:2px 0">
              <summary style="cursor:pointer;color:var(--text2)">📂 语料分类（可多选）</summary>
              <div id="corpusList_${_uid}" style="margin-top:4px;max-height:120px;overflow-y:auto;background:var(--bg3);border-radius:4px;padding:4px">
                <label style="display:flex;align-items:center;gap:4px;padding:2px 4px;cursor:pointer;font-size:10px"><input type="checkbox" class="corpus-cb-${_uid}" value="" checked onchange="window._sc_updateCorpus('${_uid}')"> 🌐 自动匹配</label>
              </div>
            </details>
            <input id="corpusInput_${_uid}" type="hidden" value="">

            <label style="display:flex;align-items:center;gap:4px;font-size:10px;color:var(--text2);cursor:pointer">
              <input id="skipAnalysis_${_uid}" type="checkbox" checked>
              ⏭ 跳过分析（导入热帖时默认开启）
            </label>
            <div style="display:flex;gap:4px">
              <button id="btn_import_${_uid}" onclick="window._sc_import('${_uid}')"
                      style="flex:1;background:var(--primary);color:#fff;border:none;padding:5px 8px;border-radius:4px;cursor:pointer;font-size:11px">📥 导入热帖</button>
              <button id="btn_go_${_uid}" onclick="window._sc_go('${_uid}')"
                      style="flex:1;background:#16a34a;color:#fff;border:none;padding:5px 8px;border-radius:4px;cursor:pointer;font-size:11px">🚀 一键执行</button>
            </div>
          </div>
        </div>

        <!-- 状态/结果 -->
        <div id="result_${_uid}" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>

      <!-- 导入面板（折叠） -->
      <div id="importPanel_${_uid}" style="display:none;margin-top:10px"></div>

      <!-- 分析预览区 -->
      <div id="preview_${_uid}" style="display:none;margin-top:10px"></div>

      <!-- 📋 执行记录 -->
      <div id="batchLogs_${_uid}" style="margin-top:16px"></div>
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
        accounts: accts, checkAll: false, height: '160px',
        showBlueprint: false, showCollectTime: false,
      });
    }
  } catch (e) {
    const el = document.getElementById(`acctList_${_uid}`);
    if (el) el.innerHTML = `<div class="error">❌ ${e.message}</div>`;
  }

  // 填充语料分类（多选 checkboxes）
  const corpusList = document.getElementById(`corpusList_${_uid}`);
  if (corpusList) {
    _allCorpusCategories.forEach(c => {
      const label = document.createElement('label');
      label.style.cssText = 'display:flex;align-items:center;gap:4px;padding:2px 4px;cursor:pointer;font-size:10px';
      label.innerHTML = `<input type="checkbox" class="corpus-cb-${_uid}" value="${c.name}" onchange="window._sc_updateCorpus('${_uid}')"> ${c.name} (${(c.accessible||[]).join(',')||'通用'})`;
      corpusList.appendChild(label);
    });
  }
  // 初始化 corpusInput
  window._sc_updateCorpus = (u) => {
    const checked = document.querySelectorAll(`.corpus-cb-${u}:checked`);
    const vals = Array.from(checked).map(cb => cb.value).filter(v => v);
    document.getElementById(`corpusInput_${u}`).value = vals.join(',');
  };

  // 加载执行记录
  _loadBatchLogs(_uid);

  registerGlobals(_uid);
}

/* ─── 注册全局函数 ──────────────────────────────────── */
function registerGlobals(uid) {
  if (window[`_sc_ready_${uid}`]) return;
  window[`_sc_ready_${uid}`] = true;

  // ⚙ 测试 API 连接
  window[`_sc_testApi`] = async (u) => {
    const url = document.getElementById(`apiUrl_${u}`)?.value;
    const resultEl = document.getElementById(`apiTestResult_${u}`);
    if (!url) { resultEl.textContent = '❌ 请输入 API 地址'; return; }
    resultEl.textContent = '⏳';
    try {
      const resp = await apiRequest('/ops/import-topics', {
        method: 'POST', body: JSON.stringify({ api_url: url, page: 1, page_size: 1 })
      });
      if (resp.status === 'ok') {
        resultEl.textContent = `✅ ${resp.total} 条`;
        localStorage.setItem('_sc_api_url', url);
        _apiUrl = url;
      } else {
        resultEl.textContent = `❌ ${resp.message}`;
      }
    } catch (e) {
      resultEl.textContent = `❌ ${e.message}`;
    }
  };

  // 📥 导入热帖
  window[`_sc_import`] = async (u) => {
    const apiUrl = document.getElementById(`apiUrl_${u}`)?.value || _apiUrl;
    if (!apiUrl) { alert('请先在⚙ 数据源设置中配置 API 地址'); return; }
    localStorage.setItem('_sc_api_url', apiUrl);
    _apiUrl = apiUrl;

    const panel = document.getElementById(`importPanel_${u}`);
    panel.style.display = 'block';
    panel.innerHTML = '<div class="loading" style="padding:10px">⏳ 加载热帖列表...</div>';

    try {
      const resp = await apiRequest('/ops/import-topics', {
        method: 'POST', body: JSON.stringify({ api_url: apiUrl, page: 1, page_size: 100 })
      });
      if (resp.status !== 'ok') {
        panel.innerHTML = `<div class="error">❌ ${resp.message || '加载失败'}</div>`;
        return;
      }
      const items = resp.items || [];
      const total = resp.total || 0;
      const unfinished = items.filter(i => !i.completed && !i.already_commented);

      panel.innerHTML = `
        <div style="background:var(--bg2);border-radius:8px;border:1px solid var(--border);overflow:hidden">
          <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 10px;background:var(--bg3);font-size:11px;font-weight:600">
            <span>📋 今日热帖（共 ${total} 条，未完成 ${unfinished.length} 条）</span>
            <div style="display:flex;gap:4px">
              <button onclick="window._sc_toggleAll('${u}', true)" style="background:none;border:1px solid var(--border);color:var(--text);padding:2px 8px;border-radius:3px;cursor:pointer;font-size:10px">☑ 全选未完成</button>
              <button onclick="window._sc_toggleAll('${u}', false)" style="background:none;border:1px solid var(--border);color:var(--text);padding:2px 8px;border-radius:3px;cursor:pointer;font-size:10px">☐ 取消全选</button>
              <button onclick="window._sc_importSelected('${u}')" style="background:#16a34a;color:#fff;border:none;padding:2px 10px;border-radius:3px;cursor:pointer;font-size:10px">导入选中</button>
            </div>
          </div>
          <div id="importList_${u}" style="max-height:320px;overflow-y:auto;font-size:10px">
            ${items.map(item => {
              const disabled = item.completed || item.already_commented;
              const tagStr = (item.tags||[]).length ? '#' + (item.tags||[]).slice(0,3).join(' #') : '';
              const timeStr = item.created_at ? item.created_at.slice(5,16) : '';
              return `<label style="display:flex;align-items:center;gap:4px;padding:4px 10px;border-bottom:1px solid var(--border);cursor:${disabled?'not-allowed':'pointer'};opacity:${disabled?0.5:1}">
                <input type="checkbox" class="import-cb" data-url="${escapeHtml(item.url)}" data-title="${escapeHtml(item.title || '')}" data-id="${item.id}" ${disabled?'disabled':''} ${!disabled?'checked':''}>
                <div style="flex:1;overflow:hidden;min-width:0">
                  <div style="font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml((item.title||'').slice(0,55))}</div>
                  <div style="font-size:8px;color:var(--text2);margin-top:1px">
                    ${escapeHtml(item.author||'')}
                    ${tagStr ? `<span style="margin-left:4px">${escapeHtml(tagStr)}</span>` : ''}
                    ${timeStr ? `<span style="margin-left:4px">${escapeHtml(timeStr)}</span>` : ''}
                  </div>
                </div>
                <span style="font-size:9px;color:${item.already_commented?'#16a34a':'var(--text2)'};white-space:nowrap">${item.already_commented?'✅已评':item.completed?'☑已完成':''}</span>
              </label>`;
            }).join('')}
          </div>
        </div>`;
    } catch (e) {
      panel.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
    }
  };

  // ☑ 全选/取消
  window[`_sc_toggleAll`] = (u, checked) => {
    document.querySelectorAll(`#importList_${u} .import-cb:not(:disabled)`).forEach(cb => cb.checked = checked);
  };

  // 导入选中
  window[`_sc_importSelected`] = (u) => {
    const checked = document.querySelectorAll(`#importList_${u} .import-cb:checked`);
    if (!checked.length) { alert('请先勾选要导入的视频'); return; }

    const urls = [];
    _importedTitles = {};
    checked.forEach(cb => {
      urls.push(cb.dataset.url);
      _importedTitles[cb.dataset.url] = cb.dataset.title;
    });
    document.getElementById(`urls_${u}`).value = urls.join('\n');
    document.getElementById(`skipAnalysis_${u}`).checked = true;
    document.getElementById(`importPanel_${u}`).style.display = 'none';
    document.getElementById(`result_${u}`).textContent = `✅ 已导入 ${urls.length} 个视频（跳过分析模式）`;
  };

  // 🔍 分析预览
  window[`_sc_analyze`] = async (u) => { /* unchanged from v2 - omitted for brevity */
    const selected = _selector?.getSelected() || [];
    const urlsText = document.getElementById(`urls_${u}`)?.value;
    const direction = document.getElementById(`dir_${u}`)?.value || 'praise';
    const corpusCategory = document.getElementById(`corpusInput_${u}`)?.value || '';
    const resultEl = document.getElementById(`result_${u}`);
    const previewEl = document.getElementById(`preview_${u}`);

    if (!urlsText || !urlsText.trim()) { resultEl.textContent = '请填写至少一个视频链接'; return; }
    const urls = urlsText.split('\n').map(x => x.trim()).filter(x => x);
    if (!urls.length) { resultEl.textContent = '请填写有效的视频链接'; return; }
    if (!selected.length) { resultEl.textContent = '请先选择要执行的账号'; return; }

    resultEl.textContent = `⏳ 正在分析 ${urls.length} 个视频...`;
    previewEl.style.display = 'none';
    const firstAcctId = selected[0].id;

    try {
      const resp = await apiRequest('/ops/run', {
        method: 'POST', body: JSON.stringify({
          type: 'smart_comment', accounts: [firstAcctId],
          params: { urls, direction, corpus_category: corpusCategory || undefined, preview: true }
        })
      });
      const preview = resp.preview || {};
      const items = Object.entries(preview);
      if (!items.length) { resultEl.textContent = '⚠️ 分析完成但没有返回结果'; return; }
      _previewData = preview;
      previewEl.innerHTML = `
        <div style="font-weight:600;font-size:12px;margin-bottom:6px">📋 分析结果（共 ${items.length} 个视频）<span style="font-size:10px;color:var(--text2);font-weight:400"> — 可修改后确认分发</span></div>
        ${items.map(([url, data]) => `
          <div style="background:var(--bg2);border-radius:6px;padding:8px 10px;border:1px solid var(--border);margin-bottom:4px">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
              <span style="font-size:11px;color:var(--text2);max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(url.slice(0,60))}</span>
              <span style="font-size:9px;padding:1px 6px;border-radius:3px;background:${data.industry==='health'?'rgba(34,197,94,.15)':'var(--bg3)'};color:${data.industry==='health'?'#16a34a':'var(--text2)'}">${data.industry||'general'}</span>
              <span style="font-size:10px;color:var(--text2)">${escapeHtml((data.title||'').slice(0,30))}</span>
            </div>
            <div style="display:flex;gap:6px;align-items:center">
              <input class="sc-preview-input" data-url="${escapeHtml(url)}" value="${escapeHtml(data.comment||'')}"
                     style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;font-size:11px">
              <span style="font-size:9px;color:var(--text2);cursor:pointer" onclick="navigator.clipboard.writeText(this.parentElement.querySelector('input').value)">📋</span>
            </div>
          </div>
        `).join('')}
        <div style="font-size:10px;color:var(--text2);margin-top:6px;text-align:center">当前选中 ${selected.length} 个账号</div>
        <button onclick="window[\`_sc_confirmDistribute\`]('${u}')" style="background:#16a34a;color:#fff;border:none;padding:5px 20px;border-radius:4px;cursor:pointer;font-size:12px;margin-top:6px;float:right">✅ 确认并分发</button>
        <div style="clear:both"></div>`;
      previewEl.style.display = 'block';
      resultEl.textContent = `✅ 分析完成，${items.length} 个视频`;
    } catch (e) {
      resultEl.textContent = `❌ 分析失败: ${e.message}`;
    }
  };

  // ✅ 确认分发（预览→手动编辑后分发）
  window[`_sc_confirmDistribute`] = async (u) => {
    const selected = _selector?.getSelected() || [];
    if (!selected.length) { alert('请选择账号'); return; }
    const inputs = document.querySelectorAll('.sc-preview-input');
    const comments = {};
    inputs.forEach(inp => { comments[inp.getAttribute('data-url')] = inp.value; });
    if (!Object.keys(comments).length) { alert('没有可分发的评论'); return; }

    const count = selected.length * Object.keys(comments).length;
    const ok = await confirmExecute(`确认分发到 ${selected.length} 个账号`, `共 ${count} 条评论任务（P0 优先）`);
    if (!ok) return;

    const resultEl = document.getElementById(`result_${u}`);
    resultEl.textContent = `⏳ 正在分发 ${count} 条任务...`;
    try {
      const resp = await apiRequest('/ops/run', {
        method: 'POST', body: JSON.stringify({
          type: 'smart_comment', accounts: selected.map(s => s.id),
          params: { urls: Object.keys(comments), comments, direction: document.getElementById(`dir_${u}`)?.value || 'praise' }
        })
      });
      resultEl.textContent = `✅ 已分发 ${count} 条评论任务 (P0)`;
      setTimeout(() => _loadBatchLogs(u), 2000);
    } catch (e) {
      resultEl.textContent = `❌ 分发失败: ${e.message}`;
    }
  };

  // 🚀 一键执行
  window[`_sc_go`] = async (u) => {
    const selected = _selector?.getSelected() || [];
    const urlsText = document.getElementById(`urls_${u}`)?.value;
    const dir = document.getElementById(`dir_${u}`)?.value;
    const corpus = document.getElementById(`corpus_${u}`)?.value || '';
    const skipAnalysis = document.getElementById(`skipAnalysis_${u}`)?.checked;
    const resultEl = document.getElementById(`result_${u}`);

    if (!urlsText || !urlsText.trim()) { resultEl.textContent = '请填写至少一个视频链接'; return; }
    const urls = urlsText.split('\n').map(x => x.trim()).filter(x => x);
    if (!selected.length) { resultEl.textContent = '请先选择账号'; return; }

    const count = selected.length * urls.length;
    const details = `账号 ${selected.length} 个 · 视频 ${urls.length} 个\n方向: ${dir}${skipAnalysis ? ' · ⏭ 跳过分析' : ''}`;
    const ok = await confirmExecute(`即将${skipAnalysis?'':'分析并'}分发 ${count} 条评论`, details);
    if (!ok) { resultEl.textContent = '已取消'; return; }

    resultEl.textContent = `⏳ 分发 ${count} 条任务...`;

    try {
      const resp = await apiRequest('/ops/run', {
        method: 'POST', body: JSON.stringify({
          type: 'smart_comment', accounts: selected.map(s => s.id),
          params: {
            urls, direction: dir, corpus_category: corpus || undefined,
            preview: false,
            skip_analysis: skipAnalysis && Object.keys(_importedTitles).length > 0,
            titles: skipAnalysis ? _importedTitles : {},
            video_ids: urls.map(u => ''),  // 前端没有 video_id，传空数组
          }
        })
      });
      const machines = resp?.per_machine || {};
      let log = '';
      const hasMachines = Object.keys(machines).length > 0;
      for (const [m, data] of Object.entries(machines)) {
        log += `🖥 ${m}: ✅${data?.success||0} ❌${data?.failed||0}\n`;
      }
      const cmdCount = resp?.commands?.length || 0;
      resultEl.textContent = hasMachines ? log : (cmdCount > 0 ? `✅ 已提交 ${cmdCount} 条任务，正在排队执行` : `✅ 已分发 ${count} 条评论任务`);
      setTimeout(() => _loadBatchLogs(u), 2000);
    } catch (e) {
      resultEl.textContent = `❌ 执行失败: ${e.message}`;
    }
  };
}

/* ─── 执行记录 ────────────────────────────────────── */
async function _loadBatchLogs(uid) {
  const el = document.getElementById(`batchLogs_${uid}`);
  if (!el) return;
  try {
    const resp = await apiRequest('/ops/batch-logs?limit=30');
    const logs = resp.logs || [];
    if (!logs.length) { el.innerHTML = ''; return; }

    el.innerHTML = `
      <details open>
        <summary style="cursor:pointer;font-weight:600;font-size:12px;color:var(--text);margin-bottom:4px">
          📋 执行记录（${logs.length} 条）
        </summary>
        <div style="font-size:10px">
          ${logs.map((log, idx) => {
            const mc = log.machine_counts || {};
            const machineStr = Object.entries(mc).map(([m, d]) => `${m}:✅${d.success||0}❌${d.failed||0}`).join(' ');
            return `<div style="background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:6px 8px;margin-bottom:3px;cursor:pointer" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span>${log.time || ''}</span>
                <span>${log.video_count||0}视频×${log.account_count||0}账号=${log.total||0}条</span>
                <span>${machineStr || '等待执行'}</span>
              </div>
            </div>
            <div style="display:none;padding:4px 8px;margin-bottom:4px;font-size:9px;color:var(--text2);background:var(--bg3);border-radius:0 0 4px 4px">
              <div>方向: ${log.direction||'-'}</div>
              <div>视频: ${(log.urls||[]).slice(0,5).map(u => u.slice(0,40)).join('; ')}${(log.urls||[]).length>5?'...':''}</div>
            </div>`;
          }).join('')}
        </div>
      </details>`;
  } catch (e) {
    // silent fail
  }
}

function escapeHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
