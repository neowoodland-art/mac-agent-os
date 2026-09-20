"""API Key 配置接口

用途：让每个使用者配置自己的 API 密钥。
安全原则：
  - 密钥只写入 agent-local/tools/ave/config/local.yaml（600 权限，不被 git 跟踪）
  - 接口返回一律脱敏（仅前 4 + 后 4 位），绝不回显完整 key
  - 日志只记录字段名与后 4 位
"""
import logging
import os
import time
from pathlib import Path

import httpx
import yaml
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("dashboard.api_config")

router = APIRouter(prefix="/api", tags=["api-config"])

AGENT_LOCAL = Path(os.environ.get(
    "AGENT_LOCAL",
    Path.home() / "workbuddy-agent-os" / "agent-local",
))
LOCAL_YAML = AGENT_LOCAL / "tools" / "ave" / "config" / "local.yaml"

# ── 可配置字段清单（path 对应 local.yaml 的嵌套路径）────────────────
FIELDS = [
    {
        "path": "llm.api_key", "group": "🤖 AI 文本生成",
        "label": "DeepSeek API Key",
        "hint": "评论生成 / 讨论剧本 · 申请: platform.deepseek.com",
        "test": "deepseek", "required": True,
    },
    {
        "path": "llm.model", "group": "🤖 AI 文本生成",
        "label": "模型名",
        "hint": "deepseek-v4-flash（推荐·最划算）/ deepseek-chat · 留空则用 ai.yaml 默认",
        "test": "", "required": False, "secret": False,
    },
    {
        "path": "llm.base_url", "group": "🤖 AI 文本生成",
        "label": "API 地址",
        "hint": "默认 https://api.deepseek.com/v1",
        "test": "", "required": False, "secret": False,
    },
    {
        "path": "aliyun.api_key", "group": "👁️ 视觉分析 / 🔄 人物置换",
        "label": "阿里百炼 API Key",
        "hint": "图像理解(vision) + 视频换人(wan2.2-animate) · 申请: bailian.console.aliyun.com",
        "test": "dashscope", "required": True,
    },
    {
        "path": "kling.api_key", "group": "🎨 图像生成",
        "label": "可灵 Kling API Key",
        "hint": "定妆照 / 角色图 · 申请: klingai.com（格式 api-key-kling-xxx）",
        "test": "kling", "required": False,
    },
    {
        "path": "pexels.api_key", "group": "🖼️ 素材图库",
        "label": "Pexels API Key",
        "hint": "视频/图片素材下载 · 申请: pexels.com/api",
        "test": "pexels", "required": False,
    },
    {
        "path": "volcano.ark_api_key", "group": "🎬 视频生成（火山方舟）",
        "label": "方舟 API Key",
        "hint": "即梦文生视频 · 火山引擎控制台",
        "test": "", "required": False,
    },
    {
        "path": "volcano.jimeng_access_key_id", "group": "🎬 视频生成（火山方舟）",
        "label": "即梦 AccessKey ID",
        "hint": "与下方 Secret 配对使用",
        "test": "", "required": False,
    },
    {
        "path": "volcano.jimeng_secret_access_key", "group": "🎬 视频生成（火山方舟）",
        "label": "即梦 Secret AccessKey",
        "hint": "高度敏感 · 仅存本机",
        "test": "", "required": False,
    },
    {
        "path": "volcano.voice_app_id", "group": "🔊 语音合成（火山）",
        "label": "语音 App ID",
        "hint": "配音服务",
        "test": "", "required": False,
    },
    {
        "path": "volcano.voice_app_key", "group": "🔊 语音合成（火山）",
        "label": "语音 Access Token",
        "hint": "配音服务",
        "test": "", "required": False,
    },
    {
        "path": "volcano.speaker_name", "group": "🔊 语音合成（火山）",
        "label": "默认音色 speaker_name",
        "hint": "非密钥，可留空用默认",
        "test": "", "required": False,
    },
]

