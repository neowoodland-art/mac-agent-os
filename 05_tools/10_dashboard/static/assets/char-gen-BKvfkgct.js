async function e(e){e.innerHTML=`<div class="view-loading"><div class="spinner"></div><p>加载角色生成器...</p></div>`;try{let t=await fetch(`/api/matrix/characters/generators`);if(!t.ok)throw Error(`获取生成器列表失败: ${t.status}`);let n=await t.json();e.innerHTML=`
      <div class="view-header">
        <h2>🎭 角色生成</h2>
      </div>
      <div class="char-gen-form">
        <div class="form-group">
          <label for="gen-select">生成器</label>
          <select id="gen-select">
            ${Array.isArray(n)&&n.length>0?n.map(e=>`<option value="${e.id||e.name}">${e.name||e.id}</option>`).join(``):`<option value="">-- 无可用生成器 --</option>`}
          </select>
        </div>
        <div class="form-group">
          <label for="gen-prompt">角色描述 / 提示词</label>
          <textarea id="gen-prompt" rows="4" placeholder="输入角色描述，例如：一位来自未来的 AI 助手..."></textarea>
        </div>
        <div class="form-group">
          <label for="gen-count">生成数量</label>
          <input type="number" id="gen-count" value="1" min="1" max="10" />
        </div>
        <button id="gen-submit-btn" class="btn btn-primary">开始生成</button>
      </div>
      <div id="gen-result-area" class="gen-result-area" style="display:none;">
        <h3>生成结果</h3>
        <div id="gen-result-content"></div>
      </div>
    `;let r=e.querySelector(`#gen-submit-btn`),i=e.querySelector(`#gen-result-area`),a=e.querySelector(`#gen-result-content`);r.addEventListener(`click`,async()=>{let t=e.querySelector(`#gen-select`).value,n=e.querySelector(`#gen-prompt`).value.trim(),o=parseInt(e.querySelector(`#gen-count`).value,10)||1;if(!t){alert(`请选择一个生成器`);return}if(!n){alert(`请输入角色描述`);return}r.disabled=!0,r.textContent=`生成中...`,i.style.display=`block`,a.innerHTML=`<div class="view-loading"><div class="spinner"></div><p>正在生成角色...</p></div>`;try{let e=await fetch(`/api/matrix/characters/generate`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({generator:t,prompt:n,count:o})});if(!e.ok){let t=await e.text().catch(()=>``);throw Error(`生成失败: ${e.status} ${t}`)}let r=await e.json(),i=Array.isArray(r)?r:r.characters||r.data||[r];i.length===0?a.innerHTML=`<div class="empty-state">生成结果为空</div>`:a.innerHTML=i.map((e,t)=>`
            <div class="char-card">
              <div class="char-card-header">
                <strong>#${t+1}</strong>
                <span class="char-name">${e.name||e.character_name||`未命名`}</span>
              </div>
              <div class="char-card-body">
                <p>${(e.description||e.bio||e.prompt||JSON.stringify(e)).replace(/\n/g,`<br>`)}</p>
              </div>
            </div>
          `).join(``)}catch(e){a.innerHTML=`<div class="error-message">${e.message}</div>`}finally{r.disabled=!1,r.textContent=`开始生成`}})}catch(t){e.innerHTML=`<div class="view-error"><h3>❌ 加载失败</h3><p>${t.message}</p></div>`}}export{e as loadView};