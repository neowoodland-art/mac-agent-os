async function e(e){let t=Math.random().toString(36).slice(2,6);e.innerHTML=`
    <div style="padding:12px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="font-size:18px;margin:0">🎬 录制标注</h2>
        <div style="display:flex;gap:6px;font-size:12px">
          <button onclick="_refreshRecordings('${t}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 12px;border-radius:6px;cursor:pointer">⟳ 刷新</button>
          <button onclick="_startRecording()" style="background:#ef4444;color:#fff;border:none;padding:5px 14px;border-radius:6px;cursor:pointer;font-weight:600">⏺ 开始录制</button>
        </div>
      </div>

      <!-- 录制列表 -->
      <div id="recordingList_${t}" style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:12px;margin-bottom:10px">
        <div style="font-size:12px;font-weight:600;margin-bottom:8px">📋 录制包列表</div>
        <div id="recordingListBody_${t}">
          <div class="loading" style="font-size:12px;padding:8px">加载录制列表...</div>
        </div>
      </div>

      <!-- 录制详情 + 标注面板 -->
      <div id="recordingDetail_${t}" style="display:none">
        <div style="background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border);padding:12px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div>
              <span id="recordingName_${t}" style="font-size:13px;font-weight:600"></span>
              <span id="recordingMeta_${t}" style="font-size:11px;color:var(--text2);margin-left:8px"></span>
            </div>
            <div style="display:flex;gap:6px">
              <button onclick="_exportBlueprint('${t}')" style="background:var(--primary);color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">📦 导出蓝图</button>
              <button onclick="_generateCode('${t}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">⚡ 生成代码</button>
            </div>
          </div>

          <!-- 步骤时间线 -->
          <div id="stepsTimeline_${t}" style="font-size:11px">
            <div class="loading" style="padding:8px">加载步骤...</div>
          </div>
        </div>
      </div>
    </div>`,n(t),window._refreshRecordings=function(e){n(e)},window._startRecording=function(){alert(`录制功能需后端支持
请使用命令行: mc record --account=xxx --platform=douyin`)},window._exportBlueprint=function(e){alert(`导出蓝图功能待实现`)},window._generateCode=function(e){alert(`代码生成功能待实现`)},window._selectRecording=function(e,t){r(e,t)},window._mergeSteps=function(e,t,n){alert(`合并步骤功能待实现`)},window._renameStep=function(e,t){let n=prompt(`输入操作名称（如: like, collect, comment）:`);if(n){let r=document.getElementById(`stepName_${e}_${t}`);r&&(r.textContent=n)}}}function t(){return[{name:`douyin_daily_20260622`,platform:`douyin`,account:`douyin_test`,steps:8,duration:`2m30s`,created:`2026-06-22 14:00`,annotated:!1,steps_detail:[{id:1,label:``,before:`首页(grid)`,action:`点击第3个视频卡片`,after:`视频播放(浮层)`,from_state:`grid`,to_state:`player_modal`,auto_op:`open_video`},{id:2,label:``,before:`视频播放(浮层)`,action:`按下键盘z`,after:`点赞按钮变红`,from_state:`player_modal`,to_state:`player_modal`,auto_op:`like`},{id:3,label:``,before:`已点赞状态`,action:`点击收藏按钮`,after:`收藏图标高亮`,from_state:`player_modal`,to_state:`player_modal`,auto_op:`collect`},{id:4,label:``,before:`已收藏状态`,action:`点击评论区`,after:`评论列表展开`,from_state:`player_modal`,to_state:`player_modal`,auto_op:`open_comments`},{id:5,label:``,before:`评论展开`,action:`输入文字+点击发送`,after:`评论发布成功`,from_state:`player_modal`,to_state:`player_modal`,auto_op:`post_comment`},{id:6,label:``,before:`评论已发送`,action:`点击作者头像`,after:`跳转到作者主页`,from_state:`player_modal`,to_state:`profile`,auto_op:`goto_author`},{id:7,label:``,before:`作者主页`,action:`滑动查看作品列表`,after:`作品列表滚动`,from_state:`profile`,to_state:`profile`,auto_op:`scroll_feed`},{id:8,label:``,before:`作者主页`,action:`点击返回按钮`,after:`回到首页推荐`,from_state:`profile`,to_state:`grid`,auto_op:`go_back`}]},{name:`xhs_collect_20260622`,platform:`xiaohongshu`,account:`xhs_01`,steps:5,duration:`1m20s`,created:`2026-06-22 13:30`,annotated:!1,steps_detail:[{id:1,label:``,before:`首页推荐(grid)`,action:`点击笔记卡片`,after:`笔记详情页`,from_state:`grid`,to_state:`note_detail`,auto_op:`click_note`},{id:2,label:``,before:`笔记详情`,action:`点击❤️按钮`,after:`❤️变红`,from_state:`note_detail`,to_state:`note_detail`,auto_op:`like`},{id:3,label:``,before:`笔记详情`,action:`点击⭐收藏`,after:`收藏成功`,from_state:`note_detail`,to_state:`note_detail`,auto_op:`collect`},{id:4,label:``,before:`笔记详情`,action:`输入评论+发布`,after:`评论成功`,from_state:`note_detail`,to_state:`note_detail`,auto_op:`post_comment`},{id:5,label:``,before:`笔记详情`,action:`点击返回`,after:`回到首页`,from_state:`note_detail`,to_state:`grid`,auto_op:`go_back`}]}]}async function n(e){let n=document.getElementById(`recordingListBody_${e}`);if(!n)return;let r=t();n.innerHTML=r.length?`<table style="width:100%;font-size:11px;border-collapse:collapse">
        <thead><tr style="border-bottom:1px solid var(--border)">
          <th style="padding:4px 6px;text-align:left">名称</th>
          <th style="padding:4px 6px;text-align:left">平台</th>
          <th style="padding:4px 6px;text-align:left">账号</th>
          <th style="padding:4px 6px;text-align:center">步数</th>
          <th style="padding:4px 6px;text-align:center">时长</th>
          <th style="padding:4px 6px;text-align:center">标注</th>
          <th style="padding:4px 6px;text-align:center">操作</th>
        </tr></thead>
        <tbody>${r.map(t=>`
          <tr style="border-bottom:1px solid var(--border)">
            <td style="padding:4px 6px;font-weight:500">${t.name}</td>
            <td style="padding:4px 6px">${t.platform===`douyin`?`🎵`:`📕`} ${t.platform}</td>
            <td style="padding:4px 6px;color:var(--text2)">${t.account}</td>
            <td style="padding:4px 6px;text-align:center">${t.steps}</td>
            <td style="padding:4px 6px;text-align:center;color:var(--text2)">${t.duration}</td>
            <td style="padding:4px 6px;text-align:center">${t.annotated?`✅`:`<span style="color:var(--amber)">⏳</span>`}</td>
            <td style="padding:4px 6px;text-align:center">
              <button onclick="window._selectRecording('${t.name}','${e}')" style="background:none;border:none;cursor:pointer;font-size:12px;color:var(--primary)" title="打开标注">📝</button>
            </td>
          </tr>
        `).join(``)}</tbody></table>`:`<div style="font-size:12px;color:var(--text2);padding:8px">暂无录制记录。点击"开始录制"创建新录制。</div>`}function r(e,n){let r=t().find(t=>t.name===e);if(!r)return;let i=document.getElementById(`recordingDetail_${n}`),a=document.getElementById(`recordingName_${n}`),o=document.getElementById(`recordingMeta_${n}`),s=document.getElementById(`stepsTimeline_${n}`);if(!i||!s)return;i.style.display=`block`,a.textContent=`📹 ${r.name}`,o.textContent=`${r.platform} · ${r.account} · ${r.steps}步 · ${r.duration}`;let c=`<div style="margin-bottom:10px;font-size:10px;color:var(--text2)">
    状态流: ${r.steps_detail.map((e,t)=>`<span style="display:inline-block;padding:1px 6px;margin:1px;background:var(--bg3);border-radius:3px">
        ${e.from_state}
        <span style="color:var(--primary)">→</span>
        ${e.to_state}
      </span>${t<r.steps_detail.length-1?` `:``}`).join(``)}
  </div>`;r.steps_detail.forEach(e=>{let t=e.auto_op?`系统建议: <code style="background:var(--bg3);padding:1px 6px;border-radius:3px;font-size:10px">${e.auto_op}</code>`:``;c+=`
      <div style="background:var(--bg3);border-radius:6px;padding:10px;margin-bottom:8px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <span style="font-size:11px;font-weight:600">步骤 ${e.id}</span>
          <div style="display:flex;gap:4px;font-size:10px">
            <button onclick="window._renameStep(${e.id},'${n}')" style="background:var(--primary);color:#fff;border:none;padding:2px 8px;border-radius:4px;cursor:pointer">✏️ 命名</button>
            <button onclick="window._mergeSteps(${e.id},${e.id+1},'${n}')" style="background:var(--bg2);border:1px solid var(--border);color:var(--text);padding:2px 8px;border-radius:4px;cursor:pointer">🔗 合并下步</button>
          </div>
        </div>

        <!-- 三栏布局: before → action → after -->
        <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:start">
          <!-- Before -->
          <div style="background:rgba(37,99,235,.08);border-radius:5px;padding:6px;border:1px solid rgba(37,99,235,.15)">
            <div style="font-size:9px;color:#3b82f6;font-weight:600;margin-bottom:2px">⬅ 前状态</div>
            <div style="font-size:11px">${e.before}</div>
          </div>

          <!-- Arrow -->
          <div style="display:flex;align-items:center;padding:0 4px;font-size:16px;color:var(--text2)">→</div>

          <!-- After -->
          <div style="background:rgba(5,150,105,.08);border-radius:5px;padding:6px;border:1px solid rgba(5,150,105,.15)">
            <div style="font-size:9px;color:#22c55e;font-weight:600;margin-bottom:2px">➡ 后状态</div>
            <div style="font-size:11px">${e.after}</div>
          </div>
        </div>

        <!-- Action + Annotation -->
        <div style="margin-top:6px;display:flex;gap:8px;align-items:flex-start;flex-wrap:wrap">
          <div style="background:var(--bg2);border-radius:4px;padding:4px 8px;font-size:11px;flex:1">
            <span style="color:var(--text2)">🖱 操作:</span> ${e.action}
          </div>
          <div style="display:flex;align-items:center;gap:4px;font-size:11px">
            <span style="color:var(--text2)">🏷️ 原子操作名:</span>
            <span id="stepName_${e.id}_${n}" style="font-weight:600;background:var(--bg2);padding:2px 8px;border-radius:4px;cursor:pointer;border:1px dashed var(--border)"
              onclick="window._renameStep(${e.id},'${n}')">${e.label||`点击命名...`}</span>
          </div>
          <div style="font-size:10px;color:var(--text2)">${t}</div>
        </div>
      </div>`}),c+=`
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:4px">
      <span style="font-size:10px;color:var(--text2);flex:1">💡 提示: 点击"命名"为每个步骤起名，连续步骤可合并为1个原子操作</span>
      <button onclick="window._exportBlueprint('${n}')" style="background:var(--primary);color:#fff;border:none;padding:5px 14px;border-radius:6px;cursor:pointer;font-size:12px">📦 导出为蓝图</button>
      <button onclick="window._generateCode('${n}')" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 14px;border-radius:6px;cursor:pointer;font-size:12px">⚡ 生成代码</button>
    </div>`,s.innerHTML=c}export{e as loadView};