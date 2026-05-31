"""
角色注册中心 (Character Registry) — 漫剧视频工厂

功能:
  - 注册/管理/切换主角
  - 存储角色描述、外观、性格、音色、画风
  - 生成角色描述块 (character block)，供角色适配器和视觉生成模块注入
  - 支持多角色切换

用法:
  from character_registry import CharacterRegistry
  registry = CharacterRegistry()
  char = registry.get_active_character()
  block = char.build_prompt_block(style="manhua", expression="微笑", scene="咖啡馆")
"""

import os
import json
import yaml
from pathlib import Path
from typing import Optional

# ── 默认路径 ──
SCRIPTS_DIR = Path(__file__).resolve().parent
AVE_ROOT = SCRIPTS_DIR.parent
CACHE_DIR = Path(os.environ.get(
    "AVE_CACHE_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local/tools/ave/cache/character_registry")
))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_FILE = SCRIPTS_DIR / "registry.yaml"
CHARACTERS_DIR = CACHE_DIR / "characters"
CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════
# 角色类
# ═══════════════════════════════════════════════════════════

class Character:
    """单个角色的完整定义"""

    def __init__(self, data: dict):
        self.name: str = data.get("name", "未命名")
        self.description: str = data.get("description", "")
        self.appearance: list[str] = data.get("appearance", [])
        self.personality: str = data.get("personality", "")
        self.voice_style: str = data.get("voice_style", "默认")
        self.art_style: str = data.get("art_style", "")
        self.default_bgm_style: str = data.get("default_bgm_style", "治愈")
        self.preferred_bgm_tags: list[str] = data.get("preferred_bgm_tags", [])
        self.reference_images: dict = data.get("reference_images", {})
        self.prompt_template: dict = data.get("prompt_template", {})
        self._raw = data

    # ── 角色描述块生成 ──

    def build_prompt_block(self, style: str = "manhua", expression: str = "中性",
                           scene: str = "", camera_angle: str = "中景") -> str:
        """
        构建角色描述块，用于注入视觉生成 prompt

        参数:
          style: "manhua" | "realistic"
          expression: 角色当前表情/情绪
          scene: 场景描述
          camera_angle: 镜头角度

        返回:
          格式化的角色描述块字符串
        """
        app_desc = "，".join(self.appearance[:3])  # 取前3个外观特征
        char_desc = f"{self.name}，{app_desc}"

        template = self.prompt_template.get(style, "")
        if template:
            return template.format(
                character_desc=char_desc,
                scene_desc=scene,
                expression=expression,
                camera_angle=camera_angle,
            )

        # 默认模板
        if style == "manhua":
            return (
                f"[角色] {char_desc}\n"
                f"[场景] {scene}\n"
                f"[表情] {expression}\n"
                f"[画风] {self.art_style}\n"
                f"[镜头] {camera_angle}"
            )
        else:
            return (
                f"[角色] {char_desc}\n"
                f"[场景] {scene}\n"
                f"[表情] {expression}\n"
                f"[画风] 电影级摄影，写实风格\n"
                f"[镜头] {camera_angle}"
            )

    def to_storyboard_block(self) -> dict:
        """生成角色描述块 JSON（供分镜引用）"""
        return {
            "character_name": self.name,
            "appearance": self.appearance,
            "personality": self.personality,
            "voice_style": self.voice_style,
            "art_style": self.art_style,
            "reference_images": self.reference_images,
            "default_bgm_style": self.default_bgm_style,
        }

    def to_dict(self) -> dict:
        return self._raw

    def __repr__(self) -> str:
        return f"<Character: {self.name}>"


# ═══════════════════════════════════════════════════════════
# 角色注册中心
# ═══════════════════════════════════════════════════════════

