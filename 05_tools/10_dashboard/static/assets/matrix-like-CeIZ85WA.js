import{n as e,t}from"./index-BFf6y10_.js";import{t as n}from"./account-selector-DBZWFo9Z.js";var r=null;async function i(e){let i=e.id||`like`;e.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">❤️ 收藏点赞 <span style="font-size:10px;color:var(--text2);font-weight:400">选择账号 → 填入视频链接 → 执行点赞</span></div>
        <div id="acctList_${i}" style="margin-bottom:6px"><div class="loading">⏳ 加载账号列表...</div></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
          <textarea id="urls_${i}" placeholder="视频链接（每行一个，支持多个）" rows="3" style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
          <button onclick="window._runLike()" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:4px;cursor:pointer;font-size:12px;align-self:flex-start">❤️ 执行点赞</button>
        </div>
        <div id="result_${i}" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;try{let e=await t(`/matrix/accounts`),a=Array.isArray(e)?e:e.accounts||[],o=document.getElementById(`acctList_${i}`);o&&(r=n(o,{accounts:a,checkAll:!1,compact:!0,height:`200px`,showBlueprint:!1,showStatus:!1,showCollectTime:!1}))}catch{}a(i)}function a(n){window._likeGlobals||(window._likeGlobals=!0,window._runLike=async function(){let i=r?.getSelected()||[],a=document.getElementById(`urls_${n}`)?.value,o=document.getElementById(`result_${n}`);if(!a||!a.trim()){o.textContent=`请填写视频链接`;return}let s=a.split(`
`).map(e=>e.trim()).filter(e=>e);if(!i.length){o.textContent=`请先选择要执行的账号`;return}let c=`账号: ${i.map(e=>e.id).join(`, `)}\n视频: ${s.join(`
`)}`;if(!await e(`即将用 ${i.length} 个账号点赞 ${s.length} 个视频`,c)){o.textContent=`已取消`;return}o.textContent=`⏳ 使用 `+i.length+` 个账号点赞 `+s.length+` 个视频...
`;let l=[];for(let e of s)for(let n of i)try{let r=await t(`/matrix/task/run`,{method:`POST`,body:JSON.stringify({type:`like`,url:e,account:n.id})});l.push({url:e,account:n.id,status:r.error?`❌`:`✅`,msg:r.error||r.task_id||`OK`})}catch(t){l.push({url:e,account:n.id,status:`❌`,msg:t.message})}o.textContent=`✅ `+l.filter(e=>e.status===`✅`).length+`/`+l.length+` 完成
`+l.slice(0,30).map(e=>e.status+` `+e.account+` `+e.url.slice(0,35)+` `+e.msg).join(`
`)})}export{i as loadView};