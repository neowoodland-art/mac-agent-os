/**
 * 语料库视图（已迁移）- 三维语料展示
 *
 * 三大维度：
 *   一维分类（Categories）— 平面分类展示
 *   二维场景（Scenes）    — 身份(Persona)×场景(Scene)
 *   三维多轮（Multi-round）— 多轮对话内容
 *
 * 底部操作区：添加评论 / 批量导入 / 格式模板
 */

export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载语料库...</div>';

  try {
    // 并行拉取一维分类 + 二维场景数据
    const [corpusRes, scenesRes] = await Promise.all([
      fetch('/api/matrix/corpus'),
      fetch('/api/matrix/corpus/scenes').catch(() => ({ json: () => ({ scenes: [], groups: {} }) })),
    ]);
    const cd = await corpusRes.json();
    const sd = await scenesRes.json();

    const cats = cd.categories || [];
    const scenes = sd.scenes || [];
    const groups = sd.groups || {};
    const totalComments = cd.total_comments || 0;

    container.innerHTML = buildCorpusPage(cats, scenes, groups, totalComments);

    // 注册全局函数（供电线 onclick 调用）
    registerWindowFns();
    switchCorpusTab('1d');

  } catch (e) {
    container.innerHTML = `<div class="error">❌ 加载失败: ${escapeHtml(e.message)}</div>`;
  }
}

// ════════════════════════════════════════════════════════════
// HTML 构建
// ════════════════════════════════════════════════════════════

function buildCorpusPage(cats, scenes, groups, totalComments) {
  return `
<div style="padding:16px">
  <!-- 标题 -->
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <h2 style="font-size:18px;margin:0">📚 语料库</h2>
    <span style="font-size:12px;color:var(--text2)">
      ${cats.length} 个分类 · ${scenes.length} 个场景 · ${totalComments} 条评论
    </span>
  </div>

  <!-- 三维标签页 -->
  <div style="display:flex;gap:4px;margin-bottom:12px;border-bottom:1px solid var(--border);padding-bottom:6px">
    <span class="corpus-tab active" data-tab="1d"
          onclick="switchCorpusTab('1d')"
          style="padding:4px 14px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;
                 background:var(--primary);color:#fff;transition:all .15s">
      📂 一维分类
    </span>
    <span class="corpus-tab" data-tab="2d"
          onclick="switchCorpusTab('2d')"
          style="padding:4px 14px;border-radius:6px;cursor:pointer;font-size:12px;
                 background:var(--bg3);color:var(--text2);transition:all .15s">
      👤 二维场景
    </span>
    <span class="corpus-tab" data-tab="3d"
          onclick="switchCorpusTab('3d')"
          style="padding:4px 14px;border-radius:6px;cursor:pointer;font-size:12px;
                 background:var(--bg3);color:var(--text2);transition:all .15s">
      🔄 三维多轮
    </span>
  </div>

  <!-- Tab 1: 一维分类（Categories） -->
  <div id="corpusTab1d" class="corpus-tab-content">
    ${render1D(cats)}
  </div>

  <!-- Tab 2: 二维场景（Persona × Scene） -->
  <div id="corpusTab2d" class="corpus-tab-content" style="display:none">
    ${render2D(scenes, groups)}
  </div>

  <!-- Tab 3: 三维多轮（Multi-round content） -->
  <div id="corpusTab3d" class="corpus-tab-content" style="display:none">
    ${render3D(scenes)}
  </div>

  <!-- ═══════ 底部操作区 ═══════ -->
  <div style="margin-top:18px">

    <!-- 单条添加 -->
    <div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border);margin-bottom:8px">
      <div style="font-weight:600;font-size:13px;margin-bottom:8px">✏️ 添加评论</div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <select id="corpusAddPlatform" style="width:120px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
          <option value="douyin">🎵 抖音</option>
          <option value="xiaohongshu">📕 小红书</option>
        </select>
        <input id="corpusAddCategory" placeholder="分类名" style="width:100px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
        <input id="corpusAddText" placeholder="评论内容" style="flex:1;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
        <button class="btn btn-primary btn-sm" onclick="corpusAdd()" style="background:var(--primary);color:#fff;border:none;padding:5px 12px;border-radius:4px;cursor:pointer;font-size:12px">+ 添加</button>
        <span id="corpusAddResult" style="font-size:11px;color:var(--text2)"></span>
      </div>
    </div>

    <!-- 批量导入 -->
    <div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border);margin-bottom:8px">
      <div style="font-weight:600;font-size:13px;margin-bottom:8px">📥 批量导入</div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px">
        <select id="corpusBatchPlatform" style="width:120px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
          <option value="douyin">🎵 抖音</option>
          <option value="xiaohongshu">📕 小红书</option>
        </select>
        <input id="corpusBatchCategory" placeholder="分类名" style="width:100px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
        <button class="btn btn-primary btn-sm" onclick="corpusBatchImport()" style="background:var(--primary);color:#fff;border:none;padding:5px 12px;border-radius:4px;cursor:pointer;font-size:12px">📥 导入</button>
        <span id="corpusBatchResult" style="font-size:11px;color:var(--text2)"></span>
      </div>
      <textarea id="corpusBatchTexts" placeholder="每行一条评论，直接粘贴即可&#10;例：&#10;讲得太好了，受益匪浅！&#10;这个观点很新颖，学习了&#10;干货满满，感谢分享"
                style="width:100%;height:90px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:8px;border-radius:5px;font-size:12px;font-family:monospace"></textarea>
      <div style="font-size:10px;color:var(--text2);margin-top:4px">支持粘贴、拖入 txt 文件（直接粘贴内容即可）</div>
    </div>

    <!-- 格式模板 -->
    <div style="background:var(--bg2);border-radius:var(--radius);padding:14px;border:1px solid var(--border)">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div style="font-weight:600;font-size:13px">📋 格式模板</div>
        <span style="font-size:10px;color:var(--text2);cursor:pointer" onclick="copyCorpusTemplate()">📋 复制模板</span>
      </div>
      <pre style="font-size:10px;background:var(--bg2);padding:8px;border-radius:4px;margin-top:6px;overflow-x:auto;white-space:pre-wrap;color:var(--text2)">
# 语料库格式模板 v2.0
# 支持身份(Persona)×场景(Scene)×内容(Content) 三维结构
# 也兼容当前的一维分类格式（categories）

## 一维格式（当前使用）
categories:
  赞美:
    weight: 30
    enabled: true
    comments:
      - "讲得太好了，受益匪浅！"
      - "干货满满，感谢分享"
  提问:
    weight: 15
    enabled: true
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
      - "对，后来我换了一种方法就好了"</pre>
    </div>

  </div>
</div>`;
}

