import{n as e,t}from"./index-BxhcoAxi.js";import{t as n}from"./account-selector-DVsh4R5m.js";var r=null;async function i(e){let i=e.id||`interact`,o=await t(`/matrix/accounts`),s=Array.isArray(o)?o:o.accounts||[];e.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:4px">💬 评论互动 <span style="font-size:10px;color:var(--text2);font-weight:400">定向评论 / 三级接力 / 点赞 / 语料库</span></div>
        <div id="acctList_${i}" style="margin-bottom:6px"></div>
        <div id="selBar_${i}" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:6px">
          <span id="selCount_${i}" style="font-size:10px;color:var(--text2)">已选 0 个</span>
          <button onclick="window._ia_selAll_${i}()" style="background:var(--bg3);border:1px solid var(--border);padding:2px 8px;border-radius:3px;cursor:pointer;font-size:10px">全选</button>
          <button onclick="window._ia_selNone_${i}()" style="background:var(--bg3);border:1px solid var(--border);padding:2px 8px;border-radius:3px;cursor:pointer;font-size:10px">清空</button>
        </div>
        <!-- 三个 Tab -->
        <div style="display:flex;gap:0;border-bottom:1px solid var(--border);margin-bottom:8px">
          <button class="ia_tab" data-tab="comment" onclick="window._ia_switchTab_${i}('comment')"
            style="padding:6px 16px;font-size:12px;cursor:pointer;border:none;border-bottom:2px solid var(--primary);background:transparent;color:var(--primary);font-weight:600">💬 定向评论</button>
          <button class="ia_tab" data-tab="like" onclick="window._ia_switchTab_${i}('like')"
            style="padding:6px 16px;font-size:12px;cursor:pointer;border:none;border-bottom:2px solid transparent;background:transparent;color:var(--text2)">❤️ 点赞互动</button>
          <button class="ia_tab" data-tab="corpus" onclick="window._ia_switchTab_${i}('corpus')"
            style="padding:6px 16px;font-size:12px;cursor:pointer;border:none;border-bottom:2px solid transparent;background:transparent;color:var(--text2)">📚 语料库</button>
        </div>
        <!-- Tab 内容容器 -->
        <div id="tabBody_${i}"></div>
        <!-- 日志（跨 Tab 共享） -->
        <div id="log_${i}" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:200px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`,r=n(document.getElementById(`acctList_${i}`),{accounts:s,checkAll:!1,height:`200px`});let c=()=>{document.getElementById(`selCount_${i}`).textContent=`已选 `+(r?.getCount()||0)+` 个`};c(),window[`_ia_selAll_${i}`]=()=>{r?.selectAll(!0),c()},window[`_ia_selNone_${i}`]=()=>{r?.selectAll(!1),c()},window[`_ia_switchTab_${i}`]=t=>{document.querySelectorAll(`#${e.id} .ia_tab`).forEach(e=>{let n=e.dataset.tab===t;e.style.borderBottomColor=n?`var(--primary)`:`transparent`,e.style.color=n?`var(--primary)`:`var(--text2)`,e.style.fontWeight=n?`600`:`400`}),a(i,t)},a(i,`comment`)}async function a(e,t){let n=document.getElementById(`tabBody_${e}`);n&&(t===`comment`?o(e,n):t===`like`?s(e,n):t===`corpus`&&c(e,n))}function o(e,t){t.innerHTML=`
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
      <textarea id="ic_urls_${e}" placeholder="视频链接（每行一个，支持多个）" rows="3"
        style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
      <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:140px">
        <div style="display:flex;gap:4px">
          <select id="ic_strategy_${e}" style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
            <option value="comment">💬 定向评论</option>
            <option value="chain">🔗 三级接力</option>
            <option value="hot">🔥 热评互动</option>
          </select>
          <select id="ic_dir_${e}" style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
            <option value="">自动方向</option>
            <option value="称赞">👍 称赞</option><option value="提问">🤔 提问</option>
            <option value="共鸣">💗 共鸣</option><option value="感慨">😌 感慨</option>
          </select>
        </div>
        <div style="display:flex;gap:4px">
          <select id="ic_corpus_${e}" style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
            <option value="">🎲 随机语料</option>
            <option value="food">🍜 美食</option><option value="travel">✈️ 旅行</option>
            <option value="tech">💻 科技</option><option value="lifestyle">🌿 生活</option>
            <option value="emotion">💛 情感</option>
          </select>
          <input id="ic_comment_${e}" placeholder="或手动写评论" style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
        </div>
        <button onclick="window._ia_runComment('${e}')" style="background:var(--primary);color:#fff;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 执行评论</button>
        <button onclick="window._ia_previewComment('${e}')" style="background:var(--bg3);border:1px solid var(--border);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px">🔍 预检</button>
      </div>
    </div>`}function s(e,t){t.innerHTML=`
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
      <div style="flex:1;min-width:200px">
        <div style="font-size:11px;color:var(--text2);margin-bottom:4px">操作类型</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <label style="font-size:11px;display:flex;align-items:center;gap:4px;cursor:pointer">
            <input type="checkbox" id="il_likeVideo_${e}" checked> ❤️ 点赞视频
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px;cursor:pointer">
            <input type="checkbox" id="il_likeComment_${e}"> 💬 点赞评论
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px;cursor:pointer">
            <input type="checkbox" id="il_follow_${e}"> 👤 关注博主
          </label>
          <label style="font-size:11px;display:flex;align-items:center;gap:4px;cursor:pointer">
            <input type="checkbox" id="il_collect_${e}"> ⭐ 收藏视频
          </label>
        </div>
      </div>
      <div style="flex:1;min-width:200px">
        <div style="font-size:11px;color:var(--text2);margin-bottom:4px">视频链接（可选）</div>
        <input id="il_url_${e}" placeholder="留空则浏览推荐页操作" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px">
        <button onclick="window._ia_runLike('${e}')" style="margin-top:6px;background:var(--primary);color:#fff;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600;width:100%">🚀 执行选中账号</button>
      </div>
    </div>`}async function c(e,n){n.innerHTML=`<div class="loading">⏳ 加载语料库...</div>`;try{let e=await t(`/matrix/corpus`),r=e.categories||e.corpus||[],i={};r.forEach(e=>{let t=e.platform===`xiaohongshu`?`📕 小红书`:`🎵 抖音`;i[t]||(i[t]=[]),i[t].push(e)});let a=`<div style="font-size:12px;color:var(--text2);margin-bottom:6px">共 ${r.length} 个分类 · ${e.total_comments||0} 条评论</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px">`;Object.entries(i).forEach(([e,t])=>{a+=`<div style="background:var(--bg2);border-radius:6px;padding:10px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:12px;margin-bottom:6px">${e}</div>
        <table style="width:100%;font-size:10px;border-collapse:collapse">
        <thead><tr><th style="text-align:left;padding:2px 4px;border-bottom:1px solid var(--border);color:var(--text2);font-weight:400">分类</th>
        <th style="padding:2px 4px;border-bottom:1px solid var(--border);color:var(--text2);font-weight:400;text-align:center">条数</th></tr></thead>
        <tbody>${t.map(e=>`<tr>
          <td style="padding:2px 4px;border-bottom:1px solid var(--border)">${e.name||e.category||`?`}</td>
          <td style="padding:2px 4px;border-bottom:1px solid var(--border);text-align:center">${e.count||e.comment_count||0}</td>
        </tr>`).join(``)}</tbody></table>
      </div>`}),a+=`<div style="background:var(--bg2);border-radius:6px;padding:10px;border:1px solid var(--border);grid-column:1/-1">
      <div style="font-weight:600;font-size:12px;margin-bottom:6px">🔗 三级接力语料</div>
      <div style="font-size:10px;color:var(--text2);margin-bottom:4px">评论→回复→再回复，5 个分类可用。在「定向评论」Tab 选择"三级接力"策略即可使用</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <span style="background:var(--bg3);padding:2px 8px;border-radius:3px;font-size:10px">🍜 美食 2组</span>
        <span style="background:var(--bg3);padding:2px 8px;border-radius:3px;font-size:10px">✈️ 旅行 2组</span>
        <span style="background:var(--bg3);padding:2px 8px;border-radius:3px;font-size:10px">💻 科技 1组</span>
        <span style="background:var(--bg3);padding:2px 8px;border-radius:3px;font-size:10px">🌿 生活 1组</span>
        <span style="background:var(--bg3);padding:2px 8px;border-radius:3px;font-size:10px">💛 情感 1组</span>
      </div>
    </div>`,a+=`</div>`,n.innerHTML=a}catch(e){n.innerHTML=`<div class="error">❌ 加载失败: ${e.message}</div>`}}window._ia_previewComment=async function(e){let n=document.getElementById(`log_${e}`),i=r?.getSelected()||[],a=document.getElementById(`ic_urls_${e}`)?.value;if(!a?.trim()){n.textContent=`❌ 请填写视频链接
`;return}if(!i.length){n.textContent=`❌ 请选择账号
`;return}n.textContent=`🔍 预检...
`;try{let r=(await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`interact`,accounts:i.map(e=>e.id),params:{url:a.split(`
`).map(e=>e.trim()).filter(Boolean)[0],strategy:document.getElementById(`ic_strategy_${e}`)?.value||`comment`,corpus:document.getElementById(`ic_corpus_${e}`)?.value||``,rounds:1,dry_run:!0}})})).commands||[];n.textContent=`✅ 预检完成 | 策略: ${document.getElementById(`ic_strategy_${e}`)?.value||`comment`}\n`,n.textContent+=`   账号: ${i.length} 个\n`,r.forEach(e=>n.textContent+=`   ${e.machine}: ${e.command||``}\n`)}catch(e){n.textContent+=`❌ `+e.message+`
`}},window._ia_runComment=async function(n){let i=document.getElementById(`log_${n}`),a=r?.getSelected()||[],o=document.getElementById(`ic_urls_${n}`)?.value;if(!o?.trim()){i.textContent=`❌ 请填写视频链接
`;return}if(!a.length){i.textContent=`❌ 请选择账号
`;return}let s=o.split(`
`).map(e=>e.trim()).filter(Boolean),c=document.getElementById(`ic_strategy_${n}`)?.value||`comment`,l=document.getElementById(`ic_dir_${n}`)?.value||``,u=document.getElementById(`ic_corpus_${n}`)?.value||``,d=document.getElementById(`ic_comment_${n}`)?.value?.trim()||``,f={comment:`定向评论`,chain:`三级接力`,hot:`热评互动`}[c]||c,p=`策略: ${f}\n链接: ${s.join(`
`)}\n方向: ${l||`自动`}\n语料: ${u||`随机`}\n自定义: ${d||`无`}`;if(!await e(`${f} ${a.length} 个账号 × ${s.length} 个视频`,p))return;i.textContent=`🚀 ${f} ${a.length} 个账号...\n`;let m={};a.forEach(e=>{let t=e.machine||`unknown`;m[t]||(m[t]=[]),m[t].push(e.id)});let h=0,g=Object.keys(m).length,_=0;for(let[e,n]of Object.entries(m))for(let r of s)try{let a=await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`interact`,accounts:n,params:{url:r,strategy:c,direction:l,corpus:u,rounds:1}})});h++,_+=+(a.status===`accepted`),i.textContent+=`📦 [${e}/${r.slice(0,30)}] ${a.status||`OK`} (${h}/${g*s.length})\n`}catch(t){i.textContent+=`❌ [${e}] ${t.message}\n`}i.textContent+=`\n✅ ${_}/${h} 提交完成\n`},window._ia_runLike=async function(n){let i=document.getElementById(`log_${n}`),a=r?.getSelected()||[];if(!a.length){i.textContent=`❌ 请选择账号
`;return}let o=document.getElementById(`il_likeVideo_${n}`)?.checked,s=document.getElementById(`il_likeComment_${n}`)?.checked,c=document.getElementById(`il_follow_${n}`)?.checked,l=document.getElementById(`il_collect_${n}`)?.checked,u=document.getElementById(`il_url_${n}`)?.value?.trim(),d=[];if(o&&d.push(`点赞视频`),s&&d.push(`点赞评论`),c&&d.push(`关注博主`),l&&d.push(`收藏视频`),!d.length){i.textContent=`❌ 请至少选择一种操作
`;return}let f=`操作: ${d.join(`, `)}\n链接: ${u||`推荐页随机`}`;if(!await e(`${a.length} 个账号执行点赞互动`,f))return;i.textContent=`🚀 ${a.length} 个账号执行 ${d.join(`/`)}...\n`;let p={};a.forEach(e=>{let t=e.machine||`unknown`;p[t]||(p[t]=[]),p[t].push(e.id)});let m=s||l?`interact_like`:`like`,h=0,g=Object.keys(p).length;for(let[e,n]of Object.entries(p))try{let r=await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:u?`interact`:`like`,accounts:n,params:{url:u,blueprint:m,rounds:1}})});h++,i.textContent+=`📦 [${e}] ${r.status||`OK`} (${h}/${g})\n`}catch(t){i.textContent+=`❌ [${e}] ${t.message}\n`}i.textContent+=`
✅ 完成
`};export{i as loadView};