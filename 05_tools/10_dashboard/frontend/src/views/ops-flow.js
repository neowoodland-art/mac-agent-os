/**
 * ops-flow.js — 操作流程图视图
 * 
 * 展示抖音/小红书的状态机：节点=页面状态，连线=原子操作
 * 颜色标记：绿=已测试通过，橙=部分通过，灰=未测试
 * 
 * 数据来源：PLAN-atomic-ops-v2.md §三
 */
export async function loadView(container) {
  const uid = Math.random().toString(36).slice(2, 6);
  let platform = 'douyin';

  container.innerHTML = `
    <div style="padding:12px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">🧭 操作流程图</h2>
        <div style="display:flex;gap:6px">
          <button id="plat_douyin_${uid}" onclick="_switchPlat('douyin','${uid}')"
            style="background:#6366f1;color:#fff;border:none;padding:5px 14px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600">🎵 抖音</button>
          <button id="plat_xiaohongshu_${uid}" onclick="_switchPlat('xiaohongshu','${uid}')"
            style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:5px 14px;border-radius:6px;cursor:pointer;font-size:12px">📕 小红书</button>
        </div>
      </div>
      <div id="flowLegend_${uid}" style="display:flex;gap:16px;margin-bottom:10px;font-size:11px;color:var(--text2)">
        <span><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#22c55e;vertical-align:middle"></span> 已测试通过</span>
        <span><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#f59e0b;vertical-align:middle"></span> 部分通过</span>
        <span><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#6b7280;vertical-align:middle"></span> 未测试</span>
        <span><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#ef4444;vertical-align:middle"></span> 测试失败</span>
        <span style="margin-left:12px;border-left:1px solid var(--border);padding-left:12px">🖱 点击节点查看可用操作 | 点击连线查看转换条件</span>
      </div>
      <div id="flowCanvas_${uid}" style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:16px;min-height:400px;overflow:auto">
        <svg id="flowSvg_${uid}" width="900" height="450" style="display:block;margin:0 auto"></svg>
      </div>
      <div id="flowDetail_${uid}" style="margin-top:8px;background:var(--bg3);border-radius:var(--radius);padding:10px;border:1px solid var(--border);font-size:12px;display:none"></div>
    </div>`;

  // 绘制流程图
  renderFlow(platform, uid);

  // 挂载全局函数供 onclick
  window._switchPlat = function(p, uid) {
    document.getElementById(`plat_douyin_${uid}`).style.background = p === 'douyin' ? '#6366f1' : 'var(--bg3)';
    document.getElementById(`plat_douyin_${uid}`).style.color = p === 'douyin' ? '#fff' : 'var(--text)';
    document.getElementById(`plat_xiaohongshu_${uid}`).style.background = p === 'xiaohongshu' ? '#6366f1' : 'var(--bg3)';
    document.getElementById(`plat_xiaohongshu_${uid}`).style.color = p === 'xiaohongshu' ? '#fff' : 'var(--text)';
    renderFlow(p, uid);
  };
  window._flowNodeClick = function(nodeId, uid) {
    showNodeDetail(nodeId, uid);
  };
}

// ── 状态机定义 ──

