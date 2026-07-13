/**
 * char-gen.js — 🎭 角色生成器（完整版）
 * 从 inline.js 迁移（原 loadCharGen + charGen* 函数）
 * 
 * 功能: 3 步向导
 *   Step 1: 输入方向描述 → 自动填充各模块
 *   Step 2: 7 个模块 Tab 逐项调整（身份/面部/五官/发肤/体型/服装/神态场景）
 *   Step 3: 生成并展示结果
 * 
 * 后端:
 *   POST /api/characters/expand-direction         → 扩展方向描述
 *   POST /api/characters/generate-from-direction  → 从方向生成角色
 */

const API = '';

// ══ 角色模块定义 ══
const CHAR_GEN_MODULES = {
  identity: { icon: '🆔', label: '身份', desc: '姓名/性别/年龄/种族' },
  face_shape: { icon: '🗿', label: '面部轮廓', desc: '脸型/下颌/颧骨' },
  facial_features: { icon: '👁️', label: '五官细节', desc: '眼/眉/鼻/唇' },
  hair_skin: { icon: '💇', label: '头发&皮肤', desc: '发型/肤色/妆容' },
  body: { icon: '🏋️', label: '体型姿态', desc: '身高/体型/姿态' },
  clothing: { icon: '👔', label: '服装配饰', desc: '上衣/下装/配饰' },
  expression_scene: { icon: '😊', label: '神态&场景', desc: '表情/光线/背景' },
};

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

const BODY_LABELS = {right_three_quarter:'右侧45°', right_side:'纯右侧面', back:'背面', front:'正面', side:'侧面'};

let charGenLayerData = {};