FIELD_MAP = {f["path"]: f for f in FIELDS}


# ── 读写工具 ────────────────────────────────────────────────────────
def _read_local() -> dict:
    if not LOCAL_YAML.exists():
        return {}
    try:
        return yaml.safe_load(LOCAL_YAML.read_text()) or {}
    except Exception as e:
        logger.warning("读取 local.yaml 失败: %s", e)
        return {}


def _write_local(cfg: dict) -> None:
    LOCAL_YAML.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_YAML.write_text(
        yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, default_flow_style=False)
    )
    try:
        os.chmod(LOCAL_YAML, 0o600)  # 仅本用户可读写
    except Exception:
        pass


def _get_path(cfg: dict, path: str):
    cur = cfg
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return ""
        cur = cur[part]
    return cur or ""


def _set_path(cfg: dict, path: str, value: str) -> None:
    parts = path.split(".")
    cur = cfg
    for part in parts[:-1]:
        if part not in cur or not isinstance(cur[part], dict):
            cur[part] = {}
        cur = cur[part]
    cur[parts[-1]] = value


def _mask(v: str) -> str:
    v = str(v or "")
    if not v:
        return ""
    if len(v) <= 12:
        return v[:2] + "…" + v[-2:]
    return v[:5] + "…" + v[-4:]


# ── Key 历史版本（轮换 / 回滚用）──────────────────────────────────
HISTORY_PATH = AGENT_LOCAL / "tools" / "ave" / "config" / "key_history.yaml"


def _read_history() -> dict:
    """{字段路径: [{"value","label","added_at","active"}]}"""
    if not HISTORY_PATH.exists():
        return {}
    try:
        return yaml.safe_load(HISTORY_PATH.read_text()) or {}
    except Exception as e:
        logger.warning("读取 key_history.yaml 失败: %s", e)
        return {}


def _write_history(hist: dict) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(
        yaml.safe_dump(hist, allow_unicode=True, sort_keys=False, default_flow_style=False)
    )
    try:
        os.chmod(HISTORY_PATH, 0o600)
    except Exception:
        pass


def _archive(path: str, value: str, label: str = "", active: bool = False) -> None:
    """把 key 值记入历史（同值则更新备注/状态）"""
    value = str(value or "").strip()
    if not value:
        return
    hist = _read_history()
    items = hist.setdefault(path, [])
    for it in items:
        if it.get("value") == value:
            it["active"] = active
            if label:
                it["label"] = label
            _write_history(hist)
            return
    items.append({
        "value": value,
        "label": label or "（无备注）",
        "added_at": time.strftime("%Y-%m-%d %H:%M"),
        "active": active,
    })
    _write_history(hist)


def _mark_active(path: str, value: str) -> None:
    """把历史中该值标为使用中，其余取消"""
    hist = _read_history()
    for it in hist.get(path, []):
        it["active"] = (it.get("value") == value)
    _write_history(hist)


# ── 接口 1：查询状态（脱敏）─────────────────────────────────────────
@router.get("/config/api-keys")
def api_get_api_keys():
    """返回各平台 key 配置状态（脱敏，不回显完整值）"""
    cfg = _read_local()
    hist_all = _read_history()
    out = []
    for f in FIELDS:
        val = str(_get_path(cfg, f["path"]) or "")
        is_secret = f.get("secret", True)  # 密钥类默认脱敏；模型名/地址等普通配置明文
        history = []
        for i, it in enumerate(hist_all.get(f["path"]) or []):
            hv = str(it.get("value") or "")
            history.append({
                "idx": i,
                "masked": _mask(hv) if is_secret else hv,
                "label": it.get("label") or "",
                "added_at": it.get("added_at") or "",
                "active": bool(it.get("active")),
            })
        out.append({
            "path": f["path"],
            "group": f["group"],
            "label": f["label"],
            "hint": f["hint"],
            "required": f.get("required", False),
            "testable": bool(f.get("test")),
            "secret": is_secret,
            "configured": bool(val.strip()),
            "masked": _mask(val) if is_secret else val,
            "history": history,
        })
    groups = []
    for item in out:
        g = next((x for x in groups if x["name"] == item["group"]), None)
        if not g:
            g = {"name": item["group"], "items": []}
            groups.append(g)
        g["items"].append(item)
    return {
        "status": "ok",
        "groups": groups,
        "total": len(out),
        "configured": sum(1 for x in out if x["configured"]),
        "config_path": str(LOCAL_YAML),
    }


