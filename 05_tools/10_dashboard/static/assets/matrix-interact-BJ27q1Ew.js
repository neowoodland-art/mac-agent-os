import{n as e,t}from"./index-B5Pcs0T5.js";import{t as n}from"./account-selector-DVsh4R5m.js";var r=null;async function i(i){let a=i.id||`interact`,o=await t(`/matrix/accounts`),s=Array.isArray(o)?o:o.accounts||[];i.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">💬 评论互动 <span style="font-size:10px;color:var(--text2);font-weight:400">定向评论 / 三级接力 / 点赞 / 热评</span></div>
        <div id="acctList_${a}" style="margin-bottom:6px"></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:11px;color:var(--text2)">策略:
            <select id="istrategy_${a}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="comment">💬 定向评论</option>
              <option value="chain">🔗 三级接力</option>
              <option value="like">❤️ 点赞互动</option>
              <option value="hot">🔥 热评互动</option>
            </select>
          </label>
          <label style="font-size:11px;color:var(--text2)">链接:
            <input id="iurl_${a}" placeholder="视频链接" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px;width:200px">
          </label>
          <label style="font-size:11px;color:var(--text2)">语料:
            <select id="icorpus_${a}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="food">🍜 美食</option>
              <option value="travel">✈️ 旅行</option>
              <option value="tech">💻 科技</option>
              <option value="lifestyle">🌿 生活</option>
              <option value="emotion">💛 情感</option>
              <option value="">🎲 随机</option>
            </select>
          </label>
          <span id="selCount_${a}" style="font-size:10px;color:var(--text2)">已选 0 个</span>
          <button onclick="window._interactPreflight('${a}')" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔍 预检</button>
          <button onclick="window._interactExec('${a}')" style="background:var(--primary);color:#fff;border:none;padding:4px 14px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 提交互动</button>
        </div>
        <div id="planPreview_${a}" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:200px;overflow-y:auto;font-family:monospace;white-space:pre-wrap;display:none"></div>
        <div id="log_${a}" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:250px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`,r=n(document.getElementById(`acctList_${a}`),{accounts:s,checkAll:!1,height:`300px`}),document.getElementById(`selCount_${a}`).textContent=`已选 `+(r?.getCount()||0)+` 个`,window._interactRegistered||(window._interactRegistered=!0,window._interactPreflight=async function(e){let n=document.getElementById(`log_${e}`),i=document.getElementById(`planPreview_${e}`),a=document.getElementById(`iurl_${e}`)?.value?.trim();if(n&&(n.textContent=`🔍 预检中...
`),i&&(i.style.display=`none`),!a){n&&(n.textContent+=`❌ 请填写视频链接
`);return}let o=r?.getSelected()||[];if(!o.length){n&&(n.textContent+=`❌ 请选择账号
`);return}try{let r=await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`interact`,accounts:o.map(e=>e.id),params:{url:a,strategy:document.getElementById(`istrategy_${e}`)?.value||`comment`,corpus:document.getElementById(`icorpus_${e}`)?.value||``,rounds:1,dry_run:!0}})});n&&(n.textContent+=`✅ 预检完成
`,n.textContent+=`   总账号: ${o.length}\n`,n.textContent+=`   策略: ${document.getElementById("istrategy_${uid}")?.value||`comment`}\n`),i&&(i.innerHTML=`<strong>📋 执行计划</strong>\n${JSON.stringify(r.commands||[],null,2)}`,i.style.display=`block`)}catch(e){n&&(n.textContent+=`❌ `+e.message+`
`)}},window._interactExec=async function(n){let i=r?.getSelected()||[];if(!i.length){alert(`请先选择账号`);return}let a=document.getElementById(`iurl_${n}`)?.value?.trim();if(!a){alert(`请填写视频链接`);return}let o=document.getElementById(`log_${n}`),s=document.getElementById(`istrategy_${n}`)?.value||`comment`,c=document.getElementById(`icorpus_${n}`)?.value||``,l={comment:`定向评论`,chain:`三级接力`,like:`点赞互动`,hot:`热评互动`}[s]||s;if(await e(`${l} ${i.length} 个账号？`,`链接: ${a.slice(0,50)}...`)){o&&(o.textContent=`🚀 ${l} ${i.length} 个账号...\n`);try{let e={};i.forEach(t=>{let n=t.machine||`unknown`;e[n]||(e[n]=[]),e[n].push(t.id)});let n=Object.keys(e).length,r=0,l=[];for(let[i,u]of Object.entries(e)){let e=await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`interact`,accounts:u,params:{url:a,strategy:s,corpus:c,rounds:1}})});r++,l.push(e),o&&(o.textContent+=`📦 [${i}] ${u.join(`,`)}: ${e.status||`OK`} (${r}/${n})\n`,e.commands&&e.commands.forEach(e=>{o.textContent+=`  → ${e.machine}: ${e.accounts?.join(`,`)} 蓝图=${e.command?.match(/blueprints=(\S+)/)?.[1]||`?`}\n`}))}o&&(o.textContent+=`
✅ 全部提交完成
`)}catch(e){o&&(o.textContent+=`❌ `+e.message+`
`)}}})}export{i as loadView};