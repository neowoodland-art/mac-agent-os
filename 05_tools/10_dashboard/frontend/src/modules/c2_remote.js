// ═══════════════════════════════════════════════════════════
// 工作流编辑器 — SVG DAG 节点编辑器
// ═══════════════════════════════════════════════════════════
let wfNodes = [], wfEdges = [], wfNodeIdCounter = 0;
let wfSelectedNodeId = null, wfDraggingNode = null, wfDragOffX = 0, wfDragOffY = 0;
let wfConnecting = null, wfCurrentRunId = null, wfPendingGateId = null;
let wfNodeDefs = {}, wfTemplates = {};
const WF_ZOOM = 1;

const NODE_COLORS = {
  input: '#6366f1', core: '#22c55e', audio: '#f59e0b', generate: '#3b82f6',
  material: '#ec4899', visual: '#8b5cf6', process: '#a855f7', flow: '#ef4444',
  output: '#64748b', default: '#888',
};

function wfNodeColor(type) {
  const def = wfNodeDefs[type];
  return def?.color || NODE_COLORS[def?.category] || NODE_COLORS.default;
}

async function loadWorkflow() {
  const el = document.getElementById('workflowContent');
  el.innerHTML = `
  <div style="display:flex;flex-direction:column;height:calc(100vh - 180px);min-height:500px">
    <!-- 工具栏 -->
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
    <!-- 主体：画布 + 配置面板 -->
    <div style="display:flex;gap:8px;flex:1;min-height:0">
      <!-- 画布区 -->
      <div style="flex:1;position:relative;background:var(--bg3);border-radius:8px;overflow:hidden;border:1px solid var(--border)">
        <svg id="wfCanvas" width="100%" height="100%" style="cursor:grab;display:block"></svg>
        <div id="wfCanvasPlaceholder" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;color:var(--text2);font-size:13px;pointer-events:none">
          从上方拖拽节点到画布，或选择模板开始
        </div>
      </div>
      <!-- 配置面板 -->
      <div id="wfConfigPanel" style="width:300px;background:var(--bg2);border-radius:8px;border:1px solid var(--border);overflow-y:auto;flex-shrink:0">
        <div id="wfConfigContent" style="padding:14px;font-size:12px;color:var(--text2)">点击节点编辑配置</div>
      </div>
    </div>
  </div>`;
  await wfInit();
}
// 导出供其他模块调用
window.loadWorkflow = loadWorkflow;


async function wfInit() {
  // 一次性加载所有节点定义和模板，避免 N+1 查询
  try {
    const [nodesR, tmplR] = await Promise.all([
      fetch(API + '/api/workflow/nodes'),
      fetch(API + '/api/workflow/templates'),
    ]);
    const nodesD = await nodesR.json();
    const tmplD = await tmplR.json();
    // 构建节点定义字典
    wfNodeDefs = {};
    for (const cat of (nodesD.categories || [])) {
      for (const nid of (cat.nodes || [])) {
        wfNodeDefs[nid] = cat._defs?.[nid] || {};
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

  // 边
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

  // 节点
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

// ══ 拖拽创建节点 ══
function wfDragStart(e, type) {
  e.dataTransfer.setData('text/plain', type);
}

function wfAddNode(type, x, y) {
  const id = 'n' + (++wfNodeIdCounter);
  const def = wfNodeDefs[type] || {};
  wfNodes.push({
    id, type, label: def.label || type,
    config: JSON.parse(JSON.stringify(def.default_config || {})),
    x, y,
  });
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

// ══ 节点拖拽移动 ══
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
    // 检测方向：从上一个节点的 output 到当前节点的 input
    if (e.target.getAttribute('fill') !== '#888' && e.target.getAttribute('fill') !== 'var(--bg3)') {
      // 当前是 output → 另一个节点的 input
    }
    wfEdges.push({from: wfConnecting.nodeId, to: nodeId, from_port: wfConnecting.port, to_port: port});
  }
  wfConnecting = null;
  wfRender();
}

// ══ 加载模板 ══
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
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({template_id: 'custom', nodes: wfNodes, edges: wfEdges}),
    });
    const d = await r.json();
    wfCurrentRunId = d.run_id;
    statusEl.textContent = '✅ 已启动';
  } catch(e) {
    statusEl.textContent = '❌ ' + e.message;
  }
}

// ══ 配置面板渲染（含中文映射） ══
const WF_FIELD_LABELS = {
  // script
  editor_mode: '编辑模式', content: '脚本内容', path: '文件路径',
  type: '脚本格式', parser: '解析方式',
  // strategy
  strategy: '生产策略',
  // tts
  voice_id: '语音模型', speed: '语速', pitch: '音调',
  // model
  provider: '供应商', model: '模型版本', duration: '时长(秒)', seed: '随机种子',
  // material
  source: '素材来源', search_keyword: '搜索关键词', count: '素材数量', orientation: '画面方向',
  // style
  style: '视觉风格', color_grade: '色调',
  // bgm
  mode: '模式', mood: '情绪风格', rhythm: '节奏强度', bpm: 'BPM',
  volume: '音量', duck_enabled: '自动避让',
  // character
  registry_name: '选择角色', outfit_preset: '服装预设',
  use_reference_images: '传递参考图', lip_sync: '唇形同步',
  // storyboard
  camera_style: '运镜风格', transition: '转场方式', scene_count: '场景数量',
  output_format: '输出格式',
  // prompt_gen
  prompt_style: '提示词风格', quality: '品质等级', add_negative: '添加负面提示',
  // subtitle
  format: '字幕格式', position: '字幕位置', style: '字幕样式', max_length: '每行最大字数',
  // output
  format: '视频格式', resolution: '分辨率', output_path: '输出路径', auto_open: '自动打开',
  // audit_gate
  message: '审核提示', auto_approve: '自动通过', timeout_minutes: '超时(分钟)',
  // story_prototype
  genre: '故事类型', title: '故事标题',
  // script_adaptor
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
  default: '默认', running: '跑步装', gym: '健身装', basketball: '篮球装',
  modern: '现代', ancient: '古风', sci_fi: '科幻',
  mystery: '悬疑', comedy: '喜剧',
  'detailed_adapt': '详细改编', 'fast_extract': '快速提炼', 'dialogue_first': '对白优先',
};

// 角色定妆照 body key 映射
const BODY_LABELS = {right_three_quarter:'右侧45°', right_side:'纯右侧面', back:'背面', front:'正面', side:'侧面'};

let wfCharacterList = [];
let wfCharDetails = {};  // {name: {description, art_style, ...}}