export async function loadView(container) {
  // 生成唯一前缀，避免多个实例冲突
  const uid = 'cg_' + Math.random().toString(36).slice(2, 6);

  container.innerHTML = `
  <div style="padding:16px">
    <div style="font-size:18px;font-weight:600;margin-bottom:16px">🎭 角色生成器</div>

    <!-- Step 1: 方向描述 -->
    <div id="${uid}_step1" style="background:var(--bg2);border-radius:10px;padding:16px;border:1px solid var(--border);margin-bottom:12px">
      <div style="font-size:14px;font-weight:600;margin-bottom:8px">1️⃣ 输入角色方向</div>
      <textarea id="${uid}_direction" rows="3" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:8px;border-radius:6px;font-size:13px;resize:vertical" placeholder="例如：一位25岁的中国男性，黑短发戴细框眼镜，性格温和内敛有点宅，常穿浅灰色卫衣和深蓝色牛仔裤..."></textarea>
      <div style="margin-top:8px;display:flex;gap:8px;align-items:center">
        <button id="${uid}_autoFillBtn" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">🤖 AI 自动填充</button>
        <span id="${uid}_step1Result" style="font-size:11px;color:var(--text2)"></span>
      </div>
    </div>

    <!-- Step 2: 模块化编辑 -->
    <div id="${uid}_step2" style="display:none">
      <div style="background:var(--bg2);border-radius:10px;padding:16px;border:1px solid var(--border);margin-bottom:12px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="font-size:14px;font-weight:600">2️⃣ 逐项调整角色细节</span>
          <span style="font-size:11px;color:var(--text2)">填写模块后自动生成完整描述</span>
        </div>
        <!-- Tab 栏 -->
        <div id="${uid}_tabs" style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:10px"></div>
        <!-- 面板内容 -->
        <div id="${uid}_panelContent" style="min-height:200px"></div>
        <!-- 完整预览 -->
        <div style="margin-top:8px">
          <div style="font-size:11px;color:var(--text2);font-weight:600;margin-bottom:4px">📝 完整角色描述预览</div>
          <textarea id="${uid}_promptPreview" rows="4" readonly style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px;border-radius:4px;font-size:11px;font-family:inherit;resize:vertical" placeholder="— 填写模块后自动生成预览 —"></textarea>
        </div>
      </div>
      <!-- Step 2 底部操作栏 -->
      <div style="background:var(--bg2);border-radius:10px;padding:12px 16px;border:1px solid var(--border);margin-bottom:12px;display:flex;gap:12px;align-items:center;flex-wrap:wrap">
        <div><span style="font-size:11px;color:var(--text2)">角色名</span><br><input id="${uid}_name" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;font-size:12px;width:120px" placeholder="留空自动"></div>
        <div><span style="font-size:11px;color:var(--text2)">Seed</span><br><input id="${uid}_seed" type="number" value="42" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;font-size:12px;width:70px"></div>
        <div style="display:flex;align-items:center;gap:4px;margin-top:12px">
          <input id="${uid}_genImages" type="checkbox" style="accent-color:var(--primary)"><label for="${uid}_genImages" style="font-size:11px;color:var(--text2)">生成定妆照</label>
        </div>
        <button id="${uid}_generateBtn" style="background:#f97316;color:#fff;border:none;padding:6px 16px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600">🚀 生成角色</button>
        <span id="${uid}_step2Result" style="font-size:11px;color:var(--text2)"></span>
      </div>
    </div>

    <!-- Step 3: 结果展示 -->
    <div id="${uid}_step3" style="display:none">
      <div style="background:var(--bg2);border-radius:10px;padding:16px;border:1px solid var(--border);margin-bottom:12px">
        <div id="${uid}_resultTitle" style="font-size:16px;font-weight:600;margin-bottom:12px"></div>
        <div id="${uid}_resultBody"></div>
        <div style="margin-top:12px;display:flex;gap:8px">
          <button onclick="switchView('characters')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 12px;border-radius:5px;cursor:pointer;font-size:11px">🧑 查看角色列表</button>
          <button onclick="location.reload()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 12px;border-radius:5px;cursor:pointer;font-size:11px">🔄 再创建一个</button>
        </div>
      </div>
    </div>
  </div>`;

  // 初始化状态
  charGenLayerData = {};

  // 渲染 Tab
  const tabsEl = container.querySelector(`#${uid}_tabs`);
  tabsEl.innerHTML = Object.entries(CHAR_GEN_MODULES).map(([id, mod]) =>
    `<div class="char-gen-tab" data-tab="${id}" data-uid="${uid}"
      style="padding:5px 10px;border-radius:6px;cursor:pointer;font-size:11px;
             background:var(--bg3);color:var(--text2);border:1px solid transparent;
             display:flex;align-items:center;gap:4px;transition:all .15s">
      ${mod.icon} ${mod.label}
    </div>`
  ).join('');

  // Tab 点击事件
  tabsEl.querySelectorAll('.char-gen-tab').forEach(el => {
    el.addEventListener('click', () => charGenSwitchTab(el.dataset.tab, uid));
  });

  // 默认选中第一个模块
  charGenSwitchTab(Object.keys(CHAR_GEN_MODULES)[0], uid);

  // AI 自动填充按钮
  container.querySelector(`#${uid}_autoFillBtn`).addEventListener('click', () => charGenAutoFill(uid));

  // 生成按钮
  container.querySelector(`#${uid}_generateBtn`).addEventListener('click', () => charGenRun(uid));
}