class CharacterRegistry:
    """角色注册中心 — 管理所有已注册角色"""

    def __init__(self, registry_path: Optional[str] = None):
        self._registry_path = Path(registry_path or REGISTRY_FILE)
        self._characters: dict[str, Character] = {}
        self._active_name: str = ""
        self._load()

    # ── 加载/刷新 ──

    def _load(self):
        """从 registry.yaml 加载角色"""
        if not self._registry_path.exists():
            raise FileNotFoundError(f"角色注册文件不存在: {self._registry_path}")

        with open(self._registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self._active_name = data.get("active_character", "")
        chars = data.get("characters", {})

        for name, char_data in chars.items():
            char_data["name"] = name
            self._characters[name] = Character(char_data)

        if not self._active_name and self._characters:
            self._active_name = list(self._characters.keys())[0]

    def reload(self):
        """重新加载注册文件"""
        self._load()

    # ── 查询 ──

    def get_active_character(self) -> Character:
        """获取当前激活的角色"""
        if self._active_name in self._characters:
            return self._characters[self._active_name]
        raise KeyError(f"未找到激活角色: {self._active_name}")

    def get_character(self, name: str) -> Character:
        """按名字获取角色"""
        if name in self._characters:
            return self._characters[name]
        raise KeyError(f"未找到角色: {name}")

    def list_characters(self) -> list[str]:
        """列出所有已注册角色名"""
        return list(self._characters.keys())

    def get_active_name(self) -> str:
        return self._active_name

    # ── 参考图管理 ──

    def set_reference_image(self, name: str, key: str, path: str) -> bool:
        """
        设置角色的单张参考图路径

        参数:
          name: 角色名
          key: 参考图类型 (portrait / grid / full_body / expressions.happy 等)
          path: 图片文件路径

        使用嵌套 key 的示例: set_reference_image("小漫", "expressions.happy", "...")
        """
        char = self.get_character(name)
        if "." in key:
            # 嵌套 key: "expressions.happy" → reference_images["expressions"]["happy"]
            parts = key.split(".", 1)
            if parts[0] not in char.reference_images:
                char.reference_images[parts[0]] = {}
            char.reference_images[parts[0]][parts[1]] = path
        else:
            char.reference_images[key] = path

        # 同步到 _raw 以持久化
        char._raw["reference_images"] = char.reference_images
        self._save()
        return True

    def update_reference_images(self, name: str, images: dict) -> bool:
        """
        批量更新角色的参考图路径

        参数:
          name: 角色名
          images: {
              "portrait": "path/to/portrait.png",
              "grid": "path/to/grid.png",
              "expressions": {"happy": "...", "sad": "...", "angry": "..."}
          }
        """
        char = self.get_character(name)
        # 深度合并
        for key, value in images.items():
            if isinstance(value, dict) and key in char.reference_images and isinstance(char.reference_images[key], dict):
                char.reference_images[key].update(value)
            else:
                char.reference_images[key] = value

        char._raw["reference_images"] = char.reference_images
        self._save()
        return True

    def get_reference_images(self, name: str) -> dict:
        """获取角色的所有参考图路径"""
        char = self.get_character(name)
        return dict(char.reference_images)

    def clear_reference_images(self, name: str) -> bool:
        """清空角色的参考图路径"""
        char = self.get_character(name)
        char.reference_images = {}
        char._raw["reference_images"] = {}
        self._save()
        return True

    # ── 切换/注册 ──

    def switch_to(self, name: str) -> bool:
        """切换到指定角色"""
        if name not in self._characters:
            raise KeyError(f"未找到角色: {name}")
        self._active_name = name
        self._save()
        return True

    def register(self, character_data: dict) -> Character:
        """注册新角色"""
        name = character_data.get("name", "")
        if not name:
            raise ValueError("角色必须包含 name 字段")

        self._characters[name] = Character(character_data)
        if not self._active_name:
            self._active_name = name
        self._save()
        return self._characters[name]

    def delete(self, name: str) -> bool:
        """删除角色"""
        if name not in self._characters:
            return False
        del self._characters[name]
        if self._active_name == name:
            self._active_name = list(self._characters.keys())[0] if self._characters else ""
        self._save()
        return True

    # ── 持久化 ──

    def _save(self):
        """保存当前状态到 registry.yaml"""
        chars_dict = {}
        for name, char in self._characters.items():
            chars_dict[name] = char.to_dict()

        data = {
            "active_character": self._active_name,
            "characters": chars_dict,
        }
        with open(self._registry_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def __len__(self) -> int:
        return len(self._characters)

    def __repr__(self) -> str:
        return f"<CharacterRegistry: {self._active_name} active, {len(self)} total>"


# ═══════════════════════════════════════════════════════════
# 独立使用入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    registry = CharacterRegistry()
    print(f"角色注册中心: {registry}")
    print(f"活跃角色: {registry.get_active_name()}")

    char = registry.get_active_character()
    print(f"\n角色详情:")
    print(f"  名字: {char.name}")
    print(f"  描述: {char.description}")
    print(f"  外观: {char.appearance}")
    print(f"  性格: {char.personality}")
    print(f"  音色: {char.voice_style}")
    print(f"  画风: {char.art_style}")

    print(f"\n角色描述块 (漫剧):")
    print(char.build_prompt_block(style="manhua", expression="微笑", scene="清晨的咖啡馆"))