async function wfLoadCharacters() {
  try {
    const r = await fetch(`${API}/api/characters`);
    const data = await r.json();
    const chars = data.characters || {};
    const active = data.active || '';
    wfCharacterList = Object.keys(chars).map(name => ({name, active: name === active}));
    // 缓存详情
    wfCharDetails = {};
    for (const [name, info] of Object.entries(chars)) {
      wfCharDetails[name] = info;
    }
  } catch(e) {
    wfCharacterList = [];
  }
}

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

    // 角色选择下拉（动态加载）
    if (key === 'registry_name') {
      const opts = Array.isArray(wfCharacterList) ? wfCharacterList : [];
      html += `<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${label}</div>
        <select id="${fieldId}" onchange="wfUpdateConfig('${node.id}','${key}',this.value)"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
          <option value="">— 请选择角色 —</option>
          ${opts.map(c => `<option value="${c.name}" ${String(curVal) === c.name ? 'selected' : ''}>${c.name}${c.active ? ' (默认)' : ''}</option>`).join('')}
        </select>
      </div>`;
      continue;
    }

    // 下拉选择（有 options_map）
    if (fieldOptions && Array.isArray(fieldOptions)) {
      html += `<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${label}</div>
        <select id="${fieldId}" onchange="wfUpdateConfig('${node.id}','${key}',this.value)"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
          ${fieldOptions.map(o => `<option value="${o}" ${String(curVal) === String(o) ? 'selected' : ''}>${WF_OPTION_LABELS[o] || o}</option>`).join('')}
        </select>
      </div>`;
      continue;
    }

    // 数字输入
    if (typeof fieldOptions === 'string' && fieldOptions.startsWith('::number:')) {
      const parts = fieldOptions.split(':');
      const min = parts[1] || 0;
      const max = parts[2] || 100;
      const step = parts[3] || 'any';
      html += `<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${label}</div>
        <input type="number" id="${fieldId}" value="${curVal}" min="${min}" max="${max}" step="${step}"
          onchange="wfUpdateConfig('${node.id}','${key}',parseFloat(this.value))"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
      </div>`;
      continue;
    }

    // 长文本（content 等）
    if (key === 'content' && typeof curVal === 'string' && curVal.length > 50) {
      html += `<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${label}</div>
        <textarea id="${fieldId}" rows="4" onchange="wfUpdateConfig('${node.id}','${key}',this.value)"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px;font-family:inherit;resize:vertical">${curVal}</textarea>
      </div>`;
      continue;
    }

    // 布尔值
    if (typeof val === 'boolean') {
      html += `<div style="margin-bottom:6px;display:flex;align-items:center;gap:8px">
        <input type="checkbox" id="${fieldId}" ${curVal ? 'checked' : ''}
          onchange="wfUpdateConfig('${node.id}','${key}',this.checked)"
          style="accent-color:${color}">
        <label for="${fieldId}" style="font-size:11px;color:var(--text2)">${label}</label>
      </div>`;
      continue;
    }

    // 普通文本输入
    html += `<div style="margin-bottom:6px">
      <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${label}</div>
      <input id="${fieldId}" value="${curVal}" onchange="wfUpdateConfig('${node.id}','${key}',this.value)"
        style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
    </div>`;
  }

  // 定妆照生成区（角色节点）
  if (node.type === 'character' && config.registry_name) {
    // 尝试从本地缓存获取角色详情
    const charDetail = wfCharDetails[config.registry_name];
    html += `<div style="margin-top:12px;padding-top:10px;border-top:1px solid var(--border)">
      <div style="font-size:10px;color:var(--text2);margin-bottom:4px">📸 定妆照生成</div>
      ${charDetail ? `
        <div style="font-size:10px;color:var(--text2);margin-bottom:6px;background:var(--bg3);padding:6px 8px;border-radius:4px">
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

// ══ 定妆照生成 ══
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
    const charInfo = chars[registryName];
    if (charInfo?.description) description = charInfo.description;
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
  } catch(e) {
    resultEl.innerHTML = '❌ ' + e.message;
  }
}

// ── Summary ──
async function loadSummary() {
  const el = document.getElementById('summaryContent');
  try {
    const [sumR, heatR, dailyR] = await Promise.all([
      fetch('/api/summary').then(r=>r.json()),
      fetch('/api/heatmap').then(r=>r.json()),
      fetch('/api/daily-summary').then(r=>r.json()),
    ]);
    const heat = heatR.machines || {};
    const daily = dailyR.machines || {};
    let html = '';
    // 热力图卡片
    for (const [hostname, info] of Object.entries(heat)) {
      const acts = info.hourly || [];
      const total = acts.reduce((a,b)=>a+b,0);
      const barMax = Math.max(...acts, 1);
      html += `<div class="card"><h3>${hostname}</h3>
        <div style="font-size:12px;color:var(--text2);margin-bottom:8px">今日心跳: ${total} 次</div>
        <div style="display:flex;gap:2px;height:40px;align-items:flex-end">`;
      for (let h=0;h<24;h++) {
        const pct = acts[h] / barMax * 100;
        html += `<div title="${h}时: ${acts[h]}次" style="flex:1;background:${acts[h] > barMax*0.7 ? 'var(--coral)' : acts[h] > barMax*0.3 ? 'var(--amber)' : 'var(--bg3)'};height:${Math.max(pct,3)}%;border-radius:2px 2px 0 0"></div>`;
      }
      html += `</div><div style="display:flex;justify-content:space-between;font-size:9px;color:var(--text2);margin-top:2px">
        <span>0时</span><span>6时</span><span>12时</span><span>18时</span><span>24时</span>
      </div>`;
      // 最近事件
      const ms = daily[hostname];
      if (ms && ms.events && ms.events.length) {
        html += `<div style="margin-top:8px;font-size:11px;color:var(--text2)">最近事件:</div>`;
        ms.events.slice(-3).forEach(ev => {
          html += `<div style="font-size:10px;color:var(--text2);padding:2px 0">• ${ev.type}: ${JSON.stringify(ev.payload||{}).slice(0,40)}</div>`;
        });
      }
      html += `</div>`;
    }
    if (!html) html = '<div class="card"><div style="color:var(--text2)">暂无推送数据</div></div>';
    el.innerHTML = html;
  } catch(e) { el.innerHTML = `<div class="error">❌ ${e.message}</div>`; }
}

// ── View switcher ──
// 已移至 matrix_views.js 统一管理
// (Rollup 模块合并后，模块级别 override 会干扰原版 switchView)

// ══ 模块化角色生成流 ══

// 角色模块定义（前端本地版，不依赖后端）
const CHAR_GEN_MODULES = {
  identity: { icon: '🆔', label: '身份', desc: '姓名/性别/年龄/种族' },
  face_shape: { icon: '🗿', label: '面部轮廓', desc: '脸型/下颌/颧骨' },
  facial_features: { icon: '👁️', label: '五官细节', desc: '眼/眉/鼻/唇' },
  hair_skin: { icon: '💇', label: '头发&皮肤', desc: '发型/肤色/妆容' },
  body: { icon: '🏋️', label: '体型姿态', desc: '身高/体型/姿态' },
  clothing: { icon: '👔', label: '服装配饰', desc: '上衣/下装/配饰' },
  expression_scene: { icon: '😊', label: '神态&场景', desc: '表情/光线/背景' },
};