# ── 接口 2：保存 key ────────────────────────────────────────────────
@router.post("/config/api-keys")
def api_save_api_keys(data: dict):
    """保存 key（body: {"updates": {"llm.api_key": "sk-xxx"}}）

    - 只允许更新 FIELDS 里声明的路径（防越权写任意字段）
    - 写入 local.yaml，权限 600
    """
    updates = data.get("updates") or {}
    if not isinstance(updates, dict) or not updates:
        raise HTTPException(400, detail="updates 不能为空")
    invalid = [p for p in updates if p not in FIELD_MAP]
    if invalid:
        raise HTTPException(400, detail=f"不支持的配置项: {invalid}")
    labels = data.get("labels") or {}

    cfg = _read_local()
    saved, cleared = [], []
    for path, value in updates.items():
        v = str(value or "").strip()
        old = str(_get_path(cfg, path) or "").strip()
        _set_path(cfg, path, v)
        if v:
            # 旧值归档到历史（轮换场景：保留可回滚）
            if old and old != v:
                _archive(path, old, label="（被替换）", active=False)
            _mark_active(path, v)
            saved.append(f"{path}(***{v[-4:]})")
        else:
            if old:
                _archive(path, old, label="（已清除）", active=False)
            cleared.append(path)
    _write_local(cfg)
    logger.info("  🔑 API 配置更新: 保存 %s | 清空 %s", saved or "无", cleared or "无")
    return {
        "status": "ok",
        "saved": len(saved),
        "cleared": len(cleared),
        "config_path": str(LOCAL_YAML),
    }


# ── 接口 4：切换生效版本（从历史里选择用哪个）──────────────────────
@router.post("/config/api-keys/activate")
def api_activate_api_key(data: dict):
    """切换生效版本: body {path, idx}

    把历史里第 idx 个版本设为当前生效（写入 local.yaml）；
    切换前的当前值自动归档，可随时再切回。
    """
    path = (data.get("path") or "").strip()
    if path not in FIELD_MAP:
        raise HTTPException(400, detail=f"不支持的配置项: {path}")
    try:
        idx = int(data.get("idx"))
    except Exception:
        raise HTTPException(400, detail="idx 必须是数字")

    hist = _read_history()
    items = hist.get(path) or []
    if idx < 0 or idx >= len(items):
        raise HTTPException(404, detail="历史版本不存在")
    target = str(items[idx].get("value") or "").strip()
    if not target:
        raise HTTPException(400, detail="该版本为空，无法启用")

    cfg = _read_local()
    old = str(_get_path(cfg, path) or "").strip()
    if old and old != target:
        _archive(path, old, label="（切换前）", active=False)
    _set_path(cfg, path, target)
    _write_local(cfg)
    _mark_active(path, target)
    logger.info("  🔄 API 版本切换: %s → ***%s", path, target[-4:])
    return {"status": "ok", "activated": _mask(target)}


