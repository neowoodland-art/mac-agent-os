export async function loadView(container) {
  container.innerHTML = `<div class="view-loading"><div class="spinner"></div><p>加载角色生成器...</p></div>`;

  try {
    // 1. Fetch available generators
    const genRes = await fetch('/api/matrix/characters/generators');
    if (!genRes.ok) throw new Error(`获取生成器列表失败: ${genRes.status}`);
    const generators = await genRes.json();

    // 2. Render UI
    container.innerHTML = `
      <div class="view-header">
        <h2>🎭 角色生成</h2>
      </div>
      <div class="char-gen-form">
        <div class="form-group">
          <label for="gen-select">生成器</label>
          <select id="gen-select">
            ${Array.isArray(generators) && generators.length > 0
              ? generators.map(g => `<option value="${g.id || g.name}">${g.name || g.id}</option>`).join('')
              : '<option value="">-- 无可用生成器 --</option>'}
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
    `;

    // 3. Wire up generate button
    const submitBtn = container.querySelector('#gen-submit-btn');
    const resultArea = container.querySelector('#gen-result-area');
    const resultContent = container.querySelector('#gen-result-content');

    submitBtn.addEventListener('click', async () => {
      const genId = container.querySelector('#gen-select').value;
      const prompt = container.querySelector('#gen-prompt').value.trim();
      const count = parseInt(container.querySelector('#gen-count').value, 10) || 1;

      if (!genId) {
        alert('请选择一个生成器');
        return;
      }
      if (!prompt) {
        alert('请输入角色描述');
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = '生成中...';
      resultArea.style.display = 'block';
      resultContent.innerHTML = `<div class="view-loading"><div class="spinner"></div><p>正在生成角色...</p></div>`;

      try {
        const genRes = await fetch('/api/matrix/characters/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ generator: genId, prompt, count })
        });

        if (!genRes.ok) {
          const errText = await genRes.text().catch(() => '');
          throw new Error(`生成失败: ${genRes.status} ${errText}`);
        }

        const result = await genRes.json();
        const characters = Array.isArray(result) ? result : (result.characters || result.data || [result]);

        if (characters.length === 0) {
          resultContent.innerHTML = `<div class="empty-state">生成结果为空</div>`;
        } else {
          resultContent.innerHTML = characters.map((ch, idx) => `
            <div class="char-card">
              <div class="char-card-header">
                <strong>#${idx + 1}</strong>
                <span class="char-name">${ch.name || ch.character_name || '未命名'}</span>
              </div>
              <div class="char-card-body">
                <p>${(ch.description || ch.bio || ch.prompt || JSON.stringify(ch)).replace(/\n/g, '<br>')}</p>
              </div>
            </div>
          `).join('');
        }
      } catch (err) {
        resultContent.innerHTML = `<div class="error-message">${err.message}</div>`;
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '开始生成';
      }
    });

  } catch (err) {
    container.innerHTML = `<div class="view-error"><h3>❌ 加载失败</h3><p>${err.message}</p></div>`;
  }
}