// 每个模块的字段配置（用于渲染表单）
const CHAR_GEN_FIELDS = {
  identity: [
    { key:'name', label:'角色名', type:'text', ph:'如: 阿远' },
    { key:'gender', label:'性别', type:'select', opts:['男性','女性'] },
    { key:'age', label:'年龄', type:'select', opts:['少年','青年','壮年','中年','老年'] },
    { key:'ethnicity', label:'地域', type:'select', opts:['中国','东亚','东南亚','南亚','欧美'] },
  ],
  face_shape: [
    { key:'shape', label:'脸型', type:'select', opts:['鹅蛋脸','瓜子脸','圆脸','方脸','国字脸','长脸','菱形脸','心形脸'] },
    { key:'jaw', label:'下颌线', type:'select', opts:['清晰分明','柔和模糊','棱角突出','圆润温和'] },
    { key:'cheekbone', label:'颧骨', type:'select', opts:['适中自然','高突出','饱满圆润','低平'] },
    { key:'forehead', label:'额头', type:'select', opts:['饱满宽阔','适中','窄小','高额头'] },
  ],
  facial_features: [
    { key:'eyes_shape', label:'眼型', type:'select', opts:['丹凤眼','杏眼','桃花眼','圆眼','细长眼','单眼皮','双眼皮','内双'] },
    { key:'eyes_color', label:'瞳孔色', type:'select', opts:['深褐','浅褐','黑色','琥珀色','灰色','蓝色','绿色'] },
    { key:'eyes_spirit', label:'眼神', type:'text', ph:'如: 深邃锐利、清澈温柔' },
    { key:'eyebrows', label:'眉型', type:'select', opts:['剑眉','柳叶眉','一字眉','上挑眉','弯眉','粗眉','细长眉'] },
    { key:'nose', label:'鼻型', type:'select', opts:['高挺','挺直窄小','中等挺拔','低平柔和'] },
    { key:'nose_tip', label:'鼻头', type:'select', opts:['小巧圆润','圆润饱满','尖翘','略宽'] },
    { key:'lips', label:'唇型', type:'select', opts:['薄唇','厚唇','M形唇','饱满','樱桃小嘴','微笑唇'] },
    { key:'lips_state', label:'唇状态', type:'select', opts:['自然闭合','微张','紧抿','嘴角微扬','含笑意'] },
  ],
  hair_skin: [
    { key:'hair_style', label:'发型', type:'select', opts:['短发','寸头','中长发','背头','三七分','齐刘海','碎发','高马尾','披肩发'] },
    { key:'hair_color', label:'发色', type:'select', opts:['黑色','深棕','浅棕','亚麻色','灰色','银白'] },
    { key:'hair_detail', label:'发型细节', type:'text', ph:'如: 两侧收短顶部略长' },
    { key:'skin_tone', label:'肤色', type:'select', opts:['冷白皮','暖白皮','健康小麦','蜜色','古铜色','深色'] },
    { key:'skin_texture', label:'肤质', type:'select', opts:['细腻光滑','自然肌理','毛孔可见','水润光泽'] },
    { key:'complexion', label:'气色', type:'select', opts:['红润健康','略显苍白','容光焕发','自然均匀'] },
    { key:'makeup', label:'妆容风格', type:'select', opts:['素颜','淡妆','精致妆容','裸妆','烟熏妆'] },
    { key:'blemish', label:'特殊标记', type:'text', ph:'如: 右眉上细疤、左颊美人痣' },
  ],
  body: [
    { key:'height', label:'身高', type:'select', opts:['矮小(155-165)','中等(165-175)','中高(175-185)','高大(185+)'] },
    { key:'build', label:'体型', type:'select', opts:['纤细瘦弱','偏瘦','标准匀称','健壮','壮硕','魁梧'] },
    { key:'shoulder', label:'肩宽', type:'select', opts:['窄肩','标准','宽肩','厚肩'] },
    { key:'posture', label:'姿态', type:'select', opts:['挺拔','自然放松','微驼','端庄','慵懒'] },
  ],
  clothing: [
    { key:'top', label:'上装', type:'text', ph:'如: 深灰色拉链运动夹克' },
    { key:'inner', label:'内搭', type:'text', ph:'如: 白色圆领速干内衬' },
    { key:'bottom', label:'下装', type:'text', ph:'如: 深蓝色牛仔裤' },
    { key:'shoes', label:'鞋子', type:'text', ph:'如: 白色跑步鞋' },
    { key:'accessories', label:'配饰', type:'text', ph:'如: 蓝色无线运动耳机(右耳)、细框眼镜' },
    { key:'style_tag', label:'穿搭风格', type:'select', opts:['运动休闲','商务正装','日系清新','街头潮流','简约素雅'] },
  ],
  expression_scene: [
    { key:'base_mood', label:'情绪基调', type:'select', opts:['平静从容','温和友善','冷峻严肃','沉稳内敛','自信昂扬','恬静淡然'] },
    { key:'expression', label:'表面表情', type:'select', opts:['中性无表情','淡淡微笑','微笑','开怀大笑','皱眉沉思','目光坚定'] },
    { key:'eye_spirit', label:'眼神细节', type:'text', ph:'如: 目光坚定直视前方、眼中带笑意' },
    { key:'aura', label:'气质气场', type:'text', ph:'如: 沉稳内敛不怒自威、亲和温暖如沐春风' },
    { key:'light_type', label:'光型', type:'select', opts:['柔光箱均匀布光','美人碟柔光','伦勃朗光','分割光','逆光轮廓光','阴天漫射光'] },
    { key:'lens', label:'镜头', type:'select', opts:['标准50mm','中焦85mm','长焦135mm'] },
    { key:'background', label:'背景环境', type:'text', ph:'如: 纯灰色专业背景、清晨城市街道' },
  ],
};

let charGenLayerData = {};  // 存储所有模块的当前值

function loadCharGen() {
  document.getElementById('charGenStep1').classList.remove('hidden');
  document.getElementById('charGenStep2').classList.add('hidden');
  document.getElementById('charGenStep3').classList.add('hidden');
  document.getElementById('charGenDirection').value = '';
  document.getElementById('charGenStep1Result').innerHTML = '';
  document.getElementById('charGenStep2Result').innerHTML = '';
  document.getElementById('charGenResultBody').innerHTML = '';
  charGenLayerData = {};
  // 渲染模块Tab
  renderCharGenTabs();
  // 默认选中第一个模块
  charGenSwitchTab(Object.keys(CHAR_GEN_MODULES)[0]);
}

