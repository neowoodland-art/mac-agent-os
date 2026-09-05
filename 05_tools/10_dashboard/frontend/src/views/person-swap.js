/**
 * person-swap.js — 人物置换工作台 (视频工厂·独立业务)
 *
 * 基于阿里云百炼 Wan2.2-Animate:
 *   原视频(人物A动作) + 人物参考图(人物B形象) → 输出「B 保留 A 动作」的新视频
 *
 * 后端: /api/person-swap/*
 * 注意: 账号欠费时页面顶部给出明确提示, 任务会失败(不烧重试)
 */
let _timer = null;
let _uid = 'ps';
const STATUS_META = {
  queued:     { icon: '⏳', label: '排队中',   color: '#d97706' },
  processing: { icon: '🔄', label: '处理中',   color: '#3b82f6' },
  succeeded:  { icon: '✅', label: '完成',     color: '#22c55e' },
  failed:     { icon: '❌', label: '失败',     color: '#ef4444' },
  cancelled:  { icon: '⏹',  label: '已取消',   color: '#6b7280' },
  blocked:    { icon: '🚫', label: '已拦截',   color: '#ef4444' },
};

export async function loadView(container) {
  _uid = container.id || 'ps';
  container.innerHTML = `
    <div style="padding:16px;max-width:1200px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">🔄 人物置换</h2>
        <span style="font-size:10px;color:var(--text2)">Wan2.2-Animate · 原视频 + 人物参考图 → 保留动作的新人物视频</span>
      </div>

      <!-- ═══ 状态条 ═══ -->
      <div id="${_uid}statusBar" style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px"></div>

      <!-- ═══ 创建任务 ═══ -->
      <div style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border);margin-bottom:12px">
        <div style="font-weight:600;font-size:13px;margin-bottom:10px">📥 新建置换任务</div>
        <div style="display:flex;gap:16px;flex-wrap:wrap">
          <label style="flex:1;min-width:220px;font-size:12px;color:var(--text2)">
            ① 原视频(动作来源, 支持 mp4/mov, ≤300MB)
            <input type="file" id="${_uid}videoFile" accept="video/mp4,video/quicktime,video/webm"
              style="display:block;width:100%;margin-top:4px;font-size:11px">
            <div id="${_uid}videoInfo" style="font-size:11px;margin-top:4px"></div>
          </label>
          <label style="flex:1;min-width:220px;font-size:12px;color:var(--text2)">
            ② 人物参考图(新形象, jpg/png, ≤20MB)
            <input type="file" id="${_uid}imageFile" accept="image/jpeg,image/png,image/webp"
              style="display:block;width:100%;margin-top:4px;font-size:11px">
            <div id="${_uid}imageInfo" style="font-size:11px;margin-top:4px"></div>
          </label>
        </div>
        <div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:10px">
          <label style="font-size:12px;color:var(--text2)">
            生成时长
            <select id="${_uid}duration" style="margin-left:6px;font-size:12px;background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:4px 8px">
              <option value="0">模型默认(≤10s)</option>
              <option value="5">5 秒</option>
              <option value="10">10 秒</option>
            </select>
          </label>
          <label style="flex:1;font-size:12px;color:var(--text2)">
            人物备注(选填)
            <input id="${_uid}charName" placeholder="如: 王总-商务正装" style="width:100%;margin-top:4px;font-size:12px;background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text)">
          </label>
          <label style="flex:2;font-size:12px;color:var(--text2)">
            动作/镜头描述(选填, 帮助模型理解)
            <input id="${_uid}prompt" placeholder="如: 面对镜头自然说话, 轻微手势" style="width:100%;margin-top:4px;font-size:12px;background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text)">
          </label>
        </div>
        <div style="display:flex;align-items:center;gap:12px;margin-top:12px">
          <button id="${_uid}submitBtn" onclick="window._psSubmit()"
            style="background:#22c55e;color:#000;border:none;border-radius:8px;padding:8px 22px;font-size:13px;font-weight:600;cursor:pointer">🚀 提交生成</button>
          <div id="${_uid}uploadProg" style="display:none;flex:1;height:8px;background:var(--bg3);border-radius:4px;overflow:hidden">
            <div id="${_uid}uploadBar" style="height:100%;width:0%;background:linear-gradient(90deg,#3b82f6,#22c55e);transition:width .3s"></div>
          </div>
          <span id="${_uid}uploadMsg" style="font-size:11px;color:var(--text2)"></span>
        </div>
      </div>

      <!-- ═══ 任务列表 ═══ -->
      <div style="background:var(--bg2);border-radius:10px;padding:14px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:10px">📋 任务记录 <span id="${_uid}taskCount" style="font-size:11px;color:var(--text2);margin-left:6px"></span></div>
        <div id="${_uid}taskList" style="overflow-x:auto"><div class="loading" style="padding:20px;text-align:center">加载中...</div></div>
      </div>
    </div>`;

  const vf = document.getElementById(`${_uid}videoFile`);
  const imf = document.getElementById(`${_uid}imageFile`);
  vf.onchange = () => {
    const f = vf.files[0];
    document.getElementById(`${_uid}videoInfo`).textContent = f ? `${f.name} · ${(f.size/1048576).toFixed(1)}MB` : '';
  };
  imf.onchange = () => {
    const f = imf.files[0];
    document.getElementById(`${_uid}imageInfo`).textContent = f ? `${f.name} · ${(f.size/1048576).toFixed(1)}MB` : '';
  };

  window._psSubmit = submitTask;
  await Promise.all([refreshStatus(), refreshTasks()]);
  startPolling();
}

