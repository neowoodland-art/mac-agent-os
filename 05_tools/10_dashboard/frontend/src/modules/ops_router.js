// ════════════════════════════════════════════════════════
// Corpus Management
// ════════════════════════════════════════════════════════

async function loadCorpus() {
  const el = document.getElementById('corpusContent');
  const meta = document.getElementById('corpusMeta');
  if (!el) return;
  el.innerHTML = '<div class="loading">加载中...</div>';
  try {
    const r = await fetch('/api/matrix/corpus');
    const d = await r.json();
    const cats = d.categories || [];
    meta.textContent = `共 ${cats.length} 个分类 · ${d.total_comments||0} 条评论`;

    let html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px">';

    // Group by platform
    const groups = {};
    cats.forEach(c => {
      const p = c.platform === 'xiaohongshu' ? '📕 小红书' : '🎵 抖音';
      if (!groups[p]) groups[p] = [];
      groups[p].push(c);
    });

    Object.entries(groups).forEach(([platform, items]) => {
      html += `<div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:14px;margin-bottom:10px">${platform}</div>
        <table><thead><tr><th>分类</th><th>权重</th><th>评论数</th><th>状态</th><th>操作</th></tr></thead><tbody>
        ${items.map(c => `<tr>
          <td><strong>${c.name}</strong></td>
          <td>${c.weight}</td>
          <td>${c.count}</td>
          <td>${c.enabled ? '<span class="badge badge-green">✅ 启用</span>' : '<span class="badge badge-gray">⏸ 停用</span>'}</td>
          <td><button class="btn btn-sm btn-outline" onclick="corpusShowDetail('${c.platform}','${c.name}')">📝</button></td>
        </tr>`).join('')}
        </tbody></table>
      </div>`;
    });
    html += '</div>';

    // Add comment form
    html += `<div style="margin-top:12px;background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
      <div style="font-weight:600;font-size:13px;margin-bottom:8px">✏️ 添加评论</div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <select id="corpusAddPlatform" style="width:120px">
          <option value="douyin">🎵 抖音</option>
          <option value="xiaohongshu">📕 小红书</option>
        </select>
        <input id="corpusAddCategory" placeholder="分类名" style="width:100px">
        <input id="corpusAddText" placeholder="评论内容" style="flex:1;min-width:200px">
        <button class="btn btn-primary btn-sm" onclick="corpusAdd()">+ 添加</button>
        <span id="corpusAddResult" style="font-size:12px"></span>
      </div>
    </div>
    <!-- 批量导入 -->
    <div style="margin-top:8px;background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
      <div style="font-weight:600;font-size:13px;margin-bottom:8px">📥 批量导入</div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px">
        <select id="corpusBatchPlatform" style="width:120px">
          <option value="douyin">🎵 抖音</option>
          <option value="xiaohongshu">📕 小红书</option>
        </select>
        <input id="corpusBatchCategory" placeholder="分类名" style="width:100px">
        <button class="btn btn-primary btn-sm" onclick="corpusBatchImport()">📥 导入</button>
        <span id="corpusBatchResult" style="font-size:12px"></span>
      </div>
      <textarea id="corpusBatchTexts" placeholder="每行一条评论，直接粘贴即可&#10;例：&#10;讲得太好了，受益匪浅！&#10;这个观点很新颖，学习了&#10;干货满满，感谢分享" style="width:100%;height:100px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:8px;border-radius:5px;font-size:12px;font-family:monospace"></textarea>
      <div style="font-size:10px;color:var(--text2);margin-top:4px">支持粘贴、拖入 txt 文件（点击下方「选择文件」或直接粘贴内容）</div>
    </div>
    <!-- 格式模板 -->
    <div style="margin-top:8px;background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div style="font-weight:600;font-size:13px">📋 格式模板</div>
        <span style="font-size:10px;color:var(--text2);cursor:pointer" onclick="copyTemplate()">📋 复制模板</span>
      </div>
      <pre style="font-size:10px;background:var(--bg2);padding:8px;border-radius:4px;margin-top:6px;overflow-x:auto;white-space:pre-wrap;color:var(--text2)">
# 语料库格式模板 v2.0
# 支持身份(Persona)×场景(Scene)×内容(Content) 三维结构
# 也兼容当前的一维分类格式（categories）

## 一维格式（当前使用）
categories:
  赞美:
    comments:
      - "讲得太好了，受益匪浅！"
      - "干货满满，感谢分享"
  提问:
    comments:
      - "请问这是在哪里？"

## 二维格式（推荐）
personas:
  health_lover:
    name: "养生爱好者"
    tags: ["养生","健康"]
scenes:
  first_comment:
    label: "首次评论"
content:
  health_lover.first_comment:
    - "这个养生方法很实用"
    - "坚持调理最重要"

## 三维格式（含多轮对话）
content:
  health_lover.follow_up:
    round_1:
      - "确实如此，{keyword}我也是这么认为的"
    round_2:
      - "对，后来我换了一种方法就好了"
      </pre>
    </div>`;

    el.innerHTML = html;
  } catch(e) {
    el.innerHTML = `<div class="error">❌ ${e.message}</div>`;
  }
}