const FLOWS = {
  douyin: {
    name: '抖音',
    nodes: [
      { id: 'grid', label: '首页精选', desc: '推荐feed流，视频卡片列表', icon: '🏠', status: 'partial',
        ops: ['scroll_feed(🟢)', 'open_video(🟢)', 'search(🟢)', 'goto_profile(🟡)', 'goto_branch(🟢)'] },
      { id: 'branch', label: '分支页', desc: '关注/朋友/同城等Tab页', icon: '📂', status: 'untested',
        ops: ['scroll_feed(🟢)', 'open_video(🟢)', 'search(🟢)'] },
      { id: 'player_modal', label: '视频播放(浮层)', desc: '半屏浮层播放，含评论区', icon: '▶️', status: 'partial',
        ops: ['like(🟢)', 'collect(🔴)', 'comment(🟢)', 'follow(🟡)', 'go_back(🟢)', 'next_video(🟢)'] },
      { id: 'player_full', label: '视频播放(全屏)', desc: '全屏/video/xxx页面', icon: '📺', status: 'partial',
        ops: ['like(🟢)', 'collect(🔴)', 'comment(🟢)', 'follow(🟡)', 'go_back(🟢)'] },
      { id: 'search', label: '搜索结果', desc: '搜索页，关键词结果列表', icon: '🔍', status: 'untested',
        ops: ['click_result(🟡)', 'scroll(🟢)', 'go_back(🟢)', 'search_user(🟡)'] },
      { id: 'profile', label: '个人主页', desc: '用户主页，含作品/粉丝/获赞', icon: '👤', status: 'untested',
        ops: ['read_field(🟢)', 'read_fans(🟡)', 'go_back(🟢)', 'follow(🟡)'] },
      { id: 'user_profile', label: '博主主页', desc: '其他博主的主页', icon: '🌟', status: 'untested',
        ops: ['read_field(🟢)', 'follow(🟡)', 'go_back(🟢)', 'collect_profile(🔴)'] },
    ],
    edges: [
      { from: 'grid', to: 'player_modal', action: 'open_video', status: 'partial', note: '点击feed卡片 → 浮层播放' },
      { from: 'grid', to: 'player_full', action: 'open_video_new', status: 'untested', note: '右键新标签打开' },
      { from: 'grid', to: 'search', action: 'search', status: 'untested', note: '点击搜索框→输入→搜索' },
      { from: 'grid', to: 'profile', action: 'goto_profile', status: 'untested', note: '点击头像→个人主页' },
      { from: 'grid', to: 'branch', action: 'goto_branch', status: 'untested', note: '切换Tab到关注/朋友' },
      { from: 'grid', to: 'user_profile', action: 'goto_user', status: 'untested', note: '点击博主头像→博主主页' },
      { from: 'player_modal', to: 'grid', action: 'go_back', status: 'partial', note: '关闭浮层→回首页' },
      { from: 'player_modal', to: 'player_modal', action: 'next_video', status: 'partial', note: '滑动/自动→下一个视频' },
      { from: 'player_modal', to: 'player_full', action: 'expand_full', status: 'untested', note: '全屏按钮' },
      { from: 'player_modal', to: 'profile', action: 'goto_author', status: 'untested', note: '点作者头像→作者主页' },
      { from: 'player_modal', to: 'comment', action: 'open_comments', status: 'untested', note: '展开全部评论' },
      { from: 'player_full', to: 'grid', action: 'go_back', status: 'untested', note: '返回→首页' },
      { from: 'player_full', to: 'player_full', action: 'next_video', status: 'untested', note: '下一个视频' },
      { from: 'search', to: 'player_modal', action: 'click_result', status: 'untested', note: '点搜索结果→视频' },
      { from: 'search', to: 'profile', action: 'click_user', status: 'untested', note: '点用户结果→个人主页' },
      { from: 'search', to: 'grid', action: 'go_back', status: 'untested', note: '取消搜索→回首页' },
      { from: 'profile', to: 'grid', action: 'go_back', status: 'untested', note: '返回→首页' },
      { from: 'user_profile', to: 'grid', action: 'go_back', status: 'untested', note: '返回→首页' },
    ]
  },
  xiaohongshu: {
    name: '小红书',
    nodes: [
      { id: 'grid', label: '首页推荐', desc: '双列瀑布流笔记列表', icon: '🏠', status: 'untested',
        ops: ['scroll_feed(🟡)', 'click_note(🟡)', 'search(🟡)', 'goto_profile(🟡)'] },
      { id: 'note_detail', label: '笔记详情', desc: '单篇笔记内容页', icon: '📄', status: 'untested',
        ops: ['like(🟡)', 'collect(🟡)', 'comment(🟡)', 'post_comment(🟡)', 'follow(🟡)', 'go_back(🟡)'] },
      { id: 'search', label: '搜索结果', desc: '搜索页，笔记/用户结果', icon: '🔍', status: 'untested',
        ops: ['click_result(🟡)', 'scroll(🟡)', 'go_back(🟡)'] },
      { id: 'profile', label: '个人主页', desc: '用户主页', icon: '👤', status: 'untested',
        ops: ['read_field(🟡)', 'go_back(🟡)'] },
    ],
    edges: [
      { from: 'grid', to: 'note_detail', action: 'click_note', status: 'untested', note: '点击笔记卡片→详情页' },
      { from: 'grid', to: 'search', action: 'search', status: 'untested', note: '搜索→搜结果页' },
      { from: 'grid', to: 'profile', action: 'goto_profile', status: 'untested', note: '点头像→个人主页' },
      { from: 'note_detail', to: 'grid', action: 'go_back', status: 'untested', note: '返回→首页' },
      { from: 'note_detail', to: 'note_detail', action: 'next_note', status: 'untested', note: '滑动→下一篇' },
      { from: 'search', to: 'note_detail', action: 'click_result', status: 'untested', note: '点结果→笔记详情' },
      { from: 'search', to: 'profile', action: 'click_user', status: 'untested', note: '点用户→个人主页' },
      { from: 'search', to: 'grid', action: 'go_back', status: 'untested', note: '返回→首页' },
      { from: 'profile', to: 'grid', action: 'go_back', status: 'untested', note: '返回→首页' },
    ]
  }
};

