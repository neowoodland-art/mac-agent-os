import{t as e}from"./index-ruflvycv.js";import{t}from"./account-selector-DBZWFo9Z.js";var n=null;async function r(r){let a=r.id||`like`;r.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">❤️ 收藏点赞 <span style="font-size:10px;color:var(--text2);font-weight:400">选择账号 → 填入视频链接 → 执行点赞</span></div>
        <div id="acctList_${a}" style="margin-bottom:6px"><div class="loading">⏳ 加载账号列表...</div></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
          <textarea id="urls_${a}" placeholder="视频链接（每行一个，支持多个）" rows="3" style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
          <button onclick="window._runLike()" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:4px;cursor:pointer;font-size:12px;align-self:flex-start">❤️ 执行点赞</button>
        </div>
        <div id="result_${a}" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;try{let r=await e(`/matrix/accounts`),i=Array.isArray(r)?r:r.accounts||[],o=document.getElementById(`acctList_${a}`);o&&(n=t(o,{accounts:i,checkAll:!1,compact:!0,height:`200px`,showBlueprint:!1,showStatus:!1,showCollectTime:!1}))}catch{}i(a)}function i(t){window._likeGlobals||(window._likeGlobals=!0,window._runLike=async function(){let r=n?.getSelected()||[],i=document.getElementById(`urls_${t}`)?.value,a=document.getElementById(`result_${t}`);if(!i||!i.trim()){a.textContent=`请填写视频链接`;return}let o=i.split(`
`).map(e=>e.trim()).filter(e=>e);if(!r.length){a.textContent=`请先选择要执行的账号`;return}a.textContent=`⏳ 使用 `+r.length+` 个账号点赞 `+o.length+` 个视频...
`;let s=[];for(let t of o)for(let n of r)try{let r=await e(`/matrix/task/run`,{method:`POST`,body:JSON.stringify({type:`like`,url:t,account:n.id})});s.push({url:t,account:n.id,status:r.error?`❌`:`✅`,msg:r.error||r.task_id||`OK`})}catch(e){s.push({url:t,account:n.id,status:`❌`,msg:e.message})}a.textContent=`✅ `+s.filter(e=>e.status===`✅`).length+`/`+s.length+` 完成
`+s.slice(0,30).map(e=>e.status+` `+e.account+` `+e.url.slice(0,35)+` `+e.msg).join(`
`)})}export{r as loadView};