// ══ Tab 切换 ══
function charGenSwitchTab(tabId, uid) {
  const container = document.querySelector(`[id$="_step2"]`).closest('div')?.parentElement || document;
  const tabsEl = container.querySelector(`#${uid}_tabs`);
  if (!tabsEl) return;

  tabsEl.querySelectorAll('.char-gen-tab').forEach(el => {
    const isActive = el.dataset.tab === tabId;
    el.style.background = isActive ? 'var(--primary)' : 'var(--bg3)';
    el.style.color = isActive ? '#fff' : 'var(--text2)';
    el.style.borderColor = isActive ? 'var(--primary)' : 'transparent';
  });

  const mod = CHAR_GEN_MODULES[tabId];
  const fields = CHAR_GEN_FIELDS[tabId] || [];
  const panel = document.getElementById(`${uid}_panelContent`);
  if (!panel) return;

  let html = `<div style="background:var(--bg3);border-radius:8px;padding:14px;margin-bottom:8px">
    <div style="font-size:12px;color:var(--text2);margin-bottom:8px">${mod.desc}</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">`;

  for (const f of fields) {
    const val = (charGenLayerData[tabId] || {})[f.key] || '';
    const fieldId = `${uid}_${tabId}_${f.key}`;

    if (f.type === 'select') {
      html += `<div>
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${f.label}</div>
        <select id="${fieldId}" data-uid="${uid}" data-tab="${tabId}" data-key="${f.key}" class="cg-field"
          style="width:100%;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
          <option value="">— 选择 —</option>
          ${(f.opts||[]).map(o => `<option value="${o}" ${val === o ? 'selected' : ''}>${o}</option>`).join('')}
        </select>
      </div>`;
    } else {
      html += `<div style="${f.key === 'eye_spirit' || f.key === 'background' || f.key === 'accessories' ? 'grid-column:1/-1' : ''}">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${f.label}</div>
        <input id="${fieldId}" data-uid="${uid}" data-tab="${tabId}" data-key="${f.key}" class="cg-field"
          value="${val}" placeholder="${f.ph||''}"
          style="width:100%;background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
      </div>`;
    }
  }

  html += `</div></div>`;
  html += `<div style="font-size:10px;color:var(--text2);background:var(--bg2);padding:6px 10px;border-radius:4px;margin-bottom:4px">
    📝 当前 <strong>${mod.label}</strong> 描述: <span id="${uid}_preview_${tabId}">${buildLayerDesc(tabId)}</span>
  </div>`;

  panel.innerHTML = html;

  // 绑定字段变更事件
  panel.querySelectorAll('.cg-field').forEach(el => {
    const changeEvent = () => {
      charGenFieldChange(el.dataset.tab, el.dataset.key, el.value, uid);
    };
    if (el.tagName === 'SELECT') el.addEventListener('change', changeEvent);
    else el.addEventListener('change', changeEvent);
  });

  charGenUpdatePreview(uid);
}

// ══ 字段变更 ══
function charGenFieldChange(tabId, key, value, uid) {
  if (!charGenLayerData[tabId]) charGenLayerData[tabId] = {};
  charGenLayerData[tabId][key] = value;
  const prev = document.getElementById(`${uid}_preview_${tabId}`);
  if (prev) prev.textContent = buildLayerDesc(tabId);
  charGenUpdatePreview(uid);
}

// ══ 描述构建 ══
function buildLayerDesc(tabId) {
  const data = charGenLayerData[tabId] || {};
  return Object.values(data).filter(Boolean).join('、') || '—';
}

function buildFullDescription() {
  const parts = [];
  for (const [tabId, data] of Object.entries(charGenLayerData)) {
    const desc = buildLayerDesc(tabId);
    if (desc && desc !== '—') parts.push(`【${CHAR_GEN_MODULES[tabId].label}】${desc}`);
  }
  return parts.join('\n');
}

function charGenUpdatePreview(uid) {
  const el = document.getElementById(`${uid}_promptPreview`);
  if (!el) return;
  const full = buildFullDescription();
  el.value = full || '— 填写模块后自动生成预览 —';
}

// ══ AI 自动填充 ══
async function charGenAutoFill(uid) {
  const dirEl = document.getElementById(`${uid}_direction`);
  const resultEl = document.getElementById(`${uid}_step1Result`);
  const step2 = document.getElementById(`${uid}_step2`);
  const direction = dirEl.value.trim();
  if (!direction) { resultEl.innerHTML = '❌ 请输入角色方向'; return; }
  resultEl.innerHTML = '⏳ AI 正在生成完整角色定义...';
  step2.style.display = 'block';

  try {
    const r = await fetch(API + '/api/characters/expand-direction', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({direction}),
    });
    const data = await r.json();
    const description = data.description || direction;
    charGenAutoFillFromDescription(description);
    const nameMatch = description.match(/([\u4e00-\u9fff]{2,6})(?:男性|女性|少年|少女|中年|老人)/);
    const nameEl = document.getElementById(`${uid}_name`);
    if (nameMatch && nameEl) nameEl.value = nameMatch[1].slice(-3).replace(/[的男女人]/g,'');
    resultEl.innerHTML = '✅ 各模块已自动填充！请逐项检查调整';
    charGenSwitchTab('identity', uid);
    step2.scrollIntoView({behavior: 'smooth', block: 'start'});
  } catch(e) {
    resultEl.innerHTML = '❌ 自动填充失败: ' + e.message;
    charGenSwitchTab('identity', uid);
    step2.style.display = 'block';
  }
}

