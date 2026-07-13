var e=``,t={},n={},r=[],i=[],a=0,o=null,s=1,c=null,l=0,u=0,d=null,f=[],p={},m={editor_mode:`编辑模式`,content:`脚本内容`,path:`文件路径`,type:`脚本格式`,parser:`解析方式`,strategy:`生产策略`,voice_id:`语音模型`,speed:`语速`,pitch:`音调`,provider:`供应商`,model:`模型版本`,duration:`时长(秒)`,seed:`随机种子`,source:`素材来源`,search_keyword:`搜索关键词`,count:`素材数量`,orientation:`画面方向`,style:`视觉风格`,color_grade:`色调`,mode:`模式`,mood:`情绪风格`,rhythm:`节奏强度`,bpm:`BPM`,volume:`音量`,duck_enabled:`自动避让`,registry_name:`选择角色`,outfit_preset:`服装预设`,use_reference_images:`传递参考图`,lip_sync:`唇形同步`,camera_style:`运镜风格`,transition:`转场方式`,scene_count:`场景数量`,output_format:`输出格式`,prompt_style:`提示词风格`,quality:`品质等级`,add_negative:`添加负面提示`,format:`视频格式`,resolution:`分辨率`,output_path:`输出路径`,auto_open:`自动打开`,message:`审核提示`,auto_approve:`自动通过`,timeout_minutes:`超时(分钟)`,genre:`故事类型`,title:`故事标题`,adapt_style:`改编风格`},h={auto:`自动`,manual:`手动`,ai_generated:`AI生成`,turbo:`极速`,standard:`标准`,quality:`高品质`,kling:`可灵AI`,jimeng:`即梦`,wan:`万相`,pexels:`Pexels图库`,local:`本地文件`,upload:`上传`,portrait:`竖屏`,landscape:`横屏`,square:`方形`,cinematic:`电影感`,hyper_realistic:`超写实`,artistic:`艺术风`,anime:`动漫`,vintage:`复古`,warm:`暖调`,cool:`冷调`,neutral:`中性`,dramatic:`戏剧性`,monochrome:`黑白`,default:`默认`,casual:`休闲`,sport:`运动`,formal:`正式`,fantasy:`奇幻`,happy:`欢快`,sad:`伤感`,epic:`史诗`,calm:`平静`,tense:`紧张`,upbeat:`积极`,romantic:`浪漫`,inspiring:`激励`,healing:`治愈`,detailed:`详细描述`,simple:`简洁指令`,stepwise:`分步式`,json:`JSON格式`,yaml:`YAML格式`,md:`Markdown格式`,inline:`在线编辑`,path:`文件路径`,srt:`SRT格式`,ass:`ASS格式`,vtt:`VTT格式`,bottom:`底部`,top:`顶部`,white:`白色`,yellow:`黄色`,cyan:`青色`,hard:`硬切`,fade_in:`淡入`,fade_out:`淡出`,dissolve:`叠化`,slide:`划像`,cut:`跳切`,running:`跑步装`,gym:`健身装`,basketball:`篮球装`,modern:`现代`,ancient:`古风`,sci_fi:`科幻`,mystery:`悬疑`,comedy:`喜剧`,detailed_adapt:`详细改编`,fast_extract:`快速提炼`,dialogue_first:`对白优先`};async function g(e){e.innerHTML=`
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
  </div>`,r=[],i=[],o=null,a=0,await _()}async function _(){try{let[e,r]=await Promise.all([fetch(`/api/workflow/nodes`),fetch(`/api/workflow/templates`)]),i=await e.json(),a=await r.json();t={};let o=i._defs||{};for(let e of i.categories||[])for(let n of e.nodes||[])t[n]=o[n]||{};n=a.templates||{}}catch{t={},n={}}y(),b(),P(),v()}function v(){let e=document.getElementById(`wfCanvas`);e&&(e.addEventListener(`dragover`,e=>e.preventDefault()),e.addEventListener(`drop`,n=>{n.preventDefault();let r=n.dataTransfer.getData(`text/plain`);if(!r||!t[r])return;let i=e.getBoundingClientRect(),a=(n.clientX-i.left-120)/s,o=(n.clientY-i.top-30)/s;C(r,Math.max(0,a),Math.max(0,o))}))}function y(){let e=document.getElementById(`wfNodePalette`);e&&(e.innerHTML=Object.entries(t).map(([e,t])=>{let n=t.color||`#888`,r=t.icon||`●`;return`<div draggable="true" ondragstart="wfDragStart(event,'${e}')" title="${t.description||``}"
      style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;margin:1px;border-radius:4px;font-size:11px;cursor:grab;white-space:nowrap;background:${n}15;border:1px solid ${n}30;color:${n}">${r} ${t.label}</div>`}).join(``))}function b(){let e=document.getElementById(`wfTemplateSelect`);e&&(e.innerHTML=`<option value="">— 选择模板 —</option>`+Object.entries(n).map(([e,t])=>`<option value="${e}">${t.name||e} ${t.cost||``}</option>`).join(``))}function x(){let e=document.getElementById(`wfCanvas`),n=document.getElementById(`wfCanvasPlaceholder`);if(!e)return;n.style.display=r.length===0?`flex`:`none`;let a=`<defs><marker id="wfArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M2 1L8 5L2 9" fill="none" stroke="#888" stroke-width="1.5"/></marker></defs>`;i.forEach((e,t)=>{let n=r.find(t=>t.id===e.from),i=r.find(t=>t.id===e.to);if(n&&i){let e=n.x+120,t=n.y+30,r=i.x,o=i.y+30,s=(e+r)/2;a+=`<path d="M${e} ${t} C${s} ${t},${s} ${o},${r} ${o}" fill="none" stroke="#888" stroke-width="2" marker-end="url(#wfArrow)" opacity="0.6"/>`}}),r.forEach(e=>{let n=t[e.type]||{},r=n.color||`#888`;a+=`<g class="wf-node" data-id="${e.id}" onmousedown="wfNodeMouseDown(event,'${e.id}')" style="cursor:move">
      <rect x="${e.x}" y="${e.y}" width="240" height="60" rx="8" fill="var(--bg2)" stroke="${o===e.id?r:`var(--border)`}" stroke-width="${o===e.id?2:1}"/>
      <rect x="${e.x}" y="${e.y}" width="240" height="24" rx="8" fill="${r}" opacity="0.15"/>
      <text x="${e.x+12}" y="${e.y+17}" font-size="12" fill="${r}" font-weight="600">${n.icon||`●`} ${e.label||n.label||e.type}</text>
      <text x="${e.x+12}" y="${e.y+42}" font-size="10" fill="var(--text2)">${n.description||``}</text>
      ${(n.ports?.input||[]).map((t,n)=>`<circle cx="${e.x}" cy="${e.y+40+n*16}" r="5" fill="var(--bg3)" stroke="${r}" stroke-width="1.5" style="cursor:crosshair" onmousedown="wfConnStart(event,'${e.id}','${t}')" onmouseup="wfConnEnd(event,'${e.id}','${t}')"/>`).join(``)}
      ${(n.ports?.output||[]).map((t,n)=>`<circle cx="${e.x+240}" cy="${e.y+30+n*16}" r="5" fill="${r}" stroke="${r}" stroke-width="1.5" style="cursor:crosshair" onmousedown="wfConnStart(event,'${e.id}','${t}')" onmouseup="wfConnEnd(event,'${e.id}','${t}')"/>`).join(``)}
      <rect x="${e.x+200}" y="${e.y+4}" width="34" height="18" rx="4" fill="${r}" opacity="0.8" style="cursor:pointer" onclick="wfSelectNode('${e.id}')"/>
      <text x="${e.x+217}" y="${e.y+16}" font-size="9" fill="#fff" text-anchor="middle" style="cursor:pointer" onclick="wfSelectNode('${e.id}')">配置</text>
    </g>`}),e.innerHTML=a}function S(e,t){e.dataTransfer.setData(`text/plain`,t)}function C(e,n,i){let o=`n`+ ++a,s=t[e]||{};r.push({id:o,type:e,label:s.label||e,config:JSON.parse(JSON.stringify(s.default_config||{})),x:n,y:i}),x(),w(o)}function w(e){o=e,x(),F(e)}function T(e){r=r.filter(t=>t.id!==e),i=i.filter(t=>t.from!==e&&t.to!==e),o===e&&(o=null),x(),document.getElementById(`wfConfigContent`).innerHTML=`<div style="text-align:center;padding:40px 0;color:var(--text2);font-size:13px">点击节点编辑配置</div>`}function E(e,t){if(e.target.closest(`circle`)||e.target.closest(`rect[onclick]`))return;let n=document.getElementById(`wfCanvas`).getBoundingClientRect(),i=r.find(e=>e.id===t);i&&(l=e.clientX-n.left-i.x,u=e.clientY-n.top-i.y,c=t,document.addEventListener(`mousemove`,D),document.addEventListener(`mouseup`,O))}function D(e){if(!c)return;let t=document.getElementById(`wfCanvas`).getBoundingClientRect(),n=r.find(e=>e.id===c);n&&(n.x=Math.max(0,(e.clientX-t.left-l)/s),n.y=Math.max(0,(e.clientY-t.top-u)/s),x())}function O(){c=null,document.removeEventListener(`mousemove`,D),document.removeEventListener(`mouseup`,O)}function k(e,t,n){d={nodeId:t,port:n,isOutput:!0},e.stopPropagation()}function A(e,t,n){d&&(d.nodeId!==t&&i.push({from:d.nodeId,to:t,from_port:d.port,to_port:n}),d=null,x())}async function j(e){if(!e||!n[e])return;let t=n[e];r=JSON.parse(JSON.stringify(t.nodes||[])),i=JSON.parse(JSON.stringify(t.edges||[])),a=r.length,o=null,x(),document.getElementById(`wfConfigContent`).innerHTML=`<div style="text-align:center;padding:40px 0;color:var(--text2);font-size:13px">点击节点编辑配置</div>`}function M(){r=[],i=[],o=null,x(),document.getElementById(`wfConfigContent`).innerHTML=`<div style="text-align:center;padding:40px 0;color:var(--text2);font-size:13px">点击节点编辑配置</div>`}async function N(){let e=document.getElementById(`wfRunStatus`);e.textContent=`⏳ 运行中...`;try{(await(await fetch(`/api/workflow/run`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({template_id:`custom`,nodes:r,edges:i})})).json()).run_id,e.textContent=`✅ 已启动`}catch(t){e.textContent=`❌ `+t.message}}async function P(){try{let t=await(await fetch(`${e}/api/characters`)).json(),n=t.characters||{};f=Object.keys(n).map(e=>({name:e,active:e===(t.active||``)})),p={};for(let[e,t]of Object.entries(n))p[e]=t}catch{f=[]}}function F(e){let n=document.getElementById(`wfConfigContent`),i=r.find(t=>t.id===e);if(!i){n.innerHTML=`<div style="text-align:center;padding:40px 0;color:var(--text2);font-size:13px">点击节点编辑配置</div>`;return}let a=t[i.type]||{},o=i.config||{},s=a.default_config||{},c=a.color||`#888`,l=a.options_map||{},u=`<div style="margin-bottom:10px">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <span style="font-size:14px;font-weight:600">${a.icon||`●`} ${i.label}</span>
      <button onclick="wfDeleteNode('${i.id}')" style="background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:var(--red);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">删除</button>
    </div>
    <div style="font-size:10px;color:var(--text2);margin-top:4px">${a.description||``}</div>
  </div>`;for(let[e,t]of Object.entries(s)){let n=o[e]===void 0?t:o[e],r=m[e]||e.replace(/_/g,` `).replace(/\b\w/g,e=>e.toUpperCase()),a=`wf_cfg_`+i.id+`_`+e,s=l[e];if(e===`registry_name`){let t=Array.isArray(f)?f:[];u+=`<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${r}</div>
        <select id="${a}" onchange="wfUpdateConfig('${i.id}','${e}',this.value)"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
          <option value="">— 请选择角色 —</option>
          ${t.map(e=>`<option value="${e.name}" ${String(n)===e.name?`selected`:``}>${e.name}${e.active?` (默认)`:``}</option>`).join(``)}
        </select>
      </div>`;continue}if(s&&Array.isArray(s)){u+=`<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${r}</div>
        <select id="${a}" onchange="wfUpdateConfig('${i.id}','${e}',this.value)"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
          ${s.map(e=>`<option value="${e}" ${String(n)===String(e)?`selected`:``}>${h[e]||e}</option>`).join(``)}
        </select>
      </div>`;continue}if(typeof s==`string`&&s.startsWith(`::number:`)){let t=s.split(`:`);u+=`<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${r}</div>
        <input type="number" id="${a}" value="${n}" min="${t[1]||0}" max="${t[2]||100}" step="${t[3]||`any`}"
          onchange="wfUpdateConfig('${i.id}','${e}',parseFloat(this.value))"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
      </div>`;continue}if(e===`content`&&typeof n==`string`&&n.length>50){u+=`<div style="margin-bottom:6px">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${r}</div>
        <textarea id="${a}" rows="4" onchange="wfUpdateConfig('${i.id}','${e}',this.value)"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px;font-family:inherit;resize:vertical">${n}</textarea>
      </div>`;continue}if(typeof t==`boolean`){u+=`<div style="margin-bottom:6px;display:flex;align-items:center;gap:8px">
        <input type="checkbox" id="${a}" ${n?`checked`:``}
          onchange="wfUpdateConfig('${i.id}','${e}',this.checked)"
          style="accent-color:${c}">
        <label for="${a}" style="font-size:11px;color:var(--text2)">${r}</label>
      </div>`;continue}u+=`<div style="margin-bottom:6px">
      <div style="font-size:10px;color:var(--text2);margin-bottom:2px">${r}</div>
      <input id="${a}" value="${n}" onchange="wfUpdateConfig('${i.id}','${e}',this.value)"
        style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px">
    </div>`}if(i.type===`character`&&o.registry_name){let e=p[o.registry_name];u+=`<div style="margin-top:12px;padding-top:10px;border-top:1px solid var(--border)">
      <div style="font-size:10px;color:var(--text2);margin-bottom:4px">📸 定妆照生成</div>
      ${e?`<div style="font-size:10px;color:var(--text2);margin-bottom:6px;background:var(--bg3);padding:6px 8px;border-radius:4px">
        <div>画风: ${e.art_style||`-`} | 性格: ${e.personality||`-`}</div>
        <div>${e.description?e.description.slice(0,60)+`...`:``}</div>
      </div>`:``}
      <div style="display:flex;gap:8px">
        <button onclick="wfGeneratePortrait()" style="background:#f97316;border:none;color:#fff;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px">🚀 一键生成</button>
        <span id="wfPortraitStatus" style="font-size:10px;color:var(--text2);display:flex;align-items:center">点击生成多角度+表情+网格定妆照</span>
      </div>
      <div id="wfPortraitResult" style="font-size:10px;color:var(--text2);margin-top:4px"></div>
    </div>`}n.innerHTML=u}function I(e,t,n){let i=r.find(t=>t.id===e);i&&(i.config[t]=n)}async function L(){let e=document.getElementById(`wfPortraitResult`),t=document.getElementById(`wfPortraitStatus`);if(!e)return;let n=r.find(e=>e.id===o);if(!n)return;let i=n.config?.registry_name||``;if(!i){e.innerHTML=`❌ 请先选择角色`;return}let a=``;try{let e=(await(await fetch(`/api/characters`)).json()).characters||{};e[i]?.description&&(a=e[i].description)}catch{}e.innerHTML=`<div style="margin-top:4px">⏳ 生成中: 基准照 → 多角度 → 表情 → 网格</div>`,t&&(t.innerHTML=`⏳ 生成中...`);try{let n=await fetch(`/api/characters/generate-portrait`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({character_name:i,description:a,force:!0})}),r=await n.json();n.ok?(e.innerHTML=`✅ 定妆照已生成！<a href="javascript:switchView('characters')" style="color:var(--primary);text-decoration:underline">查看角色库</a>`,t&&(t.innerHTML=`✅ 生成完成`)):e.innerHTML=`❌ `+(r.detail||`失败`)}catch(t){e.innerHTML=`❌ `+t.message}}window.wfRun=N,window.wfClear=M,window.wfDragStart=S,window.wfLoadTemplate=j,window.wfSelectNode=w,window.wfDeleteNode=T,window.wfNodeMouseDown=E,window.wfConnStart=k,window.wfConnEnd=A,window.wfUpdateConfig=I,window.wfGeneratePortrait=L;export{g as loadView};