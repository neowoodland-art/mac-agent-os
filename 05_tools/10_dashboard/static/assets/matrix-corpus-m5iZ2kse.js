async function e(e){e.innerHTML=`<div class="loading">⏳ 加载语料库...</div>`;try{let[n,r]=await Promise.all([fetch(`/api/matrix/corpus`),fetch(`/api/matrix/corpus/scenes`).catch(()=>({json:()=>({scenes:[],groups:{}})}))]),i=await n.json(),a=await r.json();e.innerHTML=t(i.categories||[],a.scenes||[],a.groups||{},i.total_comments||0),g(),o(`1d`)}catch(t){e.innerHTML=`<div class="error">❌ 加载失败: ${h(t.message)}</div>`}}function t(e,t,i,o){return`
<div style="padding:16px">
  <!-- 标题 -->
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <h2 style="font-size:18px;margin:0">📚 语料库</h2>
    <span style="font-size:12px;color:var(--text2)">
      ${e.length} 个分类 · ${t.length} 个场景 · ${o} 条评论
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
    ${n(e)}
  </div>

  <!-- Tab 2: 二维场景（Persona × Scene） -->
  <div id="corpusTab2d" class="corpus-tab-content" style="display:none">
    ${r(t,i)}
  </div>

  <!-- Tab 3: 三维多轮（Multi-round content） -->
  <div id="corpusTab3d" class="corpus-tab-content" style="display:none">
    ${a(t)}
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
</div>`}function n(e){let t={};return e.forEach(e=>{let n=e.platform===`xiaohongshu`?`📕 小红书`:`🎵 抖音`;t[n]||(t[n]=[]),t[n].push(e)}),Object.keys(t).length?`<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:10px">
    ${Object.entries(t).map(([e,t])=>`
      <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">${e}
          <span style="font-size:10px;color:var(--text2);font-weight:400">（${t.length} 个分类）</span>
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
            ${t.map(e=>{let t=e.platform===`xiaohongshu`?`xiaohongshu`:`douyin`,n=h(e.name);return`<tr>
                <td style="padding:5px 3px;border-bottom:1px solid var(--border)"><strong>${n}</strong></td>
                <td style="padding:5px 3px;border-bottom:1px solid var(--border);text-align:center;color:var(--text2)">${e.weight||`-`}</td>
                <td style="padding:5px 3px;border-bottom:1px solid var(--border);text-align:center">${e.count||0}</td>
                <td style="padding:5px 3px;border-bottom:1px solid var(--border);text-align:center">${e.enabled?`<span style="color:var(--green)">✅</span>`:`<span style="color:var(--text2)">⏸</span>`}</td>
                <td style="padding:5px 3px;border-bottom:1px solid var(--border)">
                  <button onclick="corpusShowDetail('${t}','${n}')"
                          style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">📝</button>
                </td>
              </tr>`}).join(``)}
          </tbody>
        </table>
      </div>
    `).join(``)}
  </div>`:`<div style="color:var(--text2);font-size:12px;padding:20px;text-align:center">暂无分类数据</div>`}function r(e,t){if(!e.length)return`<div style="color:var(--text2);font-size:12px;padding:20px;text-align:center">
      <div style="font-size:24px;margin-bottom:8px">📋</div>
      <div>暂无二维场景语料</div>
      <div style="font-size:11px;margin-top:6px;opacity:.7">
        请按模板格式在 YAML 中添加 personas 和 scenes 段落后刷新
      </div>
    </div>`;let n={first_comment:`💬 首次评论`,reply:`↩️ 回复评论`,re_reply:`🔄 再回复`},r=e.filter(e=>![`first_comment`,`reply`,`re_reply`].includes(e.id)),a=``;for(let[e,r]of Object.entries(n)){let n=t[e]||[];a+=i(e,r,n)}return r.length&&(a+=i(`other`,`📌 其他场景`,r)),a}function i(e,t,n){let r={};n.forEach(e=>{let t=e.persona||`unknown`;r[t]||(r[t]=[]),r[t].push(e)});let i=Object.keys(r);return i.length?`
    <div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border);margin-bottom:8px">
      <div style="font-weight:600;font-size:13px;margin-bottom:8px">${t}
        <span style="font-size:10px;color:var(--text2);font-weight:400">（${n.length} 个场景）</span>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:6px">
        ${i.map(e=>`<div style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:8px 10px;min-width:120px">
            <div style="font-size:11px;font-weight:600;margin-bottom:4px">👤 ${h(e.replace(/_/g,` `))}</div>
            <div style="font-size:10px;color:var(--text2)">
              ${r[e].map(e=>{let t=e.rounds||1;return`<span style="display:inline-block;background:rgba(99,102,241,.1);padding:2px 6px;border-radius:3px;margin:2px">
                  ${h(e.label||e.id)} ${t>1?`(${t}轮)`:``}
                </span>`}).join(``)}
            </div>
          </div>`).join(``)}
      </div>
    </div>`:``}function a(e){let t=e.filter(e=>(e.rounds||1)>1);return t.length?`<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px">
    ${t.map(e=>{let t=(e.persona||``).replace(/_/g,` `),n=e.label||e.id,r=e.rounds||1;return`<div style="background:var(--bg2);border-radius:var(--radius);padding:10px;border:1px solid var(--border)">
        <div style="font-size:12px;font-weight:600;margin-bottom:4px">👤 ${h(t)}</div>
        <div style="font-size:11px;margin-bottom:4px">📌 ${h(n)}</div>
        <div style="font-size:10px;color:var(--text2)">🔄 ${r} 轮对话</div>
      </div>`}).join(``)}
  </div>`:`<div style="color:var(--text2);font-size:12px;padding:20px;text-align:center">
      <div style="font-size:24px;margin-bottom:8px">🔄</div>
      <div>暂无多轮对话语料</div>
      <div style="font-size:11px;margin-top:6px;opacity:.7">
        在 YAML 的 content 段中添加 round_N 即可启用多轮语料
      </div>
    </div>`}function o(e){document.querySelectorAll(`.corpus-tab`).forEach(t=>{let n=t.dataset.tab===e;t.style.background=n?`var(--primary)`:`var(--bg3)`,t.style.color=n?`#fff`:`var(--text2)`,t.style.fontWeight=n?`600`:`400`}),document.querySelectorAll(`.corpus-tab-content`).forEach(t=>{t.style.display=t.id===`corpusTab${e}`?``:`none`})}async function s(){let e=document.getElementById(`corpusAddPlatform`)?.value,t=document.getElementById(`corpusAddCategory`)?.value,n=document.getElementById(`corpusAddText`)?.value,r=document.getElementById(`corpusAddResult`);if(!t||!n){r.textContent=`❌ 请输入分类和评论`;return}try{let i=await(await fetch(`/api/matrix/corpus/add`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({platform:e,category:t,text:n})})).json();i.status===`ok`?(r.textContent=`✅ 已添加`,document.getElementById(`corpusAddText`).value=``,m()):r.textContent=`❌ `+(i.error||`添加失败`)}catch(e){r.textContent=`❌ `+e.message}}async function c(){let e=document.getElementById(`corpusBatchPlatform`)?.value,t=document.getElementById(`corpusBatchCategory`)?.value,n=document.getElementById(`corpusBatchTexts`),r=document.getElementById(`corpusBatchResult`);if(!t||!n?.value.trim()){r.textContent=`❌ 请输入分类名和评论内容`;return}let i=n.value.split(`
`).filter(e=>e.trim());r.textContent=`⏳ 导入 `+i.length+` 条...`;try{let a=await(await fetch(`/api/matrix/corpus/batch-add`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({platform:e,category:t,texts:i})})).json();a.status===`ok`?(r.textContent=`✅ 成功导入 `+a.added+` 条`,n.value=``,m()):r.textContent=`❌ `+(a.detail||a.error)}catch(e){r.textContent=`❌ `+e.message}}function l(){navigator.clipboard.writeText(`# 语料库模板 v2.0
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
      - "对，后来我换了一种方法就好了"`).then(()=>alert(`✅ 已复制模板`)).catch(()=>alert(`复制失败，请手动选中复制`))}var u=!1;function d(e,t){if(u)return;u=!0;let n=document.createElement(`div`);n.style.cssText=`position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:9999`,n.innerHTML=`<div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:20px;max-width:600px;width:90%;max-height:70vh;display:flex;flex-direction:column">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <span style="font-weight:600;font-size:15px">📚 ${h(e)}/${h(t)}</span>
      <span style="cursor:pointer;font-size:20px" onclick="this.closest('div[style*=\\'fixed\\']').remove();_corpusModalOpen=false">✕</span>
    </div>
    <div id="corpusDetailBody" style="flex:1;overflow-y:auto;padding:4px 0">
      <div style="text-align:center;color:var(--text2);padding:20px">加载中...</div>
    </div>
    <div style="margin-top:10px;display:flex;gap:6px">
      <input id="corpusDetailAddText" placeholder="添加评论..." style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
      <button onclick="corpusDetailAdd()" style="background:var(--primary);color:#fff;border:none;padding:5px 12px;border-radius:4px;cursor:pointer;font-size:12px">添加</button>
    </div>
  </div>`,document.body.appendChild(n),fetch(`/api/matrix/corpus/category?platform=${e}&category=${encodeURIComponent(t)}`).then(e=>e.json()).then(n=>{let r=document.getElementById(`corpusDetailBody`);if(!r)return;let i=[...(n.comments||[]).map((e,t)=>({type:`comment`,text:e,index:t})),...(n.templates||[]).map((e,t)=>({type:`template`,text:e,index:t+999}))];if(!i.length){r.innerHTML=`<div style="text-align:center;padding:20px;color:var(--text2)">暂无评论</div>`;return}r.innerHTML=i.map((n,r)=>{let i=n.index>=999?-1:n.index;return`<div style="display:flex;align-items:center;gap:6px;padding:5px 0;border-bottom:1px solid var(--border)">
          <span style="font-size:10px;color:var(--text2);width:40px;flex-shrink:0">#${r+1}${n.type===`template`?` 📝`:``}</span>
          <span style="flex:1;font-size:12px">${h(n.text)}</span>
          <span style="cursor:pointer;color:var(--red);font-size:14px;opacity:.5"
                onclick="corpusDetailDelete('${e}','${h(t)}',${i})">✕</span>
        </div>`}).join(``)}).catch(e=>{let t=document.getElementById(`corpusDetailBody`);t&&(t.innerHTML=`<div style="color:var(--red);text-align:center;padding:20px">❌ ${h(e.message)}</div>`)})}async function f(){let e=document.getElementById(`corpusDetailAddText`);if(!e||!e.value.trim())return;let t=(e.closest(`div[style*="fixed"]`)?.querySelector(`span`)?.textContent||``).replace(`📚 `,``).split(`/`),n=t[0]||`douyin`,r=t[1]||``;try{(await(await fetch(`/api/matrix/corpus/add`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({platform:n,category:r,text:e.value.trim()})})).json()).status===`ok`&&(e.value=``,d(n,r),m())}catch(e){alert(e.message)}}async function p(e,t,n){if(n===-1){alert(`模板暂不支持看板删除，请使用 CLI`);return}if(confirm(`删除第 ${n+1} 条评论？`))try{(await(await fetch(`/api/matrix/corpus/delete`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({platform:e,category:t,index:n})})).json()).status===`ok`&&(document.querySelector(`div[style*="fixed"]`)?.remove(),u=!1,d(e,t),m())}catch(e){alert(e.message)}}async function m(){let t=document.getElementById(`view-dynamic`);if(!t)return;let n=document.querySelector(`.corpus-tab.active`)?.dataset?.tab||`1d`;await e(t),o(n)}function h(e){return typeof e==`string`?e.replace(/&/g,`&amp;`).replace(/</g,`&lt;`).replace(/>/g,`&gt;`).replace(/"/g,`&quot;`).replace(/'/g,`&#039;`):String(e||``)}function g(){window._corpusFnsRegistered||(window._corpusFnsRegistered=!0,window.switchCorpusTab=o,window.corpusAdd=s,window.corpusBatchImport=c,window.copyCorpusTemplate=l,window.corpusShowDetail=d,window.corpusDetailAdd=f,window.corpusDetailDelete=p)}export{e as loadView};