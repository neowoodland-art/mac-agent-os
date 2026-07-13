var e=``,t={right_three_quarter:`右侧45°`,right_side:`纯右侧面`,back:`背面`,front:`正面`,side:`侧面`};async function n(t){t.innerHTML=`<div class="loading">⏳ 加载角色数据...</div>`;try{let n=await fetch(`${e}/api/characters`);if(!n.ok)throw Error(`HTTP ${n.status}`);let i=await n.json(),a=i.characters||{},o=i.active||``,s=Object.entries(a);t.innerHTML=`
      <div style="padding:16px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <h2 style="font-size:18px;margin:0">🧑 角色管理 <span style="font-size:12px;color:var(--text2)">共 ${s.length} 个角色</span></h2>
          <button onclick="switchView('char-gen')" style="background:var(--primary);color:#fff;border:none;padding:5px 14px;border-radius:6px;cursor:pointer;font-size:12px">+ 新建角色</button>
        </div>
        ${s.length?`<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px">
          ${s.map(([e,t])=>{let n=e===o,i=t.reference_images||{},a=i.expressions||{},s=Object.keys(a).length,c=!!(i.grid||i.face_anchor||i.baseline);i.portrait||i.face_anchor;let l=i.body&&Object.values(i.body).some(Boolean),u=!!(i.real_photo_fullbody||i.real_photo_portrait);return`<div style="background:var(--bg2);border-radius:var(--radius);padding:20px;border:1px solid ${n?`var(--primary)`:`var(--border)`}">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
                <div style="display:flex;align-items:center;gap:10px">
                  <div>
                    <div style="font-weight:600;font-size:16px">${e}</div>
                    <div style="font-size:11px;color:var(--text2)">${t.description||``}</div>
                  </div>
                </div>
                ${n?`<span style="padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:rgba(99,102,241,.15);color:var(--primary);border:1px solid rgba(99,102,241,.3)" title="此角色为工作流编辑器中「角色节点」的默认选择">🔀 工作流默认</span>`:``}
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;margin-bottom:10px;color:var(--text2)">
                <div>画风: ${t.art_style||`-`}</div>
                <div>音色: ${t.voice_style||`-`}</div>
                <div>性格: ${t.personality||`-`}</div>
                <div>BGM: ${t.default_bgm_style||`-`}</div>
              </div>
              ${t.prompt_template?`<div style="margin-bottom:10px;font-size:11px;color:var(--text2)">
                <span style="font-weight:600">提示词模板:</span>
                <div style="background:var(--bg3);padding:8px;border-radius:6px;margin-top:4px;font-family:mono;font-size:10px;word-break:break-all">${Object.values(t.prompt_template).join(` | `)}</div>
              </div>`:``}
              ${t.outfit_presets?`<div style="margin-bottom:10px">
                <div style="font-size:11px;color:var(--text2);font-weight:600;margin-bottom:4px">穿搭预设</div>
                <div style="display:flex;gap:4px;flex-wrap:wrap">${Object.keys(t.outfit_presets).map(e=>`<span style="background:var(--bg3);padding:2px 8px;border-radius:4px;font-size:10px">${e}</span>`).join(``)}</div>
              </div>`:``}
              <div style="font-size:11px;color:var(--text2)">
                <div>定妆照: ${c?`✅ 已生成`:`❌ 未生成`} ${u?`·📷 真人参考照`:``} ${l?`·${Object.keys(i.body).length}个角度`:``}</div>
                ${t.seed?`<div>固定 Seed: ${t.seed}</div>`:``}
              </div>
              ${l?r(i,e,s):``}
              ${!l&&u?`<div style="margin-top:8px;border-top:1px solid var(--border);padding-top:8px">
                <div style="font-size:10px;color:var(--text2)">📷 已上传真人参考照，点击「视频工厂→工作流编辑器」中的角色节点，生成定妆照</div>
              </div>`:``}
              ${t.appearance&&t.appearance.length?`<div style="margin-top:8px;border-top:1px solid var(--border);padding-top:8px">
                <div style="font-size:11px;color:var(--text2);font-weight:600;margin-bottom:4px">外观特征</div>
                <ul style="margin:0;padding-left:16px;font-size:11px;color:var(--text2)">${t.appearance.map(e=>`<li>${e}</li>`).join(``)}</ul>
              </div>`:``}
            </div>`}).join(``)}
        </div>`:`<div style="color:var(--text2);font-size:14px;padding:40px;text-align:center">暂无角色数据，点击上方「+ 新建角色」创建</div>`}
      </div>`}catch(e){t.innerHTML=`<div style="padding:20px;color:var(--red)">❌ 加载失败: ${e.message}</div>`}}function r(e,n,r){let i=e.body||{},a=e.face_anchor||e.baseline||``,o=a?a.split(`/`).slice(-2,-1)[0]:n,s=o?`/api/portrait-files/`+encodeURIComponent(o):``,c=[];a&&c.push({label:`正面基准`,src:s+`/`+a.split(`/`).pop(),isAnchor:!0});for(let[e,n]of Object.entries(i))n&&c.push({label:t[e]||e,src:s+`/`+n.split(`/`).pop(),isAnchor:!1});let l=e=>{if(!e)return``;let t=e.replace(/\/$/,``).split(`/`),n=t.pop(),r=t.pop();return r&&n?`/api/portrait-files/`+encodeURIComponent(r)+`/`+encodeURIComponent(n):``},u=e.real_photo_fullbody||``,d=e.real_photo_portrait||``,f=Math.min(c.length+ +!!u+ +!!d,4);return`<div style="margin-top:10px;border-top:1px solid var(--border);padding-top:10px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
      <span style="font-size:12px;color:var(--text2);font-weight:600">📸 定妆照预览</span>
      <span style="font-size:10px;color:var(--text2)">${c.length} 个角度${r?` + ${r} 种表情`:``}${f<c.length?` (显示前${f}个)`:``}</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(${Math.min(f,4)},1fr);gap:6px">
      ${c.slice(0,f).map(e=>`
        <div style="text-align:center">
          <div style="width:100%;aspect-ratio:9/16;background:var(--bg3);border-radius:4px;overflow:hidden;border:${e.isAnchor?`2px solid var(--primary)`:`1px solid var(--border)`};display:flex;align-items:center;justify-content:center">
            <img src="${e.src}" style="width:100%;height:100%;object-fit:cover" onerror="this.parentElement.innerHTML='<span style=font-size:20px;opacity:.3>📷</span>'" loading="lazy">
          </div>
          <div style="font-size:9px;color:var(--text2);margin-top:2px">${e.label}</div>
        </div>
      `).join(``)}
      ${u&&c.length<f?`
        <div style="text-align:center">
          <div style="width:100%;aspect-ratio:9/16;background:var(--bg3);border-radius:4px;overflow:hidden;border:1px solid var(--border);display:flex;align-items:center;justify-content:center">
            <img src="${l(u)}" style="width:100%;height:100%;object-fit:cover" onerror="this.parentElement.innerHTML='<span style=font-size:20px;opacity:.3>📷</span>'" loading="lazy">
          </div>
          <div style="font-size:9px;color:var(--text2);margin-top:2px">真人参考(全身)</div>
        </div>`:``}
      ${d&&c.length+ +!!u<f?`
        <div style="text-align:center">
          <div style="width:100%;aspect-ratio:9/16;background:var(--bg3);border-radius:4px;overflow:hidden;border:1px solid var(--border);display:flex;align-items:center;justify-content:center">
            <img src="${l(d)}" style="width:100%;height:100%;object-fit:cover" onerror="this.parentElement.innerHTML='<span style=font-size:20px;opacity:.3>📷</span>'" loading="lazy">
          </div>
          <div style="font-size:9px;color:var(--text2);margin-top:2px">真人参考(肖像)</div>
        </div>`:``}
    </div>
  </div>`}export{n as loadView};