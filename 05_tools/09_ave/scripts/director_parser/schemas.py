"""

AVE 01_director_parser — 导演脚本解析器

职责:
  1. schemas.py: YAML 结构定义 + Pydantic 校验
  2. parser.py: 文案 → director_script.yaml (调用本地 oMLX)

本地 LLM (oMLX) 路径:
  http://localhost:8000/v1/chat/completions
  模型: Qwen3.5-4B-MLX-4bit
  API Key: omlx
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum


class StyleEnum(str, Enum):
    knowledge_lecture = "knowledge_lecture"
    bedtime_story = "bedtime_story"
    funny_talk = "funny_talk"
    tech_review = "tech_review"


class VoiceProvider(str, Enum):
    volcano = "volcano"
    aliyun = "aliyun"


class BGMSection(BaseModel):
    section: str
    description: Optional[str] = None


class BGMMeta(BaseModel):
    provider: str = "ace_step"
    genre: str = "cinematic"
    tempo: int = 110
    mood: str = "inspirational"
    structure: list[BGMSection] = []

    @field_validator("tempo")
    @classmethod
    def tempo_range(cls, v):
        if v < 40 or v > 220:
            raise ValueError("tempo 应在 40-220 之间")
        return v


class OutputMeta(BaseModel):
    resolution: str = "1080x1920"
    fps: int = 30

    @field_validator("resolution")
    @classmethod
    def valid_resolution(cls, v):
        valid = ["1080x1920", "1920x1080", "720x1280", "1280x720"]
        if v not in valid:
            raise ValueError(f"分辨率必须是 {valid} 之一")
        return v


class MaterialSource(str, Enum):
    pexels = "pexels"
    ai_generate = "ai_generate"
    local = "local"


class MaterialConfig(BaseModel):
    source: MaterialSource = MaterialSource.pexels
    search: str = ""
    transition_in: str = "fade_in"
    transition_out: str = "dissolve"
    fallback: bool = True


class CharacterRef(BaseModel):
    """角色引用（定妆照锁定）"""
    name: str = Field(description="角色名")
    description: str = Field(description="角色描述块（跨场景一致性注入）")
    grid_path: Optional[str] = Field(default="", description="定妆照网格图路径")
    lip_sync: bool = Field(default=False, description="是否对角色视频做 LipSync")


class AvatarConfig(BaseModel):
    image_url: Optional[str] = None
    provider: str = "wan2.2_s2v"
    default_position: str = "bottom_right"


class Segment(BaseModel):
    id: int = Field(ge=1)
    text: str = Field(min_length=1)
    duration_sec: float = Field(default=10, ge=1, le=300)
    voice_emotion: str = "正常讲述"
    camera: str = "static"
    bgm_section: str = "main"
    avatar: Optional[dict] = None
    material: MaterialConfig = MaterialConfig()
    subtitles: bool = True
    character_ref: Optional[str] = Field(default=None, description="引用角色名（对应 meta.character_refs）")


class VoiceMeta(BaseModel):
    provider: VoiceProvider = VoiceProvider.volcano
    voice_id: str = "default"
    default_emotion: str = "专业沉稳"


class Meta(BaseModel):
    project_id: str = ""
    style: StyleEnum = StyleEnum.knowledge_lecture
    voice: VoiceMeta = VoiceMeta()
    bgm: BGMMeta = BGMMeta()
    output: OutputMeta = OutputMeta()
    avatar: Optional[AvatarConfig] = None
    material: dict = {"fallback": True}
    character_refs: list[CharacterRef] = Field(default=[], description="角色引用列表（定妆照一致性）")


class DirectorScript(BaseModel):
    """完整导演脚本"""
    meta: Meta = Meta()
    segments: list[Segment] = Field(min_length=1)


def validate_script(data: dict) -> DirectorScript:
    """校验并返回结构化的导演脚本"""
    return DirectorScript.model_validate(data)
