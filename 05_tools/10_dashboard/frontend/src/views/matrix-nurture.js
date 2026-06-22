/**
 * matrix-nurture.js — 养号执行（壳层）
 * 委托 inline.js 渲染
 */
export async function loadView(container) {
  container.innerHTML = `<div id="view-matrix-nurture-slot"><div class="loading">⏳ 加载养号执行...</div></div>`;
  window.loadMatrixNurture();
}
