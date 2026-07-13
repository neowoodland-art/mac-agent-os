/**
 * characters.js — 🧑 角色管理（完整版）
 * 从 inline.js 迁移（原 loadCharacters + renderCharPortraitGallery）
 * 
 * 后端: GET /api/characters → {characters: {name: {...}}, active: '...'}
 *       GET /api/portrait-files/{name}/ → 定妆照图片
 */
const API = '';

const BODY_LABELS = {
  right_three_quarter:'右侧45°', right_side:'纯右侧面',
  back:'背面', front:'正面', side:'侧面'
};

export async function loadView(container) {
  container.innerHTML = '<div class="loading">⏳ 加载角色数据...</div>';
  try {
    const r = await fetch(`${API}/api/characters`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    const chars = d.characters || {};
    const active = d.active || '';
    const entries = Object.entries(chars);

    container.innerHTML = `
      <div style="padding:16px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <h2 style="font-size:18px;margin:0">🧑 角色管理 <span style="font-size:12px;color:var(--text2)">共 ${entries.length} 个角色</span></h2>
          <button onclick="switchView('char-gen')" style="background:var(--primary);color:#fff;border:none;padding:5px 14px;border-radius:6px;cursor:pointer;font-size:12px">+ 新建角色</button>
        </div>
        ${entries.length ? `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px">
          ${entries.map(([name, char]) => {
            const isActive = name === active;
            const refImgs = char.reference_images || {};
            const exprs = refImgs.expressions || {};
            const exprCount = Object.keys(exprs).length;
            const hasGrid = !!(refImgs.grid || refImgs.face_anchor || refImgs.baseline);
            const hasPortrait = !!(refImgs.portrait || refImgs.face_anchor);
            const hasBody = refImgs.body && Object.values(refImgs.body).some(Boolean);
            const hasRealPhoto = !!(refImgs.real_photo_fullbody || refImgs.real_photo_portrait);
            return `<div style="background:var(--bg2);border-radius:var(--radius);padding:20px;border:1px solid ${isActive ? 'var(--primary)' : 'var(--border)'}">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
                <div style="display:flex;align-items:center;gap:10px">
                  <div>
                    <div style="font-weight:600;font-size:16px">${name}</div>
                    <div style="font-size:11px;color:var(--text2)">${char.description||''}</div>
                  </div>
                </div>
                ${isActive ? `<span style="padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:rgba(99,102,241,.15);color:var(--primary);border:1px solid rgba(99,102,241,.3)" title="此角色为工作流编辑器中「角色节点」的默认选择">🔀 工作流默认</span>` : ''}
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;margin-bottom:10px;color:var(--text2)">
                <div>画风: ${char.art_style||'-'}</div>
                <div>音色: ${char.voice_style||'-'}</div>
                <div>性格: ${char.personality||'-'}</div>
                <div>BGM: ${char.default_bgm_style||'-'}</div>
              </div>
              ${char.prompt_template ? `<div style="margin-bottom:10px;font-size:11px;color:var(--text2)">
                <span style="font-weight:600">提示词模板:</span>
                <div style="background:var(--bg3);padding:8px;border-radius:6px;margin-top:4px;font-family:mono;font-size:10px;word-break:break-all">${Object.values(char.prompt_template).join(' | ')}</div>
              </div>` : ''}
              ${char.outfit_presets ? `<div style="margin-bottom:10px">
                <div style="font-size:11px;color:var(--text2);font-weight:600;margin-bottom:4px">穿搭预设</div>
                <div style="display:flex;gap:4px;flex-wrap:wrap">${Object.keys(char.outfit_presets).map(k => `<span style="background:var(--bg3);padding:2px 8px;border-radius:4px;font-size:10px">${k}</span>`).join('')}</div>
              </div>` : ''}
              <div style="font-size:11px;color:var(--text2)">
                <div>定妆照: ${hasGrid ? '✅ 已生成' : '❌ 未生成'} ${hasRealPhoto ? '·📷 真人参考照' : ''} ${hasBody ? `·${Object.keys(refImgs.body).length}个角度` : ''}</div>
                ${char.seed ? `<div>固定 Seed: ${char.seed}</div>` : ''}
              </div>
              ${hasBody ? renderCharPortraitGallery(refImgs, name, exprCount) : ''}
              ${!hasBody && hasRealPhoto ? `<div style="margin-top:8px;border-top:1px solid var(--border);padding-top:8px">
                <div style="font-size:10px;color:var(--text2)">📷 已上传真人参考照，点击「视频工厂→工作流编辑器」中的角色节点，生成定妆照</div>
              </div>` : ''}
              ${char.appearance && char.appearance.length ? `<div style="margin-top:8px;border-top:1px solid var(--border);padding-top:8px">
                <div style="font-size:11px;color:var(--text2);font-weight:600;margin-bottom:4px">外观特征</div>
                <ul style="margin:0;padding-left:16px;font-size:11px;color:var(--text2)">${char.appearance.map(a => `<li>${a}</li>`).join('')}</ul>
              </div>` : ''}
            </div>`;
          }).join('')}
        </div>` : '<div style="color:var(--text2);font-size:14px;padding:40px;text-align:center">暂无角色数据，点击上方「+ 新建角色」创建</div>'}
      </div>`;
  } catch(e) {
    container.innerHTML = `<div style="padding:20px;color:var(--red)">❌ 加载失败: ${e.message}</div>`;
  }
}

function renderCharPortraitGallery(refImgs, name, exprCount) {
  const body = refImgs.body || {};
  const faceAnchor = refImgs.face_anchor || refImgs.baseline || '';
  const charName = faceAnchor ? faceAnchor.split('/').slice(-2, -1)[0] : name;
  const base = charName ? API + '/api/portrait-files/' + encodeURIComponent(charName) : '';
  const items = [];
  if (faceAnchor) items.push({label:'正面基准', src: base + '/' + faceAnchor.split('/').pop(), isAnchor: true});
  for (const [k, p] of Object.entries(body)) {
    if (p) items.push({label: BODY_LABELS[k] || k, src: base + '/' + p.split('/').pop(), isAnchor: false});
  }
  // 文件系统路径转 API URL
  const _pathToUrl = (path) => {
    if (!path) return '';
    // 提取角色名和文件名: /xxx/xxx/{char_name}/{filename}
    const parts = path.replace(/\/$/, '').split('/');
    const fileName = parts.pop();
    const charName = parts.pop();
    return charName && fileName ? API + '/api/portrait-files/' + encodeURIComponent(charName) + '/' + encodeURIComponent(fileName) : '';
  };
  const realPhotoFull = refImgs.real_photo_fullbody || '';
  const realPhotoPortrait = refImgs.real_photo_portrait || '';
  const maxShow = Math.min(items.length + (realPhotoFull ? 1 : 0) + (realPhotoPortrait ? 1 : 0), 4);
  return `<div style="margin-top:10px;border-top:1px solid var(--border);padding-top:10px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
      <span style="font-size:12px;color:var(--text2);font-weight:600">📸 定妆照预览</span>
      <span style="font-size:10px;color:var(--text2)">${items.length} 个角度${exprCount ? ` + ${exprCount} 种表情` : ''}${maxShow < items.length ? ` (显示前${maxShow}个)` : ''}</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(${Math.min(maxShow,4)},1fr);gap:6px">
      ${items.slice(0, maxShow).map(item => `
        <div style="text-align:center">
          <div style="width:100%;aspect-ratio:9/16;background:var(--bg3);border-radius:4px;overflow:hidden;border:${item.isAnchor?'2px solid var(--primary)':'1px solid var(--border)'};display:flex;align-items:center;justify-content:center">
            <img src="${item.src}" style="width:100%;height:100%;object-fit:cover" onerror="this.parentElement.innerHTML='<span style=font-size:20px;opacity:.3>📷</span>'" loading="lazy">
          </div>
          <div style="font-size:9px;color:var(--text2);margin-top:2px">${item.label}</div>
        </div>
      `).join('')}
      ${realPhotoFull && items.length < maxShow ? `
        <div style="text-align:center">
          <div style="width:100%;aspect-ratio:9/16;background:var(--bg3);border-radius:4px;overflow:hidden;border:1px solid var(--border);display:flex;align-items:center;justify-content:center">
            <img src="${_pathToUrl(realPhotoFull)}" style="width:100%;height:100%;object-fit:cover" onerror="this.parentElement.innerHTML='<span style=font-size:20px;opacity:.3>📷</span>'" loading="lazy">
          </div>
          <div style="font-size:9px;color:var(--text2);margin-top:2px">真人参考(全身)</div>
        </div>` : ''}
      ${realPhotoPortrait && items.length + (realPhotoFull?1:0) < maxShow ? `
        <div style="text-align:center">
          <div style="width:100%;aspect-ratio:9/16;background:var(--bg3);border-radius:4px;overflow:hidden;border:1px solid var(--border);display:flex;align-items:center;justify-content:center">
            <img src="${_pathToUrl(realPhotoPortrait)}" style="width:100%;height:100%;object-fit:cover" onerror="this.parentElement.innerHTML='<span style=font-size:20px;opacity:.3>📷</span>'" loading="lazy">
          </div>
          <div style="font-size:9px;color:var(--text2);margin-top:2px">真人参考(肖像)</div>
        </div>` : ''}
    </div>
  </div>`;
}
