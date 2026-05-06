"""
口播素材系统 - Web 界面（Gradio）
用法：python app.py

功能：
  - 搜索/筛选素材（关键词、平台、标签、情绪、下载状态）
  - 查看素材详情和 AI 分析结果
  - 一键复制金句
  - 标记下载 / 本地播放

启动后访问：http://127.0.0.1:7860
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_config, get_db, init_db, setup_logger, PROJECT_ROOT

try:
    import gradio as gr
except ImportError:
    print("[ERROR] Gradio 未安装，请执行：pip install gradio")
    sys.exit(1)


# ============================================================
# 数据库查询
# ============================================================

def search_materials(
    keyword: str = "",
    platform: str = "全部",
    emotion: str = "全部",
    has_file: str = "全部",
    worth_download: str = "全部",
    sort_by: str = "fetched_at DESC",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """搜索素材，返回（结果列表, 总数）"""
    config = load_config()
    db = get_db(init_db())
    
    where_clauses = []
    params = []
    
    if keyword:
        where_clauses.append("(m.title LIKE ? OR m.description LIKE ? OR a.tags LIKE ? OR a.golden_quote LIKE ?)")
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw, kw])
    
    if platform and platform != "全部":
        where_clauses.append("m.platform = ?")
        params.append(platform)
    
    if emotion and emotion != "全部":
        where_clauses.append("a.emotion = ?")
        params.append(emotion)
    
    if has_file == "已下载":
        where_clauses.append("m.download_status = 'done'")
    elif has_file == "未下载":
        where_clauses.append("m.download_status != 'done'")
    
    if worth_download == "推荐下载":
        where_clauses.append("a.worth_downloading = 'yes'")
    elif worth_download == "不推荐":
        where_clauses.append("a.worth_downloading = 'no'")
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # 总数
    count_sql = f"""
        SELECT COUNT(*) FROM materials m
        LEFT JOIN analysis a ON m.id = a.material_id
        WHERE {where_sql}
    """
    total = db.execute(count_sql, params).fetchone()[0]
    
    # 排序和分页
    offset = (page - 1) * page_size
    data_sql = f"""
        SELECT m.*, a.tags, a.golden_quote, a.core_idea, a.structure,
               a.emotion, a.worth_downloading, a.download_reason
        FROM materials m
        LEFT JOIN analysis a ON m.id = a.material_id
        WHERE {where_sql}
        ORDER BY {sort_by}
        LIMIT ? OFFSET ?
    """
    params.extend([page_size, offset])
    rows = db.execute(data_sql, params).fetchall()
    results = [dict(r) for r in rows]
    
    db.close()
    return results, total


def get_material_detail(material_id: int) -> dict:
    """获取素材详情"""
    db = get_db(init_db())
    row = db.execute("""
        SELECT m.*, a.tags, a.golden_quote, a.core_idea, a.structure,
               a.emotion, a.worth_downloading, a.download_reason, a.raw_model_output
        FROM materials m
        LEFT JOIN analysis a ON m.id = a.material_id
        WHERE m.id = ?
    """, (material_id,)).fetchone()
    db.close()
    return dict(row) if row else {}


def mark_download(material_id: int) -> str:
    """标记素材为待下载"""
    db = get_db(init_db())
    db.execute("UPDATE materials SET download_status = 'pending' WHERE id = ?", (material_id,))
    db.commit()
    db.close()
    return "已加入下载队列"


def get_stats() -> dict:
    """获取统计信息"""
    db = get_db(init_db())
    total = db.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
    analyzed = db.execute("SELECT COUNT(*) FROM materials WHERE analyzed = 1").fetchone()[0]
    downloaded = db.execute("SELECT COUNT(*) FROM materials WHERE download_status = 'done'").fetchone()[0]
    pending = db.execute("SELECT COUNT(*) FROM materials WHERE download_status = 'pending'").fetchone()[0]
    recommended = db.execute("SELECT COUNT(*) FROM analysis WHERE worth_downloading = 'yes'").fetchone()[0]
    db.close()
    return {
        "总素材": total,
        "已分析": analyzed,
        "已下载": downloaded,
        "待下载": pending,
        "AI推荐": recommended,
    }


# ============================================================
# Gradio 界面
# ============================================================

def build_app() -> gr.Blocks:
    config = load_config()
    
    # 初始化数据库
    init_db()
    stats = get_stats()
    
    with gr.Blocks(
        title=config.get("web", {}).get("title", "口播灵感工坊"),
        theme=gr.themes.Soft(),
    ) as app:
        gr.Markdown("# 🎬 口播灵感工坊 — 素材采集 → 脚本生成")
        
        with gr.Tabs():
            # ====== 标签页1：素材库 ======
            with gr.Tab("📦 素材库"):
                stats_text = gr.Markdown(
                    f"📊 **统计** | 总素材: {stats['总素材']} | 已分析: {stats['已分析']} | "
                    f"已下载: {stats['已下载']} | 待下载: {stats['待下载']} | AI推荐: {stats['AI推荐']}"
                )
                
                with gr.Row():
                    keyword_input = gr.Textbox(label="关键词搜索", placeholder="标题/描述/标签/金句", scale=2)
                    platform_dd = gr.Dropdown(
                        label="平台", choices=["全部", "xiaohongshu", "douyin", "bilibili"],
                        value="全部", scale=1
                    )
                    emotion_dd = gr.Dropdown(
                        label="情绪", choices=["全部", "治愈", "励志", "震惊", "沉思", "有趣", "感动"],
                        value="全部", scale=1
                    )
                
                with gr.Row():
                    has_file_dd = gr.Dropdown(
                        label="下载状态", choices=["全部", "已下载", "未下载"],
                        value="全部", scale=1
                    )
                    worth_dd = gr.Dropdown(
                        label="AI推荐", choices=["全部", "推荐下载", "不推荐"],
                        value="全部", scale=1
                    )
                    sort_dd = gr.Dropdown(
                        label="排序", choices=["fetched_at DESC", "like_count DESC", "collect_count DESC"],
                        value="fetched_at DESC", scale=1
                    )
                    search_btn = gr.Button("🔍 搜索", variant="primary", scale=1)
                    refresh_btn = gr.Button("🔄 刷新统计", scale=1)
                
                result_table = gr.Dataframe(
                    headers=["ID", "平台", "标题", "作者", "金句", "情绪", "推荐下载", "状态"],
                    label="搜索结果",
                    interactive=False,
                )
                
                with gr.Row():
                    with gr.Column(scale=1):
                        detail_id = gr.Number(label="素材ID", precision=0)
                        with gr.Row():
                            detail_btn = gr.Button("查看详情", variant="secondary")
                            download_btn = gr.Button("📥 加入下载队列", variant="stop")
                    
                    with gr.Column(scale=2):
                        detail_output = gr.Markdown("选择一条素材后点击「查看详情」")
            
            # ====== 标签页2：脚本工厂 ======
            with gr.Tab("🎬 脚本工厂"):
                gr.Markdown("### 从素材或主题生成 AVE v2.0 导演脚本")
                
                with gr.Row():
                    script_source = gr.Radio(
                        choices=["输入主题", "从素材库ID"],
                        label="脚本来源", value="输入主题"
                    )
                
                with gr.Row():
                    topic_input = gr.Textbox(
                        label="主题", placeholder="输入口播主题，如：普通人如何抓住AI时代的机会",
                        visible=True, scale=3
                    )
                    material_id_input = gr.Number(
                        label="素材ID", precision=0, value=0,
                        visible=False, scale=1
                    )
                
                with gr.Row():
                    style_dd = gr.Dropdown(
                        label="视频风格",
                        choices=["knowledge_lecture", "bedtime_story", "funny_talk", "tech_review"],
                        value="knowledge_lecture", scale=1
                    )
                    gen_btn = gr.Button("🚀 生成脚本", variant="primary", scale=1)
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### 📄 AVE 导演脚本 (YAML)")
                        yaml_output = gr.Textbox(label="", lines=20, max_lines=30)
                    with gr.Column():
                        gr.Markdown("#### 📝 说明文档 (MD)")
                        md_output = gr.Textbox(label="", lines=20, max_lines=30)
                
                with gr.Row():
                    project_id_display = gr.Textbox(label="项目ID", visible=False)
                    save_btn = gr.Button("💾 保存到素材库", variant="primary")
                    save_status = gr.Markdown("")
                
                # 脚本工厂回调
                def toggle_source(source):
                    show_topic = source == "输入主题"
                    return (
                        gr.update(visible=show_topic),
                        gr.update(visible=not show_topic),
                    )
                
                def generate_script(topic, material_id, style):
                    import subprocess, sys
                    from pathlib import Path
                    
                    script_path = Path(__file__).parent / "script_factory.py"
                    cmd = [sys.executable, str(script_path), "--topic", topic, "--style", style]
                    
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                        if result.returncode != 0:
                            return "生成失败:\n" + result.stderr[:500], "生成失败", ""
                        
                        # 找到最新生成的YAML和MD
                        output_dir = Path(__file__).parent / "scripts_output"
                        yamls = sorted(output_dir.glob("*.yaml"))
                        mds = sorted(output_dir.glob("*.md"))
                        
                        if not yamls:
                            return "未找到生成的脚本文件", "未找到", ""
                        
                        latest_yaml = yamls[-1]
                        latest_md = mds[-1]
                        
                        pid = latest_yaml.stem
                        yaml_content = latest_yaml.read_text(encoding="utf-8")
                        md_content = latest_md.read_text(encoding="utf-8")
                        
                        return yaml_content, md_content, pid
                    except subprocess.TimeoutExpired:
                        return "生成超时（>5分钟）", "超时", ""
                    except Exception as e:
                        return f"生成异常: {str(e)}", "异常", ""
                
                def save_script(pid):
                    if not pid:
                        return "请先生成脚本"
                    # 复制到 materials/
                    import shutil
                    from pathlib import Path
                    
                    output_dir = Path(__file__).parent / "scripts_output"
                    materials_dir = Path.home() / "workbuddy-agent-os/agent-local/materials/videos"
                    materials_dir.mkdir(parents=True, exist_ok=True)
                    
                    yaml_src = output_dir / f"{pid}.yaml"
                    md_src = output_dir / f"{pid}.md"
                    
                    if yaml_src.exists():
                        shutil.copy2(str(yaml_src), str(materials_dir / f"{pid}.yaml"))
                    if md_src.exists():
                        shutil.copy2(str(md_src), str(materials_dir / f"{pid}.md"))
                    
                    return f"✅ 已保存到 `{materials_dir}`"
                
                # 事件绑定
                script_source.change(
                    toggle_source,
                    inputs=[script_source],
                    outputs=[topic_input, material_id_input]
                )
                
                gen_btn.click(
                    generate_script,
                    inputs=[topic_input, material_id_input, style_dd],
                    outputs=[yaml_output, md_output, project_id_display]
                )
                
                save_btn.click(
                    save_script,
                    inputs=[project_id_display],
                    outputs=[save_status]
                )
        
        # 素材库事件绑定（共用）
        def show_detail(material_id):
            if not material_id:
                return "请输入素材ID"
            detail = get_material_detail(int(material_id))
            if not detail:
                return "未找到该素材"
            
            local_info = ""
            if detail.get("local_files"):
                files = json.loads(detail["local_files"])
                local_info = f"\n\n**本地文件**：\n"
                for k, v in files.items():
                    local_info += f"- {k}: `{v}`\n"
            
            tags = detail.get("tags") or "未分析"
            quote = detail.get("golden_quote") or "—"
            idea = detail.get("core_idea") or "—"
            structure = detail.get("structure") or "—"
            emotion = detail.get("emotion") or "—"
            worth = detail.get("worth_downloading") or "—"
            reason = detail.get("download_reason") or "—"
            status = detail.get("download_status") or "none"
            
            return f"""### {detail.get('title', '无标题')}
