import{t as e}from"./index-D_EddaiW.js";import{t}from"./account-selector-DVsh4R5m.js";async function n(n){n.innerHTML=`
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h2 style="font-size:18px">👤 账号管理</h2>
      <div style="display:flex;gap:6px">
        <button onclick="window.showCreateAccount()" class="btn btn-primary btn-sm" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">+ 新建账号</button>
        <button onclick="window._goSmsProxy()" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">📡 短信与代理</button>
      </div>
    </div>
    <div id="matrixAccountsContent"><div class="loading">⏳ 加载账号数据...</div></div>`,window._goSmsProxy=()=>{try{window.switchView(`matrix-sms-proxy`)}catch{}};try{let[n,r]=await Promise.all([e(`/matrix/accounts`),e(`/matrix/homepage-info`).catch(()=>({results:[]}))]),i=Array.isArray(n)?n:n.accounts||[],a=document.getElementById(`matrixAccountsContent`);if(!a)return;if(!i.length){a.innerHTML=`<div class="error">暂无账号</div>`;return}let o={};(r.results||[]).forEach(e=>{e.identity_dir&&(o[e.identity_dir]=e),e.phone&&(o[e.phone]=e)});let s=document.createElement(`div`);a.innerHTML=``,a.appendChild(s),t(s,{accounts:i,hpIndex:o,checkAll:!1,height:`500px`,showBlueprint:!0})}catch(e){let t=document.getElementById(`matrixAccountsContent`);t&&(t.innerHTML=`<div class="error">❌ 加载失败: ${e.message}</div>`)}}export{n as loadView};