/**
 * workflow.js — 🔀 工作流编辑器
 * 从 inline.js 迁移（原 loadWorkflow + wf* 函数）
 * 
 * 后端 API:
 *   GET  /api/workflow/nodes     — 节点定义
 *   GET  /api/workflow/templates — 模板
 *   POST /api/workflow/run       — 执行工作流
 *   GET  /api/characters         — 角色列表
 *   POST /api/characters/generate-portrait — 生成定妆照
 */

const API = '';

// ── 全局状态 ──
let wfNodeDefs = {};
let wfTemplates = {};
let wfNodes = [];
let wfEdges = [];
let wfNodeIdCounter = 0;
let wfSelectedNodeId = null;
let wfCurrentRunId = null;
const WF_ZOOM = 1;
let wfDraggingNode = null;
let wfDragOffX = 0, wfDragOffY = 0;
let wfConnecting = null;

let wfCharacterList = [];
let wfCharDetails = {};

// ══ 中文标签映射 ══
const WF_FIELD_LABELS = {
  editor_mode: '编辑模式', content: '脚本内容', path: '文件路径',
  type: '脚本格式', parser: '解析方式',
  strategy: '生产策略',
  voice_id: '语音模型', speed: '语速', pitch: '音调',
  provider: '供应商', model: '模型版本', duration: '时长(秒)', seed: '随机种子',
  source: '素材来源', search_keyword: '搜索关键词', count: '素材数量', orientation: '画面方向',
  style: '视觉风格', color_grade: '色调',
  mode: '模式', mood: '情绪风格', rhythm: '节奏强度', bpm: 'BPM',
  volume: '音量', duck_enabled: '自动避让',
  registry_name: '选择角色', outfit_preset: '服装预设',
  use_reference_images: '传递参考图', lip_sync: '唇形同步',
  camera_style: '运镜风格', transition: '转场方式', scene_count: '场景数量',
  output_format: '输出格式',
  prompt_style: '提示词风格', quality: '品质等级', add_negative: '添加负面提示',
  format: '视频格式', resolution: '分辨率', output_path: '输出路径', auto_open: '自动打开',
  message: '审核提示', auto_approve: '自动通过', timeout_minutes: '超时(分钟)',
  genre: '故事类型', title: '故事标题',
  adapt_style: '改编风格',
};

const WF_OPTION_LABELS = {
  auto: '自动', manual: '手动', ai_generated: 'AI生成',
  turbo: '极速', standard: '标准', quality: '高品质',
  kling: '可灵AI', jimeng: '即梦', wan: '万相',
  pexels: 'Pexels图库', local: '本地文件', upload: '上传',
  portrait: '竖屏', landscape: '横屏', square: '方形',
  cinematic: '电影感', hyper_realistic: '超写实', artistic: '艺术风',
  anime: '动漫', vintage: '复古',
  warm: '暖调', cool: '冷调', neutral: '中性', dramatic: '戏剧性', monochrome: '黑白',
  default: '默认', casual: '休闲', sport: '运动', formal: '正式', fantasy: '奇幻',
  happy: '欢快', sad: '伤感', epic: '史诗', calm: '平静', tense: '紧张', upbeat: '积极',
  romantic: '浪漫', inspiring: '激励', healing: '治愈',
  detailed: '详细描述', simple: '简洁指令', stepwise: '分步式',
  json: 'JSON格式', yaml: 'YAML格式', md: 'Markdown格式',
  inline: '在线编辑', path: '文件路径',
  srt: 'SRT格式', ass: 'ASS格式', vtt: 'VTT格式',
  bottom: '底部', top: '顶部', white: '白色', yellow: '黄色', cyan: '青色',
  'hard': '硬切', 'fade_in': '淡入', 'fade_out': '淡出', 'dissolve': '叠化',
  'slide': '划像', 'cut': '跳切',
  running: '跑步装', gym: '健身装', basketball: '篮球装',
  modern: '现代', ancient: '古风', sci_fi: '科幻',
  mystery: '悬疑', comedy: '喜剧',
  'detailed_adapt': '详细改编', 'fast_extract': '快速提炼', 'dialogue_first': '对白优先',
};

