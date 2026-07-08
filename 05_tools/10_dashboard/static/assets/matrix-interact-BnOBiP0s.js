import{n as e,t}from"./index-wekEWxQs.js";import{t as n}from"./account-selector-D87mja1n.js";var r=null;async function i(e){let i=(e.id||`interact`).replace(/-/g,`_`),o=await t(`/matrix/accounts`),s=Array.isArray(o)?o:o.accounts||[];e.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:4px">💬 评论互动 <span style="font-size:10px;color:var(--text2);font-weight:400">定向评论 / 三级接力 / 点赞 / 语料库</span></div>
        <div id="acctList_${i}" style="margin-bottom:6px"></div>
        <div id="selBar_${i}" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:6px">
          <span id="selCount_${i}" style="font-size:10px;color:var(--text2)">已选 0 个</span>
          <button onclick="window._ia_selAll_${i}()" style="background:var(--bg3);border:1px solid var(--border);padding:2px 8px;border-radius:3px;cursor:pointer;font-size:10px">全选</button>
          <button onclick="window._ia_selNone_${i}()" style="background:var(--bg3);border:1px solid var(--border);padding:2px 8px;border-radius:3px;cursor:pointer;font-size:10px">清空</button>
        </div>
        <!-- 两个 Tab -->
        <div style="display:flex;gap:0;border-bottom:1px solid var(--border);margin-bottom:8px">
          <button class="ia_tab" data-tab="comment" onclick="window._ia_switchTab_${i}('comment')"
            style="padding:6px 16px;font-size:12px;cursor:pointer;border:none;border-bottom:2px solid var(--primary);background:transparent;color:var(--primary);font-weight:600">💬 评论互动</button>
          <button class="ia_tab" data-tab="corpus" onclick="window._ia_switchTab_${i}('corpus')"
            style="padding:6px 16px;font-size:12px;cursor:pointer;border:none;border-bottom:2px solid transparent;background:transparent;color:var(--text2)">📚 语料库</button>
        </div>
        <!-- Tab 内容容器 -->
        <div id="tabBody_${i}"></div>
        <!-- 日志（跨 Tab 共享） -->
        <div id="log_${i}" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:200px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`,r=n(document.getElementById(`acctList_${i}`),{accounts:s,checkAll:!1,height:`200px`});let c=()=>{document.getElementById(`selCount_${i}`).textContent=`已选 `+(r?.getCount()||0)+` 个`};c(),window[`_ia_selAll_${i}`]=()=>{r?.selectAll(!0),c()},window[`_ia_selNone_${i}`]=()=>{r?.selectAll(!1),c()},window[`_ia_switchTab_${i}`]=t=>{document.querySelectorAll(`#${e.id} .ia_tab`).forEach(e=>{let n=e.dataset.tab===t;e.style.borderBottomColor=n?`var(--primary)`:`transparent`,e.style.color=n?`var(--primary)`:`var(--text2)`,e.style.fontWeight=n?`600`:`400`}),a(i,t)},a(i,`comment`)}async function a(e,t){let n=document.getElementById(`tabBody_${e}`);n&&(t===`comment`?o(e,n):t===`corpus`&&s(e,n))}function o(e,t){t.innerHTML=`
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <!-- 左 1/3：视频链接 -->
      <div style="flex:1;min-width:160px;max-width:33%">
        <div style="font-size:10px;color:var(--text2);margin-bottom:2px">🔗 视频链接（每行一条）</div>
        <textarea id="ic_urls_${e}" placeholder="https://..." rows="10"
          style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px;resize:vertical;box-sizing:border-box"></textarea>
      </div>
      <!-- 右 2/3 -->
      <div style="flex:2;min-width:350px">
        <!-- 三列分类 -->
        <div id="ic_corpus_checks_${e}" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;margin-bottom:6px">
          <div style="background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:5px">
            <div style="font-weight:600;font-size:11px;margin-bottom:4px;border-bottom:1px solid var(--border);padding-bottom:3px">🎯 通用</div>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value=""> 🎲 随机混合</label>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="food"> 🍜 美食探店</label>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="travel"> ✈️ 旅行打卡</label>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="tech"> 💻 科技数码</label>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="lifestyle"> 🌿 生活方式</label>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="emotion"> 💛 情感共鸣</label>
          </div>
          <div style="background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:5px">
            <div style="font-weight:600;font-size:11px;margin-bottom:4px;border-bottom:1px solid var(--border);padding-bottom:3px">🎯 定向</div>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="共情弹幕"> 💔 共情扎心弹幕</label>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="朱晓光主任"> 👨‍⚕️ 朱晓光主任</label>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="公众号约号"> 📱 公众号约号</label>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="捡漏绿通"> 💎 捡漏绿通</label>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="优势卖点"> ⭐ 优势卖点</label>
          </div>
          <div style="background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:5px">
            <div style="font-weight:600;font-size:11px;margin-bottom:4px;border-bottom:1px solid var(--border);padding-bottom:3px">💬 多轮对话</div>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="pain_fear"> 😰 怕疼怕手术</label>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="social_anxiety"> 😶 社恐不好意思</label>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="busy_worker"> 💼 上班族没时间</label>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="home_remedy"> 🧪 偏方没用过</label>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="elderly"> 👴 长辈不舒服</label>
            <label style="display:flex;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:2px 0"><input type="checkbox" class="ic_cb_${e}" value="general_health"> 🔄 综合对话</label>
          </div>
        </div>
        <!-- 设置栏 -->
        <div style="display:flex;flex-direction:column;gap:4px;background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:6px 8px">
          <div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap">
            <select id="ic_strategy_${e}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:3px;font-size:10px">
              <option value="comment">💬 定向评论</option>
              <option value="chain">🔗 三级接力</option>
              <option value="hot">🔥 热评互动</option>
            </select>
            <select id="ic_dir_${e}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:3px;font-size:10px" title="评论语气">
              <option value="">🎯 自动</option>
              <option value="称赞">👍 称赞</option><option value="提问">🤔 提问</option>
              <option value="共鸣">💗 共鸣</option><option value="感慨">😌 感慨</option>
            </select>
            <span style="font-size:9px;color:var(--text2)">互动:</span>
            <label style="display:flex;align-items:center;gap:2px;cursor:pointer;font-size:10px"><input type="checkbox" id="il_likeVideo_${e}" checked> ❤️点赞</label>
            <label style="display:flex;align-items:center;gap:2px;cursor:pointer;font-size:10px"><input type="checkbox" id="il_likeComment_${e}"> 👍评论</label>
            <label style="display:flex;align-items:center;gap:2px;cursor:pointer;font-size:10px"><input type="checkbox" id="il_follow_${e}"> 👤关注</label>
            <label style="display:flex;align-items:center;gap:2px;cursor:pointer;font-size:10px"><input type="checkbox" id="il_collect_${e}"> ⭐收藏</label>
          </div>
          <div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap">
            <input id="ic_comment_${e}" placeholder="自定义评论内容" style="flex:1;min-width:80px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:3px;font-size:10px">
            <input id="ic_interval_${e}" type="text" value="300-600" placeholder="间隔秒" style="width:70px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:3px;font-size:10px" title="每步间隔(秒)">
            <span style="font-size:9px;color:var(--text2)">⌛</span>
            <button onclick="window._ia_previewComment('${e}')" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:3px 8px;border-radius:3px;cursor:pointer;font-size:10px">🔍 预检</button>
            <button onclick="window._ia_runComment('${e}')" style="background:var(--primary);color:#fff;border:none;padding:4px 14px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600">🚀 执行</button>
          </div>
        </div>
      </div>
    </div>`}async function s(e,n){n.innerHTML=`<div class="loading">⏳ 加载语料库...</div>`;try{let r=await t(`/matrix/corpus`),i=r.categories||[],a=r.total_comments||0,o={douyin:`🎵 抖音`,xiaohongshu:`📕 小红书`},c={douyin:[],xiaohongshu:[]};i.forEach(e=>{c[e.platform]&&c[e.platform].push(e)});let l=`<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
      <span style="font-size:12px;color:var(--text2)">共 ${i.length} 个分类 · ${a} 条评论</span>
      <span style="font-size:10px;color:var(--text2)">点分类行展开管理</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:8px" id="corpusGrid_${e}">`;Object.entries(c).forEach(([t,n])=>{if(!n.length)return;let r=o[t]||t;l+=`<div style="background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:12px;margin-bottom:6px">${r}</div>
        ${n.map((n,r)=>`
          <div style="border:1px solid var(--border);border-radius:4px;margin-bottom:3px;overflow:hidden">
            <div onclick="_ia_toggleCorpusCat_${e}('${t}','${n.name}',${r})"
              style="display:flex;align-items:center;gap:4px;padding:4px 6px;background:var(--bg3);cursor:pointer;font-size:10px;user-select:none">
              <span id="corpusArrow_${e}_${t}_${r}" style="font-size:8px;opacity:.6">▶</span>
              <span style="flex:1"><strong>${n.label||n.name}</strong></span>
              <span style="color:var(--text2)">${n.count}条</span>
              <span style="color:var(--text2);font-size:9px">权重${n.weight}</span>
            </div>
            <div id="corpusBody_${e}_${t}_${r}" style="display:none;padding:4px 6px"></div>
          </div>
        `).join(``)}
        <!-- 新增批量导入 -->
        <div style="margin-top:4px;display:flex;gap:4px">
          <textarea id="corpusImport_${e}_${t}" placeholder="批量导入评论（每行一条）" rows="2"
            style="flex:1;font-size:10px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;padding:3px 5px;resize:vertical"></textarea>
          <button onclick="_ia_batchImportCorpus_${e}('${t}')"
            style="background:var(--primary);color:#fff;border:none;padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px;white-space:nowrap">📥 导入</button>
        </div>
      </div>`}),l+=`</div>`,l+=`<div style="margin-top:8px;background:var(--bg2);border-radius:8px;padding:10px;border:1px solid var(--border)">
      <div style="font-weight:600;font-size:12px;margin-bottom:6px">🔗 三阶接力语料 <span style="font-size:10px;color:var(--text2);font-weight:400">一阶(评论) → 二阶(回复) → 三阶(再回复)</span></div>
      <div style="font-size:10px;color:var(--text2);margin-bottom:4px">在「定向评论」Tab 选"三级接力"策略时使用</div>
      <div id="corpusScenes_${e}" style="font-size:10px;color:var(--text2)">⏳ 加载场景数据...</div>
    </div>`,n.innerHTML=l;try{let n=(await t(`/matrix/corpus/scenes`)).groups||{},r=document.getElementById(`corpusScenes_${e}`);if(r){let e=`<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px">`;for(let[t,r]of Object.entries({first_comment:`💬 一阶(评论)`,reply:`💬 二阶(回复)`,re_reply:`💬 三阶(再回复)`})){let i=n[t]||[];e+=`<div style="background:var(--bg3);border-radius:6px;padding:6px">
            <div style="font-weight:600;font-size:11px;margin-bottom:3px">${r}</div>
            ${i.length?i.map(e=>`<span style="display:inline-block;background:var(--bg2);padding:1px 5px;border-radius:3px;margin:1px;font-size:9px">${e.persona}</span>`).join(``):`<span style="color:var(--text2);font-size:9px">暂无数据，可在 YAML 中配置</span>`}
          </div>`}e+=`</div>`,r.innerHTML=e}}catch{}window[`_ia_toggleCorpusCat_${e}`]=async(n,r,i)=>{let a=document.getElementById(`corpusBody_${e}_${n}_${i}`),o=document.getElementById(`corpusArrow_${e}_${n}_${i}`);if(a){if(a.style.display!==`none`){a.style.display=`none`,o&&(o.textContent=`▶`);return}a.innerHTML=`<div style="font-size:10px;color:var(--text2)">⏳ 加载中...</div>`,a.style.display=`block`,o&&(o.textContent=`▼`);try{let o=(await t(`/matrix/corpus/category?platform=${n}&category=${encodeURIComponent(r)}`)).comments||[],s=`<div style="font-size:10px">`;o.length?o.forEach((t,i)=>{let a=t.length>60?t.slice(0,58)+`…`:t;s+=`<div style="display:flex;align-items:center;gap:4px;padding:2px 0;border-bottom:1px solid var(--border)">
              <span style="flex:1;word-break:break-all">${a}</span>
              <button onclick="_ia_delCorpus_${e}('${n}','${r.replace(/'/g,`\\'`)}',${i})" style="background:none;border:none;color:var(--red);cursor:pointer;font-size:10px;padding:0 2px" title="删除">✕</button>
            </div>`}):s+=`<div style="color:var(--text2);padding:2px 0">暂无评论，在下方批量导入</div>`,s+=`<div style="display:flex;gap:4px;margin-top:4px">
          <input id="corpusAddInput_${e}_${n}_${i}" placeholder="输入新评论..."
            style="flex:1;font-size:10px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px;padding:3px 5px">
          <button onclick="_ia_addCorpus_${e}('${n}','${r.replace(/'/g,`\\'`)}',${i})"
            style="background:var(--primary);color:#fff;border:none;padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">➕ 添加</button>
        </div>`,s+=`</div>`,a.innerHTML=s}catch(e){a.innerHTML=`<div style="color:var(--red);font-size:10px">❌ ${e.message}</div>`}}},window[`_ia_addCorpus_${e}`]=async(n,r,i)=>{let a=document.getElementById(`corpusAddInput_${e}_${n}_${i}`),o=a?.value?.trim();if(o)try{await t(`/matrix/corpus/add`,{method:`POST`,body:JSON.stringify({platform:n,category:r,text:o})}),a.value=``;let s=window[`_ia_toggleCorpusCat_${e}`];s&&s(n,r,i)}catch(e){alert(`❌ `+e.message)}},window[`_ia_delCorpus_${e}`]=async(r,i,a)=>{if(confirm(`确定删除这条评论？`))try{await t(`/matrix/corpus/delete`,{method:`POST`,body:JSON.stringify({platform:r,category:i,index:a})}),s(e,n)}catch(e){alert(`❌ `+e.message)}},window[`_ia_batchImportCorpus_${e}`]=async r=>{let i=document.getElementById(`corpusImport_${e}_${r}`),a=i?.value?.split(`
`).map(e=>e.trim()).filter(Boolean);if(!a||!a.length){alert(`请先在文本框中输入评论（每行一条）`);return}let o=c[r]||[];if(!o.length){alert(`该平台暂无分类`);return}let l=o.map((e,t)=>`${t+1}. ${e.label||e.name}`).join(`
`),u=prompt(`选择导入到哪个分类？\n${l}\n\n输入编号 (1-${o.length}):`),d=parseInt(u)-1;if(isNaN(d)||d<0||d>=o.length){alert(`无效选择`);return}let f=o[d].name;if(confirm(`向 ${r}/${f} 导入 ${a.length} 条评论？`))try{let o=await t(`/matrix/corpus/batch-add`,{method:`POST`,body:JSON.stringify({platform:r,category:f,texts:a})});o.status===`ok`?(i.value=``,s(e,n)):alert(`❌ `+(o.error||`导入失败`))}catch(e){alert(`❌ `+e.message)}}}catch(e){n.innerHTML=`<div class="error">❌ 加载失败: ${e.message}</div>`}}window._ia_previewComment=async function(e){let n=document.getElementById(`log_${e}`),i=r?.getSelected()||[],a=document.getElementById(`ic_urls_${e}`)?.value;if(!a?.trim()){n.textContent=`❌ 请填写视频链接
`;return}if(!i.length){n.textContent=`❌ 请选择账号
`;return}n.textContent=`🔍 预检...
`;try{let r=(await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`interact`,accounts:i.map(e=>e.id),params:{url:a.split(`
`).map(e=>e.trim()).filter(Boolean)[0],strategy:document.getElementById(`ic_strategy_${e}`)?.value||`comment`,corpus:document.getElementById(`ic_corpus_${e}`)?.value||``,rounds:1,dry_run:!0}})})).commands||[];n.textContent=`✅ 预检完成 | 策略: ${document.getElementById(`ic_strategy_${e}`)?.value||`comment`}\n`,n.textContent+=`   账号: ${i.length} 个\n`,r.forEach(e=>n.textContent+=`   ${e.machine}: ${e.command||``}\n`)}catch(e){n.textContent+=`❌ `+e.message+`
`}},window._ia_runComment=async function(n){let i=document.getElementById(`log_${n}`),a=r?.getSelected()||[],o=document.getElementById(`ic_urls_${n}`)?.value;if(!o?.trim()){i.textContent=`❌ 请填写视频链接
`;return}if(!a.length){i.textContent=`❌ 请选择账号
`;return}let s=o.split(`
`).map(e=>e.trim()).filter(Boolean),c=document.getElementById(`ic_strategy_${n}`)?.value||`comment`,l=document.getElementById(`ic_dir_${n}`)?.value||``,u=document.querySelectorAll(`.ic_cb_${n}:checked`),d=u.length?Array.from(u).map(e=>e.value).filter(Boolean).join(`,`):``,f=document.getElementById(`ic_comment_${n}`)?.value?.trim()||``,p=document.getElementById(`ic_interval_${n}`)?.value?.trim()||`300-600`,m={comment:`定向评论`,chain:`三级接力`,hot:`热评互动`}[c]||c,h=`策略: ${m}\n链接: ${s.join(`
`)}\n方向: ${l||`自动`}\n语料: ${d||`随机`}\n自定义: ${f||`无`}\n间隔: ${p}s`;if(!await e(`${m} ${a.length} 个账号 × ${s.length} 个视频`,h))return;i.textContent=`🚀 ${m} ${a.length} 个账号，间隔 ${p}s...\n`;let g={};a.forEach(e=>{let t=e.machine||`unknown`;g[t]||(g[t]=[]),g[t].push(e.id)});let _=0,v=Object.keys(g).length,y=0;for(let[e,n]of Object.entries(g))for(let r of s)try{let a=await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`interact`,accounts:n,params:{url:r,strategy:c,direction:l,corpus:d,rounds:1,interval:p}})});_++,y+=+(a.status===`accepted`),i.textContent+=`📦 [${e}/${r.slice(0,30)}] ${a.status||`OK`} (${_}/${v*s.length})\n`}catch(t){i.textContent+=`❌ [${e}] ${t.message}\n`}i.textContent+=`\n✅ ${y}/${_} 提交完成\n`},window._ia_runLike=async function(n){let i=document.getElementById(`log_${n}`),a=r?.getSelected()||[];if(!a.length){i.textContent=`❌ 请选择账号
`;return}let o=document.getElementById(`il_likeVideo_${n}`)?.checked,s=document.getElementById(`il_likeComment_${n}`)?.checked,c=document.getElementById(`il_follow_${n}`)?.checked,l=document.getElementById(`il_collect_${n}`)?.checked,u=document.getElementById(`il_url_${n}`)?.value?.trim(),d=[];if(o&&d.push(`点赞视频`),s&&d.push(`点赞评论`),c&&d.push(`关注博主`),l&&d.push(`收藏视频`),!d.length){i.textContent=`❌ 请至少选择一种操作
`;return}let f=`操作: ${d.join(`, `)}\n链接: ${u||`推荐页随机`}`;if(!await e(`${a.length} 个账号执行点赞互动`,f))return;i.textContent=`🚀 ${a.length} 个账号执行 ${d.join(`/`)}...\n`;let p={};a.forEach(e=>{let t=e.machine||`unknown`;p[t]||(p[t]=[]),p[t].push(e.id)});let m=s||l?`interact_like`:`like`,h=0,g=Object.keys(p).length;for(let[e,n]of Object.entries(p))try{let r=await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:u?`interact`:`like`,accounts:n,params:{url:u,blueprint:m,rounds:1}})});h++,i.textContent+=`📦 [${e}] ${r.status||`OK`} (${h}/${g})\n`}catch(t){i.textContent+=`❌ [${e}] ${t.message}\n`}i.textContent+=`
✅ 完成
`};export{i as loadView};