import{t as e}from"./index-B-ODlb3w.js";import{t}from"./account-selector-DBZWFo9Z.js";var n=null;async function r(r){let a=r.id||`comment`;r.innerHTML=`
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">💬 定向评论 <span style="font-size:10px;color:var(--text2);font-weight:400">选择账号 → 填入视频链接 → 方向/语料 → 执行</span></div>
        <div id="acctList_${a}" style="margin-bottom:6px"><div class="loading">⏳ 加载账号列表...</div></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start">
          <textarea id="urls_${a}" placeholder="视频链接（每行一个，支持多个）" rows="3" style="flex:2;min-width:200px;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:5px;font-size:12px;resize:vertical"></textarea>
          <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:140px">
            <select id="dir_${a}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
              <option value="">自动选方向</option>
              <option value="称赞">👍 称赞</option><option value="提问">🤔 提问</option>
              <option value="共鸣">💗 共鸣</option><option value="感慨">😌 感慨</option>
              <option value="客观">📊 客观</option>
            </select>
            <select id="corpus_${a}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px">
              <option value="">默认语料</option>
              <option value="通用">📚 通用</option><option value="科技">💻 科技</option>
              <option value="生活">🏠 生活</option><option value="美食">🍔 美食</option>
              <option value="娱乐">🎮 娱乐</option>
            </select>
            <button onclick="window._runComment()" style="background:var(--primary);color:#fff;border:none;padding:5px 12px;border-radius:4px;cursor:pointer;font-size:12px">🚀 执行评论</button>
          </div>
        </div>
        <div id="result_${a}" style="font-size:10px;color:var(--text2);margin-top:4px;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;try{let r=await e(`/matrix/accounts`),i=Array.isArray(r)?r:r.accounts||[],o=document.getElementById(`acctList_${a}`);o&&(n=t(o,{accounts:i,checkAll:!1,compact:!0,height:`200px`,showBlueprint:!1,showCollectTime:!1}))}catch(e){let t=document.getElementById(`acctList_${a}`);t&&(t.innerHTML=`<div class="error">❌ ${e.message}</div>`)}i(a)}function i(t){window._commentGlobals||(window._commentGlobals=!0,window._runComment=async function(){let r=n?.getSelected()||[],i=document.getElementById(`urls_${t}`)?.value,a=document.getElementById(`dir_${t}`)?.value,o=document.getElementById(`corpus_${t}`)?.value,s=document.getElementById(`result_${t}`);if(!i||!i.trim()){s.textContent=`请填写至少一个视频链接`;return}let c=i.split(`
`).map(e=>e.trim()).filter(e=>e);if(!c.length){s.textContent=`请填写有效的视频链接`;return}if(!r.length){s.textContent=`请先选择要执行的账号`;return}s.textContent=`⏳ 使用 `+r.length+` 个账号评论 `+c.length+` 个视频...
`;let l=[];for(let t of c)for(let n of r)try{let r=await e(`/matrix/task/run`,{method:`POST`,body:JSON.stringify({type:`comment`,url:t,direction:a||null,account:n.id,corpus:o||null})});l.push({url:t,account:n.id,status:r.error?`❌`:`✅`,msg:r.error||r.task_id||`OK`})}catch(e){l.push({url:t,account:n.id,status:`❌`,msg:e.message})}s.textContent=`✅ `+l.filter(e=>e.status===`✅`).length+`/`+l.length+` 完成
`+l.slice(0,30).map(e=>e.status+` `+e.account+` `+e.url.slice(0,35)+` `+e.msg).join(`
`)})}export{r as loadView};