const BODY_LABELS = {right_three_quarter:'右侧45°', right_side:'纯右侧面', back:'背面', front:'正面', side:'侧面'};

export async function loadView(container) {
  container.innerHTML = `
  <div style="display:flex;flex-direction:column;height:calc(100vh - 180px);min-height:500px">
    <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;flex-shrink:0">
      <span style="font-size:14px;font-weight:600;color:var(--text)">🔀 工作流</span>
      <select id="wfTemplateSelect" onchange="wfLoadTemplate(this.value)"
        style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 8px;border-radius:4px;font-size:12px;width:160px">
        <option value="">— 模板 —</option>
      </select>
      <div style="display:flex;gap:3px;flex-wrap:wrap;flex:1;overflow-x:auto;padding:2px 0" id="wfNodePalette"></div>
      <button onclick="wfRun()" style="background:var(--primary);border:none;color:#fff;padding:3px 12px;border-radius:4px;cursor:pointer;font-size:12px;white-space:nowrap">▶ 运行</button>
      <button onclick="wfClear()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:12px;white-space:nowrap">🗑 清空</button>
      <span id="wfRunStatus" style="font-size:11px;color:var(--text2);white-space:nowrap"></span>
    </div>
    <div style="display:flex;gap:8px;flex:1;min-height:0">
      <div style="flex:1;position:relative;background:var(--bg3);border-radius:8px;overflow:hidden;border:1px solid var(--border)">
        <svg id="wfCanvas" width="100%" height="100%" style="cursor:grab;display:block"></svg>
        <div id="wfCanvasPlaceholder" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;color:var(--text2);font-size:13px;pointer-events:none">
          从上方拖拽节点到画布，或选择模板开始
        </div>
      </div>
      <div id="wfConfigPanel" style="width:300px;background:var(--bg2);border-radius:8px;border:1px solid var(--border);overflow-y:auto;flex-shrink:0">
        <div id="wfConfigContent" style="padding:14px;font-size:12px;color:var(--text2)">点击节点编辑配置</div>
      </div>
    </div>
  </div>`;

  // 重置状态
  wfNodes = []; wfEdges = []; wfSelectedNodeId = null; wfCurrentRunId = null; wfNodeIdCounter = 0;

  await wfInit();
}

// ══ 初始化 ══
async function wfInit() {
  try {
    const [nodesR, tmplR] = await Promise.all([
      fetch(API + '/api/workflow/nodes'),
      fetch(API + '/api/workflow/templates'),
    ]);
    const nodesD = await nodesR.json();
    const tmplD = await tmplR.json();
    wfNodeDefs = {};
    const rootDefs = nodesD._defs || {};
    for (const cat of (nodesD.categories || [])) {
      for (const nid of (cat.nodes || [])) {
        wfNodeDefs[nid] = rootDefs[nid] || {};
      }
    }
    wfTemplates = tmplD.templates || {};
  } catch(e) {
    wfNodeDefs = {};
    wfTemplates = {};
  }
  wfRenderPalette();
  wfRenderTemplateSelect();
  wfLoadCharacters();
  wfInitCanvas();
}

// ══ Canvas 初始化 ══
function wfInitCanvas() {
  const canvas = document.getElementById('wfCanvas');
  if (!canvas) return;
  canvas.addEventListener('dragover', e => e.preventDefault());
  canvas.addEventListener('drop', e => {
    e.preventDefault();
    const type = e.dataTransfer.getData('text/plain');
    if (!type || !wfNodeDefs[type]) return;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - 120) / WF_ZOOM;
    const y = (e.clientY - rect.top - 30) / WF_ZOOM;
    wfAddNode(type, Math.max(0,x), Math.max(0,y));
  });
}

