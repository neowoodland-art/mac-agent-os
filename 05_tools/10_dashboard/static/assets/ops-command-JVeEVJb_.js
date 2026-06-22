import{n as e}from"./index-DScJLzZv.js";async function t(t){let o=`cmd_`+Math.random().toString(36).slice(2,6);t.innerHTML=`
    <div style="padding:16px;max-width:1100px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <div><span style="font-weight:600;font-size:15px">🖥️ 联邦指挥台</span>
        <span style="font-size:11px;color:var(--text2);margin-left:8px">跨机器命令下发 · 批量执行 · 状态监控</span></div>
        <div style="display:flex;gap:6px">
          <button onclick="window._refCmd('${o}')" style="background:var(--bg2);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:11px;cursor:pointer">⟳ 刷新状态</button>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px">

        <!-- 左栏: 命令配置 -->
        <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
          <div style="font-weight:600;font-size:12px;margin-bottom:8px">📋 命令配置</div>

          <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:4px">目标机器</label>
          <select id="tgtMachine_${o}" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:5px;font-size:11px;margin-bottom:8px">
            <option value="">⏳ 加载机器列表...</option>
          </select>

          <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:4px">操作类型</label>
          <select id="opsType_${o}" onchange="window._opsTypeChange_${o}()" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:5px;font-size:11px;margin-bottom:8px">
            <option value="nurture">🏃 养号</option>
            <option value="collect">📡 采集</option>
            <option value="comment">💬 评论</option>
            <option value="login">🔑 登录</option>
            <option value="logout">🔒 登出</option>
          </select>

          <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:4px">选择蓝图</label>
          <select id="bpSelect_${o}" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:5px;font-size:11px;margin-bottom:8px">
            <option value="">⏳ 加载蓝图...</option>
          </select>

          <div id="paramsArea_${o}" style="margin-bottom:8px;display:none">
            <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:4px">参数配置</label>
            <div id="paramFields_${o}"></div>
          </div>

          <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:4px">轮数</label>
          <select id="rounds_${o}" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:5px;font-size:11px;margin-bottom:8px">
            <option value="1">1</option><option value="3">3</option>
            <option value="5" selected>5</option><option value="10">10</option><option value="20">20</option>
          </select>

          <div style="display:flex;gap:6px">
            <button onclick="window._execCmd_${o}()" style="flex:1;background:#22c55e;color:#000;border:none;padding:7px 0;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600">🚀 执行</button>
            <button onclick="window._clearLog_${o}()" style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:11px;cursor:pointer">✕ 清空</button>
          </div>
        </div>

        <!-- 右栏: 账号选择 + 执行结果 -->
        <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
          <div style="font-weight:600;font-size:12px;margin-bottom:8px">👥 账号选择 <span id="selCount_${o}" style="font-size:10px;color:var(--text2);font-weight:400"></span></div>
          <div id="acctList_${o}" style="max-height:180px;overflow-y:auto;margin-bottom:8px;font-size:11px"><div class="loading">⏳ 加载账号列表...</div></div>

          <div style="font-weight:600;font-size:12px;margin-bottom:4px">📊 执行日志</div>
          <div id="log_${o}" style="background:var(--bg3);border-radius:6px;padding:8px;font-size:10px;font-family:monospace;white-space:pre-wrap;max-height:260px;overflow-y:auto;border:1px solid var(--border)"><span style="color:var(--text2)">等待执行...</span></div>
        </div>
      </div>

      <!-- 底栏: 机器状态 + 快捷操作 -->
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <span style="font-weight:600;font-size:12px">🔌 机器状态</span>
          <div style="display:flex;gap:6px">
            <button onclick="window._syncAll_${o}()" style="background:var(--bg3);border:1px solid var(--border);border-radius:5px;padding:3px 8px;font-size:10px;cursor:pointer">🔄 同步所有</button>
          </div>
        </div>
        <div id="machineList_${o}" style="display:flex;gap:8px;flex-wrap:wrap;font-size:11px"><span style="color:var(--text2)">加载中...</span></div>
        <div id="statusLog_${o}" style="margin-top:6px;font-size:10px;color:var(--text2);font-family:monospace"></div>
      </div>
    </div>`,n(o),r(o),i(o),window[`_opsTypeChange_${o}`]=function(){let e=document.getElementById(`opsType_${o}`)?.value,t=document.getElementById(`paramsArea_${o}`),n=document.getElementById(`paramFields_${o}`);e===`comment`?(t.style.display=``,n.innerHTML=`
        <input id="url_${o}" placeholder="视频链接" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:10px;margin-bottom:4px">
        <input id="text_${o}" placeholder="评论内容(空=用语料库)" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:10px;margin-bottom:4px">
        <select id="corpus_${o}" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:10px">
          <option value="">不用语料库</option>
          <option value="corpus_praise">赞美</option>
          <option value="corpus_question">提问</option>
          <option value="corpus_discuss">讨论</option>
        </select>`):e===`collect`?(t.style.display=``,n.innerHTML=`<input id="keyword_${o}" placeholder="搜索关键词(可选)" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:10px">`):t.style.display=`none`},window[`_execCmd_${o}`]=async function(){let t=document.getElementById(`log_${o}`),n=a(o);if(!n.length){t.innerHTML=`<span style="color:var(--red)">⚠️ 请选择至少一个账号</span>`;return}let r=document.getElementById(`opsType_${o}`)?.value||`nurture`,i=document.getElementById(`bpSelect_${o}`)?.value||`douyin_daily`,s=parseInt(document.getElementById(`rounds_${o}`)?.value||`5`),c=document.getElementById(`tgtMachine_${o}`)?.value||``,l=`操作: ${r}\n蓝图: ${i}\n账号: ${n.join(`, `)}\n轮数: ${s}\n机器: ${c||`自动分配`}`;if(!await e(`即将在 ${n.length} 个账号上执行 ${r} 操作`,l)){t.innerHTML=`<span style="color:var(--text2)">已取消</span>`;return}let u={blueprint:i,rounds:s};if(r===`comment`){let e=document.getElementById(`url_${o}`)?.value,t=document.getElementById(`text_${o}`)?.value,n=document.getElementById(`corpus_${o}`)?.value;e&&(u.url=e),t&&(u.text=t),n&&(u.corpus=n)}c&&(u.machine=c),t.innerHTML=`<span style="color:var(--text2)">⏳ 提交执行...</span>
`;try{let e=await(await fetch(`/api/ops/run`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({type:r,accounts:n,params:u})})).json(),i=`<span style="color:var(--green)">✅ 已提交</span>
`;(e.commands||e.results||[]).forEach(e=>{let t=e.account||e.account_id||e.target||`?`,n=e.status||e.machine||`sent`;i+=`  ${t}: ${n}\n`}),e.errors&&(i+=`<span style="color:var(--red)">⚠️ 错误: ${JSON.stringify(e.errors)}</span>\n`),t.innerHTML=i}catch(e){t.innerHTML=`<span style="color:var(--red)">❌ ${e.message}</span>`}},window[`_clearLog_${o}`]=function(){document.getElementById(`log_${o}`).innerHTML=`<span style="color:var(--text2)">已清空</span>`},window[`_refCmd_${o}`]=function(){n(o);let e=document.getElementById(`log_${o}`);e&&(e.innerHTML=`<span style="color:var(--text2)">⟳ 已刷新</span>
`)},window[`_syncAll_${o}`]=async function(){let e=document.getElementById(`statusLog_${o}`);e&&(e.textContent=`⏳ 同步中...`);try{let t=await(await fetch(`/api/fleet/sync`,{method:`POST`})).json();e&&(e.textContent=`✅ 同步完成: `+(t.message||JSON.stringify(t)))}catch(t){e&&(e.textContent=`❌ 同步失败: `+t.message)}}}async function n(e){try{let t=(await(await fetch(`/api/machines`)).json()).machines||[],n=document.getElementById(`tgtMachine_${e}`);n&&(n.innerHTML=`<option value="">全部机器(自动分配)</option>`+t.map(e=>`<option value="${e.hostname}">${e.hostname} ${e.status===`online`?`🟢`:`🔴`}</option>`).join(``),!t.find(e=>e.status===`online`)&&t.length&&(n.value=t[0].hostname));let r=document.getElementById(`machineList_${e}`);r&&(r.innerHTML=t.map(e=>`<div style="background:var(--bg3);border-radius:6px;padding:6px 10px;border:1px solid var(--border);display:flex;align-items:center;gap:6px">
          ${e.status===`online`?`🟢`:`🔴`}
          <span style="font-weight:500">${e.hostname}</span>
          <span style="font-size:10px;color:var(--text2)">${e.ip||e.tailscale_ip||``}</span>
          <span style="font-size:10px;color:${e.status===`online`?`var(--green)`:`var(--red)`}">${e.status||`?`}</span>
        </div>`).join(``))}catch{let t=document.getElementById(`tgtMachine_${e}`);t&&(t.innerHTML=`<option value="">加载失败</option>`)}}async function r(e){try{let t=await(await fetch(`/api/matrix/blueprints`)).json(),n=Array.isArray(t)?t:t.blueprints||[],r=document.getElementById(`bpSelect_${e}`);r&&(r.innerHTML=n.map(e=>`<option value="${e.file?e.file.replace(`.json`,``):e.name}">${`${e.name} — ${(e.description||``).slice(0,36)}`}</option>`).join(``))}catch{let t=document.getElementById(`bpSelect_${e}`);t&&(t.innerHTML=`<option value="">加载失败</option>`)}}async function i(e){try{let t=await(await fetch(`/api/matrix/accounts`)).json(),n=Array.isArray(t)?t:t.accounts||[],r=document.getElementById(`acctList_${e}`);if(!r)return;r.innerHTML=n.map(t=>`<label style="display:flex;align-items:center;gap:4px;padding:2px 0;cursor:pointer">
        <input type="checkbox" id="${`acct_${e}_${t.id}`}" value="${t.id}" onchange="window._updateCount_${e}()">
        <span>${t.id}</span>
        <span style="font-size:10px;color:var(--text2)">${t.platform||``}</span>
        <span style="font-size:10px;color:${t._status===`logged_in`?`var(--green)`:`var(--red)`}">${t._status===`logged_in`?`🟢`:t._status===`remote`?`🟡远程`:`🔴离线`}</span>
      </label>`).join(``),window[`_updateCount_${e}`]=function(){let t=document.querySelectorAll(`#acctList_${e} input:checked`).length,n=document.getElementById(`selCount_${e}`);n&&(n.textContent=`已选 ${t} 个`)},window[`_updateCount_${e}`]()}catch(t){let n=document.getElementById(`acctList_${e}`);n&&(n.innerHTML=`<span style="color:var(--red)">❌ ${t.message}</span>`)}}function a(e){return[...document.querySelectorAll(`#acctList_${e} input:checked`)].map(e=>e.value)}export{t as loadView};