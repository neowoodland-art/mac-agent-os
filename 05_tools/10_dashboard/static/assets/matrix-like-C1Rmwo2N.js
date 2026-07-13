import{n as e,t}from"./index-D3FNW5HD.js";import{t as n}from"./account-selector-D87mja1n.js";var r=null;async function i(i){let a=(i.id||`like`).replace(/-/g,`_`);i.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">❤️ 收藏点赞 <span style="font-size:10px;color:var(--text2);font-weight:400">选择账号 → 执行点赞/收藏</span></div>
        <div id="acctList_${a}" style="margin-bottom:6px"><div class="loading">⏳ 加载账号列表...</div></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:11px;color:var(--text2)">操作:
            <select id="likeType_${a}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="like">❤️ 点赞</option>
              <option value="collect">⭐ 收藏</option>
            </select>
          </label>
          <button onclick="window._runLike_${a}()" style="background:var(--primary);color:#fff;border:none;padding:4px 14px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 执行选中账号</button>
          <span id="selCount_${a}" style="font-size:10px;color:var(--text2)">已选 0 个</span>
        </div>
        <div id="result_${a}" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;try{let e=await t(`/matrix/accounts`),i=Array.isArray(e)?e:e.accounts||[],o=document.getElementById(`acctList_${a}`);o&&(r=n(o,{accounts:i,checkAll:!1,height:`200px`,showBlueprint:!1,showStatus:!1,showCollectTime:!1})),document.getElementById(`selCount_${a}`).textContent=`已选 `+(r?.getCount()||0)+` 个`}catch{}window[`_runLike_${a}`]=async function(){let n=r?.getSelected()||[];if(!n.length){alert(`请先选择账号`);return}let i=document.getElementById(`result_${a}`),o=document.getElementById(`likeType_${a}`)?.value||`like`,s=`账号: ${n.map(e=>e.id).join(`, `)}`;if(await e(`对 ${n.length} 个账号执行${o===`like`?`点赞`:`收藏`}？`,s)){i.textContent=`🚀 提交 `+n.length+` 个账号...
`;try{let e=await t(`/ops/run`,{method:`POST`,body:JSON.stringify({type:`like`,accounts:n.map(e=>e.id),params:{rounds:1}})});i.textContent+=`✅ 状态: ${e.status}\n`,e.commands&&e.commands.forEach(e=>{i.textContent+=`  ${e.machine}: ${e.accounts.join(`,`)} → ${e.status}\n`}),e.errors&&(i.textContent+=`⚠️ 错误: ${JSON.stringify(e.errors)}\n`)}catch(e){i.textContent+=`❌ `+e.message+`
`}}}}export{i as loadView};