// ══ 调色板 ══
function wfRenderPalette() {
  const el = document.getElementById('wfNodePalette');
  if (!el) return;
  el.innerHTML = Object.entries(wfNodeDefs).map(([type, def]) => {
    const color = def.color || '#888';
    const icon = def.icon || '●';
    return `<div draggable="true" ondragstart="wfDragStart(event,'${type}')" title="${def.description||''}"
      style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;margin:1px;border-radius:4px;font-size:11px;cursor:grab;white-space:nowrap;background:${color}15;border:1px solid ${color}30;color:${color}">${icon} ${def.label}</div>`;
  }).join('');
}

function wfRenderTemplateSelect() {
  const sel = document.getElementById('wfTemplateSelect');
  if (!sel) return;
  sel.innerHTML = '<option value="">— 选择模板 —</option>' +
    Object.entries(wfTemplates).map(([id, t]) =>
      `<option value="${id}">${t.name||id} ${t.cost||''}</option>`
    ).join('');
}

// ══ SVG 渲染 ══
function wfRender() {
  const svg = document.getElementById('wfCanvas');
  const ph = document.getElementById('wfCanvasPlaceholder');
  if (!svg) return;
  ph.style.display = wfNodes.length === 0 ? 'flex' : 'none';

  let html = `<defs><marker id="wfArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M2 1L8 5L2 9" fill="none" stroke="#888" stroke-width="1.5"/></marker></defs>`;

  wfEdges.forEach((e, i) => {
    const from = wfNodes.find(n => n.id === e.from);
    const to = wfNodes.find(n => n.id === e.to);
    if (from && to) {
      const x1 = from.x + 120, y1 = from.y + 30;
      const x2 = to.x, y2 = to.y + 30;
      const cx = (x1 + x2) / 2;
      html += `<path d="M${x1} ${y1} C${cx} ${y1},${cx} ${y2},${x2} ${y2}" fill="none" stroke="#888" stroke-width="2" marker-end="url(#wfArrow)" opacity="0.6"/>`;
    }
  });

  wfNodes.forEach(n => {
    const def = wfNodeDefs[n.type] || {};
    const color = def.color || '#888';
    html += `<g class="wf-node" data-id="${n.id}" onmousedown="wfNodeMouseDown(event,'${n.id}')" style="cursor:move">
      <rect x="${n.x}" y="${n.y}" width="240" height="60" rx="8" fill="var(--bg2)" stroke="${wfSelectedNodeId === n.id ? color : 'var(--border)'}" stroke-width="${wfSelectedNodeId === n.id ? 2 : 1}"/>
      <rect x="${n.x}" y="${n.y}" width="240" height="24" rx="8" fill="${color}" opacity="0.15"/>
      <text x="${n.x+12}" y="${n.y+17}" font-size="12" fill="${color}" font-weight="600">${def.icon||'●'} ${n.label||def.label||n.type}</text>
      <text x="${n.x+12}" y="${n.y+42}" font-size="10" fill="var(--text2)">${def.description||''}</text>
      ${(def.ports?.input||[]).map((p,i) =>
        `<circle cx="${n.x}" cy="${n.y+40+i*16}" r="5" fill="var(--bg3)" stroke="${color}" stroke-width="1.5" style="cursor:crosshair" onmousedown="wfConnStart(event,'${n.id}','${p}')" onmouseup="wfConnEnd(event,'${n.id}','${p}')"/>`
      ).join('')}
      ${(def.ports?.output||[]).map((p,i) =>
        `<circle cx="${n.x+240}" cy="${n.y+30+i*16}" r="5" fill="${color}" stroke="${color}" stroke-width="1.5" style="cursor:crosshair" onmousedown="wfConnStart(event,'${n.id}','${p}')" onmouseup="wfConnEnd(event,'${n.id}','${p}')"/>`
      ).join('')}
      <rect x="${n.x+200}" y="${n.y+4}" width="34" height="18" rx="4" fill="${color}" opacity="0.8" style="cursor:pointer" onclick="wfSelectNode('${n.id}')"/>
      <text x="${n.x+217}" y="${n.y+16}" font-size="9" fill="#fff" text-anchor="middle" style="cursor:pointer" onclick="wfSelectNode('${n.id}')">配置</text>
    </g>`;
  });

  svg.innerHTML = html;
}

