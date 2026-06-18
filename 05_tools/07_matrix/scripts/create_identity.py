#!/usr/bin/env python3
"""
身份工厂 — 创建新身份（生成固化指纹 + 目录 + 配置）

用法:
  python create_identity.py <identity_name> [--platform douyin]

示例:
  python create_identity.py douyin_01
  python create_identity.py douyin_02 --platform douyin

目录结构:
  identities/{name}/
  ├── config.yaml       ← 身份配置（可编辑、可版本控制）
  ├── fingerprint.pkl   ← BrowserForge 固化指纹（不可编辑）
  └── user_data/        ← Camoufox 持久化 Profile（自动生成，不提交）
"""
import argparse
import os
import pickle
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ 需要 PyYAML: pip install pyyaml")
    sys.exit(1)

try:
    from browserforge.fingerprints import FingerprintGenerator
except ImportError:
    print("❌ 需要 browserforge: pip install browserforge")
    sys.exit(1)


# ─── 路径配置 ───

SCRIPTS_DIR = Path(__file__).parent
TOOL_DIR = SCRIPTS_DIR.parent
# identities 目录放在 agent-local/tools/matrix/identities/
from matrix_mgmt import AGENT_LOCAL
IDENTITIES_ROOT = AGENT_LOCAL / "tools" / "matrix" / "identities"


def create_identity(name: str, platform: str = "douyin", proxy: str = None):
    """创建新的虚拟身份"""

    identity_dir = IDENTITIES_ROOT / name

    # 检查是否已存在
    if identity_dir.exists():
        print(f"⚠️  身份 '{name}' 已存在: {identity_dir}")
        confirm = input("  覆盖? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ 已取消")
            return False
        import shutil
        shutil.rmtree(identity_dir)

    # 创建目录
    os.makedirs(identity_dir, exist_ok=True)
    user_data_dir = identity_dir / "user_data"
    os.makedirs(user_data_dir, exist_ok=True)

    # ── 生成 BrowserForge 指纹 ──
    print(f"\n🔄 生成指纹 (Windows/Firefox)...")
    fg = FingerprintGenerator(browser='firefox', os=('windows',))
    fp = fg.generate()

    # 保存 pickle（供 Camoufox 加载）
    fp_path = identity_dir / "fingerprint.pkl"
    with open(fp_path, 'wb') as f:
        pickle.dump(fp, f)

    # ── 生成可读的 config.yaml ──
    config = {
        'identity': {
            'name': name,
            'platform': platform,
            'proxy': proxy,
            'notes': '',
            'created_at': datetime.now().isoformat(),
            'fingerprint_file': 'fingerprint.pkl',
        },
        'window': [702, 783],  # 窗口尺寸（可手动修改）
        'fingerprint_summary': {
            'userAgent': fp.headers['User-Agent'],
            'platform': fp.navigator.platform,
            'screen': f"{fp.screen.width}x{fp.screen.height}",
            'hardwareConcurrency': fp.navigator.hardwareConcurrency,
            'fonts_count': len(fp.fonts),
            'videoCard': fp.videoCard.renderer[:60] if fp.videoCard else 'N/A',
        },
    }

    config_path = identity_dir / "config.yaml"
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    # ── 输出摘要 ──
    print(f"\n{'='*55}")
    print(f" ✅ 新身份已创建: {name}")
    print(f"{'='*55}")
    print(f"   路径:          {identity_dir}")
    print(f"   User-Agent:    {config['fingerprint_summary']['userAgent'][:70]}")
    print(f"   平台:          {config['fingerprint_summary']['platform']}")
    print(f"   屏幕:          {config['fingerprint_summary']['screen']}")
    print(f"   核心数:        {config['fingerprint_summary']['hardwareConcurrency']}")
    print(f"   字体数量:      {config['fingerprint_summary']['fonts_count']}")
    print(f"   GPU:           {config['fingerprint_summary']['videoCard']}")
    print()
    print(f" 📋 下一步: 运行登录脚本")
    print(f"    python login_identity.py {name}")
    print()

    return True


def main():
    parser = argparse.ArgumentParser(description="身份工厂 — 创建新虚拟身份")
    parser.add_argument("name", help="身份名称 (如 douyin_01)")
    parser.add_argument("--platform", "-p", default="douyin", help="目标平台 (默认 douyin)")
    parser.add_argument("--proxy", help="可选代理地址 (如 socks5://127.0.0.1:1080)")
    args = parser.parse_args()

    create_identity(
        name=args.name,
        platform=args.platform,
        proxy=args.proxy,
    )


if __name__ == "__main__":
    main()