async function corpusAdd() {
  const platform = document.getElementById('corpusAddPlatform')?.value;
  const category = document.getElementById('corpusAddCategory')?.value;
  const text = document.getElementById('corpusAddText')?.value;
  const result = document.getElementById('corpusAddResult');
  if (!category || !text) { result.textContent = '❌ 请输入分类和评论'; return; }
  try {
    const r = await fetch('/api/matrix/corpus/add', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({platform, category, text})
    });
    const d = await r.json();
    if (d.status === 'ok') {
      result.textContent = '✅ 已添加';
      document.getElementById('corpusAddText').value = '';
      loadCorpus();
    } else {
      result.textContent = '❌ '+d.error;
    }
  } catch(e) { result.textContent = '❌ '+e.message; }
}

async function corpusBatchImport() {
  const platform = document.getElementById('corpusBatchPlatform')?.value;
  const category = document.getElementById('corpusBatchCategory')?.value;
  const textsEl = document.getElementById('corpusBatchTexts');
  const result = document.getElementById('corpusBatchResult');
  if (!category || !textsEl?.value.trim()) { result.textContent = '❌ 请输入分类名和评论内容'; return; }
  const texts = textsEl.value.split('\n').filter(t => t.trim());
  result.textContent = '⏳ 导入 ' + texts.length + ' 条...';
  try {
    const r = await fetch('/api/matrix/corpus/batch-add', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({platform, category, texts})
    });
    const d = await r.json();
    if (d.status === 'ok') {
      result.textContent = '✅ 成功导入 ' + d.added + ' 条';
      textsEl.value = '';
      loadCorpus();
    } else {
      result.textContent = '❌ ' + (d.detail || d.error);
    }
  } catch(e) { result.textContent = '❌ ' + e.message; }
}

function copyTemplate() {
  const text = `# 语料库模板 v2.0
# 分类 + 评论（一维）
categories:
  赞美:
    comments:
      - "讲得太好了，受益匪浅！"
  提问:
    comments:
      - "请问这是在哪里？"

# 身份 + 场景 + 内容（三维）
personas:
  health_lover:
    name: "养生爱好者"
    tags: ["养生","健康"]
scenes:
  first_comment:
    label: "首次评论"
content:
  health_lover.first_comment:
    - "这个养生方法很实用"
  health_lover.follow_up:
    round_1:
      - "确实如此，{keyword}我也是这么认为的"
    round_2:
      - "对，后来我换了一种方法就好了"`;
  navigator.clipboard.writeText(text).then(() => alert('✅ 已复制模板')).catch(() => alert('复制失败，请手动选中复制'));
}

let _corpusModalOpen = false;

function corpusShowDetail(platform, category) {
  if (_corpusModalOpen) return;
  _corpusModalOpen = true;

  // Create modal
  const modal = document.createElement('div');
  modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:9999';
  modal.innerHTML = `<div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:20px;max-width:600px;width:90%;max-height:70vh;display:flex;flex-direction:column">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <span style="font-weight:600;font-size:15px">📚 ${platform}/${category}</span>
      <span style="cursor:pointer;font-size:20px" onclick="this.closest('div[style*=\\'fixed\\']').remove();_corpusModalOpen=false">✕</span>
    </div>
    <div id="corpusDetailBody" style="flex:1;overflow-y:auto;padding:4px 0">
      <div style="text-align:center;color:var(--text2);padding:20px">加载中...</div>
    </div>
    <div style="margin-top:10px;display:flex;gap:6px">
      <input id="corpusDetailAddText" placeholder="添加评论..." style="flex:1">
      <button class="btn btn-primary btn-sm" onclick="corpusDetailAdd()">添加</button>
    </div>
  </div>`;
  document.body.appendChild(modal);

  // Load comments
  fetch(`/api/matrix/corpus/detail?platform=${platform}&category=${encodeURIComponent(category)}`)
    .then(r => r.json())
    .then(d => {
      const body = document.getElementById('corpusDetailBody');
      if (!body) return;
      const allComments = [...(d.comments||[]).map((c,i) => ({type:'comment', text:c, index:i})),
                          ...(d.templates||[]).map((t,i) => ({type:'template', text:t, index:i+999}))];
      if (!allComments.length) {
        body.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text2)">暂无评论</div>';
        return;
      }
      body.innerHTML = allComments.map((item,i) => `<div style="display:flex;align-items:center;gap:6px;padding:5px 0;border-bottom:1px solid var(--border)">
        <span style="font-size:10px;color:var(--text2);width:40px;flex-shrink:0">#${i+1}${item.type==='template'?' 📝':''}</span>
        <span style="flex:1;font-size:12px">${item.text}</span>
        <span style="cursor:pointer;color:var(--red);font-size:14px;opacity:.5" onclick="corpusDetailDelete('${platform}','${category}',${item.index >= 999 ? -1 : item.index})">✕</span>
      </div>`).join('');
    })
    .catch(e => {
      const body = document.getElementById('corpusDetailBody');
      if (body) body.innerHTML = `<div style="color:var(--red);text-align:center;padding:20px">❌ ${e.message}</div>`;
    });
}

