/**
 * 评论互动视图 (interact)
 * 合并定向评论 + 收藏点赞 + 三级接力 + 热评互动
 *
 * 调用规范:
 *   POST /api/ops/run {type:'interact', accounts, params}
 *   → CommandBus → CMD_REGISTRY["interact"] → mc run --blueprints=interact_*
 *
 * 策略:
 *   - comment:  定向评论（指定视频发评论）
 *   - chain:    三级接力（A评→B回复→C再回复）
 *   - like:     点赞互动（点赞视频+评论+关注）
 *   - hot:      热评互动（在热评下回复）
 */

import { apiRequest, confirmExecute } from '../router.js';
import { createAccountSelector } from '../components/account-selector.js';

let _selector = null;

export async function loadView(container) {
  const uid = container.id || 'interact';
  const data = await apiRequest('/matrix/accounts');
  const allAccts = Array.isArray(data) ? data : (data.accounts || []);

  container.innerHTML = `
    <div style="padding:16px">
      <div style="background:var(--bg2);border-radius:10px;padding:12px;border:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px;margin-bottom:8px">💬 评论互动 <span style="font-size:10px;color:var(--text2);font-weight:400">定向评论 / 三级接力 / 点赞 / 热评</span></div>
        <div id="acctList_${uid}" style="margin-bottom:6px"></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <label style="font-size:11px;color:var(--text2)">策略:
            <select id="istrategy_${uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="comment">💬 定向评论</option>
              <option value="chain">🔗 三级接力</option>
              <option value="like">❤️ 点赞互动</option>
              <option value="hot">🔥 热评互动</option>
            </select>
          </label>
          <label style="font-size:11px;color:var(--text2)">链接:
            <input id="iurl_${uid}" placeholder="视频链接" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px;width:200px">
          </label>
          <label style="font-size:11px;color:var(--text2)">语料:
            <select id="icorpus_${uid}" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 6px;border-radius:4px;font-size:11px">
              <option value="food">🍜 美食</option>
              <option value="travel">✈️ 旅行</option>
              <option value="tech">💻 科技</option>
              <option value="lifestyle">🌿 生活</option>
              <option value="emotion">💛 情感</option>
              <option value="">🎲 随机</option>
            </select>
          </label>
          <span id="selCount_${uid}" style="font-size:10px;color:var(--text2)">已选 0 个</span>
          <button onclick="window._interactPreflight('${uid}')" style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">🔍 预检</button>
          <button onclick="window._interactExec('${uid}')" style="background:var(--primary);color:#fff;border:none;padding:4px 14px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600">🚀 提交互动</button>
        </div>
        <div id="planPreview_${uid}" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:200px;overflow-y:auto;font-family:monospace;white-space:pre-wrap;display:none"></div>
        <div id="log_${uid}" style="font-size:10px;background:var(--bg2);border-radius:6px;padding:6px;margin-top:4px;max-height:250px;overflow-y:auto;font-family:monospace;white-space:pre-wrap"></div>
      </div>
    </div>`;

  _selector = createAccountSelector(document.getElementById(`acctList_${uid}`), {
    accounts: allAccts,
    checkAll: false,
    height: '300px',
  });

  document.getElementById(`selCount_${uid}`).textContent = '已选 ' + (_selector?.getCount() || 0) + ' 个';

  if (!window._interactRegistered) {
    window._interactRegistered = true;

    window._interactPreflight = async function(uid) {
      const log = document.getElementById(`log_${uid}`);
      const plan = document.getElementById(`planPreview_${uid}`);
      const url = document.getElementById(`iurl_${uid}`)?.value?.trim();
      if (log) log.textContent = '🔍 预检中...\n';
      if (plan) plan.style.display = 'none';
      if (!url) { if (log) log.textContent += '❌ 请填写视频链接\n'; return; }
      const selected = _selector?.getSelected() || [];
      if (!selected.length) { if (log) log.textContent += '❌ 请选择账号\n'; return; }
      try {
        const d = await apiRequest('/ops/run', {
          method: 'POST',
          body: JSON.stringify({
            type: 'interact',
            accounts: selected.map(s => s.id),
            params: {
              url,
              strategy: document.getElementById(`istrategy_${uid}`)?.value || 'comment',
              corpus: document.getElementById(`icorpus_${uid}`)?.value || '',
              rounds: 1,
              dry_run: true,
            },
          }),
        });
        if (log) {
          log.textContent += `✅ 预检完成\n`;
          log.textContent += `   总账号: ${selected.length}\n`;
          log.textContent += `   策略: ${document.getElementById('istrategy_${uid}')?.value || 'comment'}\n`;
        }
        if (plan) {
          plan.innerHTML = `<strong>📋 执行计划</strong>\n${JSON.stringify(d.commands || [], null, 2)}`;
          plan.style.display = 'block';
        }
      } catch(e) {
        if (log) log.textContent += '❌ ' + e.message + '\n';
      }
    };

    window._interactExec = async function(uid) {
      const selected = _selector?.getSelected() || [];
      if (!selected.length) { alert('请先选择账号'); return; }
      const url = document.getElementById(`iurl_${uid}`)?.value?.trim();
      if (!url) { alert('请填写视频链接'); return; }
      const log = document.getElementById(`log_${uid}`);
      const strategy = document.getElementById(`istrategy_${uid}`)?.value || 'comment';
      const corpus = document.getElementById(`icorpus_${uid}`)?.value || '';

      const label = {comment:'定向评论', chain:'三级接力', like:'点赞互动', hot:'热评互动'}[strategy] || strategy;
      if (!await confirmExecute(`${label} ${selected.length} 个账号？`, `链接: ${url.slice(0,50)}...`)) return;

      if (log) log.textContent = `🚀 ${label} ${selected.length} 个账号...\n`;
      try {
        // 按机器分组，每机一条命令（复用采集模式）
        const byMachine = {};
        selected.forEach(s => {
          const m = s.machine || 'unknown';
          if (!byMachine[m]) byMachine[m] = [];
          byMachine[m].push(s.id);
        });
        const totalCmds = Object.keys(byMachine).length;
        let done = 0;
        const allResults = [];

        for (const [machine, ids] of Object.entries(byMachine)) {
          const d = await apiRequest('/ops/run', {
            method: 'POST',
            body: JSON.stringify({
              type: 'interact',
              accounts: ids,
              params: { url, strategy, corpus, rounds: 1 },
            }),
          });
          done++;
          allResults.push(d);
          if (log) {
            log.textContent += `📦 [${machine}] ${ids.join(',')}: ${d.status || 'OK'} (${done}/${totalCmds})\n`;
            if (d.commands) {
              d.commands.forEach(c => {
                log.textContent += `  → ${c.machine}: ${c.accounts?.join(',')} 蓝图=${c.command?.match(/blueprints=(\S+)/)?.[1] || '?'}\n`;
              });
            }
          }
        }
        if (log) log.textContent += '\n✅ 全部提交完成\n';
      } catch(e) {
        if (log) log.textContent += '❌ ' + e.message + '\n';
      }
    };
  }
}