const STATUS_COLORS = {
  'tested': '#22c55e',
  'partial': '#f59e0b',
  'untested': '#6b7280',
  'failed': '#ef4444',
};

// ── 渲染流程图 ──

function renderFlow(platform, uid) {
  const svg = document.getElementById(`flowSvg_${uid}`);
  if (!svg) return;
  const flow = FLOWS[platform];
  if (!flow) return;

  // 定义节点位置（手动布局以确保清晰）
  const layout = {
    douyin: [
      { id: 'grid', x: 400, y: 40 },
      { id: 'branch', x: 150, y: 40 },
      { id: 'player_modal', x: 400, y: 170 },
      { id: 'player_full', x: 650, y: 170 },
      { id: 'search', x: 150, y: 300 },
      { id: 'profile', x: 400, y: 300 },
      { id: 'user_profile', x: 650, y: 300 },
    ],
    xiaohongshu: [
      { id: 'grid', x: 350, y: 60 },
      { id: 'note_detail', x: 350, y: 200 },
      { id: 'search', x: 150, y: 200 },
      { id: 'profile', x: 550, y: 200 },
    ]
  };

  const positions = layout[platform] || layout.douyin;
  const posMap = {};
  positions.forEach(p => { posMap[p.id] = { x: p.x, y: p.y }; });

  // 构建SVG
  let svgContent = '';

  // 1. 连线
  flow.edges.forEach(edge => {
    const from = posMap[edge.from];
    const to = posMap[edge.to];
    if (!from || !to) return;

    const color = STATUS_COLORS[edge.status] || '#6b7280';
    const isSelf = edge.from === edge.to;

    if (isSelf) {
      // 自环：画弧线在上方
      const rx = 40, ry = 30;
      svgContent += `
        <path d="M ${from.x} ${from.y - 22} Q ${from.x + rx} ${from.y - ry - 30} ${from.x} ${from.y - 22}"
          fill="none" stroke="${color}" stroke-width="2" stroke-dasharray="5,3"
          onclick="_flowEdgeClick('${edge.action}','${platform}','${uid}')" style="cursor:pointer"
          opacity="0.7"/>
        <text x="${from.x + rx + 10}" y="${from.y - ry - 20}" font-size="9" fill="${color}" text-anchor="middle"
          onclick="_flowEdgeClick('${edge.action}','${platform}','${uid}')" style="cursor:pointer">${edge.action}</text>`;
    } else {
      // 普通连线：贝塞尔曲线
      const mx = (from.x + to.x) / 2;
      const my = (from.y + to.y) / 2 - 15;

      svgContent += `
        <path d="M ${from.x} ${from.y + 22} Q ${(from.x+to.x)/2} ${(from.y+to.y)/2 - 30} ${to.x} ${to.y - 22}"
          fill="none" stroke="${color}" stroke-width="2" marker-end="url(#arrow_${uid})"
          onclick="_flowEdgeClick('${edge.action}','${platform}','${uid}')" style="cursor:pointer"
          opacity="0.7"/>
        <text x="${mx}" y="${my}" font-size="9" fill="${color}" text-anchor="middle"
          onclick="_flowEdgeClick('${edge.action}','${platform}','${uid}')" style="cursor:pointer">${edge.action}</text>`;
    }
  });

  // 箭头定义
  svgContent += `
    <defs>
      <marker id="arrow_${uid}" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#6b7280"/>
      </marker>
    </defs>`;

  // 2. 节点
  flow.nodes.forEach(node => {
    const pos = posMap[node.id];
    if (!pos) return;
    const color = STATUS_COLORS[node.status] || '#6b7280';

    svgContent += `
      <g onclick="_flowNodeClick('${node.id}','${uid}')" style="cursor:pointer">
        <!-- 节点背景 -->
        <rect x="${pos.x - 60}" y="${pos.y - 20}" width="120" height="40" rx="8" ry="8"
          fill="var(--bg3)" stroke="${color}" stroke-width="2.5"/>
        <!-- 状态指示灯 -->
        <circle cx="${pos.x - 50}" cy="${pos.y}" r="5" fill="${color}"/>
        <!-- 图标 -->
        <text x="${pos.x - 35}" y="${pos.y + 4}" font-size="13" text-anchor="middle">${node.icon}</text>
        <!-- 标签 -->
        <text x="${pos.x + 8}" y="${pos.y + 4}" font-size="11" fill="var(--text)" text-anchor="start"
          font-weight="600">${node.label}</text>
      </g>`;
  });

  svg.innerHTML = svgContent;
  document.getElementById(`flowDetail_${uid}`).style.display = 'none';

  // 挂载边点击函数
  window._flowEdgeClick = function(action, platform, uid) {
    const detailEl = document.getElementById(`flowDetail_${uid}`);
    if (!detailEl) return;
    detailEl.style.display = 'block';
    detailEl.innerHTML = `<span style="color:var(--text2)">🔗 操作: </span><strong>${action}</strong>
      <span style="color:var(--text2);margin-left:12px">平台: ${FLOWS[platform].name}</span>`;
  };
}