async function corpusDetailAdd() {
  const input = document.getElementById('corpusDetailAddText');
  if (!input || !input.value.trim()) return;
  const modal = input.closest('div[style*="fixed"]');
  const platform = modal?.querySelector('span')?.textContent?.split('/')[0]?.replace('📚 ','') || 'douyin';
  const category = modal?.querySelector('span')?.textContent?.split('/')[1] || '';
  try {
    const r = await fetch('/api/matrix/corpus/add', {method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({platform, category, text: input.value.trim()})});
    const d = await r.json();
    if (d.status === 'ok') {
      input.value = '';
      corpusShowDetail(platform, category);
      loadCorpus();
    }
  } catch(e) { alert(e.message); }
}

async function corpusDetailDelete(platform, category, index) {
  if (index === -1) { alert('模板暂不支持看板删除，请使用 CLI'); return; }
  if (!confirm(`删除第 ${index+1} 条评论？`)) return;
  try {
    const r = await fetch('/api/matrix/corpus/delete', {method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({platform, category, index})});
    const d = await r.json();
    if (d.status === 'ok') {
      // Close old modal, reopen
      document.querySelector('div[style*="fixed"]')?.remove();
      _corpusModalOpen = false;
      corpusShowDetail(platform, category);
      loadCorpus();
    }
  } catch(e) { alert(e.message); }
}

// ── Git Sync ──
async function gitSync() {
  var btn = document.querySelector('[onclick="gitSync()"]');
  if (!btn) return;
  btn.textContent = 'sync...';
  btn.style.opacity = '0.5';
  try {
    var r = await fetch('/api/git-sync', {method: 'POST'});
    var res = await r.json();
    btn.textContent = 'done';
    setTimeout(function(){ btn.textContent = 'sync'; btn.style.opacity = '1'; }, 2000);
    if (typeof loadMachines === 'function') loadMachines();
    if (typeof loadStats === 'function') loadStats();
  } catch(e) {
    btn.textContent = 'err';
    setTimeout(function(){ btn.textContent = 'sync'; btn.style.opacity = '1'; }, 2000);
  }
}

// ── 账号注册 ──
async function accountRegister() {
  const plat = document.getElementById('regPlatform')?.value;
  const phone = document.getElementById('regPhone')?.value;
  const nick = document.getElementById('regNickname')?.value;
  const statusEl = document.getElementById('regStatus');
  if (!phone) { alert('请输入手机号'); return; }
  if (statusEl) statusEl.innerHTML = '<span style="color:var(--text2)">⏳ 注册中...</span>';
  try {
    const r = await fetch('/api/matrix/accounts/register', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({platform:plat, phone:phone, nickname:nick})
    });
    const d = await r.json();
    if (d.status === 'ok') {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--green)">✅ '+d.message+'</span>'+
        '<div style="margin-top:4px;font-size:10px;color:var(--text2)">账号ID: '+d.account_id+' | 登录后可以采集昵称</div>';
      document.getElementById('regPhone').value = '';
      document.getElementById('regNickname').value = '';
      setTimeout(loadSmsAccounts, 2000);
    } else {
      if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ '+(d.error||'注册失败')+'</span>';
    }
  } catch(e) {
    if (statusEl) statusEl.innerHTML = '<span style="color:var(--red)">❌ '+e.message+'</span>';
  }
}
// ── 导出（防 Rollup tree-shake）──
window.accountRegister = accountRegister;
window.copyTemplate = copyTemplate;
window.corpusAdd = corpusAdd;
window.corpusBatchImport = corpusBatchImport;
window.corpusDetailAdd = corpusDetailAdd;
window.corpusDetailDelete = corpusDetailDelete;
window.corpusShowDetail = corpusShowDetail;
window.gitSync = gitSync;
window.loadCorpus = loadCorpus;