// ════════════════════════════════════════════════════════════
// Tab 渲染函数
// ════════════════════════════════════════════════════════════

/** 一维分类 — 按平台分组展示 categories */
function render1D(cats) {
  const groups = {};
  cats.forEach(c => {
    const p = c.platform === 'xiaohongshu' ? '📕 小红书' : '🎵 抖音';
    if (!groups[p]) groups[p] = [];
    groups[p].push(c);
  });

  const platforms = Object.keys(groups);
  if (!platforms.length) {
    return '<div style="color:var(--text2);font-size:12px;padding:20px;text-align:center">暂无分类数据</div>';
  }

  return `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:10px">
    ${Object.entries(groups).map(([platform, items]) => `
      <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">${platform}
          <span style="font-size:10px;color:var(--text2);font-weight:400">（${items.length} 个分类）</span>
        </div>
        <table style="width:100%;font-size:11px;border-collapse:collapse">
          <thead>
            <tr>
              <th style="text-align:left;padding:4px 3px;border-bottom:1px solid var(--border);color:var(--text2);font-weight:500">分类</th>
              <th style="padding:4px 3px;border-bottom:1px solid var(--border);color:var(--text2);font-weight:500">权重</th>
              <th style="padding:4px 3px;border-bottom:1px solid var(--border);color:var(--text2);font-weight:500">评论</th>
              <th style="padding:4px 3px;border-bottom:1px solid var(--border);color:var(--text2);font-weight:500">状态</th>
              <th style="padding:4px 3px;border-bottom:1px solid var(--border)"></th>
            </tr>
          </thead>
          <tbody>
            ${items.map(c => {
              const p = c.platform === 'xiaohongshu' ? 'xiaohongshu' : 'douyin';
              const name = escapeHtml(c.name);
              return `<tr>
                <td style="padding:5px 3px;border-bottom:1px solid var(--border)"><strong>${name}</strong></td>
                <td style="padding:5px 3px;border-bottom:1px solid var(--border);text-align:center;color:var(--text2)">${c.weight || '-'}</td>
                <td style="padding:5px 3px;border-bottom:1px solid var(--border);text-align:center">${c.count || 0}</td>
                <td style="padding:5px 3px;border-bottom:1px solid var(--border);text-align:center">${c.enabled ? '<span style="color:var(--green)">✅</span>' : '<span style="color:var(--text2)">⏸</span>'}</td>
                <td style="padding:5px 3px;border-bottom:1px solid var(--border)">
                  <button onclick="corpusShowDetail('${p}','${name}')"
                          style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">📝</button>
                </td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>
    `).join('')}
  </div>`;
}

/** 二维场景 — 身份(Persona) × 场景(Scene) */
function render2D(scenes, groups) {
  const totalScenes = scenes.length;
  if (!totalScenes) {
    return `<div style="color:var(--text2);font-size:12px;padding:20px;text-align:center">
      <div style="font-size:24px;margin-bottom:8px">📋</div>
      <div>暂无二维场景语料</div>
      <div style="font-size:11px;margin-top:6px;opacity:.7">
        请按模板格式在 YAML 中添加 personas 和 scenes 段落后刷新
      </div>
    </div>`;
  }

  // 按场景类型分组
  const sceneLabels = {
    first_comment: '💬 首次评论',
    reply: '↩️ 回复评论',
    re_reply: '🔄 再回复',
  };
  const otherScenes = scenes.filter(s => !['first_comment', 'reply', 're_reply'].includes(s.id));

  let html = '';
  for (const [key, label] of Object.entries(sceneLabels)) {
    const items = groups[key] || [];
    html += renderSceneGroup(key, label, items);
  }
  if (otherScenes.length) {
    html += renderSceneGroup('other', '📌 其他场景', otherScenes);
  }

  return html;
}

function renderSceneGroup(key, label, items) {
  // 按 persona 分组
  const personas = {};
  items.forEach(s => {
    const pid = s.persona || 'unknown';
    if (!personas[pid]) personas[pid] = [];
    personas[pid].push(s);
  });

  const pids = Object.keys(personas);
  if (!pids.length) return '';

  return `
    <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);margin-bottom:8px">
      <div style="font-weight:600;font-size:13px;margin-bottom:8px">${label}
        <span style="font-size:10px;color:var(--text2);font-weight:400">（${items.length} 个场景）</span>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:6px">
        ${pids.map(pid => {
          const personaLabel = pid.replace(/_/g, ' ');
          return `<div style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:8px 10px;min-width:120px">
            <div style="font-size:11px;font-weight:600;margin-bottom:4px">👤 ${escapeHtml(personaLabel)}</div>
            <div style="font-size:10px;color:var(--text2)">
              ${personas[pid].map(s => {
                const rounds = s.rounds || 1;
                return `<span style="display:inline-block;background:rgba(99,102,241,.1);padding:2px 6px;border-radius:3px;margin:2px">
                  ${escapeHtml(s.label || s.id)} ${rounds > 1 ? `(${rounds}轮)` : ''}
                </span>`;
              }).join('')}
            </div>
          </div>`;
        }).join('')}
      </div>
    </div>`;
}

/** 三维多轮 — 多轮对话内容 */
function render3D(scenes) {
  const multiRound = scenes.filter(s => (s.rounds || 1) > 1);
  if (!multiRound.length) {
    return `<div style="color:var(--text2);font-size:12px;padding:20px;text-align:center">
      <div style="font-size:24px;margin-bottom:8px">🔄</div>
      <div>暂无多轮对话语料</div>
      <div style="font-size:11px;margin-top:6px;opacity:.7">
        在 YAML 的 content 段中添加 round_N 即可启用多轮语料
      </div>
    </div>`;
  }

  return `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px">
    ${multiRound.map(s => {
      const pid = (s.persona || '').replace(/_/g, ' ');
      const label = s.label || s.id;
      const rounds = s.rounds || 1;
      return `<div style="background:var(--bg2);border-radius:var(--radius);padding:10px;border:1px solid var(--border)">
        <div style="font-size:12px;font-weight:600;margin-bottom:4px">👤 ${escapeHtml(pid)}</div>
        <div style="font-size:11px;margin-bottom:4px">📌 ${escapeHtml(label)}</div>
        <div style="font-size:10px;color:var(--text2)">🔄 ${rounds} 轮对话</div>
      </div>`;
    }).join('')}
  </div>`;
}

// ════════════════════════════════════════════════════════════
// 标签页切换
// ════════════════════════════════════════════════════════════

function switchCorpusTab(tab) {
  // 更新 tab 样式
  document.querySelectorAll('.corpus-tab').forEach(t => {
    const isActive = t.dataset.tab === tab;
    t.style.background = isActive ? 'var(--primary)' : 'var(--bg3)';
    t.style.color = isActive ? '#fff' : 'var(--text2)';
    t.style.fontWeight = isActive ? '600' : '400';
  });

  // 切换内容区
  document.querySelectorAll('.corpus-tab-content').forEach(el => {
    el.style.display = el.id === `corpusTab${tab}` ? '' : 'none';
  });
}

// ════════════════════════════════════════════════════════════
// 操作函数
// ════════════════════════════════════════════════════════════

async function corpusAdd() {
  const platform = document.getElementById('corpusAddPlatform')?.value;
  const category = document.getElementById('corpusAddCategory')?.value;
  const text = document.getElementById('corpusAddText')?.value;
  const result = document.getElementById('corpusAddResult');
  if (!category || !text) { result.textContent = '❌ 请输入分类和评论'; return; }
  try {
    const r = await fetch('/api/matrix/corpus/add', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform, category, text }),
    });
    const d = await r.json();
    if (d.status === 'ok') {
      result.textContent = '✅ 已添加';
      document.getElementById('corpusAddText').value = '';
      reloadCorpus();
    } else {
      result.textContent = '❌ ' + (d.error || '添加失败');
    }
  } catch (e) {
    result.textContent = '❌ ' + e.message;
  }
}

async function corpusBatchImport() {
  const platform = document.getElementById('corpusBatchPlatform')?.value;
  const category = document.getElementById('corpusBatchCategory')?.value;
  const textsEl = document.getElementById('corpusBatchTexts');
  const result = document.getElementById('corpusBatchResult');
  if (!category || !textsEl?.value.trim()) {
    result.textContent = '❌ 请输入分类名和评论内容';
    return;
  }
  const texts = textsEl.value.split('\n').filter(t => t.trim());
  result.textContent = '⏳ 导入 ' + texts.length + ' 条...';
  try {
    const r = await fetch('/api/matrix/corpus/batch-add', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform, category, texts }),
    });
    const d = await r.json();
    if (d.status === 'ok') {
      result.textContent = '✅ 成功导入 ' + d.added + ' 条';
      textsEl.value = '';
      reloadCorpus();
    } else {
      result.textContent = '❌ ' + (d.detail || d.error);
    }
  } catch (e) {
    result.textContent = '❌ ' + e.message;
  }
}

function copyCorpusTemplate() {
  const text = `# 语料库模板 v2.0
# 分类 + 评论（一维）
categories:
  赞美:
    weight: 30
    enabled: true
    comments:
      - "讲得太好了，受益匪浅！"
  提问:
    weight: 15
    enabled: true
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
  navigator.clipboard.writeText(text)
    .then(() => alert('✅ 已复制模板'))
    .catch(() => alert('复制失败，请手动选中复制'));
}