// ── 点击节点显示详情 ──

function showNodeDetail(nodeId, uid) {
  // 找当前平台
  let node = null;
  let platform = '';

  ['douyin', 'xiaohongshu'].forEach(p => {
    const found = FLOWS[p].nodes.find(n => n.id === nodeId);
    if (found) { node = found; platform = p; }
  });
  if (!node) return;

  const detailEl = document.getElementById(`flowDetail_${uid}`);
  if (!detailEl) return;
  detailEl.style.display = 'block';

  // 找到从该节点出发的边
  const outgoing = FLOWS[platform].edges.filter(e => e.from === nodeId);
  const incoming = FLOWS[platform].edges.filter(e => e.to === nodeId);

  const statusText = { tested: '✅ 已测试通过', partial: '🟡 部分通过', untested: '⚪ 未测试', failed: '🔴 测试失败' };

  let html = `
    <div style="display:flex;gap:16px;flex-wrap:wrap">
      <div style="flex:1;min-width:200px">
        <div style="font-size:14px;font-weight:600;margin-bottom:6px">${node.icon} ${node.label}</div>
        <div style="font-size:11px;color:var(--text2);margin-bottom:4px">${node.desc}</div>
        <div style="font-size:11px">${statusText[node.status] || '⚪ 未测试'}</div>
      </div>
      <div style="flex:1;min-width:200px">
        <div style="font-size:11px;font-weight:600;margin-bottom:4px">🚀 当前可用操作</div>
        ${node.ops.map(op => `<span style="display:inline-block;font-size:10px;background:var(--bg3);padding:2px 8px;border-radius:4px;margin:2px">${op}</span>`).join('')}
      </div>
      <div style="flex:1;min-width:150px">
        <div style="font-size:11px;font-weight:600;margin-bottom:4px">⬅ 到达路径 (${incoming.length})</div>
        ${incoming.length ? incoming.map(e => `<div style="font-size:10px;color:var(--text2);padding:1px 0">← ${e.action}</div>`).join('') : '<div style="font-size:10px;color:var(--text2)">起始页</div>'}
        <div style="font-size:11px;font-weight:600;margin-top:6px;margin-bottom:4px">➡ 可前往 (${outgoing.length})</div>
        ${outgoing.map(e => `<div style="font-size:10px;color:var(--text2);padding:1px 0">→ ${e.action} → ${FLOWS[platform].nodes.find(n => n.id === e.to)?.label || e.to}</div>`).join('')}
      </div>
    </div>`;

  detailEl.innerHTML = html;
}