# ── 接口 5：删除历史版本 ────────────────────────────────────────────
@router.post("/config/api-keys/delete")
def api_delete_api_key(data: dict):
    """删除历史版本: body {path, idx}（使用中的版本不允许删）"""
    path = (data.get("path") or "").strip()
    if path not in FIELD_MAP:
        raise HTTPException(400, detail=f"不支持的配置项: {path}")
    try:
        idx = int(data.get("idx"))
    except Exception:
        raise HTTPException(400, detail="idx 必须是数字")

    hist = _read_history()
    items = hist.get(path) or []
    if idx < 0 or idx >= len(items):
        raise HTTPException(404, detail="历史版本不存在")
    if items[idx].get("active"):
        raise HTTPException(400, detail="使用中的版本不能删除，请先切换到其他版本")
    removed = items.pop(idx)
    if not items:
        hist.pop(path, None)
    _write_history(hist)
    logger.info("  🗑 删除 API 历史版本: %s ***%s", path, str(removed.get("value") or "")[-4:])
    return {"status": "ok", "removed": _mask(str(removed.get("value") or ""))}


# ── 接口 3：测试连通性 ──────────────────────────────────────────────
def _test_deepseek(key: str) -> tuple:
    r = httpx.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
        timeout=30,
    )
    if r.status_code == 200:
        return True, "✅ 连通正常"
    if r.status_code == 401:
        return False, "❌ Key 无效（401）"
    if r.status_code == 402 or "Insufficient Balance" in r.text:
        return False, "⚠️ Key 有效但账户余额不足"
    return False, f"❌ HTTP {r.status_code}: {r.text[:80]}"


def _test_dashscope(key: str) -> tuple:
    r = httpx.post(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "qwen-turbo", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
        timeout=30,
    )
    if r.status_code == 200:
        return True, "✅ 连通正常"
    if r.status_code == 401:
        return False, "❌ Key 无效（401）"
    if "Arrearage" in r.text or "good standing" in r.text:
        return False, "⚠️ Key 有效但账号欠费/状态不良（需充值）"
    return False, f"❌ HTTP {r.status_code}: {r.text[:80]}"


def _test_kling(key: str) -> tuple:
    base = "https://api-beijing.klingai.com"
    r = httpx.get(
        f"{base}/v1/images/generations",
        headers={"Authorization": f"Bearer {key}"},
        timeout=30,
    )
    if r.status_code != 200:
        return False, f"❌ HTTP {r.status_code}: {r.text[:80]}"
    d = r.json()
    code = d.get("code")
    if code == 0:
        return True, f"✅ 鉴权通过（历史任务 {len(d.get('data') or [])} 个）"
    if code == 1102:
        return False, "⚠️ Key 有效但账户余额不足（需充值）"
    return False, f"❌ code={code}: {str(d.get('message'))[:60]}"


def _test_pexels(key: str) -> tuple:
    r = httpx.get(
        "https://api.pexels.com/v1/search?query=test&per_page=1",
        headers={"Authorization": key},
        timeout=30,
    )
    if r.status_code == 200:
        return True, "✅ 连通正常"
    if r.status_code == 401:
        return False, "❌ Key 无效（401）"
    return False, f"❌ HTTP {r.status_code}"


_TESTERS = {
    "deepseek": _test_deepseek,
    "dashscope": _test_dashscope,
    "kling": _test_kling,
    "pexels": _test_pexels,
}


@router.post("/config/api-keys/test")
def api_test_api_key(data: dict):
    """测试指定字段的 key 连通性

    body: {"path": "llm.api_key", "value": "可选，不传则用已保存的值"}
    """
    path = (data.get("path") or "").strip()
    f = FIELD_MAP.get(path)
    if not f:
        raise HTTPException(400, detail=f"不支持的配置项: {path}")
    tester = _TESTERS.get(f.get("test") or "")
    if not tester:
        return {"status": "ok", "ok": None, "detail": "该平台暂不支持自动测试（保存后可实际调用验证）"}

    value = str(data.get("value") or "").strip() or str(_get_path(_read_local(), path) or "").strip()
    if not value:
        return {"status": "ok", "ok": False, "detail": "⚠️ 未配置 key"}

    try:
        ok, detail = tester(value)
    except Exception as e:
        ok, detail = False, f"❌ 测试异常: {str(e)[:100]}"
    logger.info("  🧪 API 测试 %s: %s", path, detail)
    return {"status": "ok", "ok": ok, "detail": detail}
