/**
 * 工作流视图（已迁移 - 简版）
 */
export async function loadView(container) {
  container.innerHTML = `
    <div style="padding:16px">
      <div style="display:flex;flex-direction:column;min-height:500px">
        <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
          <span style="font-size:14px;font-weight:600">🔀 工作流</span>
          <div style="flex:1"></div>
          <button onclick="switchView('workflow')" style="background:var(--primary);color:#fff;border:none;padding:3px 12px;border-radius:4px;cursor:pointer;font-size:12px">▶ 打开工作流</button>
        </div>
        <div style="background:var(--bg2);border-radius:var(--radius);padding:40px;border:1px solid var(--border);text-align:center;flex:1;display:flex;align-items:center;justify-content:center;flex-direction:column">
          <div style="font-size:48px;margin-bottom:16px">🔀</div>
          <div style="font-size:16px;color:var(--text);margin-bottom:8px">工作流编辑器</div>
          <div style="font-size:12px;color:var(--text2);max-width:400px">从上方拖拽节点到画布，或选择模板开始。工作流引擎功能完整实现中。</div>
        </div>
      </div>
    </div>`;
}