function stopPolling() {
  if (_timer) { clearInterval(_timer); _timer = null; }
}

export function unloadView() { stopPolling(); }

// ═══ 轮询(仅页面存活时) ═══
function startPolling() {
  stopPolling();
  _timer = setInterval(async () => {
    const el = document.getElementById(`${_uid}taskList`);
    if (!el || !document.body.contains(el)) { stopPolling(); return; }
    await refreshTasks();
  }, 3000);
}

// ═══ 状态条 ═══
async function refreshStatus() {
  try {
    const r = await fetch('/api/person-swap/status');
    const d = await r.json();
    const bar = document.getElementById(`${_uid}statusBar`);
    if (!bar) return;
    const acct = d.account || {};
    const st = acct.status;
    const card = (bg, border, title, sub) => `
      <div style="flex:1;min-width:180px;background:${bg};border:1px solid ${border};border-radius:8px;padding:8px 12px">
        <div style="font-size:11px;color:var(--text2)">${title}</div>
        <div style="font-size:12px;font-weight:600;color:var(--text)">${sub}</div>
      </div>`;
    let acctCard;
    if (st === 'ok') acctCard = card('rgba(34,197,94,.08)', '#22c55e', '🟢 百炼账号', `可用 · ${d.model || ''}`);
    else if (st === 'arrears') acctCard = card('rgba(239,68,68,.08)', '#ef4444', '🔴 百炼账号欠费', '需充值/解除冻结后才能生成');
    else if (st === 'unconfigured') acctCard = card('rgba(239,68,68,.08)', '#ef4444', '⚠️ 未配置 API Key', 'agent-local → local.yaml → aliyun.api_key');
    else acctCard = card('rgba(239,68,68,.08)', '#ef4444', '❌ 账号异常', (acct.detail || '').slice(0, 60));
    bar.innerHTML = acctCard +
      card('rgba(59,130,246,.06)', '#3b82f6', '队列活跃', `${d.queue_active || 0} 个任务`) +
      card('rgba(217,119,6,.06)', '#d97706', '本月费用', `¥${(d.monthly?.used || 0).toFixed(2)} / ¥${(d.monthly?.budget || 0).toFixed(0)}`) +
      (st !== 'ok' ? `<div style="flex:2;font-size:11px;color:#ef4444;align-self:center">${(acct.detail || '')}</div>` : '');
  } catch (e) { /* 静默 */ }
}

// ═══ 任务列表 ═══
async function refreshTasks() {
  const el = document.getElementById(`${_uid}taskList`);
  if (!el) return;
  try {
    const r = await fetch('/api/person-swap/tasks?limit=30');
    const d = await r.json();
    const tasks = d.tasks || [];
    document.getElementById(`${_uid}taskCount`).textContent = `共 ${tasks.length} 条`;
    if (!tasks.length) {
      el.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text2);font-size:12px">暂无任务 — 上传原视频和人物参考图开始第一次置换</div>';
      return;
    }
    el.innerHTML = `<table style="width:100%;font-size:12px;border-collapse:collapse;min-width:900px">
      <thead><tr>
        <th style="text-align:left;padding:6px 8px;border-bottom:2px solid var(--border)">时间</th>
        <th style="text-align:left;padding:6px 8px;border-bottom:2px solid var(--border)">人物</th>
        <th style="text-align:left;padding:6px 8px;border-bottom:2px solid var(--border)">素材</th>
        <th style="text-align:left;padding:6px 8px;border-bottom:2px solid var(--border)">状态</th>
        <th style="text-align:left;padding:6px 8px;border-bottom:2px solid var(--border)">进度</th>
        <th style="text-align:left;padding:6px 8px;border-bottom:2px solid var(--border)">成片</th>
        <th style="text-align:left;padding:6px 8px;border-bottom:2px solid var(--border)">操作</th>
      </tr></thead>
      <tbody>${tasks.map(taskRow).join('')}</tbody>
    </table>`;
  } catch (e) {
    el.innerHTML = `<div class="error" style="padding:16px">❌ 加载任务失败: ${e.message}</div>`;
  }
}