// ══ 节点操作 ══
function wfDragStart(e, type) {
  e.dataTransfer.setData('text/plain', type);
}

function wfAddNode(type, x, y) {
  const id = 'n' + (++wfNodeIdCounter);
  const def = wfNodeDefs[type] || {};
  wfNodes.push({id, type, label: def.label || type, config: JSON.parse(JSON.stringify(def.default_config || {})), x, y});
  wfRender();
  wfSelectNode(id);
}

function wfSelectNode(id) {
  wfSelectedNodeId = id;
  wfRender();
  wfRenderConfig(id);
}

function wfDeleteNode(id) {
  wfNodes = wfNodes.filter(n => n.id !== id);
  wfEdges = wfEdges.filter(e => e.from !== id && e.to !== id);
  if (wfSelectedNodeId === id) wfSelectedNodeId = null;
  wfRender();
  document.getElementById('wfConfigContent').innerHTML = '<div style="text-align:center;padding:40px 0;color:var(--text2);font-size:13px">点击节点编辑配置</div>';
}

// ══ 拖拽移动 ══
function wfNodeMouseDown(e, id) {
  if (e.target.closest('circle') || e.target.closest('rect[onclick]')) return;
  const rect = document.getElementById('wfCanvas').getBoundingClientRect();
  const n = wfNodes.find(x => x.id === id);
  if (!n) return;
  wfDragOffX = e.clientX - rect.left - n.x;
  wfDragOffY = e.clientY - rect.top - n.y;
  wfDraggingNode = id;
  document.addEventListener('mousemove', wfNodeMouseMove);
  document.addEventListener('mouseup', wfNodeMouseUp);
}

function wfNodeMouseMove(e) {
  if (!wfDraggingNode) return;
  const rect = document.getElementById('wfCanvas').getBoundingClientRect();
  const n = wfNodes.find(x => x.id === wfDraggingNode);
  if (n) {
    n.x = Math.max(0, (e.clientX - rect.left - wfDragOffX) / WF_ZOOM);
    n.y = Math.max(0, (e.clientY - rect.top - wfDragOffY) / WF_ZOOM);
    wfRender();
  }
}

function wfNodeMouseUp() {
  wfDraggingNode = null;
  document.removeEventListener('mousemove', wfNodeMouseMove);
  document.removeEventListener('mouseup', wfNodeMouseUp);
}

// ══ 连线 ══
function wfConnStart(e, nodeId, port) {
  wfConnecting = {nodeId, port, isOutput: true};
  e.stopPropagation();
}

function wfConnEnd(e, nodeId, port) {
  if (!wfConnecting) return;
  if (wfConnecting.nodeId !== nodeId) {
    wfEdges.push({from: wfConnecting.nodeId, to: nodeId, from_port: wfConnecting.port, to_port: port});
  }
  wfConnecting = null;
  wfRender();
}

// ══ 模板 ══
async function wfLoadTemplate(tid) {
  if (!tid || !wfTemplates[tid]) return;
  const t = wfTemplates[tid];
  wfNodes = JSON.parse(JSON.stringify(t.nodes || []));
  wfEdges = JSON.parse(JSON.stringify(t.edges || []));
  wfNodeIdCounter = wfNodes.length;
  wfSelectedNodeId = null;
  wfRender();
  document.getElementById('wfConfigContent').innerHTML = '<div style="text-align:center;padding:40px 0;color:var(--text2);font-size:13px">点击节点编辑配置</div>';
}

function wfClear() {
  wfNodes = []; wfEdges = []; wfSelectedNodeId = null; wfCurrentRunId = null;
  wfRender();
  document.getElementById('wfConfigContent').innerHTML = '<div style="text-align:center;padding:40px 0;color:var(--text2);font-size:13px">点击节点编辑配置</div>';
}

