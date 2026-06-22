async function e(e){let t=Math.random().toString(36).slice(2,6);e.innerHTML=`
    <div style="padding:12px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">🧭 操作流程图</h2>
        <div style="display:flex;gap:6px">
          <button id="plat_douyin_${t}" onclick="_switchPlat('douyin','${t}')"
            style="background:#6366f1;color:#fff;border:none;padding:5px 14px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600">🎵 抖音</button>
          <button id="plat_xiaohongshu_${t}" onclick="_switchPlat('xiaohongshu','${t}')"
            style="background:var(--bg3);color:var(--text);border:1px solid var(--border);padding:5px 14px;border-radius:6px;cursor:pointer;font-size:12px">📕 小红书</button>
        </div>
      </div>
      <div id="flowLegend_${t}" style="display:flex;gap:16px;margin-bottom:10px;font-size:11px;color:var(--text2)">
        <span><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#22c55e;vertical-align:middle"></span> 已测试通过</span>
        <span><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#f59e0b;vertical-align:middle"></span> 部分通过</span>
        <span><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#6b7280;vertical-align:middle"></span> 未测试</span>
        <span><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#ef4444;vertical-align:middle"></span> 测试失败</span>
        <span style="margin-left:12px;border-left:1px solid var(--border);padding-left:12px">🖱 点击节点查看可用操作 | 点击连线查看转换条件</span>
      </div>
      <div id="flowCanvas_${t}" style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:16px;min-height:400px;overflow:auto">
        <svg id="flowSvg_${t}" width="900" height="450" style="display:block;margin:0 auto"></svg>
      </div>
      <div id="flowDetail_${t}" style="margin-top:8px;background:var(--bg3);border-radius:var(--radius);padding:10px;border:1px solid var(--border);font-size:12px;display:none"></div>
    </div>`,r(`douyin`,t),window._switchPlat=function(e,t){document.getElementById(`plat_douyin_${t}`).style.background=e===`douyin`?`#6366f1`:`var(--bg3)`,document.getElementById(`plat_douyin_${t}`).style.color=e===`douyin`?`#fff`:`var(--text)`,document.getElementById(`plat_xiaohongshu_${t}`).style.background=e===`xiaohongshu`?`#6366f1`:`var(--bg3)`,document.getElementById(`plat_xiaohongshu_${t}`).style.color=e===`xiaohongshu`?`#fff`:`var(--text)`,r(e,t)},window._flowNodeClick=function(e,t){i(e,t)}}var t={douyin:{name:`抖音`,nodes:[{id:`grid`,label:`首页精选`,desc:`推荐feed流，视频卡片列表`,icon:`🏠`,status:`partial`,ops:[`scroll_feed(🟢)`,`open_video(🟢)`,`search(🟢)`,`goto_profile(🟡)`,`goto_branch(🟢)`]},{id:`branch`,label:`分支页`,desc:`关注/朋友/同城等Tab页`,icon:`📂`,status:`untested`,ops:[`scroll_feed(🟢)`,`open_video(🟢)`,`search(🟢)`]},{id:`player_modal`,label:`视频播放(浮层)`,desc:`半屏浮层播放，含评论区`,icon:`▶️`,status:`partial`,ops:[`like(🟢)`,`collect(🔴)`,`comment(🟢)`,`follow(🟡)`,`go_back(🟢)`,`next_video(🟢)`]},{id:`player_full`,label:`视频播放(全屏)`,desc:`全屏/video/xxx页面`,icon:`📺`,status:`partial`,ops:[`like(🟢)`,`collect(🔴)`,`comment(🟢)`,`follow(🟡)`,`go_back(🟢)`]},{id:`search`,label:`搜索结果`,desc:`搜索页，关键词结果列表`,icon:`🔍`,status:`untested`,ops:[`click_result(🟡)`,`scroll(🟢)`,`go_back(🟢)`,`search_user(🟡)`]},{id:`profile`,label:`个人主页`,desc:`用户主页，含作品/粉丝/获赞`,icon:`👤`,status:`untested`,ops:[`read_field(🟢)`,`read_fans(🟡)`,`go_back(🟢)`,`follow(🟡)`]},{id:`user_profile`,label:`博主主页`,desc:`其他博主的主页`,icon:`🌟`,status:`untested`,ops:[`read_field(🟢)`,`follow(🟡)`,`go_back(🟢)`,`collect_profile(🔴)`]}],edges:[{from:`grid`,to:`player_modal`,action:`open_video`,status:`partial`,note:`点击feed卡片 → 浮层播放`},{from:`grid`,to:`player_full`,action:`open_video_new`,status:`untested`,note:`右键新标签打开`},{from:`grid`,to:`search`,action:`search`,status:`untested`,note:`点击搜索框→输入→搜索`},{from:`grid`,to:`profile`,action:`goto_profile`,status:`untested`,note:`点击头像→个人主页`},{from:`grid`,to:`branch`,action:`goto_branch`,status:`untested`,note:`切换Tab到关注/朋友`},{from:`grid`,to:`user_profile`,action:`goto_user`,status:`untested`,note:`点击博主头像→博主主页`},{from:`player_modal`,to:`grid`,action:`go_back`,status:`partial`,note:`关闭浮层→回首页`},{from:`player_modal`,to:`player_modal`,action:`next_video`,status:`partial`,note:`滑动/自动→下一个视频`},{from:`player_modal`,to:`player_full`,action:`expand_full`,status:`untested`,note:`全屏按钮`},{from:`player_modal`,to:`profile`,action:`goto_author`,status:`untested`,note:`点作者头像→作者主页`},{from:`player_modal`,to:`comment`,action:`open_comments`,status:`untested`,note:`展开全部评论`},{from:`player_full`,to:`grid`,action:`go_back`,status:`untested`,note:`返回→首页`},{from:`player_full`,to:`player_full`,action:`next_video`,status:`untested`,note:`下一个视频`},{from:`search`,to:`player_modal`,action:`click_result`,status:`untested`,note:`点搜索结果→视频`},{from:`search`,to:`profile`,action:`click_user`,status:`untested`,note:`点用户结果→个人主页`},{from:`search`,to:`grid`,action:`go_back`,status:`untested`,note:`取消搜索→回首页`},{from:`profile`,to:`grid`,action:`go_back`,status:`untested`,note:`返回→首页`},{from:`user_profile`,to:`grid`,action:`go_back`,status:`untested`,note:`返回→首页`}]},xiaohongshu:{name:`小红书`,nodes:[{id:`grid`,label:`首页推荐`,desc:`双列瀑布流笔记列表`,icon:`🏠`,status:`untested`,ops:[`scroll_feed(🟡)`,`click_note(🟡)`,`search(🟡)`,`goto_profile(🟡)`]},{id:`note_detail`,label:`笔记详情`,desc:`单篇笔记内容页`,icon:`📄`,status:`untested`,ops:[`like(🟡)`,`collect(🟡)`,`comment(🟡)`,`post_comment(🟡)`,`follow(🟡)`,`go_back(🟡)`]},{id:`search`,label:`搜索结果`,desc:`搜索页，笔记/用户结果`,icon:`🔍`,status:`untested`,ops:[`click_result(🟡)`,`scroll(🟡)`,`go_back(🟡)`]},{id:`profile`,label:`个人主页`,desc:`用户主页`,icon:`👤`,status:`untested`,ops:[`read_field(🟡)`,`go_back(🟡)`]}],edges:[{from:`grid`,to:`note_detail`,action:`click_note`,status:`untested`,note:`点击笔记卡片→详情页`},{from:`grid`,to:`search`,action:`search`,status:`untested`,note:`搜索→搜结果页`},{from:`grid`,to:`profile`,action:`goto_profile`,status:`untested`,note:`点头像→个人主页`},{from:`note_detail`,to:`grid`,action:`go_back`,status:`untested`,note:`返回→首页`},{from:`note_detail`,to:`note_detail`,action:`next_note`,status:`untested`,note:`滑动→下一篇`},{from:`search`,to:`note_detail`,action:`click_result`,status:`untested`,note:`点结果→笔记详情`},{from:`search`,to:`profile`,action:`click_user`,status:`untested`,note:`点用户→个人主页`},{from:`search`,to:`grid`,action:`go_back`,status:`untested`,note:`返回→首页`},{from:`profile`,to:`grid`,action:`go_back`,status:`untested`,note:`返回→首页`}]}},n={tested:`#22c55e`,partial:`#f59e0b`,untested:`#6b7280`,failed:`#ef4444`};function r(e,r){let i=document.getElementById(`flowSvg_${r}`);if(!i)return;let a=t[e];if(!a)return;let o={douyin:[{id:`grid`,x:400,y:40},{id:`branch`,x:150,y:40},{id:`player_modal`,x:400,y:170},{id:`player_full`,x:650,y:170},{id:`search`,x:150,y:300},{id:`profile`,x:400,y:300},{id:`user_profile`,x:650,y:300}],xiaohongshu:[{id:`grid`,x:350,y:60},{id:`note_detail`,x:350,y:200},{id:`search`,x:150,y:200},{id:`profile`,x:550,y:200}]},s=o[e]||o.douyin,c={};s.forEach(e=>{c[e.id]={x:e.x,y:e.y}});let l=``;a.edges.forEach(t=>{let i=c[t.from],a=c[t.to];if(!i||!a)return;let o=n[t.status]||`#6b7280`;if(t.from===t.to)l+=`
        <path d="M ${i.x} ${i.y-22} Q ${i.x+40} ${i.y-30-30} ${i.x} ${i.y-22}"
          fill="none" stroke="${o}" stroke-width="2" stroke-dasharray="5,3"
          onclick="_flowEdgeClick('${t.action}','${e}','${r}')" style="cursor:pointer"
          opacity="0.7"/>
        <text x="${i.x+40+10}" y="${i.y-30-20}" font-size="9" fill="${o}" text-anchor="middle"
          onclick="_flowEdgeClick('${t.action}','${e}','${r}')" style="cursor:pointer">${t.action}</text>`;else{let n=(i.x+a.x)/2,s=(i.y+a.y)/2-15;l+=`
        <path d="M ${i.x} ${i.y+22} Q ${(i.x+a.x)/2} ${(i.y+a.y)/2-30} ${a.x} ${a.y-22}"
          fill="none" stroke="${o}" stroke-width="2" marker-end="url(#arrow_${r})"
          onclick="_flowEdgeClick('${t.action}','${e}','${r}')" style="cursor:pointer"
          opacity="0.7"/>
        <text x="${n}" y="${s}" font-size="9" fill="${o}" text-anchor="middle"
          onclick="_flowEdgeClick('${t.action}','${e}','${r}')" style="cursor:pointer">${t.action}</text>`}}),l+=`
    <defs>
      <marker id="arrow_${r}" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#6b7280"/>
      </marker>
    </defs>`,a.nodes.forEach(e=>{let t=c[e.id];if(!t)return;let i=n[e.status]||`#6b7280`;l+=`
      <g onclick="_flowNodeClick('${e.id}','${r}')" style="cursor:pointer">
        <!-- 节点背景 -->
        <rect x="${t.x-60}" y="${t.y-20}" width="120" height="40" rx="8" ry="8"
          fill="var(--bg3)" stroke="${i}" stroke-width="2.5"/>
        <!-- 状态指示灯 -->
        <circle cx="${t.x-50}" cy="${t.y}" r="5" fill="${i}"/>
        <!-- 图标 -->
        <text x="${t.x-35}" y="${t.y+4}" font-size="13" text-anchor="middle">${e.icon}</text>
        <!-- 标签 -->
        <text x="${t.x+8}" y="${t.y+4}" font-size="11" fill="var(--text)" text-anchor="start"
          font-weight="600">${e.label}</text>
      </g>`}),i.innerHTML=l,document.getElementById(`flowDetail_${r}`).style.display=`none`,window._flowEdgeClick=function(e,n,r){let i=document.getElementById(`flowDetail_${r}`);i&&(i.style.display=`block`,i.innerHTML=`<span style="color:var(--text2)">🔗 操作: </span><strong>${e}</strong>
      <span style="color:var(--text2);margin-left:12px">平台: ${t[n].name}</span>`)}}function i(e,n){let r=null,i=``;if([`douyin`,`xiaohongshu`].forEach(n=>{let a=t[n].nodes.find(t=>t.id===e);a&&(r=a,i=n)}),!r)return;let a=document.getElementById(`flowDetail_${n}`);if(!a)return;a.style.display=`block`;let o=t[i].edges.filter(t=>t.from===e),s=t[i].edges.filter(t=>t.to===e);a.innerHTML=`
    <div style="display:flex;gap:16px;flex-wrap:wrap">
      <div style="flex:1;min-width:200px">
        <div style="font-size:14px;font-weight:600;margin-bottom:6px">${r.icon} ${r.label}</div>
        <div style="font-size:11px;color:var(--text2);margin-bottom:4px">${r.desc}</div>
        <div style="font-size:11px">${{tested:`✅ 已测试通过`,partial:`🟡 部分通过`,untested:`⚪ 未测试`,failed:`🔴 测试失败`}[r.status]||`⚪ 未测试`}</div>
      </div>
      <div style="flex:1;min-width:200px">
        <div style="font-size:11px;font-weight:600;margin-bottom:4px">🚀 当前可用操作</div>
        ${r.ops.map(e=>`<span style="display:inline-block;font-size:10px;background:var(--bg3);padding:2px 8px;border-radius:4px;margin:2px">${e}</span>`).join(``)}
      </div>
      <div style="flex:1;min-width:150px">
        <div style="font-size:11px;font-weight:600;margin-bottom:4px">⬅ 到达路径 (${s.length})</div>
        ${s.length?s.map(e=>`<div style="font-size:10px;color:var(--text2);padding:1px 0">← ${e.action}</div>`).join(``):`<div style="font-size:10px;color:var(--text2)">起始页</div>`}
        <div style="font-size:11px;font-weight:600;margin-top:6px;margin-bottom:4px">➡ 可前往 (${o.length})</div>
        ${o.map(e=>`<div style="font-size:10px;color:var(--text2);padding:1px 0">→ ${e.action} → ${t[i].nodes.find(t=>t.id===e.to)?.label||e.to}</div>`).join(``)}
      </div>
    </div>`}export{e as loadView};