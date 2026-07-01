async function e(e){e.innerHTML=`<div class="loading">⏳ 加载中...</div>`;try{let[t,n]=await Promise.all([fetch(`/api/matrix/recordings/list`),fetch(`/api/matrix/recordings/stats`)]),r=t.ok?await t.json():{recordings:[]},i=n.ok?await n.json():{},a=Array.isArray(r)?r:r.recordings||[],o=i.stats||i;function s(e){if(e==null)return`-`;let t=Math.floor(e),n=Math.floor(t/3600),r=Math.floor(t%3600/60),i=t%60;return n>0?`${n}h${r}m`:r>0?`${r}m${i}s`:`${i}s`}function c(e){if(!e)return`-`;try{return new Date(e).toLocaleString(`zh-CN`,{month:`2-digit`,day:`2-digit`,hour:`2-digit`,minute:`2-digit`,second:`2-digit`})}catch{return e}}let l=o.total_duration||a.reduce((e,t)=>e+(t.duration||0),0);e.innerHTML=`
      <div style="padding:16px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
          <h2 style="font-size:18px;margin:0">📹 录制管理</h2>
          <span style="font-size:12px;color:var(--text2)">
            <strong>${a.length}</strong> 条录制 · 总时长 <strong>${s(l)}</strong>
          </span>
        </div>
        <div style="display:flex;gap:6px;margin-bottom:8px;align-items:center">
          <input id="recSearch" placeholder="🔍 搜索账号/任务/备注..." oninput="_filterRec()"
            style="flex:1;padding:4px 8px;font-size:12px;background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:4px">
          <span id="recCount" style="font-size:11px;color:var(--text2);white-space:nowrap">共 ${a.length} 条</span>
        </div>
        <div id="recTable" style="overflow-x:auto"></div>
      </div>`;function u(e){if(!e.length)return`<div style="font-size:12px;color:var(--text2);padding:20px;text-align:center">暂无录制记录</div>`;let t=`<table style="width:100%;font-size:11px;border-collapse:collapse">`;return t+=`<tr style="font-size:9px;color:var(--text2);border-bottom:1px solid var(--border)">
        <th style="padding:4px 6px;font-weight:400;text-align:left">账号</th>
        <th style="padding:4px 6px;font-weight:400;text-align:left">机器</th>
        <th style="padding:4px 6px;font-weight:400;text-align:left">任务</th>
        <th style="padding:4px 6px;font-weight:400;text-align:right">时长</th>
        <th style="padding:4px 6px;font-weight:400;text-align:right">大小</th>
        <th style="padding:4px 6px;font-weight:400;text-align:left">录制时间</th>
        <th style="padding:4px 6px;font-weight:400;text-align:left">状态</th>
        <th style="padding:4px 6px;font-weight:400;text-align:left">备注</th>
      </tr>`,e.forEach(e=>{let n={completed:`✅ 完成`,running:`🔄 录制中`,failed:`❌ 失败`,pending:`⏳ 等待`}[e.status]||e.status||`-`;t+=`<tr style="border-bottom:1px solid var(--border)" data-filter="${((e.account||``)+(e.task||``)+(e.note||``)).toLowerCase()}">
          <td style="padding:3px 6px"><strong>${e.account||`-`}</strong></td>
          <td style="padding:3px 6px;font-size:10px">${e.machine?`🖥️ `+e.machine:`🖥️ 本机`}</td>
          <td style="padding:3px 6px;color:var(--text2)">${e.task||`-`}</td>
          <td style="padding:3px 6px;text-align:right">${s(e.duration)}</td>
          <td style="padding:3px 6px;text-align:right;font-size:10px">${e.size?(e.size/1024/1024).toFixed(1)+`MB`:`-`}</td>
          <td style="padding:3px 6px;font-size:10px;color:var(--text2)">${c(e.created_at||e.time)}</td>
          <td style="padding:3px 6px;font-size:10px">${n}</td>
          <td style="padding:3px 6px;font-size:10px;color:var(--text2);max-width:150px;overflow:hidden;text-overflow:ellipsis">${e.note||``}</td>
        </tr>`}),t+=`</table>`,t}if(document.getElementById(`recTable`).innerHTML=u(a),window._filterRec=()=>{let e=(document.getElementById(`recSearch`)?.value||``).toLowerCase(),t=e?a.filter(t=>((t.account||``)+(t.task||``)+(t.note||``)+(t.id||``)).toLowerCase().includes(e)):a;document.getElementById(`recCount`).textContent=`共 ${t.length}/${a.length} 条`,document.getElementById(`recTable`).innerHTML=u(t)},o.total_recordings!==void 0||o.by_account){let e=document.createElement(`div`);e.style.cssText=`margin-top:10px;padding:10px;background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);font-size:11px`;let t=`<div style="font-weight:600;font-size:12px;margin-bottom:6px">📊 录制统计</div>`;o.by_account&&(t+=`<div style="display:flex;flex-wrap:wrap;gap:4px">`,Object.entries(o.by_account).forEach(([e,n])=>{t+=`<span style="background:var(--bg3);padding:2px 8px;border-radius:4px;border:1px solid var(--border)">${e}: ${n}</span>`}),t+=`</div>`),e.innerHTML=t,document.querySelector(`#recTable`)?.parentElement?.appendChild(e)}}catch(t){e.innerHTML=`<div class="error">❌ ${t.message||t}</div>`}}export{e as loadView};