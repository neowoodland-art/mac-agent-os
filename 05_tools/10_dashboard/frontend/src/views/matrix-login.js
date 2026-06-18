/**
 * 登录管理视图（已迁移 - 跳转到信息采集）
 */
export async function loadView(container) {
  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:16px;border:1px solid var(--border);text-align:center">
        <div style="font-size:24px;margin-bottom:8px">🔑</div>
        <div style="font-size:14px;font-weight:600;margin-bottom:4px">登录管理已合并到信息采集</div>
        <div style="font-size:12px;color:var(--text2);margin-bottom:12px">登录 → 采集是同一流程，请前往「信息采集」页面操作</div>
        <button onclick="switchView('matrix-collect')" style="background:var(--primary);color:#fff;border:none;padding:8px 24px;border-radius:6px;cursor:pointer;font-size:13px">→ 前往信息采集</button>
      </div>
    </div>`;
}