**平台**：{detail.get('platform', '')} | **作者**：{detail.get('author', '')}
**链接**：{detail.get('url', '')}
**状态**：{status}

---

**🏷️ 标签**：{tags}
**💡 金句**：> {quote}
**🎯 核心立意**：{idea}
**📐 脚本结构**：{structure}
**🎭 情绪**：{emotion}
**⭐ 推荐下载**：{worth} — {reason}
{local_info}"""
        
        def do_search(keyword, platform, emotion, has_file, worth, sort_by):
            results, total = search_materials(keyword, platform, emotion, has_file, worth, sort_by)
            if not results:
                return [["—"] * 8]
            table_data = []
            for r in results:
                table_data.append([
                    r["id"],
                    r["platform"],
                    (r["title"] or "")[:30],
                    (r["author"] or "")[:15],
                    (r.get("golden_quote") or "")[:25],
                    r.get("emotion") or "—",
                    r.get("worth_downloading") or "—",
                    r.get("download_status") or "none",
                ])
            return table_data
        
        def do_download(material_id):
            if not material_id:
                return "请输入素材ID"
            return mark_download(int(material_id))
        
        def refresh_stats():
            s = get_stats()
            return (
                f"📊 **统计** | 总素材: {s['总素材']} | 已分析: {s['已分析']} | "
                f"已下载: {s['已下载']} | 待下载: {s['待下载']} | AI推荐: {s['AI推荐']}"
            )
        
        # 素材库事件绑定
        search_btn.click(do_search, inputs=[keyword_input, platform_dd, emotion_dd, has_file_dd, worth_dd, sort_dd], outputs=[result_table])
        detail_btn.click(show_detail, inputs=[detail_id], outputs=[detail_output])
        download_btn.click(do_download, inputs=[detail_id], outputs=[detail_output])
        refresh_btn.click(refresh_stats, outputs=[stats_text])
    
    return app


def main():
    config = load_config()
    host = config.get("web", {}).get("host", "127.0.0.1")
    port = config.get("web", {}).get("port", 7860)
    
    app = build_app()
    print(f"[INFO] 启动 Web 界面: http://{host}:{port}")
    app.launch(server_name=host, server_port=port)


if __name__ == "__main__":
    main()
