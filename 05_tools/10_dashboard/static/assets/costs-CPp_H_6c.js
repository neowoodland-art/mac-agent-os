async function e(e){e.innerHTML=`
    <div style="padding:16px">
      <h2 style="font-size:18px;margin-bottom:12px">💰 费用统计</h2>
      <div id="costSummary"></div>
      <div id="costBreakdown" style="margin-top:12px"></div>
    </div>`;try{let e=await(await fetch(`/api/summary`)).json(),t=e.ave||e;document.getElementById(`costSummary`).innerHTML=`
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
        <div style="background:var(--bg2);border-radius:var(--radius);padding:16px;border:1px solid var(--border);text-align:center">
          <div style="font-size:11px;color:var(--text2)">总费用</div>
          <div style="font-size:24px;font-weight:700">¥${(t.total_cost||0).toFixed(2)}</div>
        </div>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:16px;border:1px solid var(--border);text-align:center">
          <div style="font-size:11px;color:var(--text2)">本月费用</div>
          <div style="font-size:24px;font-weight:700">¥${(t.month_cost||0).toFixed(2)}</div>
        </div>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:16px;border:1px solid var(--border);text-align:center">
          <div style="font-size:11px;color:var(--text2)">平均费用/生产</div>
          <div style="font-size:24px;font-weight:700">¥${t.total_productions?(t.total_cost/t.total_productions).toFixed(2):`0.00`}</div>
        </div>
      </div>`;let n=await(await fetch(`/api/costs/breakdown`)).json();if(!n.length){document.getElementById(`costBreakdown`).innerHTML=`<div class="error" style="padding:40px">暂无费用数据</div>`;return}let r=Math.max(...n.map(e=>e.total_cost),1),i=[`#6366f1`,`#22c55e`,`#f59e0b`,`#ef4444`,`#3b82f6`];document.getElementById(`costBreakdown`).innerHTML=`
      <div style="background:var(--bg2);border-radius:var(--radius);padding:16px;border:1px solid var(--border)">
        <div style="font-size:14px;font-weight:600;margin-bottom:12px">按策略统计</div>
        ${n.map((e,t)=>`
          <div style="margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:2px">
              <span>${e.name||e.strategy}</span>
              <span>¥${(e.total_cost||0).toFixed(2)} (${e.count||0} 次)</span>
            </div>
            <div style="height:8px;background:var(--bg3);border-radius:4px;overflow:hidden">
              <div style="height:100%;width:${((e.total_cost||0)/r*100).toFixed(1)}%;background:${i[t%i.length]};border-radius:4px;transition:width .3s"></div>
            </div>
          </div>
        `).join(``)}
      </div>`}catch(t){e.innerHTML=`<div class="error">❌ 加载失败: ${t.message}</div>`}}export{e as loadView};