// ── 分类详情弹窗 ──

let _corpusModalOpen = false;

function corpusShowDetail(platform, category) {
  if (_corpusModalOpen) return;
  _corpusModalOpen = true;

  const modal = document.createElement('div');
  modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:9999';
  modal.innerHTML = `<div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:20px;max-width:600px;width:90%;max-height:70vh;display:flex;flex-direction:column">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <span style="font-weight:600;font-size:15px">📚 ${escapeHtml(platform)}/${escapeHtml(category)}</span>
      <span style="cursor:pointer;font-size:20px" onclick="this.closest('div[style*=\\'fixed\\']').remove();_corpusModalOpen=false">✕</span>
    </div>
    <div id="corpusDetailBody" style="flex:1;overflow-y:auto;padding:4px 0">
      <div style="text-align:center;color:var(--text2);padding:20px">加载中...</div>
    </div>
    <div style="margin-top:10px;display:flex;gap:6px">
      <input id="corpusDetailAddText" placeholder="添加评论..." style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
      <button onclick="corpusDetailAdd()" style="background:var(--primary);color:#fff;border:none;padding:5px 12px;border-radius:4px;cursor:pointer;font-size:12px">添加</button>
    </div>
  </div>`;
  document.body.appendChild(modal);

  // 加载评论
  fetch(`/api/matrix/corpus/category?platform=${platform}&category=${encodeURIComponent(category)}`)
    .then(r => r.json())
    .then(d => {
      const body = document.getElementById('corpusDetailBody');
      if (!body) return;
      const allComments = [
        ...(d.comments || []).map((c, i) => ({ type: 'comment', text: c, index: i })),
        ...(d.templates || []).map((t, i) => ({ type: 'template', text: t, index: i + 999 })),
      ];
      if (!allComments.length) {
        body.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text2)">暂无评论</div>';
        return;
      }
      body.innerHTML = allComments.map((item, i) => {
        const idx = item.index >= 999 ? -1 : item.index;
        return `<div style="display:flex;align-items:center;gap:6px;padding:5px 0;border-bottom:1px solid var(--border)">
          <span style="font-size:10px;color:var(--text2);width:40px;flex-shrink:0">#${i + 1}${item.type === 'template' ? ' 📝' : ''}</span>
          <span style="flex:1;font-size:12px">${escapeHtml(item.text)}</span>
          <span style="cursor:pointer;color:var(--red);font-size:14px;opacity:.5"
                onclick="corpusDetailDelete('${platform}','${escapeHtml(category)}',${idx})">✕</span>
        </div>`;
      }).join('');
    })
    .catch(e => {
      const body = document.getElementById('corpusDetailBody');
      if (body) body.innerHTML = `<div style="color:var(--red);text-align:center;padding:20px">❌ ${escapeHtml(e.message)}</div>`;
    });
}

