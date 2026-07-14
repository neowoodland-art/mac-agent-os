// views/ave-render.js
export async function loadView(container) {
  container.innerHTML = `
    <div style="padding:40px;text-align:center;color:var(--text2)">
      <div style="font-size:32px;margin-bottom:12px">🎬</div>
      <div style="font-size:16px;font-weight:600;margin-bottom:8px">渲染任务</div>
      <div style="font-size:12px;opacity:.7">功能开发中，敬请期待</div>
    </div>`;
}