function taskRow(t) {
  const meta = STATUS_META[t.status] || { icon: '❓', label: t.status, color: '#6b7280' };
  const created = (t.created_at || '').replace('T', ' ').slice(5, 16);
  const files = (t.video_info ? '' : '') + (t.source_orig ? t.source_orig.split('/').pop().split('_').pop() : '');
  const imgThumb = t.image_orig
    ? `<img src="/api/person-swap/tasks/${t.id}/file/image?t=${t.updated_at.replace(/[^0-9]/g,'')}" style="width:36px;height:36px;object-fit:cover;border-radius:6px;border:1px solid var(--border)" onerror="this.style.display='none'">`
    : '';
  const outCell = t.status === 'succeeded'
    ? `<a href="/api/person-swap/tasks/${t.id}/file/output" download style="color:#22c55e;font-weight:600">⬇ 下载</a>`
    : `<span style="color:var(--text2)">${t.status === 'processing' ? '生成中…' : '-'}</span>`;
  const cancelBtn = (t.status === 'queued' || t.status === 'processing')
    ? `<a href="#" onclick="event.preventDefault();window._psCancel('${t.id}')" style="color:#ef4444">取消</a>` : '';
  const error = t.error ? `<div style="color:#ef4444;font-size:10px;max-width:260px;white-space:normal">${esc(t.error)}</div>` : '';
  return `<tr>
    <td style="padding:5px 8px;border-bottom:1px solid var(--border);white-space:nowrap;color:var(--text2)">${created}</td>
    <td style="padding:5px 8px;border-bottom:1px solid var(--border);max-width:130px">
      <div style="display:flex;align-items:center;gap:6px">${imgThumb}<span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(t.character_name || t.id.slice(0,8))}</span></div>
      ${t.prompt ? `<div style="color:var(--text2);font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px">📝 ${esc(t.prompt)}</div>` : ''}
    </td>
    <td style="padding:5px 8px;border-bottom:1px solid var(--border);color:var(--text2);font-size:11px">${esc(files)}${t.duration_sec ? ` · ${t.duration_sec}s` : ''}</td>
    <td style="padding:5px 8px;border-bottom:1px solid var(--border)"><span style="color:${meta.color};font-weight:600">${meta.icon} ${meta.label}</span></td>
    <td style="padding:5px 8px;border-bottom:1px solid var(--border);min-width:140px">
      ${t.status === 'processing' ? progressBar(t.progress) : ''}
      <div style="font-size:10px;color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:220px">${esc(t.note || '')}</div>
      ${error}
    </td>
    <td style="padding:5px 8px;border-bottom:1px solid var(--border)">${outCell}</td>
    <td style="padding:5px 8px;border-bottom:1px solid var(--border)">${cancelBtn}</td>
  </tr>`;
}

function progressBar(pct) {
  pct = Math.max(0, Math.min(100, pct || 0));
  return `<div style="width:130px;height:6px;background:var(--bg3);border-radius:3px;overflow:hidden"><div style="height:100%;width:${pct}%;background:linear-gradient(90deg,#3b82f6,#22c55e);transition:width .5s"></div></div>`;
}

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// ═══ 提交任务(XHR 带上传进度) ═══
function submitTask() {
  const vf = document.getElementById(`${_uid}videoFile`);
  const imf = document.getElementById(`${_uid}imageFile`);
  const video = vf.files[0];
  const image = imf.files[0];
  const msg = document.getElementById(`${_uid}uploadMsg`);
  if (!video || !image) { alert('请选择 原视频 和 人物参考图'); return; }
  if (video.size > 300 * 1048576) { alert('视频超过 300MB'); return; }

  const fd = new FormData();
  fd.append('video', video);
  fd.append('image', image);
  fd.append('character_name', document.getElementById(`${_uid}charName`).value || '');
  fd.append('prompt', document.getElementById(`${_uid}prompt`).value || '');
  fd.append('duration_sec', document.getElementById(`${_uid}duration`).value || '0');

  const xhr = new XMLHttpRequest();
  const prog = document.getElementById(`${_uid}uploadProg`);
  const bar = document.getElementById(`${_uid}uploadBar`);
  prog.style.display = 'block';
  bar.style.width = '0%';
  msg.textContent = '上传中...';

  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) bar.style.width = `${Math.round(e.loaded / e.total * 100)}%`;
  };
  xhr.onload = async () => {
    prog.style.display = 'none';
    try {
      const d = JSON.parse(xhr.responseText);
      if (xhr.status >= 400) throw new Error(d.detail || d.message || `HTTP ${xhr.status}`);
      msg.textContent = `✅ 已提交 ${d.task?.id || ''}`;
      vf.value = ''; imf.value = '';
      document.getElementById(`${_uid}videoInfo`).textContent = '';
      document.getElementById(`${_uid}imageInfo`).textContent = '';
      await refreshTasks();
    } catch (e) {
      msg.textContent = '';
      alert('❌ ' + e.message);
    }
  };
  xhr.onerror = () => { prog.style.display = 'none'; msg.textContent = ''; alert('❌ 网络错误'); };
  xhr.open('POST', '/api/person-swap/tasks');
  xhr.send(fd);
}

// ═══ 取消任务 ═══
window._psCancel = async function(id) {
  if (!confirm('取消该任务?')) return;
  try {
    const r = await fetch(`/api/person-swap/tasks/${id}/cancel`, { method: 'POST' });
    const d = await r.json();
    if (d.task?.status === 'cancelled') { await refreshTasks(); return; }
    alert(d.task?.note || '已登记取消');
  } catch (e) { alert('❌ ' + e.message); }
};