function charGenAutoFillFromDescription(desc) {
  const match = (pattern) => { const m = new RegExp(pattern).exec(desc); return m ? m[1] : ''; };
  charGenLayerData = {};
  charGenLayerData.identity = { gender: match(/(男性|女性)/), age: match(/(少年|青年|壮年|中年|老年)/), ethnicity: match(/(中国|东亚|东南亚|南亚|欧美)/) || '中国', name: match(/([\u4e00-\u9fff]{2,4})[，,]/) };
  charGenLayerData.face_shape = { shape: match(/(鹅蛋脸|瓜子脸|圆脸|方脸|国字脸|长脸|菱形脸|心形脸)/), jaw: match(/(清晰分明|柔和模糊|棱角突出|圆润温和)/), cheekbone: match(/(高突出|饱满圆润|低平)/) || '适中自然', forehead: match(/(饱满宽阔|窄小|高额头)/) || '适中' };
  charGenLayerData.facial_features = { eyes_shape: match(/(丹凤眼|杏眼|桃花眼|圆眼|细长眼|单眼皮|双眼皮|内双)/), eyes_color: match(/(深褐|浅褐|黑色|琥珀色|灰色|蓝色|绿色)/) || '深褐', eyes_spirit: match(/(深邃[^，。]*?|清澈[^，。]*?|锐利[^，。]*?|温柔[^，。]*?|沉稳[^，。]*?)/) || '', eyebrows: match(/(剑眉|柳叶眉|一字眉|上挑眉|弯眉|粗眉|细长眉)/), nose: match(/(高挺|挺直窄小|中等挺拔|低平柔和)/) || '高挺', nose_tip: match(/(小巧圆润|圆润饱满|尖翘|略宽)/) || '适中', lips: match(/(薄唇|厚唇|M形唇|饱满|樱桃小嘴|微笑唇)/), lips_state: match(/(微张|紧抿|嘴角微扬|含笑意)/) || '自然闭合' };
  charGenLayerData.hair_skin = { hair_style: match(/(短发|寸头|中长发|背头|三七分|齐刘海|碎发|高马尾|披肩发)/) || '短发', hair_color: match(/(黑色|深棕|浅棕|亚麻色|灰色|银白)/) || '黑色', hair_detail: match(/(两侧收短[^，。]*?|发际线[^，。]*?)/) || '', skin_tone: match(/(冷白皮|暖白皮|健康小麦|蜜色|古铜色|深色)/) || '健康小麦', skin_texture: match(/(细腻光滑|自然肌理|毛孔可见|水润光泽)/) || '自然肌理', complexion: match(/(红润健康|略显苍白|容光焕发|自然均匀)/) || '红润健康', makeup: match(/(素颜|淡妆|精致妆容|裸妆|烟熏妆)/) || '素颜', blemish: match(/([^，。]*?疤[^，。]*?|[^，。]*?痣[^，。]*?|[^，。]*?纹[^，。]*?)/) || '' };
  const heightMatch = desc.match(/(\d+)/);
  const heightStr = heightMatch ? (parseInt(heightMatch[1]) < 170 ? '中等(165-175)' : parseInt(heightMatch[1]) < 180 ? '中高(175-185)' : '高大(185+)') : '';
  charGenLayerData.body = { height: heightStr, build: match(/(纤细瘦弱|偏瘦|标准匀称|健壮|壮硕|魁梧)/), shoulder: match(/(窄肩|标准|宽肩|厚肩)/) || '标准', posture: match(/(挺拔|自然放松|微驼|端庄|慵懒)/) || '挺拔' };
  const topMatch = match(/身穿([^，。]*?夹克|[^，。]*?卫衣|[^，。]*?T恤|[^，。]*?衬衫|[^，。]*?外套|[^，。]*?运动装)/);
  const accMatch = match(/[佩戴戴着带着]([^，。]*?耳机|[^，。]*?眼镜|[^，。]*?手表|[^，。]*?手环|[^，。]*?帽子|[^，。]*?项链)/);
  charGenLayerData.clothing = { top: topMatch || '', inner: '', bottom: '', shoes: '', accessories: accMatch || '', style_tag: match(/(运动休闲|商务正装|日系清新|街头潮流|简约素雅)/) || '' };
  charGenLayerData.expression_scene = { base_mood: match(/(平静从容|温和友善|冷峻严肃|沉稳内敛|自信昂扬|恬静淡然)/), expression: match(/(中性无表情|淡淡微笑|微笑|开怀大笑|皱眉沉思|目光坚定)/), eye_spirit: match(/(目光[^，。]*?|眼神[^，。]*?)/) || '', aura: match(/(沉稳内敛[^，。]*|亲和温暖[^，。]*|疏离清冷[^，。]*)/) || '', light_type: '柔光箱均匀布光', lens: '中焦85mm', background: match(/([^，。]*?背景[^，。]*?|在[^，。]*?[城里路巷][^，。]*?|[^，。]*?环境[^，。]*?)/) || '纯灰色专业背景' };
}