function renderCharGenTabs() {
  const tabsEl = document.getElementById('charGenTabs');
  tabsEl.innerHTML = Object.entries(CHAR_GEN_MODULES).map(([id, mod]) =>
    `<div class="char-gen-tab" data-tab="${id}" onclick="charGenSwitchTab('${id}')"
      style="padding:5px 10px;border-radius:6px;cursor:pointer;font-size:11px;
             background:var(--bg3);color:var(--text2);border:1px solid transparent;
             display:flex;align-items:center;gap:4px;
             transition:all .15s">
      ${mod.icon} ${mod.label}
    </div>`
  ).join('');
}

function charGenSwitchTab(tabId) {
  // 更新tab高亮
  document.querySelectorAll('.char-gen-tab').forEach(el => {
    const isActive = el.dataset.tab === tabId;
    el.style.background = isActive ? 'var(--primary)' : 'var(--bg3)';
    el.style.color = isActive ? '#fff' : 'var(--text2)';
    el.style.borderColor = isActive ? 'var(--primary)' : 'transparent';
  });
  
  // 渲染选中模块的表单
  const mod = CHAR_GEN_MODULES[tabId];
  const fields = CHAR_GEN_FIELDS[tabId] || [];
  const container = document.getElementById('charGenPanelContent');
  
  let html = `<div style="background:var(--bg3);border-radius:8px;padding:14px;margin-bottom:8px">
    <div style="font-size:12px;color:var(--text2);margin-bottom:8px">${mod.desc}</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">`;
  
  for (const f of fields) {
    const val = (charGenLayerData[tabId] || {})[f.key] || '';
    const fieldId = 'cg_' + tabId + '_' + f.key;
    
    if (f.type === 'select') {
      html += `<div>
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${f.label}</div>
        <select id="${fieldId}" onchange="charGenFieldChange('${tabId}','${f.key}',this.value)"
          style="width:100%;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
          <option value="">— 选择 —</option>
          ${(f.opts||[]).map(o => `<option value="${o}" ${val === o ? 'selected' : ''}>${o}</option>`).join('')}
        </select>
      </div>`;
    } else {
      html += `<div style="${f.key === 'eye_spirit' || f.key === 'background' || f.key === 'accessories' ? 'grid-column:1/-1' : ''}">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${f.label}</div>
        <input id="${fieldId}" value="${val}" placeholder="${f.ph||''}"
          onchange="charGenFieldChange('${tabId}','${f.key}',this.value)"
          style="width:100%;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
      </div>`;
    }
  }
  
  html += `</div></div>`;
  
  // 这个模块的文本描述预览
  html += `<div style="font-size:10px;color:var(--text2);background:var(--bg2);padding:6px 10px;border-radius:4px;margin-bottom:4px">
    📝 当前 <strong>${mod.label}</strong> 描述: <span id="cg_preview_${tabId}">${buildLayerDesc(tabId)}</span>
  </div>`;
  
  container.innerHTML = html;
  charGenUpdatePreview();
}

function charGenFieldChange(tabId, key, value) {
  if (!charGenLayerData[tabId]) charGenLayerData[tabId] = {};
  charGenLayerData[tabId][key] = value;
  // 更新该模块的描述预览
  const prev = document.getElementById('cg_preview_' + tabId);
  if (prev) prev.textContent = buildLayerDesc(tabId);
  // 更新总预览
  charGenUpdatePreview();
}

function buildLayerDesc(tabId) {
  const data = charGenLayerData[tabId] || {};
  const parts = [];
  for (const v of Object.values(data)) {
    if (v) parts.push(v);
  }
  return parts.join('、') || '—';
}

function buildFullDescription() {
  const parts = [];
  // 按模块顺序组装
  const moduleOrder = Object.keys(CHAR_GEN_MODULES);
  for (const tabId of moduleOrder) {
    const desc = buildLayerDesc(tabId);
    if (desc && desc !== '—') {
      parts.push(`【${CHAR_GEN_MODULES[tabId].label}】${desc}`);
    }
  }
  return parts.join('\n');
}

function charGenUpdatePreview() {
  const el = document.getElementById('charGenPromptPreview');
  if (!el) return;
  const full = buildFullDescription();
  el.value = full || '— 填写模块后自动生成预览 —';
}

async function charGenAutoFill() {
  const dirEl = document.getElementById('charGenDirection');
  const resultEl = document.getElementById('charGenStep1Result');
  const direction = dirEl.value.trim();
  if (!direction) { resultEl.innerHTML = '❌ 请输入角色方向'; return; }
  
  resultEl.innerHTML = '⏳ AI 正在生成完整角色定义...';
  document.getElementById('charGenStep2').classList.remove('hidden');
  
  try {
    const r = await fetch(API + '/api/characters/expand-direction', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({direction}),
    });
    const data = await r.json();
    const description = data.description || direction;
    
    // 从描述中智能填充各模块的字段
    charGenAutoFillFromDescription(description);
    
    // 自动生成角色名
    const nameMatch = description.match(/([\u4e00-\u9fff]{2,6})(?:男性|女性|少年|少女|中年|老人)/);
    if (nameMatch) {
      document.getElementById('charGenName').value = nameMatch[1].slice(-3).replace(/[的男女人]/g,'');
    }
    
    resultEl.innerHTML = '✅ 各模块已自动填充！请逐项检查调整';
    // 默认选中"身份"模块
    charGenSwitchTab('identity');
    document.getElementById('charGenStep2').scrollIntoView({behavior: 'smooth', block: 'start'});
  } catch(e) {
    resultEl.innerHTML = '❌ 自动填充失败: ' + e.message;
    // 降级：显示空面板
    charGenSwitchTab('identity');
    document.getElementById('charGenStep2').classList.remove('hidden');
  }
}

