/**
 * matrix-sms-proxy.js — 短信与代理管理（壳层）
 * 
 * 创建 inline 函数需要的 DOM 结构，委托 inline.js 渲染
 */
export async function loadView(container) {
  container.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h2 style="font-size:18px">📡 短信与代理</h2>
      <button onclick="loadSmsProxy()" style="background:transparent;color:var(--text);border:1px solid var(--border);padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px">🔄 刷新</button>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-size:13px;font-weight:600;margin-bottom:8px">📱 短信接收</div>
        <div id="smsConfigPanel" style="font-size:12px">加载中...</div>
        <hr style="border-color:var(--border);margin:8px 0">
        <div style="font-size:11px;color:var(--text2);margin-bottom:4px">选择账号 <span style="font-size:10px;color:#6366f1">(输入手机号快速匹配)</span></div>
        <div style="display:flex;gap:4px;margin-bottom:4px">
          <div style="flex:1;position:relative">
            <input id="smsAccountSearch" placeholder="输入手机号/昵称搜索..." autocomplete="off"
              oninput="smsFilterAccounts()" onfocus="smsFilterAccounts()"
              style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px;border-radius:5px;font-size:12px">
            <select id="smsAccountSelect" onchange="smsSelectAccount()" size="4"
              style="display:none;position:absolute;top:100%;left:0;right:0;z-index:10;background:var(--bg2);border:1px solid var(--primary);color:var(--text);padding:2px;border-radius:5px;font-size:11px;max-height:150px">
              <option value="">— 选择账号 —</option>
            </select>
          </div>
          <button onclick="smsCheckSelected()" style="background:var(--primary);color:#fff;border:none;padding:5px 12px;border-radius:5px;cursor:pointer;font-size:12px">📥 查短信</button>
        </div>
        <div id="smsMessages" style="font-size:11px;margin-top:4px;max-height:200px;overflow-y:auto"></div>
        <div id="collectProfileStatus" style="font-size:11px;margin-top:2px"></div>
      </div>
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-size:13px;font-weight:600;margin-bottom:8px">🖥️ 代理配置</div>
        <div id="proxyList" style="font-size:12px">加载中...</div>
        <hr style="border-color:var(--border);margin:8px 0">
        <div style="font-size:11px;color:var(--text2);margin-bottom:4px">账号概览</div>
        <div id="smsAccountsOverview" style="font-size:12px">加载中...</div>
      </div>
    </div>
    <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
      <div style="font-size:13px;font-weight:600;margin-bottom:8px">🔧 API 配置</div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <input id="smsNewPhone" placeholder="新手机号" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px;width:140px">
        <input id="smsApiKey" placeholder="API Key" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:11px;width:200px">
        <button onclick="smsUpdateAndTest()" style="background:#22c55e;color:#000;border:none;padding:5px 12px;border-radius:5px;cursor:pointer;font-size:12px">💾 保存并测试</button>
      </div>
      <div id="smsQueryPanel" style="font-size:11px;margin-top:4px"></div>
    </div>
  `;
  // 先预加载账号列表到缓存，确保输入框匹配立即可用
  fetch('/api/matrix/sms/accounts').then(function(r) { return r.json(); }).then(function(d) {
    var accts = d.accounts || [];
    if (!window._smsFetchedOnce) {
      window._smsAccountOptions = accts;
      window._smsFetchedOnce = true;
    }
  }).catch(function() { /* 静默失败，loadSmsProxy 会重试 */ });

  window.loadSmsProxy();
}