async function corpusDetailAdd() {
  const input = document.getElementById('corpusDetailAddText');
  if (!input || !input.value.trim()) return;
  const modal = input.closest('div[style*="fixed"]');
  const header = modal?.querySelector('span')?.textContent || '';
  const parts = header.replace('📚 ', '').split('/');
  const platform = parts[0] || 'douyin';
  const category = parts[1] || '';
  try {
    const r = await fetch('/api/matrix/corpus/add', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform, category, text: input.value.trim() }),
    });
    const d = await r.json();
    if (d.status === 'ok') {
      input.value = '';
      corpusShowDetail(platform, category);
      reloadCorpus();
    }
  } catch (e) {
    alert(e.message);
  }
}

async function corpusDetailDelete(platform, category, index) {
  if (index === -1) { alert('模板暂不支持看板删除，请使用 CLI'); return; }
  if (!confirm(`删除第 ${index + 1} 条评论？`)) return;
  try {
    const r = await fetch('/api/matrix/corpus/delete', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform, category, index }),
    });
    const d = await r.json();
    if (d.status === 'ok') {
      document.querySelector('div[style*="fixed"]')?.remove();
      _corpusModalOpen = false;
      corpusShowDetail(platform, category);
      reloadCorpus();
    }
  } catch (e) {
    alert(e.message);
  }
}

// ── 重新加载语料库（保留当前 tab） ──
async function reloadCorpus() {
  const container = document.getElementById('view-dynamic');
  if (!container) return;
  // 记住当前 tab
  const activeTab = document.querySelector('.corpus-tab.active')?.dataset?.tab || '1d';
  await loadView(container);
  switchCorpusTab(activeTab);
}

// ── 工具 ──
function escapeHtml(str) {
  if (typeof str !== 'string') return String(str || '');
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

// ════════════════════════════════════════════════════════════
// 注册全局函数（弹窗 onclick 需要）
// ════════════════════════════════════════════════════════════

function registerWindowFns() {
  // 只在第一次加载时注册，避免重复
  if (window._corpusFnsRegistered) return;
  window._corpusFnsRegistered = true;

  window.switchCorpusTab = switchCorpusTab;
  window.corpusAdd = corpusAdd;
  window.corpusBatchImport = corpusBatchImport;
  window.copyCorpusTemplate = copyCorpusTemplate;
  window.corpusShowDetail = corpusShowDetail;
  window.corpusDetailAdd = corpusDetailAdd;
  window.corpusDetailDelete = corpusDetailDelete;
}