function charGenAutoFillFromDescription(desc) {
  // 智能提取：从自然语言描述中提取各字段值
  const match = (pattern) => {
    const m = new RegExp(pattern).exec(desc);
    return m ? m[1] : '';
  };
  
  // 试探性地填充各字段
  charGenLayerData = {};
  
  // 身份
  charGenLayerData.identity = {
    gender: match(/(男性|女性)/),
    age: match(/(少年|青年|壮年|中年|老年)/),
    ethnicity: match(/(中国|东亚|东南亚|南亚|欧美)/) || '中国',
    name: match(/([\u4e00-\u9fff]{2,4})[，,]/),
  };
  
  // 面部轮廓
  charGenLayerData.face_shape = {
    shape: match(/(鹅蛋脸|瓜子脸|圆脸|方脸|国字脸|长脸|菱形脸|心形脸)/),
    jaw: match(/(清晰分明|柔和模糊|棱角突出|圆润温和)/),
    cheekbone: match(/(高突出|饱满圆润|低平)/) || '适中自然',
    forehead: match(/(饱满宽阔|窄小|高额头)/) || '适中',
  };
  
  // 五官
  charGenLayerData.facial_features = {
    eyes_shape: match(/(丹凤眼|杏眼|桃花眼|圆眼|细长眼|单眼皮|双眼皮|内双)/),
    eyes_color: match(/(深褐|浅褐|黑色|琥珀色|灰色|蓝色|绿色)/) || '深褐',
    eyes_spirit: match(/(深邃[^，。]*?|清澈[^，。]*?|锐利[^，。]*?|温柔[^，。]*?|沉稳[^，。]*?)/) || '',
    eyebrows: match(/(剑眉|柳叶眉|一字眉|上挑眉|弯眉|粗眉|细长眉)/),
    nose: match(/(高挺|挺直窄小|中等挺拔|低平柔和)/) || '高挺',
    nose_tip: match(/(小巧圆润|圆润饱满|尖翘|略宽)/) || '适中',
    lips: match(/(薄唇|厚唇|M形唇|饱满|樱桃小嘴|微笑唇)/),
    lips_state: match(/(微张|紧抿|嘴角微扬|含笑意)/) || '自然闭合',
  };
  
  // 头发皮肤
  charGenLayerData.hair_skin = {
    hair_style: match(/(短发|寸头|中长发|背头|三七分|齐刘海|碎发|高马尾|披肩发)/) || '短发',
    hair_color: match(/(黑色|深棕|浅棕|亚麻色|灰色|银白)/) || '黑色',
    hair_detail: match(/(两侧收短[^，。]*?|发际线[^，。]*?)/) || '',
    skin_tone: match(/(冷白皮|暖白皮|健康小麦|蜜色|古铜色|深色)/) || '健康小麦',
    skin_texture: match(/(细腻光滑|自然肌理|毛孔可见|水润光泽)/) || '自然肌理',
    complexion: match(/(红润健康|略显苍白|容光焕发|自然均匀)/) || '红润健康',
    makeup: match(/(素颜|淡妆|精致妆容|裸妆|烟熏妆)/) || '素颜',
    blemish: match(/([^，。]*?疤[^，。]*?|[^，。]*?痣[^，。]*?|[^，。]*?纹[^，。]*?)/) || '',
  };
  
  // 体型
  const heightMatch = desc.match(/(\d+)/);
  const heightStr = heightMatch ? (parseInt(heightMatch[1]) < 170 ? '中等(165-175)' : parseInt(heightMatch[1]) < 180 ? '中高(175-185)' : '高大(185+)') : '';
  charGenLayerData.body = {
    height: heightStr,
    build: match(/(纤细瘦弱|偏瘦|标准匀称|健壮|壮硕|魁梧)/),
    shoulder: match(/(窄肩|标准|宽肩|厚肩)/) || '标准',
    posture: match(/(挺拔|自然放松|微驼|端庄|慵懒)/) || '挺拔',
  };
  
  // 服装配饰
  const topMatch = match(/身穿([^，。]*?夹克|[^，。]*?卫衣|[^，。]*?T恤|[^，。]*?衬衫|[^，。]*?外套|[^，。]*?运动装)/);
  const innerMatch = match(/内搭([^，。]*?内衬|[^，。]*?T恤|[^，。]*?打底|[^，。]*?背心)/);
  const bottomMatch = match(/(下穿|下着|穿着)[^，。]*?(牛仔裤|[^，。]*?短裤|[^，。]*?长裤|[^，。]*?裙子)/);
  const accMatch = match(/[佩戴戴着带着]([^，。]*?耳机|[^，。]*?眼镜|[^，。]*?手表|[^，。]*?手环|[^，。]*?帽子|[^，。]*?项链)/);
  
  charGenLayerData.clothing = {
    top: topMatch || '',
    inner: innerMatch || '',
    bottom: bottomMatch ? bottomMatch[0] : '',
    shoes: '',
    accessories: accMatch || '',
    style_tag: match(/(运动休闲|商务正装|日系清新|街头潮流|简约素雅)/) || '',
  };
  
  // 神态场景
  charGenLayerData.expression_scene = {
    base_mood: match(/(平静从容|温和友善|冷峻严肃|沉稳内敛|自信昂扬|恬静淡然)/),
    expression: match(/(中性无表情|淡淡微笑|微笑|开怀大笑|皱眉沉思|目光坚定)/),
    eye_spirit: match(/(目光[^，。]*?|眼神[^，。]*?)/) || '',
    aura: match(/(沉稳内敛[^，。]*|亲和温暖[^，。]*|疏离清冷[^，。]*)/) || '',
    light_type: '柔光箱均匀布光',
    lens: '中焦85mm',
    background: match(/([^，。]*?背景[^，。]*?|在[^，。]*?[城里路巷][^，。]*?|[^，。]*?环境[^，。]*?)/) || '纯灰色专业背景',
  };
}

