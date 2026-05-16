#!/usr/bin/env python3
"""
系统监控面板 — 独立启动入口

用法:
  python run.py                    # 默认 9988 端口
  python run.py 9988               # 指定端口
  python run.py 9988 --no-reload   # 关闭热重载

版本: 1.0.0 | 更新: 2026-05-16
"""
import sys
import os
from pathlib import Path

# ── 确保能找到 app.py ─────────────────────────────────────
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from app import app


def main():
    import uvicorn

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9988
    reload = True
    if "--no-reload" in sys.argv:
        reload = False

    print(f"📊 系统监控面板")
    print(f"   → 前端页面: http://localhost:{port}")
    print(f"   → 插件列表: http://localhost:{port}/api/plugins")
    print(f"   → 总览:     http://localhost:{port}/api/summary")
    print(f"   → 生产列表: http://localhost:{port}/api/productions")
    print(f"   → 资产列表: http://localhost:{port}/api/assets")
    print(f"   → 文档:     http://localhost:{port}/docs")
    print()
    print(f"支持的插件: AVE (视频工厂)")
    print(f"  后续插件: Matrix (矩阵养号) / guardd (系统状态) 即将接入")
    print()
    print(f"按 Ctrl+C 停止")

    uvicorn.run(app, host="0.0.0.0", port=port, reload=reload)


if __name__ == "__main__":
    main()
