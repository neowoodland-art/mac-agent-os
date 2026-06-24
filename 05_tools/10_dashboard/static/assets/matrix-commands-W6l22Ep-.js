async function e(e){e.innerHTML=`<div class="loading">⏳ 加载中...</div>`;try{let t=(await(await fetch(`/api/ops/history`)).json()).commands||[];e.innerHTML=`
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">🎯 命令与任务</h2>
        <button onclick="location.reload()" style="background:var(--bg3);border:1px solid var(--border);padding:5px 12px;border-radius:5px;cursor:pointer;font-size:12px">🔄 刷新</button>
      </div>
      <div style="font-size:11px;margin-bottom:8px;color:var(--text2)">共 ${t.length} 条记录</div>
      <table style="width:100%;font-size:11px;border-collapse:collapse">
        <tr style="border-bottom:1px solid var(--border);color:var(--text2);font-size:10px">
          <th style="padding:4px;text-align:left">状态</th><th style="padding:4px;text-align:left">类型</th><th style="padding:4px;text-align:left">账号</th><th style="padding:4px;text-align:left">机器</th><th style="padding:4px;text-align:left">消息</th><th style="padding:4px;text-align:right">耗时</th><th style="padding:4px;text-align:right">时间</th>
        </tr>
        ${t.slice(0,50).map(e=>`<tr style="border-bottom:1px solid var(--border)">
            <td style="padding:3px 4px">${e.status===`completed`?`✅`:e.status===`running`?`🟢`:e.status===`failed`?`❌`:e.status===`dispatching`?`📡`:`⏳`}</td>
            <td style="padding:3px 4px">${e.type||e.command_type||`?`}</td>
            <td style="padding:3px 4px">${(e.accounts||[e.account||``]).filter(Boolean).join(`,`)}</td>
            <td style="padding:3px 4px">${e.machine||`?`}</td>
            <td style="padding:3px 4px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${e.message||e.status||``}</td>
            <td style="padding:3px 4px;text-align:right">${e.elapsed_sec?e.elapsed_sec+`s`:`-`}</td>
            <td style="padding:3px 4px;text-align:right;font-size:10px;color:var(--text2)">${e.created_at?e.created_at.slice(11,19):``}</td>
          </tr>`).join(``)}
      </table>`}catch(t){e.innerHTML=`<div class="error">❌ ${t.message}</div>`}}export{e as loadView};