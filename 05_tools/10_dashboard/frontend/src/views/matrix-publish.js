/**
 * 内容发布视图（已迁移 - 简版）
 */
export async function loadView(container) {
  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:var(--radius);padding:40px;border:1px solid var(--border);text-align:center">
        <div style="font-size:48px;margin-bottom:16px">📤</div>
        <div style="font-size:16px;color:var(--text);margin-bottom:8px">内容发布</div>
        <div style="font-size:12px;color:var(--text2)">多平台内容发布功能正在开发中...</div>
      </div>
    </div>`;
}
