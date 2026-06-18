/**
 * 对账检查视图（v2 — 统计卡片 + 维度筛选 + 状态明细 + 导出）
 */
export async function loadView(container) {
  const uid = 'fr_' + Math.random().toString(36).slice(2, 6);
  let _rawData = null;  // 缓存上次对账结果

  container.innerHTML = `
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">🔍 对账检查</h2>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">检查本机是否符合 ORACLE.yaml 宪法定义</p>

      <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
        <button onclick="window._doFleetReconcile('${uid}')" style="background:var(--primary);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px">🔍 执行对账</button>
        <button id="exportBtn_${uid}" onclick="window._exportReconcile('${uid}')" style="display:none;background:var(--bg2);color:var(--text);border:1px solid var(--border);padding:8px 16px;border-radius:6px;cursor:pointer;font-size:12px">📋 导出报告</button>
      </div>

      <!-- 统计卡片 -->
      <div id="stats_${uid}" style="display:none;margin-bottom:12px">
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:8px">
          <div style="background:var(--bg3);border-radius:8px;padding:10px 14px;text-align:center">
            <div style="font-size:11px;color:var(--text2)">总项</div>
            <div id="statTotal_${uid}" style="font-size:22px;font-weight:500;margin-top:4px">0</div>
          </div>
          <div id="statPassCard_${uid}" style="background:#EAF3DE;border-radius:8px;padding:10px 14px;text-align:center">
            <div style="font-size:11px;color:#27500A">通过</div>
            <div id="statPass_${uid}" style="font-size:22px;font-weight:500;color:#3B6D11;margin-top:4px">0</div>
          </div>
          <div id="statWarnCard_${uid}" style="background:#FAEEDA;border-radius:8px;padding:10px 14px;text-align:center">
            <div style="font-size:11px;color:#633806">警告</div>
            <div id="statWarn_${uid}" style="font-size:22px;font-weight:500;color:#854F0B;margin-top:4px">0</div>
          </div>
          <div id="statFailCard_${uid}" style="background:#FCEBEB;border-radius:8px;padding:10px 14px;text-align:center">
            <div style="font-size:11px;color:#791F1F">失败</div>
            <div id="statFail_${uid}" style="font-size:22px;font-weight:500;color:#A32D2D;margin-top:4px">0</div>
          </div>
          <div style="background:var(--bg3);border-radius:8px;padding:10px 14px;text-align:center">
            <div style="font-size:11px;color:var(--text2)">通过率</div>
            <div id="statRate_${uid}" style="font-size:22px;font-weight:500;margin-top:4px">0%</div>
          </div>
        </div>
      </div>

      <!-- 筛选 tab -->
      <div id="filter_${uid}" style="display:none;margin-bottom:10px">
        <div style="display:flex;gap:6px;flex-wrap:wrap;font-size:12px">
          ${['全部','环境','目录','文件','Git','服务','任务'].map((label, i) =>
            `<div id="filterTab_${uid}_${i}" class="reconcile-filter-tab" style="height:28px;padding:0 14px;border-radius:6px;display:inline-flex;align-items:center;cursor:pointer;background:${i===0?'var(--primary)':'var(--bg3)'};color:${i===0?'#fff':'var(--text)'}" onclick="window._filterReconcile('${uid}',${i})">${label}</div>`
          ).join('')}
        </div>
      </div>

      <!-- 明细 -->
      <div id="detail_${uid}" style="display:none">
        <div style="font-size:11px;color:var(--text2);margin-bottom:6px">明细</div>
        <div id="detailList_${uid}" style="display:flex;flex-direction:column;gap:4px"></div>
      </div>

      <!-- 原始日志 -->
      <div id="log_${uid}" style="margin-top:12px;background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:300px;overflow:auto;display:none"></div>
    </div>`;

  // ── 执行对账 ──
  window._doFleetReconcile = window._doFleetReconcile || (async function(uid) {
    const logEl = document.getElementById('log_' + uid);
    const statsEl = document.getElementById('stats_' + uid);
    const filterEl = document.getElementById('filter_' + uid);
    const detailEl = document.getElementById('detail_' + uid);
    const detailList = document.getElementById('detailList_' + uid);

    if (!logEl) return;
    logEl.style.display = '';
    logEl.textContent = '⏳ 执行对账...\n';

    try {
      const r = await fetch('/api/fleet/reconcile', { method: 'POST', timeout: 120000 });
      const d = await r.json();
      const output = d.output || JSON.stringify(d, null, 2);
      logEl.textContent = output;

      // 解析结构化数据
      _rawData = parseReconcileOutput(output);
      renderReconcileStats(uid, _rawData);

    } catch(e) {
      logEl.textContent = '❌ ' + e.message;
    }
  });

  // ── 解析对账输出 ──
  function parseReconcileOutput(text) {
    const items = [];
    let currentSection = '';

    const lines = text.split('\n');
    for (const line of lines) {
      const trimmed = line.replace(/\u001b\[[\d;]+m/g, '').trim();  // strip ANSI
      if (!trimmed) continue;

      // Section header: 「━━━ N. Section ━━━」 or 「═...═」
      if (/^[═━]{3,}\s*\d+\.\s/.test(trimmed)) {
        currentSection = trimmed.replace(/[═━\s]+/g, ' ').trim();
        continue;
      }

      // Status item: 「  ✅ Item: detail」 or 「  ⚠️ Item」 or 「  ❌ Item」
      let status = null;
      let content = trimmed;
      if (/^✅/.test(trimmed)) { status = 'pass'; content = trimmed.replace(/^✅\s*/, ''); }
      else if (/^⚠️/.test(trimmed)) { status = 'warn'; content = trimmed.replace(/^⚠️\s*/, ''); }
      else if (/^❌/.test(trimmed)) { status = 'fail'; content = trimmed.replace(/^❌\s*/, ''); }

      if (status && content) {
        // Split into label and detail
        const colonIdx = content.indexOf(':');
        let label = content;
        let detail = '';
        if (colonIdx > 0) {
          label = content.slice(0, colonIdx).trim();
          detail = content.slice(colonIdx + 1).trim();
        }
        items.push({ status, label, detail, section: currentSection });
      }
    }

    return items;
  }

  // ── 渲染统计和明细 ──
  function renderReconcileStats(uid, items) {
    const total = items.length;
    const pass = items.filter(i => i.status === 'pass').length;
    const warn = items.filter(i => i.status === 'warn').length;
    const fail = items.filter(i => i.status === 'fail').length;
    const rate = total > 0 ? Math.round(pass / total * 100) : 0;

    // Stats cards
    document.getElementById('statTotal_' + uid).textContent = total;
    document.getElementById('statPass_' + uid).textContent = pass;
    document.getElementById('statWarn_' + uid).textContent = warn;
    document.getElementById('statFail_' + uid).textContent = fail;
    document.getElementById('statRate_' + uid).textContent = rate + '%';

    document.getElementById('stats_' + uid).style.display = '';
    document.getElementById('filter_' + uid).style.display = '';
    document.getElementById('detail_' + uid).style.display = '';

    const exportBtn = document.getElementById('exportBtn_' + uid);
    if (exportBtn) exportBtn.style.display = '';

    // Stats card colors
    const passCard = document.getElementById('statPassCard_' + uid);
    const warnCard = document.getElementById('statWarnCard_' + uid);
    const failCard = document.getElementById('statFailCard_' + uid);

    if (pass > 0 && fail === 0) {
      passCard.style.background = '#EAF3DE';
    } else if (total > 0 && fail === 0) {
      // warn only
    } else if (fail > 0) {
      failCard.style.background = '#FCEBEB';
    }

    // Store data for filters
    _rawData = items;
    // Set all filter tab (index 0) active by default
    window._filterReconcile(uid, 0);
  }

  // ── 筛选 ──
  window._filterReconcile = window._filterReconcile || function(uid, tabIdx) {
    const tabs = document.querySelectorAll('#filter_' + uid + ' [id^="filterTab_"]');
    tabs.forEach((t, i) => {
      t.style.background = i === tabIdx ? 'var(--primary)' : 'var(--bg3)';
      t.style.color = i === tabIdx ? '#fff' : 'var(--text)';
    });

    const filterLabels = ['全部', '环境', '目录', '文件', 'Git', '服务', '任务'];
    const filter = filterLabels[tabIdx];

    let filtered = _rawData || [];
    if (filter !== '全部') {
      filtered = filtered.filter(i => i.section.includes(filter));
    }

    renderDetailList(uid, filtered);
  };

  // ── 渲染明细列表 ──
  function renderDetailList(uid, items) {
    const list = document.getElementById('detailList_' + uid);
    if (!list) return;

    if (items.length === 0) {
      list.innerHTML = '<div style="font-size:12px;color:var(--text2);padding:8px">无匹配项</div>';
      return;
    }

    let html = '';
    for (const item of items) {
      const icon = item.status === 'pass' ? '✅' : item.status === 'warn' ? '⚠️' : '❌';
      const color = item.status === 'pass' ? 'var(--green)' : item.status === 'warn' ? 'var(--amber)' : 'var(--red)';
      html += `<div style="display:flex;gap:8px;align-items:flex-start;padding:6px 8px;background:var(--bg3);border-radius:6px;font-size:12px;line-height:1.5">`;
      html += `<span style="color:${color};flex-shrink:0">${icon}</span>`;
      html += `<span style="color:var(--text2);flex-shrink:0;min-width:80px">${escapeHtml(item.label)}</span>`;
      if (item.detail) html += `<span>${escapeHtml(item.detail)}</span>`;
      html += `</div>`;
    }
    list.innerHTML = html;
  }

  // ── 导出报告 ──
  window._exportReconcile = window._exportReconcile || function(uid) {
    if (!_rawData || _rawData.length === 0) return;

    const pass = _rawData.filter(i => i.status === 'pass').length;
    const warn = _rawData.filter(i => i.status === 'warn').length;
    const fail = _rawData.filter(i => i.status === 'fail').length;
    const total = _rawData.length;
    const rate = total > 0 ? Math.round(pass / total * 100) : 0;
    const now = new Date().toLocaleString();

    let md = `# AgentOS 联邦对账报告\n\n`;
    md += `**生成时间**: ${now}\n\n`;
    md += `## 统计\n\n`;
    md += `| 指标 | 数值 |\n|:-----|:-----|\n`;
    md += `| 总项 | ${total} |\n`;
    md += `| 通过 | ${pass} |\n`;
    md += `| 警告 | ${warn} |\n`;
    md += `| 失败 | ${fail} |\n`;
    md += `| 通过率 | ${rate}% |\n\n`;
    md += `## 明细\n\n`;
    md += `| 状态 | 检查项 | 详情 |\n|:-----|:-------|:------|\n`;
    for (const item of _rawData) {
      const icon = item.status === 'pass' ? '✅' : item.status === 'warn' ? '⚠️' : '❌';
      md += `| ${icon} | ${item.label} | ${item.detail} |\n`;
    }

    // Copy to clipboard
    navigator.clipboard.writeText(md).then(() => {
      const btn = document.getElementById('exportBtn_' + uid);
      if (btn) {
        const orig = btn.textContent;
        btn.textContent = '✅ 已复制';
        setTimeout(() => { btn.textContent = orig; }, 2000);
      }
    }).catch(() => {
      // Fallback: show in textarea
      const ta = document.createElement('textarea');
      ta.value = md;
      ta.style.cssText = 'position:fixed;left:-9999px';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    });
  };

  function escapeHtml(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
}