// ══ 生成角色 ══
async function charGenRun(uid) {
  const resultEl = document.getElementById(`${uid}_step2Result`);
  const name = document.getElementById(`${uid}_name`).value.trim();
  const seed = parseInt(document.getElementById(`${uid}_seed`).value) || 42;
  const genImages = document.getElementById(`${uid}_genImages`).checked;

  const allData = {};
  for (const [tabId, data] of Object.entries(charGenLayerData)) {
    for (const [key, val] of Object.entries(data)) {
      if (val) allData[`${tabId}.${key}`] = val;
    }
  }
  const fullDesc = buildFullDescription();
  if (!fullDesc || fullDesc === '— 填写模块后自动生成预览 —') {
    resultEl.innerHTML = '❌ 请至少填写1个模块的字段'; return;
  }
  resultEl.innerHTML = '⏳ 正在生成角色...<br><span style="font-size:10px;color:var(--text2)">步骤: 注册属性 → ' + (genImages ? '生成变体 → ' : '') + '写入知识库</span>';

  try {
    const r = await fetch(API + '/api/characters/generate-from-direction', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({direction: fullDesc, name, generate_images: genImages, seed, layers: allData}),
    });
    const data = await r.json();
    if (!r.ok) { resultEl.innerHTML = '❌ 生成失败: ' + (data.detail || '未知错误'); return; }

    document.getElementById(`${uid}_step3`).style.display = 'block';
    document.getElementById(`${uid}_resultTitle`).textContent = `✅ 角色「${data.name}」生成完成`;

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
      html += `<div style="margin-top:12px"><div style="font-size:12px;color:var(--text2);font-weight:600;margin-bottom:6px">📸 生成结果</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px">`;
      if (data.baseline && data.baseline.url) {
        html += `<div style="text-align:center"><img src="${data.baseline.url}" style="width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:6px;background:var(--bg3)" onerror="this.parentElement.style.display='none'"><div style="font-size:10px;color:var(--text2);margin-top:2px">正面基准</div></div>`;
      }
      if (data.angles) {
        for (const [angle, info] of Object.entries(data.angles)) {
          if (info && info.url) html += `<div style="text-align:center"><img src="${info.url}" style="width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:6px;background:var(--bg3)" onerror="this.parentElement.style.display='none'"><div style="font-size:10px;color:var(--text2);margin-top:2px">${BODY_LABELS[angle] || angle}</div></div>`;
        }
      }
      if (data.expressions) {
        const exprLabels = {neutral:'中性', smile:'微笑', focused:'专注', laugh:'大笑', serious:'严肃'};
        for (const [expr, info] of Object.entries(data.expressions)) {
          if (info && info.url) html += `<div style="text-align:center"><img src="${info.url}" style="width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:6px;background:var(--bg3)" onerror="this.parentElement.style.display='none'"><div style="font-size:10px;color:var(--text2);margin-top:2px">${exprLabels[expr] || expr}</div></div>`;
        }
      }
      html += `</div></div>`;
    }
    document.getElementById(`${uid}_resultBody`).innerHTML = html;
    resultEl.innerHTML = '';
  } catch(e) { resultEl.innerHTML = '❌ ' + e.message; }
}
