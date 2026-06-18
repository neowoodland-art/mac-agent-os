/**
 * Dashboard日志（Shell - 待实现）
 */
export async function loadView(container) {
  container.innerHTML = `
    <div style="padding:20px">
      <h2 style="font-size:18px;margin-bottom:12px">📊 Dashboard日志</h2>
      <div style="background:var(--bg2);border-radius:var(--radius);padding:40px;border:1px solid var(--border);text-align:center">
        <div style="font-size:48px;margin-bottom:16px">📊</div>
        <div style="font-size:16px;color:var(--text);margin-bottom:8px">日志聚合</div>
        <div style="font-size:12px;color:var(--text2)">Dashboard 日志聚合页面尚未实现。将汇总各模块的运行日志。</div>
      </div>
    </div>`;
}
