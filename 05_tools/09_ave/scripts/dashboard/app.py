"""
AVE Dashboard — FastAPI 后端

用法:
  python -m uvicorn dashboard.app:app --reload --port 9988
  或: python main.py dashboard

API:
  GET  /api/summary           — 总览统计
  GET  /api/productions       — 生产列表 (limit, offset, strategy, status)
  GET  /api/productions/{id}  — 生产详情 + steps + assets + costs
  GET  /api/assets            — 资产列表 (type, tag, limit, offset)
"""
import sys
import os
from pathlib import Path

# 确保能找到 lib/ 下的 dashboard.py
_script_dir = Path(__file__).resolve().parents[1]
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from lib.dashboard import (
    init_db, get_summary, get_productions,
    get_production_detail, get_assets,
)

app = FastAPI(
    title="AVE Dashboard",
    version="1.0.0",
    description="AVE 视频工厂生产监控 API",
)

# CORS — 允许前端页面访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()


# ── 总览 ──────────────────────────────────────────────────

@app.get("/api/summary")
def api_summary():
    """总览统计"""
    return get_summary()


# ── 生产列表 ──────────────────────────────────────────────

@app.get("/api/productions")
def api_productions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    strategy: str | None = Query(None),
    status: str | None = Query(None),
):
    """生产列表"""
    return get_productions(limit=limit, offset=offset, strategy=strategy, status=status)


@app.get("/api/productions/{production_id}")
def api_production_detail(production_id: int):
    """生产详情"""
    result = get_production_detail(production_id)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Production not found")
    return result


# ── 资产 ──────────────────────────────────────────────────

@app.get("/api/assets")
def api_assets(
    type: str | None = Query(None, alias="type"),
    tag: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """资产列表"""
    return get_assets(asset_type=type, tag=tag, limit=limit, offset=offset)


# ── 健康检查 ──────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


# ── 直接运行 ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9988
    print(f"AVE Dashboard API → http://localhost:{port}")
    print(f"  总览:     http://localhost:{port}/api/summary")
    print(f"  生产列表: http://localhost:{port}/api/productions")
    print(f"  资产列表: http://localhost:{port}/api/assets")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
