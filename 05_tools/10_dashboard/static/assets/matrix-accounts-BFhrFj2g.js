async function e(e){e.innerHTML=`<div class="loading">⏳ 加载中...</div>`;try{let[t,n]=await Promise.all([fetch(`/api/matrix/accounts`).then(e=>e.ok?e.json():{accounts:[]}).catch(()=>({accounts:[]})),fetch(`/api/matrix/homepage-info`).then(e=>e.ok?e.json():{results:[]}).catch(()=>({results:[]}))]),r=Array.isArray(t)?t:t.accounts||[],i=n.results||[],a={};i.forEach(e=>{e.identity_dir&&(a[e.identity_dir]=e),e.phone&&(a[e.phone]=e)});let o=[`chengzigedeAir`,`5kechengdeAir`,`7kecheng`],s={};r.forEach(e=>{let t=e.owner_machine||`unknown`;s[t]||(s[t]=[]);let n=a[e.identity_dir]||a[e.phone],r=n?e.platform===`douyin`?n.douyin:n.xiaohongshu:null;s[t].push({id:e.id,platform:e.platform,phone:e.phone||``,identity_dir:(e.identity_dir||``).replace(`identities/`,``),nickname:r?.nickname||e.nickname||``,fans:r?.fans||e.fans||``,following:r?.following||e.following||``,likes:r?.likes||e.likes||``,posts:r?.posts||e.posts||``,status:e._status||`unknown`,collected_at:r?.collected_at||``})});let c=`
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px">👤 账号管理</h2>
        <div style="display:flex;gap:6px">
          <button onclick="window.showCreateAccount()" style="background:var(--primary);color:#fff;border:none;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">+ 新建账号</button>
          <button onclick="try{window.switchView('matrix-sms-proxy')}catch(e){}" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">📡 短信与代理</button>
        </div>
      </div>
      <div style="overflow-x:auto">
      <table style="width:100%;font-size:11px;border-collapse:collapse">
        <tr style="font-size:9px;color:var(--text2);border-bottom:1px solid var(--border)">
          <th style="padding:4px 6px;font-weight:400;text-align:left">机器</th>
          <th style="padding:4px 6px;font-weight:400;text-align:left">身份</th>
          <th style="padding:4px 6px;font-weight:400;text-align:left">账号ID</th>
          <th style="padding:4px 6px;font-weight:400;text-align:left">平台</th>
          <th style="padding:4px 6px;font-weight:400;text-align:left">昵称</th>
          <th style="padding:4px 6px;font-weight:400;text-align:right">👥</th>
          <th style="padding:4px 6px;font-weight:400;text-align:right">👍</th>
          <th style="padding:4px 6px;font-weight:400;text-align:right">❤️</th>
          <th style="padding:4px 6px;font-weight:400;text-align:right">📝</th>
          <th style="padding:4px 6px;font-weight:400;text-align:left">状态</th>
        </tr>`;o.filter(e=>s[e]).forEach(e=>{s[e].forEach(t=>{let n=t.platform===`douyin`?`🎵`:`📕`,r={logged_in:`🟢 已登录`,remote:`🔵 远程`,expired:`🟡 过期`,no_cookie:`🔴 无Cookie`,disabled:`⚪ 禁用`}[t.status]||t.status;c+=`<tr style="border-bottom:1px solid var(--border)">
          <td style="padding:3px 6px">${e===`chengzigedeAir`?`🖥️`:`☁️`}${e}</td>
          <td style="padding:3px 6px;font-size:10px;color:var(--text2)">📁${t.identity_dir}</td>
          <td style="padding:3px 6px"><strong>${t.id}</strong></td>
          <td style="padding:3px 6px">${n}</td>
          <td style="padding:3px 6px">${t.nickname||`-`}</td>
          <td style="padding:3px 6px;text-align:right">${t.fans||`-`}</td>
          <td style="padding:3px 6px;text-align:right">${t.following||`-`}</td>
          <td style="padding:3px 6px;text-align:right">${t.likes||`-`}</td>
          <td style="padding:3px 6px;text-align:right">${t.posts||`-`}</td>
          <td style="padding:3px 6px;font-size:10px">${r}</td>
        </tr>`})}),c+=`</table></div>`,c+=`<div style="padding:4px 6px;font-size:10px;color:var(--text2);margin-top:6px">共 ${r.length} 个账号 | 🎵 ${r.filter(e=>e.platform===`douyin`).length} | 📕 ${r.filter(e=>e.platform===`xiaohongshu`).length}</div>`,e.innerHTML=c}catch(t){e.innerHTML=`<div class="error">❌ ${t.message||t}</div>`}}export{e as loadView};