async function charGenRun() {
  const resultEl = document.getElementById('charGenStep2Result');
  const name = document.getElementById('charGenName').value.trim();
  const seed = parseInt(document.getElementById('charGenSeed').value) || 42;
  const genImages = document.getElementById('charGenGenImages').checked;
  
  // 收集所有模块数据
  const allData = {};
  for (const [tabId, data] of Object.entries(charGenLayerData)) {
    for (const [key, val] of Object.entries(data)) {
      if (val) allData[`${tabId}.${key}`] = val;
    }
  }
  
  const fullDesc = buildFullDescription();
  if (!fullDesc || fullDesc === '— 填写模块后自动生成预览 —') {
    resultEl.innerHTML = '❌ 请至少填写1个模块的字段';
    return;
  }
  
  resultEl.innerHTML = '⏳ 正在生成角色...<br>';
  resultEl.innerHTML += '<div style="font-size:10px;color:var(--text2);margin-top:4px">步骤: 注册属性 → ' + (genImages ? '生成变体 → ' : '') + '写入知识库</div>';
  
  try {
    const r = await fetch(API + '/api/characters/generate-from-direction', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        direction: fullDesc,
        name: name,
        generate_images: genImages,
        seed: seed,
        layers: allData,
      }),
    });
    const data = await r.json();
    if (!r.ok) {
      resultEl.innerHTML = '❌ 生成失败: ' + (data.detail || '未知错误');
      return;
    }
    
    document.getElementById('charGenStep3').classList.remove('hidden');
    document.getElementById('charGenResultTitle').textContent = `✅ 角色「${data.name}」生成完成`;
    
    let html = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
      <div style="background:var(--bg3);border-radius:6px;padding:14px">
        <div style="font-size:11px;color:var(--text2);font-weight:600;margin-bottom:6px">📋 角色信息</div>
        <div style="font-size:12px;color:var(--text);line-height:1.6">${data.description}</div>
      </div>
      <div style="background:var(--bg3);border-radius:6px;padding:14px">
        <div style="font-size:11px;color:var(--text2);font-weight:600;margin-bottom:6px">🏷 标签 & 属性</div>
        <div style="font-size:11px;color:var(--text2)">
          外观特征: ${(data.attributes?.appearance || []).join('、') || '-'}<br>
          性格: ${data.attributes?.personality || '-'}<br>
          画风: ${data.attributes?.art_style || '-'}<br>
          音色: ${data.attributes?.voice_style || '-'}
        </div>
      </div>
    </div>`;
    
    if (data.baseline && data.baseline.path) {
      html += `<div style="margin-top:12px">
        <div style="font-size:12px;color:var(--text2);font-weight:600;margin-bottom:6px">📸 生成结果</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px">`;
      if (data.baseline && data.baseline.url) {
        html += `<div style="text-align:center"><img src="${data.baseline.url}" style="width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:6px;background:var(--bg3)" onerror="this.parentElement.style.display='none'"><div style="font-size:10px;color:var(--text2);margin-top:2px">正面基准</div></div>`;
      }
      if (data.angles) {
        for (const [angle, info] of Object.entries(data.angles)) {
          if (info && info.url) {
            html += `<div style="text-align:center"><img src="${info.url}" style="width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:6px;background:var(--bg3)" onerror="this.parentElement.style.display='none'"><div style="font-size:10px;color:var(--text2);margin-top:2px">${BODY_LABELS[angle] || angle}</div></div>`;
          }
        }
      }
      if (data.expressions) {
        const exprLabels = {neutral:'中性', smile:'微笑', focused:'专注', laugh:'大笑', serious:'严肃'};
        for (const [expr, info] of Object.entries(data.expressions)) {
          if (info && info.url) {
            html += `<div style="text-align:center"><img src="${info.url}" style="width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:6px;background:var(--bg3)" onerror="this.parentElement.style.display='none'"><div style="font-size:10px;color:var(--text2);margin-top:2px">${exprLabels[expr] || expr}</div></div>`;
          }
        }
      }
      if (data.grid && data.grid.url) {
        html += `<div style="text-align:center;grid-column:1/-1"><img src="${data.grid.url}" style="width:100%;max-height:300px;object-fit:contain;border-radius:6px;background:var(--bg3)" onerror="this.parentElement.style.display='none'"><div style="font-size:10px;color:var(--text2);margin-top:2px">网格定妆照</div></div>`;
      }
      html += `</div></div>`;
    }
    
    html += `<div style="margin-top:12px;display:flex;gap:8px">
      <button onclick="switchView('characters')" style="background:var(--primary);border:none;color:#fff;padding:6px 16px;border-radius:4px;cursor:pointer;font-size:12px">📋 查看角色库</button>
      <button onclick="switchView('workflow')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 16px;border-radius:4px;cursor:pointer;font-size:12px">🔀 去工作流</button>
      <button onclick="loadCharGen()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 16px;border-radius:4px;cursor:pointer;font-size:12px">🔄 新建角色</button>
    </div>`;
    
    document.getElementById('charGenResultBody').innerHTML = html;
    resultEl.innerHTML = '✅ 角色生成完成！';
    document.getElementById('charGenStep3').scrollIntoView({behavior: 'smooth', block: 'center'});
  } catch(e) {
    resultEl.innerHTML = '❌ 生成失败: ' + e.message;
  }
}