// ══ 运行 ══
async function wfRun() {
  const statusEl = document.getElementById('wfRunStatus');
  statusEl.textContent = '⏳ 运行中...';
  try {
    const r = await fetch(API + '/api/workflow/run', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({template_id: 'custom', nodes: wfNodes, edges: wfEdges}),
    });
    const d = await r.json();
    wfCurrentRunId = d.run_id;
    statusEl.textContent = '✅ 已启动';
  } catch(e) {
    statusEl.textContent = '❌ ' + e.message;
  }
}

// ══ 角色加载 ══
async function wfLoadCharacters() {
  try {
    const r = await fetch(`${API}/api/characters`);
    const data = await r.json();
    const chars = data.characters || {};
    wfCharacterList = Object.keys(chars).map(name => ({name, active: name === (data.active||'')}));
    wfCharDetails = {};
    for (const [name, info] of Object.entries(chars)) wfCharDetails[name] = info;
  } catch(e) { wfCharacterList = []; }
}

// ══ 配置面板 ══
function wfRenderConfig(nodeId) {
  const el = document.getElementById('wfConfigContent');
  const node = wfNodes.find(n => n.id === nodeId);
  if (!node) { el.innerHTML = '<div style="text-align:center;padding:40px 0;color:var(--text2);font-size:13px">点击节点编辑配置</div>'; return; }
  const def = wfNodeDefs[node.type] || {};
  const config = node.config || {};
  const fields = def.default_config || {};
  const color = def.color || '#888';
  const optMap = def.options_map || {};

  let html = `<div style="margin-bottom:10px">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <span style="font-size:14px;font-weight:600">${def.icon||'●'} ${node.label}</span>
      <button onclick="wfDeleteNode('${node.id}')" style="background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:var(--red);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">删除</button>
    </div>
    <div style="font-size:10px;color:var(--text2);margin-top:4px">${def.description||''}</div>
  </div>`;

  for (const [key, val] of Object.entries(fields)) {
    const curVal = config[key] !== undefined ? config[key] : val;
    const label = WF_FIELD_LABELS[key] || key.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
    const fieldId = 'wf_cfg_' + node.id + '_' + key;
    const fieldOptions = optMap[key];

    if (key === 'registry_name') {
      const opts = Array.isArray(wfCharacterList) ? wfCharacterList : [];
      html += `<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${label}</div>
        <select id="${fieldId}" onchange="wfUpdateConfig('${node.id}','${key}',this.value)"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
          <option value="">— 请选择角色 —</option>
          ${opts.map(c => `<option value="${c.name}" ${String(curVal) === c.name ? 'selected' : ''}>${c.name}${c.active ? ' (默认)' : ''}</option>`).join('')}
        </select>
      </div>`; continue;
    }

    if (fieldOptions && Array.isArray(fieldOptions)) {
      html += `<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${label}</div>
        <select id="${fieldId}" onchange="wfUpdateConfig('${node.id}','${key}',this.value)"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
          ${fieldOptions.map(o => `<option value="${o}" ${String(curVal) === String(o) ? 'selected' : ''}>${WF_OPTION_LABELS[o] || o}</option>`).join('')}
        </select>
      </div>`; continue;
    }

    if (typeof fieldOptions === 'string' && fieldOptions.startsWith('::number:')) {
      const parts = fieldOptions.split(':');
      html += `<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${label}</div>
        <input type="number" id="${fieldId}" value="${curVal}" min="${parts[1]||0}" max="${parts[2]||100}" step="${parts[3]||'any'}"
          onchange="wfUpdateConfig('${node.id}','${key}',parseFloat(this.value))"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
      </div>`; continue;
    }

    if (key === 'content' && typeof curVal === 'string' && curVal.length > 50) {
      html += `<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${label}</div>
        <textarea id="${fieldId}" rows="4" onchange="wfUpdateConfig('${node.id}','${key}',this.value)"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px;font-family:inherit;resize:vertical">${curVal}</textarea>
      </div>`; continue;
    }

    if (typeof val === 'boolean') {
      html += `<div style="margin-bottom:6px;display:flex;align-items:center;gap:8px">
        <input type="checkbox" id="${fieldId}" ${curVal ? 'checked' : ''}
          onchange="wfUpdateConfig('${node.id}','${key}',this.checked)"
          style="accent-color:${color}">
        <label for="${fieldId}" style="font-size:11px;color:var(--text2)">${label}</label>
      </div>`; continue;
    }

    html += `<div style="margin-bottom:6px">
      <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${label}</div>
      <input id="${fieldId}" value="${curVal}" onchange="wfUpdateConfig('${node.id}','${key}',this.value)"
        style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
    </div>`;
  }

  if (node.type === 'character' && config.registry_name) {
    const charDetail = wfCharDetails[config.registry_name];
    html += `<div style="margin-top:12px;padding-top:10px;border-top:1px solid var(--border)">
      <div style="font-size:10px;color:var(--text2);margin-bottom:4px">📸 定妆照生成</div>
      ${charDetail ? `<div style="font-size:10px;color:var(--text2);margin-bottom:6px;background:var(--bg3);padding:6px 8px;border-radius:4px">
        <div>画风: ${charDetail.art_style || '-'} | 性格: ${charDetail.personality || '-'}</div>
        <div>${charDetail.description ? charDetail.description.slice(0,60)+'...' : ''}</div>
      </div>` : ''}
      <div style="display:flex;gap:8px">
        <button onclick="wfGeneratePortrait()" style="background:#f97316;border:none;color:#fff;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px">🚀 一键生成</button>
        <span id="wfPortraitStatus" style="font-size:10px;color:var(--text2);display:flex;align-items:center">点击生成多角度+表情+网格定妆照</span>
      </div>
      <div id="wfPortraitResult" style="font-size:10px;color:var(--text2);margin-top:4px"></div>
    </div>`;
  }
  el.innerHTML = html;
}

