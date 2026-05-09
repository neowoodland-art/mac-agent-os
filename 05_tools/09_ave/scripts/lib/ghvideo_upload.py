#!/usr/bin/env python3
"""
AVE 文件上传助手 — 上传文件到 ghvideo Gitee 仓库获取公网直链

用途:
  即梦/火山引擎 API 需要图片/视频/音频的公网 HTTP URL。
  通过 Gitee raw 服务提供直链: https://gitee.com/babycalf/ghvideo/raw/main/{filename}

用法:
  python ghvideo_upload.py /path/to/file.jpg
  python ghvideo_upload.py --dir /path/to/dir/   # 批量上传目录下所有文件

返回:
  https://gitee.com/babycalf/ghvideo/raw/main/filename.ext
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "ave" / "ghvideo"
REPO_URL = "https://gitee.com/babycalf/ghvideo.git"
RAW_BASE = "https://gitee.com/babycalf/ghvideo/raw/main"


def main():
    parser = argparse.ArgumentParser(description="上传文件到 ghvideo 中转仓库")
    parser.add_argument("path", nargs="*", help="文件或目录路径")
    parser.add_argument("--dir", help="批量上传目录")
    args = parser.parse_args()

    files = []
    if args.dir:
        for f in sorted(Path(args.dir).iterdir()):
            if f.is_file():
                files.append(str(f))
    elif args.path:
        for p in args.path:
            if os.path.isdir(p):
                for f in sorted(Path(p).iterdir()):
                    if f.is_file():
                        files.append(str(f))
            else:
                files.append(p)
    else:
        parser.print_help()
        return

    if not files:
        print("没有文件")
        return

    # 确保仓库存在
    if not (REPO_DIR / ".git").exists():
        print(f"初始化仓库: {REPO_DIR}")
        subprocess.run(["git", "init"], cwd=REPO_DIR, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", REPO_URL], cwd=REPO_DIR, capture_output=True)

    # 复制文件到仓库目录
    for f in files:
        src = Path(f)
        if not src.exists():
            print(f"  跳过: {f} (不存在)")
            continue
        dest = REPO_DIR / src.name
        import shutil
        shutil.copy2(str(src), str(dest))
        print(f"  复制: {src.name}")

    # Git 提交推送
    subprocess.run(["git", "add", "-A"], cwd=REPO_DIR, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"upload: {len(files)} files"], cwd=REPO_DIR, capture_output=True)
    r = subprocess.run(["git", "push", "-u", "origin", "master"], cwd=REPO_DIR,
                       capture_output=True, text=True, timeout=60)
    if r.returncode == 0:
        print(f"\n✅ 推送成功! {len(files)} 个文件")
        for f in files:
            name = Path(f).name
            url = f"{RAW_BASE}/{name}"
            print(f"  {url}")
    else:
        # 可能已经有内容, 尝试 pull 再 push
        print(f"  推送失败, 尝试 pull...")
        subprocess.run(["git", "pull", "--rebase", "origin", "master"], cwd=REPO_DIR,
                       capture_output=True, timeout=30)
        r2 = subprocess.run(["git", "push", "-u", "origin", "master"], cwd=REPO_DIR,
                           capture_output=True, text=True, timeout=60)
        if r2.returncode == 0:
            print(f"✅ 推送成功!")
            for f in files:
                name = Path(f).name
                url = f"{RAW_BASE}/{name}"
                print(f"  {url}")
        else:
            print(f"❌ 推送失败: {r2.stderr[:200]}")


if __name__ == "__main__":
    main()