// ── Characters ──
async function loadCharacters() {
  const el = document.getElementById('characterGrid');
  const countEl = document.getElementById('charCount');
  el.innerHTML = '<div class="loading">加载角色数据...</div>';
  try {
    const r = await fetch(`${API}/api/characters`);
    const d = await r.json();
    const chars = d.characters || {};
    const active = d.active || '';
    const entries = Object.entries(chars);
    countEl.textContent = `共 ${entries.length} 个角色`;

    if (!entries.length) {
      el.innerHTML = '<div class="error" style="padding:40px">暂无角色数据</div>';
      return;
    }

    el.innerHTML = entries.map(([name, char]) => {
      const isActive = name === active;
      const refImgs = char.reference_images || {};
      const exprs = refImgs.expressions || {};
      const exprCount = Object.keys(exprs).length;
      // 兼容新旧两种 key 名: 旧=grid/portrait, 新=face_anchor/baseline/body
      const hasGrid = !!(refImgs.grid || refImgs.face_anchor || refImgs.baseline);
      const hasPortrait = !!(refImgs.portrait || refImgs.face_anchor);
      const hasBody = refImgs.body && Object.values(refImgs.body).some(Boolean);
      const hasRealPhoto = !!(refImgs.real_photo_fullbody || refImgs.real_photo_portrait);
      return `<div style="background:var(--bg2);border-radius:var(--radius);padding:20px;border:1px solid ${isActive ? 'var(--primary)' : 'var(--border)'}">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px">
            <div>
              <div style="font-weight:600;font-size:16px">${name}</div>
              <div style="font-size:11px;color:var(--text2)">${char.description||''}</div>
            </div>
          </div>
          ${isActive ? `<span style="padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:rgba(99,102,241,.15);color:var(--primary);border:1px solid rgba(99,102,241,.3)">当前角色</span>` : ''}
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;margin-bottom:10px;color:var(--text2)">
          <div>画风: ${char.art_style||'-'}</div>
          <div>音色: ${char.voice_style||'-'}</div>
          <div>性格: ${char.personality||'-'}</div>
          <div>BGM: ${char.default_bgm_style||'-'}</div>
        </div>

        ${char.prompt_template ? `<div style="margin-bottom:10px;font-size:11px;color:var(--text2)">
          <span style="font-weight:600">提示词模板:</span>
          <div style="background:var(--bg3);padding:8px;border-radius:6px;margin-top:4px;font-family:mono;font-size:10px;word-break:break-all">${Object.values(char.prompt_template).join(' | ')}</div>
        </div>` : ''}

        ${char.outfit_presets ? `<div style="margin-bottom:10px">
          <div style="font-size:11px;color:var(--text2);font-weight:600;margin-bottom:4px">穿搭预设</div>
          <div style="display:flex;gap:4px;flex-wrap:wrap">${Object.keys(char.outfit_presets).map(k => `<span style="background:var(--bg3);padding:2px 8px;border-radius:4px;font-size:10px">${k}</span>`).join('')}</div>
        </div>` : ''}

        <div style="font-size:11px;color:var(--text2)">
          <div>定妆照: ${hasGrid ? '✅ 已生成' : '❌ 未生成'} ${hasRealPhoto ? '·📷 真人参考照' : ''} ${hasBody ? `·${Object.keys(refImgs.body).length}个角度` : ''}</div>
          ${char.seed ? `<div>固定 Seed: ${char.seed}</div>` : ''}
        </div>

        ${hasBody ? renderCharPortraitGallery(refImgs, name) : ''}

        ${!hasBody && hasRealPhoto ? `<div style="margin-top:8px;border-top:1px solid var(--border);padding-top:8px">
          <div style="font-size:10px;color:var(--text2)">📷 已上传真人参考照，点击「视频工厂→工作流编辑器」中的角色节点，生成定妆照</div>
        </div>` : ''}

        ${char.appearance && char.appearance.length ? `<div style="margin-top:8px;border-top:1px solid var(--border);padding-top:8px">
          <div style="font-size:11px;color:var(--text2);font-weight:600;margin-bottom:4px">外观特征</div>
          <ul style="margin:0;padding-left:16px;font-size:11px;color:var(--text2)">${char.appearance.map(a => `<li>${a}</li>`).join('')}</ul>
        </div>` : ''}
      </div>`;
    }).join('');
  } catch(e) {
    el.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}

// ── 角色定妆照画廊预览（兼容新旧 body key） ──
function renderCharPortraitGallery(refImgs, name) {
  const body = refImgs.body || {};
  const faceAnchor = refImgs.face_anchor || refImgs.baseline || '';
  const charName = faceAnchor ? faceAnchor.split('/').slice(-2, -1)[0] : name;
  const base = charName ? API + '/api/portrait-files/' + encodeURIComponent(charName) : '';
  
  const items = [];
  if (faceAnchor) items.push({
    label: '正面基准', 
    src: base + '/' + faceAnchor.split('/').pop(),
    isAnchor: true,
  });
  for (const [k, p] of Object.entries(body)) {
    if (p) {
      items.push({
        label: BODY_LABELS[k] || k,
        src: base + '/' + p.split('/').pop(),
        isAnchor: false,
      });
    }
  }
  
  // 也尝试显示真人参考照
  const realPhoto = refImgs.real_photo_fullbody || refImgs.real_photo_portrait || '';
  
  const folderPath = faceAnchor ? faceAnchor.substring(0, faceAnchor.lastIndexOf('/')) : '';
  const colCount = Math.min(items.length + (realPhoto ? 1 : 0), 4);
  
  return `<div style="margin-top:10px;border-top:1px solid var(--border);padding-top:10px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
      <span style="font-size:12px;color:var(--text2);font-weight:600">📸 定妆照预览</span>
      ${folderPath ? `<a href="file://${folderPath}" target="_blank" style="font-size:10px;color:var(--primary);text-decoration:none">📂 打开文件夹</a>` : ''}
    </div>
    <div style="display:grid;grid-template-columns:repeat(${colCount},1fr);gap:6px">
      ${items.map(item => `<div style="text-align:center">
        <img src="${item.src}" style="width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:6px;background:var(--bg3);border:2px solid ${item.isAnchor ? 'var(--primary)' : 'transparent'}"
          onerror="this.parentElement.style.display='none'"
          onclick="window.open('file://${faceAnchor ? body[Object.keys(body).find(k => body[k].split('/').pop() === item.src.split('/').pop())] || faceAnchor : ''}')">
        <div style="font-size:10px;color:var(--text2);margin-top:2px">${item.label}</div>
      </div>`).join('')}
    </div>
  </div>`;
}

// ── Capabilities ──
let currentCapGroup = null;
async function loadCapabilities() {
  const el = document.getElementById('capabilityContent');
  const tabsEl = document.getElementById('capGroupTabs');
  const countEl = document.getElementById('capCount');
  el.innerHTML = '<div class="loading">加载原子能力...</div>';
  try {
    const r = await fetch(`${API}/api/capabilities`);
    const d = await r.json();
    const groups = d.groups || [];
    const matrix = d.matrix || [];
    countEl.textContent = `共 ${d.total_items||0} 个能力`;

    if (!groups.length) {
      el.innerHTML = '<div class="error" style="padding:40px">暂无能力数据</div>';
      return;
    }

    // 分组标签
    tabsEl.innerHTML = groups.map((g, i) =>
      `<button class="btn ${i === 0 ? 'active' : ''}" onclick="switchCapGroup(${i})" style="${i === 0 ? 'background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px' : 'background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px'}">${g.name} (${g.items.length})</button>`
    ).join('');

    currentCapGroup = 0;
    renderCapGroup(groups[0], matrix);
  } catch(e) {
    el.innerHTML = `<div class="error">❌ 加载失败: ${e.message}</div>`;
  }
}
// 导出供其他模块调用
window.loadCapabilities = loadCapabilities;


function switchCapGroup(idx) {
  currentCapGroup = idx;
  const tabs = document.getElementById('capGroupTabs').children;
  for (let i = 0; i < tabs.length; i++) {
    tabs[i].style.background = i === idx ? 'var(--primary)' : 'var(--bg2)';
    tabs[i].style.color = i === idx ? '#fff' : 'var(--text)';
    tabs[i].style.border = i === idx ? 'none' : '1px solid var(--border)';
  }
  fetch(`${API}/api/capabilities`).then(r => r.json()).then(d => {
    renderCapGroup(d.groups[idx], d.matrix);
  });
}

function renderCapGroup(group, matrix) {
  const el = document.getElementById('capabilityContent');
  if (!group || !group.items) {
    el.innerHTML = '<div class="error">无数据</div>';
    return;
  }

  el.innerHTML = `<div class="chart-box">
    <div style="font-size:14px;font-weight:600;margin-bottom:12px">${group.name}</div>
    <table><thead><tr>${Object.keys(group.items[0]||{}).map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>
      ${group.items.map(item => `<tr>${Object.values(item).map(v => `<td>${v||'-'}</td>`).join('')}</tr>`).join('')}
    </tbody></table>
  </div>`;

  // 如果当前是第一个分组（音频），且有关联的 matrix，显示交叉矩阵
  if (matrix && matrix.length && currentCapGroup === 0) {
    const matrixHeaders = Object.keys(matrix[0]?.usages || {});
    el.innerHTML += `<div class="chart-box" style="margin-top:16px">
      <div style="font-size:14px;font-weight:600;margin-bottom:12px">交叉能力矩阵 (全量)</div>
      <div style="font-size:11px;color:var(--text2);margin-bottom:8px">⬛ = 核心依赖 · ⬜ = 可用 · ↔ = 可选接入</div>
      <table><thead><tr><th style="position:sticky;left:0;background:var(--bg2)">能力</th>${matrixHeaders.map(h => `<th style="font-size:10px">${h}</th>`).join('')}</tr></thead><tbody>
        ${matrix.map(row => `<tr><td style="position:sticky;left:0;background:var(--bg2);font-weight:600;white-space:nowrap">${row.name}</td>${matrixHeaders.map(h => {
          const v = row.usages[h] || '';
          const bg = v.includes('⬛') ? 'rgba(99,102,241,.15)' : v.includes('↔') ? 'rgba(245,158,11,.1)' : v ? 'rgba(34,197,94,.08)' : '';
          return `<td style="text-align:center;background:${bg};font-size:11px">${v||'-'}</td>`;
        }).join('')}</tr>`).join('')}
      </tbody></table>
    </div>`;
  }
}

// ── Plugin Detail View ──
async function loadPluginView(name) {
  let viewId = 'plugin-view-' + name;
  document.querySelectorAll('[id^="plugin-view-"]').forEach(el => el.style.display = 'none');
  
  let el = document.getElementById(viewId);
  if (!el) {
    el = document.createElement('div');
    el.id = viewId;
    document.getElementById('app').appendChild(el);
  }
  el.style.display = 'block';
  el.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text2)">加载中...</div>';

  try {
    const [metaR, sumR, detR] = await Promise.all([
      fetch('/api/plugins').then(r=>r.json()),
      fetch('/api/plugins/'+name+'/summary').then(r=>r.json()),
      fetch('/api/plugins/'+name+'/detail').then(r=>r.json()),
    ]);

    const meta = (metaR.plugins || []).find(p => p.name === name) || {};
    const summary = sumR.data || {};
    const detail = detR.data || {};
    
    let html = '<h2 style="font-size:18px;font-weight:500;margin-bottom:16px">' + (meta.icon || '') + ' ' + (meta.label || name) + '</h2>';

    // Summary cards
    var machData = summary['各机器'] || {};
    if (Object.keys(machData).length > 0) {
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;margin-bottom:20px">';
      for (var hn in machData) {
        var info = machData[hn];
        if (typeof info === 'object' && info._note) {
          html += '<div class="card"><h4 style="margin:0 0 6px">' + hn + '</h4><div style="color:var(--text2);font-size:12px">' + info._note + '</div></div>';
          continue;
        }
        if (typeof info === 'object') {
          html += '<div class="card"><h4 style="margin:0 0 6px">' + hn + '</h4>';
          for (var k in info) {
            html += '<div style="font-size:12px;padding:2px 0"><span style="color:var(--text2)">' + k + ':</span> <strong>' + info[k] + '</strong></div>';
          }
          html += '</div>';
        }
      }
      html += '</div>';
    }

    // Detail lists
    if (Object.keys(detail).length > 0) {
      for (var hn in detail) {
        var info = detail[hn];
        if (typeof info === 'object') {
          // Table fields (arrays)
          for (var key in info) {
            var items = info[key];
            if (Array.isArray(items) && items.length > 0) {
              html += '<div class="card" style="margin-bottom:12px"><h4 style="margin:0 0 8px">' + hn + ' - ' + key + '</h4>';
              html += '<table style="width:100%;font-size:12px;border-collapse:collapse">';
              html += '<thead><tr style="background:var(--bg3)">';
              var sample = items[0];
              if (typeof sample === 'object') {
                var keys = Object.keys(sample).slice(0, 6);
                for (var ki = 0; ki < keys.length; ki++) {
                  html += '<th style="padding:6px 8px;text-align:left;font-weight:500">' + keys[ki] + '</th>';
                }
              }
              html += '</tr></thead><tbody>';
              var maxItems = Math.min(items.length, 50);
              for (var ii = 0; ii < maxItems; ii++) {
                var item = items[ii];
                html += '<tr style="border-top:1px solid var(--border)">';
                if (typeof item === 'object') {
                  var vals = Object.values(item).slice(0, 6);
                  for (var vi = 0; vi < vals.length; vi++) {
                    html += '<td style="padding:4px 8px">' + String(vals[vi] || '-').slice(0,40) + '</td>';
                  }
                }
                html += '</tr>';
              }
              if (items.length > 50) {
                html += '<tr><td colspan="6" style="padding:8px;text-align:center;color:var(--text2)">... 还有 ' + (items.length - 50) + ' 条</td></tr>';
              }
              html += '</tbody></table></div>';
            }
          }
          // Key-value fields
          var plainItems = [];
          for (var key in info) {
            var v = info[key];
            if (!Array.isArray(v) && typeof v !== 'object') {
              plainItems.push({k:key, v:v});
            }
          }
          if (plainItems.length > 0) {
            html += '<div class="card" style="margin-bottom:12px"><h4 style="margin:0 0 6px">' + hn + '</h4>';
            for (var pi = 0; pi < plainItems.length; pi++) {
              html += '<div style="font-size:12px;padding:2px 0"><span style="color:var(--text2)">' + plainItems[pi].k + ':</span> <strong>' + plainItems[pi].v + '</strong></div>';
            }
            html += '</div>';
          }
        }
      }
    }

    if (html.indexOf('card') === -1) {
      html += '<div style="padding:40px;text-align:center;color:var(--text2)">暂无数据</div>';
    }
    el.innerHTML = html;
  } catch(e) {
    el.innerHTML = '<div class="error">加载失败: ' + e.message + '</div>';
  }
}
// ── 导出（防 Rollup tree-shake）──
window.buildFullDescription = buildFullDescription;
window.buildLayerDesc = buildLayerDesc;
window.charGenAutoFill = charGenAutoFill;
window.charGenAutoFillFromDescription = charGenAutoFillFromDescription;
window.charGenFieldChange = charGenFieldChange;
window.charGenRun = charGenRun;
window.charGenSwitchTab = charGenSwitchTab;
window.charGenUpdatePreview = charGenUpdatePreview;
window.loadCharGen = loadCharGen;
window.loadCharacters = loadCharacters;
window.loadPluginView = loadPluginView;
window.loadSummary = loadSummary;
window.renderCapGroup = renderCapGroup;
window.renderCharGenTabs = renderCharGenTabs;
window.renderCharPortraitGallery = renderCharPortraitGallery;
window.switchCapGroup = switchCapGroup;
window.wfAddNode = wfAddNode;
window.wfClear = wfClear;
window.wfConnEnd = wfConnEnd;
window.wfConnStart = wfConnStart;
window.wfDeleteNode = wfDeleteNode;
window.wfDragStart = wfDragStart;
window.wfGeneratePortrait = wfGeneratePortrait;
window.wfInit = wfInit;
window.wfInitCanvas = wfInitCanvas;
window.wfLoadCharacters = wfLoadCharacters;
window.wfLoadTemplate = wfLoadTemplate;
window.wfNodeColor = wfNodeColor;
window.wfNodeMouseDown = wfNodeMouseDown;
window.wfNodeMouseMove = wfNodeMouseMove;
window.wfNodeMouseUp = wfNodeMouseUp;
window.wfRender = wfRender;
window.wfRenderConfig = wfRenderConfig;
window.wfRenderPalette = wfRenderPalette;
window.wfRenderTemplateSelect = wfRenderTemplateSelect;
window.wfRun = wfRun;
window.wfSelectNode = wfSelectNode;
window.wfUpdateConfig = wfUpdateConfig;