function wfUpdateConfig(nodeId, key, value) {
  const node = wfNodes.find(n => n.id === nodeId);
  if (node) node.config[key] = value;
}

async function wfGeneratePortrait() {
  const resultEl = document.getElementById('wfPortraitResult');
  const statusEl = document.getElementById('wfPortraitStatus');
  if (!resultEl) return;
  const node = wfNodes.find(n => n.id === wfSelectedNodeId);
  if (!node) return;
  const registryName = node.config?.registry_name || '';
  if (!registryName) { resultEl.innerHTML = '❌ 请先选择角色'; return; }
  let description = '';
  try {
    const r = await fetch(API + '/api/characters');
    const d = await r.json();
    const chars = d.characters || {};
    if (chars[registryName]?.description) description = chars[registryName].description;
  } catch(e) {}
  resultEl.innerHTML = '<div style="margin-top:4px">⏳ 生成中: 基准照 → 多角度 → 表情 → 网格</div>';
  if (statusEl) statusEl.innerHTML = '⏳ 生成中...';
  try {
    const r = await fetch(API + '/api/characters/generate-portrait', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({character_name: registryName, description, force: true}),
    });
    const data = await r.json();
    if (r.ok) {
      resultEl.innerHTML = '✅ 定妆照已生成！<a href="javascript:switchView(\'characters\')" style="color:var(--primary);text-decoration:underline">查看角色库</a>';
      if (statusEl) statusEl.innerHTML = '✅ 生成完成';
    } else {
      resultEl.innerHTML = '❌ ' + (data.detail || '失败');
    }
  } catch(e) { resultEl.innerHTML = '❌ ' + e.message; }
}

// ══ 暴露到 window（供 HTML onclick 使用）══
window.wfRun = wfRun;
window.wfClear = wfClear;
window.wfDragStart = wfDragStart;
window.wfLoadTemplate = wfLoadTemplate;
window.wfSelectNode = wfSelectNode;
window.wfDeleteNode = wfDeleteNode;
window.wfNodeMouseDown = wfNodeMouseDown;
window.wfConnStart = wfConnStart;
window.wfConnEnd = wfConnEnd;
window.wfUpdateConfig = wfUpdateConfig;
window.wfGeneratePortrait = wfGeneratePortrait;
