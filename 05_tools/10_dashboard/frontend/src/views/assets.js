/**
 * 资产视图（已迁移）
 */
let _assetSearchTimer = null;
export async function loadView(container) {
  container.innerHTML = `
    <div style="padding:16px">
      <h2 style="font-size:18px;margin-bottom:12px">📦 资产库</h2>
      <div class="filter-bar">
        <select id="assetTypeFilter">
          <option value="">全部类型</option>
          <option value="generated_clip">视频片段</option>
          <option value="character_sheet">定妆照</option>
          <option value="bgm">背景音乐</option>
          <option value="script">脚本</option>
        </select>
        <input id="assetSearch" placeholder="搜索标签..." oninput="window._debounceAssetSearch()">
        <button onclick="window._loadAssets()">查询</button>
      </div>
      <div id="assetList" style="margin-top:8px"><div class="loading">加载中...</div></div>
    </div>`;

  window._loadAssets = window._loadAssets || async function() {
    const el = document.getElementById('assetList');
    if (!el) return;
    el.innerHTML = '<div class="loading">加载中...</div>';
    try {
      const type = document.getElementById('assetTypeFilter')?.value || '';
      const tag = document.getElementById('assetSearch')?.value || '';
      const params = new URLSearchParams({ limit: 50 });
      if (type) params.set('type', type);
      if (tag) params.set('tag', tag);
      const r = await fetch(`/api/assets?${params}`);
      const data = await r.json();
      if (!data.length) {
        el.innerHTML = '<div class="error" style="padding:40px">暂无资产</div>';
        return;
      }
      el.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px">
        ${data.map(a => `<div style="background:var(--bg2);border-radius:var(--radius);padding:12px;border:1px solid var(--border)">
          <div style="font-size:11px;color:var(--text2);margin-bottom:4px">${a.asset_type || '-'}</div>
          <div style="font-size:12px;font-weight:500">${(a.name || a.file_path || '-').slice(0, 40)}</div>
          <div style="font-size:10px;color:var(--text2);margin-top:2px">${a.source || ''}${a.file_size ? ' · ' + (a.file_size / 1024).toFixed(0) + 'KB' : ''}</div>
          ${a.tags ? `<div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap">${a.tags.split(',').map(t => `<span style="background:var(--bg3);padding:1px 6px;border-radius:4px;font-size:10px">${t}</span>`).join('')}</div>` : ''}
        </div>`).join('')}
      </div>`;
    } catch (e) {
      el.innerHTML = `<div class="error">❌ 加载失败</div>`;
    }
  };
  window._debounceAssetSearch = window._debounceAssetSearch || function() {
    clearTimeout(_assetSearchTimer);
    _assetSearchTimer = setTimeout(() => window._loadAssets(), 400);
  };

  window._loadAssets();
}
