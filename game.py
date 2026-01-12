"""Design atlas for "We Called This Is Real" – Solmara first release blueprint.

This module replaces the earlier prototype gameplay loop with a structured
knowledge base that encodes the complete solo-dev specification. The goal is to
keep every pillar, continent brief, art bible note, and CODEX 1~150 system tag
accessible through a lightweight command-line explorer. It allows the creator to
browse, search, and export the required data before committing to full
production.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from textwrap import dedent
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Pixel sandbox data models
# ---------------------------------------------------------------------------


class EmotionState(Enum):
    """High-level mood buckets that tint interactions and UI."""

    NEUTRAL = "Neutral"
    FRIENDLY = "Friendly"
    AFFECTIONATE = "Affectionate"
    SAD = "Sad"
    HOSTILE = "Hostile"


TIME_SLOTS: Sequence[str] = ("Morning", "Afternoon", "Evening", "Night")


@dataclass(frozen=True)
class Position:
    x: int
    y: int

    def translate(self, dx: int, dy: int) -> "Position":
        return Position(self.x + dx, self.y + dy)


@dataclass(frozen=True)
class TileInfo:
    glyph: str
    name: str
    walkable: bool
    description: str


@dataclass(frozen=True)
class SceneTransition:
    target_scene: str
    location: Position
    arrival: Position
    description: str


@dataclass
class SceneDefinition:
    key: str
    name: str
    ascii_map: Sequence[str]
    spawn: Position
    description: str
    transitions: Sequence[SceneTransition]
    legend: Mapping[str, TileInfo]
    farmland_tiles: Sequence[Position] = field(default_factory=tuple)

    def width(self) -> int:
        return len(self.ascii_map[0]) if self.ascii_map else 0

    def height(self) -> int:
        return len(self.ascii_map)

    def is_within_bounds(self, pos: Position) -> bool:
        return 0 <= pos.y < self.height() and 0 <= pos.x < self.width()

    def tile_at(self, pos: Position) -> TileInfo:
        if not self.is_within_bounds(pos):
            raise ValueError("Position outside of scene bounds.")
        char = self.ascii_map[pos.y][pos.x]
        return self.legend.get(char, self.legend["."])


@dataclass(frozen=True)
class NPCScheduleEntry:
    scene: str
    position: Position


@dataclass
class NPCProfile:
    npc_id: str
    name: str
    short: str
    mood_bias: EmotionState
    schedule: Mapping[str, NPCScheduleEntry]
    dialogues: Mapping[EmotionState, str]
    map_token: str
    favorite_items: Mapping[str, int]
    neutral_items: Sequence[str]
    description: str

    def position_for(self, time_slot: str) -> Optional[NPCScheduleEntry]:
        return self.schedule.get(time_slot)

    def dialogue_for(self, emotion: EmotionState) -> str:
        if emotion in self.dialogues:
            return self.dialogues[emotion]
        if EmotionState.NEUTRAL in self.dialogues:
            return self.dialogues[EmotionState.NEUTRAL]
        return "..."


@dataclass(frozen=True)
class ItemDescriptor:
    item_id: str
    name: str
    description: str
    category: str
    emoji: str = ""


@dataclass(frozen=True)
class CropType:
    crop_id: str
    name: str
    growth_days: int
    season: str
    yield_item: str
    stages: Sequence[str]
    description: str


@dataclass
class CropInstance:
    crop_type: CropType
    planted_day: int
    age: int = 0
    watered: bool = False

    def advance_day(self) -> None:
        if self.watered and self.age < self.crop_type.growth_days:
            self.age += 1
        self.watered = False

    @property
    def ready(self) -> bool:
        return self.age >= self.crop_type.growth_days

    def glyph(self) -> str:
        if not self.crop_type.stages:
            return "?"
        stage_index = min(self.age, len(self.crop_type.stages) - 1)
        return self.crop_type.stages[stage_index]


@dataclass
class PlayerState:
    position: Position
    scene: str
    energy: int = 10
    emotion_scores: Dict[EmotionState, int] = field(
        default_factory=lambda: {state: 0 for state in EmotionState}
    )
    inventory: Dict[str, int] = field(default_factory=dict)
    relationships: Dict[str, int] = field(default_factory=dict)

    def current_emotion(self) -> EmotionState:
        ranked = sorted(
            self.emotion_scores.items(),
            key=lambda item: (item[1], item[0] is EmotionState.NEUTRAL),
            reverse=True,
        )
        emotion, score = ranked[0]
        return emotion if score > 0 else EmotionState.NEUTRAL


# ---------------------------------------------------------------------------
# Design atlas data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DesignSection:
    """Top-level design section with human-readable content."""

    key: str
    title: str
    body: str


@dataclass(frozen=True)
class SystemEntry:
    """Single CODEX system bullet (1~150)."""

    code: str
    name: str
    description: str


class DesignAtlas:
    """In-memory encyclopedia for the We Called This Is Real blueprint."""

    def __init__(self) -> None:
        self._sections: Dict[str, DesignSection] = build_sections()
        self._systems: List[SystemEntry] = build_system_entries()

    # ---- section helpers -------------------------------------------------
    def list_sections(self) -> List[Tuple[str, str]]:
        """Return key-title pairs sorted by key."""

        return sorted(((sec.key, sec.title) for sec in self._sections.values()), key=lambda item: item[0])

    def get_section(self, key: str) -> DesignSection:
        """Return a design section by key, raising KeyError if missing."""

        normalized = key.strip().lower()
        if normalized not in self._sections:
            raise KeyError(f"Unknown section '{key}'. Use 'list' to see available keys.")
        return self._sections[normalized]

    # ---- system helpers --------------------------------------------------
    def system_range(self, start: int, end: int) -> List[SystemEntry]:
        """Return CODEX entries within the inclusive range."""

        if start < 1 or end > len(self._systems):
            raise ValueError("Requested range is outside CODEX 001~150.")
        if start > end:
            raise ValueError("Start index must be less than or equal to end index.")
        # Convert to zero-based indexes.
        return self._systems[start - 1 : end]

    def search(self, keyword: str) -> Dict[str, List[str]]:
        """Search both sections and systems for a keyword."""

        needle = keyword.strip().lower()
        if not needle:
            raise ValueError("Keyword must not be empty.")

        section_hits = []
        for section in self._sections.values():
            if needle in section.title.lower() or needle in section.body.lower():
                section_hits.append(f"{section.key} – {section.title}")

        system_hits = []
        for entry in self._systems:
            if needle in entry.name.lower() or needle in entry.description.lower():
                system_hits.append(f"{entry.code} – {entry.name}")

        return {"sections": section_hits, "systems": system_hits}

    # ---- formatting helpers ---------------------------------------------
    def render_section(self, section: DesignSection) -> str:
        header = f"[{section.key}] {section.title}\n" + "-" * (len(section.title) + len(section.key) + 3)
        return f"{header}\n{section.body.strip()}\n"

    def render_systems(self, entries: Iterable[SystemEntry]) -> str:
        lines = []
        for entry in entries:
            lines.append(f"{entry.code}: {entry.name}\n    {entry.description}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pixel sandbox helpers and game loop
# ---------------------------------------------------------------------------


def build_tile_legend() -> Dict[str, TileInfo]:
    """Return the base tile palette used by the pixel sandbox."""

    return {
        "#": TileInfo("#", "Stone Wall", False, "두껍게 쌓인 성벽입니다."),
        ".": TileInfo("·", "Cobblestone", True, "돌로 깔린 마을의 길."),
        "P": TileInfo("·", "Dirt Path", True, "다져진 흙길."),
        "F": TileInfo("░", "Farmland", True, "갈아엎은 밭. 씨앗을 심을 수 있습니다."),
        "T": TileInfo("♣", "Tree", False, "무성한 나무. 도끼가 필요합니다."),
        "W": TileInfo("≈", "Water", False, "얕은 물. 반딧불과 수초가 떠다닙니다."),
        "H": TileInfo("⌂", "Home", True, "쉼터. 잠을 자거나 회복할 수 있습니다."),
        "G": TileInfo("◆", "Gate", True, "다른 지역으로 통하는 문."),
    }


def _extract_farmland(map_rows: Sequence[str]) -> Sequence[Position]:
    tiles: List[Position] = []
    for y, row in enumerate(map_rows):
        for x, char in enumerate(row):
            if char == "F":
                tiles.append(Position(x, y))
    return tuple(tiles)


def build_scene_definitions(legend: Mapping[str, TileInfo]) -> Dict[str, SceneDefinition]:
    """Construct the playable scenes for the text-based pixel prototype."""

    rodendell_map = [
        "################",
        "#....T....T..G.#",
        "#..T....##.....#",
        "#......#..T....#",
        "#..H...#.......#",
        "#......#..T....#",
        "#..T....##..T..#",
        "#....P.G.P.....#",
        "################",
    ]

    braile_map = [
        "################",
        "#......G.......#",
        "#..FFFF....TT..#",
        "#..FFFF....TT..#",
        "#..FFFF........#",
        "#..FFFF....W...#",
        "#......P...W...#",
        "#....H..P......#",
        "################",
    ]

    forest_map = [
        "################",
        "#TTTT....TTTTG.#",
        "#T....W....T...#",
        "#T..W..W..T....#",
        "#....W....T....#",
        "#..TT....TT....#",
        "#....P.........#",
        "#...H....T.....#",
        "################",
    ]

    scenes = [
        SceneDefinition(
            key="rodendell",
            name="로덴델",
            ascii_map=rodendell_map,
            spawn=Position(3, 4),
            description="왕국의 성 안쪽 마을. 기사단과 연금술사가 오가는 중심지입니다.",
            transitions=(
                SceneTransition(
                    target_scene="braile",
                    location=Position(13, 1),
                    arrival=Position(7, 1),
                    description="브레일 농촌으로 이어지는 남문.",
                ),
                SceneTransition(
                    target_scene="forest",
                    location=Position(6, 7),
                    arrival=Position(4, 6),
                    description="로렐레 숲으로 이어지는 작은 숲길.",
                ),
            ),
            legend=legend,
            farmland_tiles=_extract_farmland(rodendell_map),
        ),
        SceneDefinition(
            key="braile",
            name="브레일",
            ascii_map=braile_map,
            spawn=Position(6, 6),
            description="외곽 농촌 마을. 넓은 밭과 잔잔한 연못이 있는 힐링 지역입니다.",
            transitions=(
                SceneTransition(
                    target_scene="rodendell",
                    location=Position(7, 1),
                    arrival=Position(12, 1),
                    description="로덴델 성문으로 돌아가는 길.",
                ),
                SceneTransition(
                    target_scene="forest",
                    location=Position(13, 1),
                    arrival=Position(13, 1),
                    description="숲으로 이어지는 작은 트레일.",
                ),
            ),
            legend=legend,
            farmland_tiles=_extract_farmland(braile_map),
        ),
        SceneDefinition(
            key="forest",
            name="로렐레 숲",
            ascii_map=forest_map,
            spawn=Position(3, 6),
            description="안개와 반딧불이 감싸는 힐링 포레스트. 감정의 실타래 포털이 숨어 있습니다.",
            transitions=(
                SceneTransition(
                    target_scene="rodendell",
                    location=Position(13, 1),
                    arrival=Position(5, 7),
                    description="성으로 돌아가는 고요한 오솔길.",
                ),
                SceneTransition(
                    target_scene="braile",
                    location=Position(1, 6),
                    arrival=Position(2, 5),
                    description="브레일 연못으로 이어지는 길.",
                ),
            ),
            legend=legend,
            farmland_tiles=_extract_farmland(forest_map),
        ),
    ]

    return {scene.key: scene for scene in scenes}


def build_item_catalog() -> Dict[str, ItemDescriptor]:
    """Create the item database used in the prototype."""

    items = {
        "seed_moonbud": ItemDescriptor(
            "seed_moonbud",
            "문버드 씨앗",
            "달빛을 닮은 꽃을 피우는 씨앗입니다.",
            "Seed",
            emoji="✧",
        ),
        "seed_starbean": ItemDescriptor(
            "seed_starbean",
            "스타빈 씨앗",
            "작은 별 모양의 콩을 키울 수 있는 씨앗.",
            "Seed",
            emoji="★",
        ),
        "seed_sungrain": ItemDescriptor(
            "seed_sungrain",
            "선그레인 씨앗",
            "햇살을 머금은 밀을 키우는 종자.",
            "Seed",
            emoji="☀",
        ),
        "produce_moonbud": ItemDescriptor(
            "produce_moonbud",
            "문버드 꽃",
            "밤이 되면 은은히 빛나는 꽃송이.",
            "Produce",
            emoji="❀",
        ),
        "produce_starbean": ItemDescriptor(
            "produce_starbean",
            "스타빈",
            "하모니 레시피에 쓰이는 별빛 콩.",
            "Produce",
            emoji="✶",
        ),
        "produce_sungrain": ItemDescriptor(
            "produce_sungrain",
            "선그레인 밀",
            "따뜻한 풍미의 곡물.",
            "Produce",
            emoji="♨",
        ),
        "forage_mint": ItemDescriptor(
            "forage_mint",
            "습지 민트 묶음",
            "상쾌한 향이 감정 진정을 돕습니다.",
            "Forage",
            emoji="🌿",
        ),
        "forage_thyme": ItemDescriptor(
            "forage_thyme",
            "왕가의 백리향",
            "집중력을 높여주는 향초.",
            "Forage",
            emoji="🌱",
        ),
        "forage_lantern_moss": ItemDescriptor(
            "forage_lantern_moss",
            "랜턴 이끼",
            "은은히 빛나는 이끼. 정령을 볼 수 있게 합니다.",
            "Forage",
            emoji="✨",
        ),
        "wood_bundle": ItemDescriptor(
            "wood_bundle",
            "목재 묶음",
            "간단한 제작에 쓰이는 튼튼한 목재.",
            "Material",
            emoji="🪵",
        ),
        "watering_can": ItemDescriptor(
            "watering_can",
            "물뿌리개",
            "밭을 물 주는 데 필요한 기본 도구.",
            "Tool",
            emoji="🪣",
        ),
        "hoe": ItemDescriptor(
            "hoe",
            "괭이",
            "땅을 일구거나 밭을 정리합니다.",
            "Tool",
            emoji="⛏",
        ),
        "lute": ItemDescriptor(
            "lute",
            "현악기 루테르음",
            "감정의 실타래를 공명시키는 고대 악기.",
            "Instrument",
            emoji="🎻",
        ),
        "SOL_BR_RoyalRoseTea": ItemDescriptor(
            "SOL_BR_RoyalRoseTea",
            "로열 로즈 티",
            "귀족용 향긋한 차. 마음을 차분하게 합니다.",
            "Brew",
            emoji="🍵",
        ),
        "SOL_DI_RoyalSteak": ItemDescriptor(
            "SOL_DI_RoyalSteak",
            "로열 비프 스테이크",
            "기사단이 즐기는 묵직한 스테이크.",
            "Dish",
            emoji="🥩",
        ),
        "SOL_BR_AppleWine": ItemDescriptor(
            "SOL_BR_AppleWine",
            "솔마라 사과 와인",
            "긴장을 풀어주는 달콤한 와인.",
            "Brew",
            emoji="🍷",
        ),
        "SOL_DI_FarmersPotage": ItemDescriptor(
            "SOL_DI_FarmersPotage",
            "농부의 포타주",
            "심신을 녹이는 따뜻한 수프.",
            "Dish",
            emoji="🥣",
        ),
        "ACC_MaskSilk": ItemDescriptor(
            "ACC_MaskSilk",
            "실크 마스크",
            "클로드의 공연에서 쓰이는 고급 가면.",
            "Accessory",
            emoji="🎭",
        ),
        "CH_CharmCollar": ItemDescriptor(
            "CH_CharmCollar",
            "행운의 목장 방울",
            "리안이 아끼는 마구간 고양이의 목걸이. 친밀감을 높여 줍니다.",
            "Accessory",
            emoji="🔔",
        ),
        "SOL_BR_FireflyElixir": ItemDescriptor(
            "SOL_BR_FireflyElixir",
            "반딧불 엘릭서",
            "밤의 정령을 볼 수 있게 해 주는 음료.",
            "Brew",
            emoji="🧪",
        ),
        "SOL_DI_IroncapStew": ItemDescriptor(
            "SOL_DI_IroncapStew",
            "아이언캡 스튜",
            "광부들이 즐겨 먹는 진득한 스튜.",
            "Dish",
            emoji="🍲",
        ),
        "SWEET_HoneyTart": ItemDescriptor(
            "SWEET_HoneyTart",
            "허니 타르트",
            "달콤한 벌꿀과 라벤더 향이 어우러진 힐링 디저트.",
            "Dessert",
            emoji="🥧",
        ),
        "PLAY_ChalkSet": ItemDescriptor(
            "PLAY_ChalkSet",
            "분필 놀이 세트",
            "광장 돌길에 hopscotch 판을 그릴 수 있는 다채로운 분필.",
            "Toy",
            emoji="🖍️",
        ),
        "TOY_WoodTop": ItemDescriptor(
            "TOY_WoodTop",
            "나무 팽이",
            "균형 잡힌 목재 팽이. 집중하면 오래 회전한다.",
            "Toy",
            emoji="🪀",
        ),
    }

    return items


def build_crop_catalog() -> Dict[str, CropType]:
    """Define cultivable crops for the Solmara prototype."""

    return {
        "moonbud": CropType(
            crop_id="moonbud",
            name="문버드",
            growth_days=3,
            season="Spring",
            yield_item="produce_moonbud",
            stages=("·", "ˢ", "❀"),
            description="달빛을 머금어 부드러운 향을 내는 꽃.",
        ),
        "starbean": CropType(
            crop_id="starbean",
            name="스타빈",
            growth_days=4,
            season="Summer",
            yield_item="produce_starbean",
            stages=("·", "✧", "✶"),
            description="콩 속에 별빛이 반짝이는 작물.",
        ),
        "sungrain": CropType(
            crop_id="sungrain",
            name="선그레인",
            growth_days=5,
            season="Autumn",
            yield_item="produce_sungrain",
            stages=("·", "✱", "♨"),
            description="햇살을 닮은 따뜻한 곡물.",
        ),
    }


def build_npc_profiles(items: Mapping[str, ItemDescriptor]) -> Dict[str, NPCProfile]:
    """Return the Solmara core NPC roster."""

    def gift_delta(*item_ids: str) -> Dict[str, int]:
        return {item_id: GIFT_WEIGHTS.get(item_id, 2) for item_id in item_ids}

    profiles = [
        NPCProfile(
            npc_id="SOL_NPC_SEIRA",
            name="세이라",
            short="Seira",
            mood_bias=EmotionState.FRIENDLY,
            schedule={
                "Morning": NPCScheduleEntry("rodendell", Position(6, 2)),
                "Afternoon": NPCScheduleEntry("rodendell", Position(6, 2)),
                "Evening": NPCScheduleEntry("rodendell", Position(12, 1)),
                "Night": NPCScheduleEntry("rodendell", Position(4, 4)),
            },
            dialogues={
                EmotionState.NEUTRAL: "훈련을 계속해야 해. 다친 곳은 없지?",
                EmotionState.FRIENDLY: "오늘은 마을을 순찰했어. 함께 걸을래?",
                EmotionState.AFFECTIONATE: "너와 함께라면 검도 마음도 흔들리지 않아.",
                EmotionState.SAD: "아직 지켜야 할 사람들을 지키지 못했어.",
            },
            map_token="S",
            favorite_items=gift_delta(
                "SOL_DI_RoyalSteak",
                "SOL_BR_RoyalRoseTea",
                "SOL_DI_FarmersPotage",
            ),
            neutral_items=("forage_thyme", "produce_starbean"),
            description="정의감 넘치는 기사 후보생. 책임과 사랑 사이에서 갈등한다.",
        ),
        NPCProfile(
            npc_id="SOL_NPC_BERTA",
            name="베르타",
            short="Berta",
            mood_bias=EmotionState.SAD,
            schedule={
                "Morning": NPCScheduleEntry("rodendell", Position(3, 3)),
                "Afternoon": NPCScheduleEntry("rodendell", Position(3, 3)),
                "Evening": NPCScheduleEntry("rodendell", Position(3, 3)),
                "Night": NPCScheduleEntry("rodendell", Position(3, 3)),
            },
            dialogues={
                EmotionState.NEUTRAL: "실험 노트를 정리해야겠어. 감정은 변수일 뿐이야.",
                EmotionState.FRIENDLY: "네가 가져온 재료 덕분에 새로운 조합을 시도했어.",
                EmotionState.AFFECTIONATE: "감정이 공식이 될 수 있다는 걸 네가 보여 줬어.",
                EmotionState.SAD: "언젠가 실험이 누군가를 구할 수 있을까?",
            },
            map_token="B",
            favorite_items=gift_delta(
                "SOL_BR_FireflyElixir",
                "SOL_BR_RoyalRoseTea",
                "forage_thyme",
            ),
            neutral_items=("forage_lantern_moss", "produce_moonbud"),
            description="연금술 연구소의 수석 연금술사. 감정보다 논리를 신뢰한다.",
        ),
        NPCProfile(
            npc_id="SOL_NPC_CLAUDE",
            name="클로드",
            short="Claude",
            mood_bias=EmotionState.FRIENDLY,
            schedule={
                "Morning": NPCScheduleEntry("rodendell", Position(5, 6)),
                "Afternoon": NPCScheduleEntry("rodendell", Position(5, 6)),
                "Evening": NPCScheduleEntry("rodendell", Position(5, 6)),
                "Night": NPCScheduleEntry("rodendell", Position(5, 6)),
            },
            dialogues={
                EmotionState.NEUTRAL: "웃음은 감정을 비추는 거울이야! 공연 보고 갈래?",
                EmotionState.FRIENDLY: "네가 웃을 때 관객들도 따라 웃어. 그게 내가 원하는 무대야.",
                EmotionState.AFFECTIONATE: "네가 무대에 서면 내 연출이 완성될 것 같아.",
                EmotionState.SAD: "가끔은 무대 뒤에서 울고 싶을 때도 있어.",
            },
            map_token="C",
            favorite_items=gift_delta(
                "ACC_MaskSilk",
                "SOL_BR_AppleWine",
            ),
            neutral_items=("produce_starbean", "SOL_DI_RoyalSteak"),
            description="광장에서 관객의 감정을 끌어올리는 광대.",
        ),
        NPCProfile(
            npc_id="SOL_NPC_LIAN",
            name="리안",
            short="Lian",
            mood_bias=EmotionState.SAD,
            schedule={
                "Morning": NPCScheduleEntry("braile", Position(4, 2)),
                "Afternoon": NPCScheduleEntry("braile", Position(4, 3)),
                "Evening": NPCScheduleEntry("braile", Position(6, 5)),
                "Night": NPCScheduleEntry("braile", Position(5, 7)),
            },
            dialogues={
                EmotionState.NEUTRAL: "오늘도 송아지를 돌봐야 해. 관찰자가 보고 있다는데 믿어?",
                EmotionState.FRIENDLY: "연못에 비친 별이 네가 왔다는 걸 알려 줘.",
                EmotionState.AFFECTIONATE: "다음 생에서도 널 알아볼 수 있을까?",
                EmotionState.SAD: "또 누군가를 보내야 했어. 하지만 다시 만나겠지?",
            },
            map_token="L",
            favorite_items=gift_delta(
                "SOL_DI_FarmersPotage",
                "SOL_BR_AppleWine",
                "CH_CharmCollar",
            ),
            neutral_items=("produce_moonbud",),
            description="감정 기복이 큰 목장 소년. 관찰자 이야기를 자주 꺼낸다.",
        ),
        NPCProfile(
            npc_id="SOL_NPC_MAIRA",
            name="마이라",
            short="Maira",
            mood_bias=EmotionState.AFFECTIONATE,
            schedule={
                "Morning": NPCScheduleEntry("braile", Position(5, 6)),
                "Afternoon": NPCScheduleEntry("braile", Position(5, 6)),
                "Evening": NPCScheduleEntry("braile", Position(5, 6)),
                "Night": NPCScheduleEntry("braile", Position(5, 6)),
            },
            dialogues={
                EmotionState.NEUTRAL: "여관은 언제나 따뜻해야 해. 너도 쉬고 가렴.",
                EmotionState.FRIENDLY: "차 한 잔 할래? 마음이 조금씩 치유되는 느낌이야.",
                EmotionState.AFFECTIONATE: "네가 있어야 벽난로 불빛이 완성돼.",
                EmotionState.SAD: "오늘은 손님들의 이야기가 더 깊게 다가오네.",
            },
            map_token="M",
            favorite_items=gift_delta(
                "SOL_BR_RoyalRoseTea",
                "SOL_BR_AppleWine",
                "SOL_DI_FarmersPotage",
            ),
            neutral_items=("produce_sungrain",),
            description="삶의 굴곡을 지나 온 여관 주인. 따뜻한 위로를 건넨다.",
        ),
        NPCProfile(
            npc_id="SOL_NPC_SENTINEL",
            name="순찰 기사",
            short="Sentinel",
            mood_bias=EmotionState.NEUTRAL,
            schedule={
                "Morning": NPCScheduleEntry("rodendell", Position(12, 1)),
                "Afternoon": NPCScheduleEntry("rodendell", Position(12, 1)),
                "Evening": NPCScheduleEntry("rodendell", Position(12, 1)),
                "Night": NPCScheduleEntry("rodendell", Position(12, 1)),
            },
            dialogues={
                EmotionState.NEUTRAL: "규칙은 모두를 지키기 위한 것. 통행증은 잊지 마.",
                EmotionState.FRIENDLY: "네가 세이라를 도와줬다고 들었어. 신뢰할 수 있는 사람이군.",
                EmotionState.AFFECTIONATE: "규칙보다 사람을 믿게 해 준 건 네가 처음이야.",
                EmotionState.SAD: "사람을 믿고 싶지만 책임이 발목을 잡네.",
            },
            map_token="K",
            favorite_items=gift_delta(
                "SOL_DI_RoyalSteak",
                "SOL_DI_IroncapStew",
            ),
            neutral_items=("produce_sungrain",),
            description="성문을 지키는 기사. 의무감과 따뜻함 사이에서 균형을 찾는다.",
        ),
        NPCProfile(
            npc_id="SOL_NPC_MINA",
            name="미나",
            short="Mina",
            mood_bias=EmotionState.FRIENDLY,
            schedule={
                "Morning": NPCScheduleEntry("rodendell", Position(7, 4)),
                "Afternoon": NPCScheduleEntry("rodendell", Position(8, 4)),
                "Evening": NPCScheduleEntry("rodendell", Position(6, 5)),
                "Night": NPCScheduleEntry("rodendell", Position(4, 4)),
            },
            dialogues={
                EmotionState.NEUTRAL: "돌 위에 hopscotch 선을 그렸어. 밟지 않을 거지?",
                EmotionState.FRIENDLY: "같이 뛰면 분필이 더 반짝거려!",
                EmotionState.AFFECTIONATE: "너와 놀면 세이라 언니도 웃는 것 같아.",
                EmotionState.SAD: "비가 오면 선이 다 번져버려… 그래도 내일 다시 그리면 되겠지?",
            },
            map_token="m",
            favorite_items=gift_delta("SWEET_HoneyTart", "PLAY_ChalkSet"),
            neutral_items=("forage_mint",),
            description="광장의 쌍둥이 언니. hopscotch와 숨바꼭질로 사람들의 마음을 녹인다.",
        ),
        NPCProfile(
            npc_id="SOL_NPC_MINO",
            name="미노",
            short="Mino",
            mood_bias=EmotionState.FRIENDLY,
            schedule={
                "Morning": NPCScheduleEntry("rodendell", Position(6, 5)),
                "Afternoon": NPCScheduleEntry("rodendell", Position(7, 6)),
                "Evening": NPCScheduleEntry("braile", Position(6, 4)),
                "Night": NPCScheduleEntry("braile", Position(5, 5)),
            },
            dialogues={
                EmotionState.NEUTRAL: "팽이가 얼마나 오래 도는지 세어볼래?",
                EmotionState.FRIENDLY: "손바닥으로 살짝 밀어주면 더 오래 돌아!",
                EmotionState.AFFECTIONATE: "너랑 있으면 팽이도 길을 잃지 않는대.",
                EmotionState.SAD: "팽이가 멈추면 마음도 멈춘 것 같아… 다시 돌려줄래?",
            },
            map_token="n",
            favorite_items=gift_delta("TOY_WoodTop", "PLAY_ChalkSet"),
            neutral_items=("SWEET_HoneyTart",),
            description="장난기 많은 쌍둥이 동생. 팽이놀이로 플레이어의 긴장을 풀어 준다.",
        ),
        NPCProfile(
            npc_id="SOL_NPC_HARK",
            name="하크",
            short="Hark",
            mood_bias=EmotionState.NEUTRAL,
            schedule={
                "Morning": NPCScheduleEntry("rodendell", Position(12, 2)),
                "Afternoon": NPCScheduleEntry("rodendell", Position(11, 2)),
                "Evening": NPCScheduleEntry("rodendell", Position(11, 4)),
                "Night": NPCScheduleEntry("braile", Position(5, 6)),
            },
            dialogues={
                EmotionState.NEUTRAL: "검을 내려놓고도 지킬 약속은 남아 있지.",
                EmotionState.FRIENDLY: "성문이란 건 사람을 믿어야 지켜진다네.",
                EmotionState.AFFECTIONATE: "자네 덕분에 다시 마음을 여는 법을 기억했지.",
                EmotionState.SAD: "지키지 못한 이름이 아직 귓가를 맴돈다…",
            },
            map_token="H",
            favorite_items=gift_delta("SOL_BR_AppleWine", "SOL_DI_IroncapStew"),
            neutral_items=("SWEET_HoneyTart",),
            description="퇴역 기사. 약속과 책임의 무게를 이야기로 전한다.",
        ),
    ]

    return {profile.npc_id: profile for profile in profiles}


GIFT_WEIGHTS: Dict[str, int] = {
    "SOL_BR_RoyalRoseTea": 4,
    "SOL_DI_RoyalSteak": 4,
    "SOL_BR_AppleWine": 3,
    "SOL_DI_FarmersPotage": 4,
    "ACC_MaskSilk": 4,
    "SOL_BR_FireflyElixir": 4,
    "SOL_DI_IroncapStew": 4,
    "CH_CharmCollar": 3,
    "SWEET_HoneyTart": 4,
    "PLAY_ChalkSet": 4,
    "TOY_WoodTop": 4,
}


class ArcPixelGame:
    """Cozy sandbox prototype that mirrors the Solmara slice in text form."""

    def __init__(self) -> None:
        self.legend = build_tile_legend()
        self.scenes = build_scene_definitions(self.legend)
        self.items = build_item_catalog()
        self.crop_types = build_crop_catalog()
        self.npcs = build_npc_profiles(self.items)
        self.farmland_sets = {key: set(scene.farmland_tiles) for key, scene in self.scenes.items()}
        self.forage_table: Dict[str, Sequence[str]] = {
            "rodendell": ("forage_thyme", "wood_bundle", "seed_starbean"),
            "braile": ("forage_mint", "produce_moonbud", "seed_moonbud"),
            "forest": ("forage_lantern_moss", "produce_starbean", "seed_sungrain"),
        }
        self.max_log_entries = 24
        self.reset_state()

    # ---- high-level helpers -------------------------------------------
    def reset_state(self) -> None:
        start_scene = self.scenes["rodendell"]
        self.player = PlayerState(position=start_scene.spawn, scene=start_scene.key)
        self.player.inventory.update(
            {
                "seed_moonbud": 3,
                "seed_starbean": 2,
                "seed_sungrain": 1,
                "watering_can": 1,
                "hoe": 1,
                "lute": 1,
                "SOL_DI_FarmersPotage": 1,
                "SOL_BR_RoyalRoseTea": 1,
                "SOL_BR_AppleWine": 1,
                "SWEET_HoneyTart": 1,
                "PLAY_ChalkSet": 1,
                "TOY_WoodTop": 1,
            }
        )
        for npc_id in self.npcs:
            self.player.relationships[npc_id] = 0
        self.crop_plots: Dict[Tuple[str, Position], CropInstance] = {}
        self.day = 1
        self._time_index = 0
        self._time_meter = 0
        self.must_sleep = False
        self.log: List[str] = []

    # Properties ---------------------------------------------------------
    @property
    def current_scene(self) -> SceneDefinition:
        return self.scenes[self.player.scene]

    def current_time_slot(self) -> str:
        return TIME_SLOTS[self._time_index]

    # Logging ------------------------------------------------------------
    def log_event(self, message: str) -> None:
        stamp = f"Day {self.day} {self.current_time_slot()}"
        entry = f"[{stamp}] {message}"
        self.log.append(entry)
        if len(self.log) > self.max_log_entries:
            self.log.pop(0)

    # Command loop -------------------------------------------------------
    def run(self) -> None:
        self.reset_state()
        print("\n=== Solmara Pixel Prototype ===")
        print("'help'로 명령을 확인하고, 'quit'으로 아틀라스로 돌아갑니다.\n")
        self.describe_scene()
        while True:
            try:
                raw = input("solmara> ").strip()
            except EOFError:
                print()
                break

            if not raw:
                continue

            lowered = raw.lower()
            if lowered in {"quit", "exit"}:
                print("솔마라 산책을 마치고 아틀라스로 돌아갑니다.\n")
                break

            self.dispatch_command(raw)

    def dispatch_command(self, raw: str) -> None:
        tokens = raw.split()
        command = tokens[0].lower()
        args = tokens[1:]

        restful_commands = {"sleep", "rest", "look", "map", "help", "where", "status", "inventory", "inv", "log"}
        if self.must_sleep and command not in restful_commands:
            print("밤이 깊어 행동할 수 없습니다. 'sleep'으로 휴식하세요.")
            return

        if command in {"help", "?"}:
            self.show_help()
        elif command in {"look", "map"}:
            self.render_map()
        elif command in {"where", "status"}:
            self.show_status()
        elif command == "inventory" or command == "inv":
            self.show_inventory()
        elif command == "log":
            self.show_log()
        elif command == "move" and args:
            self.move_player(args[0])
        elif command in {"north", "south", "east", "west", "n", "s", "e", "w"}:
            self.move_player(command)
        elif command == "travel":
            target = " ".join(args) if args else ""
            self.travel_to(target)
        elif command == "talk" and args:
            self.talk_to(" ".join(args))
        elif command == "gift" and len(args) >= 2:
            item_token = args[0]
            npc_name = " ".join(args[1:])
            self.give_gift(item_token, npc_name)
        elif command == "plant" and args:
            self.plant_crop(" ".join(args))
        elif command == "water":
            self.water_crop()
        elif command == "harvest":
            self.harvest_crop()
        elif command == "forage":
            self.forage()
        elif command in {"sleep", "rest"}:
            self.sleep()
        elif command == "wait":
            self.progress_time(energy_cost=0, time_cost=1)
            self.log_event("잠시 숨을 고르며 주변을 둘러봤습니다.")
        else:
            print("알 수 없는 명령입니다. 'help'를 참고하세요.")

    # Rendering ----------------------------------------------------------
    def show_help(self) -> None:
        print(
            dedent(
                """
                사용 가능한 명령
                - look/map: 현재 지도를 확인합니다.
                - where/status: 날짜, 시간대, 감정, 관계를 요약합니다.
                - move <방향> 또는 n/s/e/w: 한 칸 이동합니다.
                - travel [지역]: 출입구에 있을 때 다른 씬으로 이동합니다.
                - talk <NPC>: 인접한 NPC와 대화합니다.
                - gift <아이템> <NPC>: 아이템을 선물합니다.
                - plant <작물>: 밭 위에서 씨앗을 심습니다.
                - water: 물뿌리개로 작물을 물 줍니다.
                - harvest: 성장한 작물을 수확합니다.
                - forage: 주변에서 자원을 채집합니다.
                - inventory: 보유 아이템을 확인합니다.
                - log: 오늘의 행동 로그를 열람합니다.
                - sleep: 휴식을 취하고 다음 날로 넘어갑니다.
                - quit: 픽셀 프로토타입을 종료합니다.
                """
            ).strip()
        )

    def render_map(self) -> None:
        scene = self.current_scene
        npc_positions = {
            entry.position: npc
            for npc in self.active_npcs()
            if (entry := npc.position_for(self.current_time_slot())) and entry.scene == scene.key
        }
        rows: List[str] = []
        for y, row in enumerate(scene.ascii_map):
            chars: List[str] = []
            for x, base_char in enumerate(row):
                pos = Position(x, y)
                glyph = scene.legend.get(base_char, scene.legend["."] ).glyph
                crop = self.crop_plots.get((scene.key, pos))
                if crop:
                    glyph = crop.glyph()
                    if crop.watered:
                        glyph = glyph.upper()
                if pos == self.player.position:
                    glyph = "@"
                elif pos in npc_positions:
                    glyph = npc_positions[pos].map_token
                chars.append(glyph)
            rows.append("".join(chars))
        print("\n".join(rows))
        if npc_positions:
            listing = ", ".join(npc.name for npc in npc_positions.values())
            print(f"NPC 인접: {listing}")
        else:
            print("NPC 인접: 없음")
        self.describe_tile()

    def describe_scene(self) -> None:
        scene = self.current_scene
        print(f"현재 위치: {scene.name}")
        print(scene.description)
        self.render_map()

    def describe_tile(self) -> None:
        scene = self.current_scene
        tile = scene.tile_at(self.player.position)
        print(f"타일: {tile.name} – {tile.description}")
        crop = self.crop_plots.get((scene.key, self.player.position))
        if crop:
            progress = f"{crop.age}/{crop.crop_type.growth_days}"
            status = "수확 가능" if crop.ready else f"성장 중({progress})"
            water = "물 공급" if crop.watered else "건조"
            print(f"  · {crop.crop_type.name}: {status}, {water}")
        exits = [t for t in scene.transitions if t.location == self.player.position]
        for transition in exits:
            target_name = self.scenes[transition.target_scene].name
            print(f"  · 출입구: {transition.description} → {target_name}")

    def show_status(self) -> None:
        emotion = self.player.current_emotion().value
        print(
            f"Day {self.day} / {self.current_time_slot()} / 에너지 {self.player.energy}/10 / 현재 감정 {emotion}"
        )
        important = []
        for npc_id, score in sorted(self.player.relationships.items(), key=lambda item: item[1], reverse=True):
            npc = self.npcs[npc_id]
            important.append(f"{npc.name}: {score}")
        if important:
            print("관계: " + ", ".join(important))
        else:
            print("관계: 아직 인연이 쌓이지 않았습니다.")

    def show_inventory(self) -> None:
        if not self.player.inventory:
            print("인벤토리가 비어 있습니다.")
            return
        print("보유 아이템:")
        for item_id, qty in sorted(self.player.inventory.items()):
            descriptor = self.items.get(item_id)
            if descriptor:
                emoji = f"{descriptor.emoji} " if descriptor.emoji else ""
                print(f"- {emoji}{descriptor.name} ×{qty}")
            else:
                print(f"- {item_id} ×{qty}")

    def show_log(self) -> None:
        if not self.log:
            print("아직 기록된 로그가 없습니다.")
            return
        for entry in self.log[-12:]:
            print(entry)

    # Gameplay actions ---------------------------------------------------
    def move_player(self, direction: str) -> None:
        dir_map = {
            "north": (0, -1),
            "n": (0, -1),
            "south": (0, 1),
            "s": (0, 1),
            "east": (1, 0),
            "e": (1, 0),
            "west": (-1, 0),
            "w": (-1, 0),
        }
        if direction not in dir_map:
            print("이동할 방향을 n/s/e/w 중에서 선택하세요.")
            return
        dx, dy = dir_map[direction]
        scene = self.current_scene
        new_pos = self.player.position.translate(dx, dy)
        if not scene.is_within_bounds(new_pos):
            print("이 방향으로는 나아갈 수 없습니다.")
            return
        tile = scene.tile_at(new_pos)
        if not tile.walkable:
            print(f"{tile.name} 때문에 막혀 있습니다.")
            return
        self.player.position = new_pos
        self.progress_time(energy_cost=1, time_cost=1)
        self.log_event("한 걸음 이동했습니다.")
        self.describe_tile()

    def travel_to(self, target: str) -> None:
        scene = self.current_scene
        exits = [t for t in scene.transitions if t.location == self.player.position]
        if not exits:
            print("이 위치에는 출입구가 없습니다.")
            return
        if not target and len(exits) == 1:
            destination = exits[0]
        else:
            normalized = target.lower()
            destination = None
            for candidate in exits:
                scene_name = self.scenes[candidate.target_scene].name.lower()
                if candidate.target_scene.lower() == normalized or scene_name == normalized:
                    destination = candidate
                    break
            if destination is None:
                print("이 출입구에서 이동 가능한 지역 이름을 입력하세요.")
                print("가능: " + ", ".join(self.scenes[c.target_scene].name for c in exits))
                return
        self.player.scene = destination.target_scene
        self.player.position = destination.arrival
        self.progress_time(energy_cost=1, time_cost=2)
        self.log_event(f"{self.current_scene.name}으로 이동했습니다.")
        self.describe_scene()

    def talk_to(self, npc_name: str) -> None:
        npc = self.resolve_npc(npc_name)
        if npc is None:
            print("그런 인물을 찾을 수 없습니다.")
            return
        entry = npc.position_for(self.current_time_slot())
        if not entry or entry.scene != self.player.scene:
            print(f"{npc.name}은(는) 지금 이 지역에 없습니다.")
            return
        if self.distance(self.player.position, entry.position) > 1:
            print(f"{npc.name}에게 조금 더 가까이 다가가야 합니다.")
            return
        line = npc.dialogue_for(self.player.current_emotion())
        print(f"{npc.name}: {line}")
        self.progress_time(energy_cost=1, time_cost=1)
        self.apply_emotion_shift({npc.mood_bias: 1}, f"{npc.name}의 기운이 마음에 스며듭니다.")
        self.adjust_relationship(npc, 2)

    def give_gift(self, item_token: str, npc_name: str) -> None:
        npc = self.resolve_npc(npc_name)
        if npc is None:
            print("선물을 줄 NPC를 찾을 수 없습니다.")
            return
        entry = npc.position_for(self.current_time_slot())
        if not entry or entry.scene != self.player.scene:
            print(f"{npc.name}은(는) 지금 이 지역에 없습니다.")
            return
        if self.distance(self.player.position, entry.position) > 1:
            print(f"{npc.name}에게 다가가야 선물을 건넬 수 있습니다.")
            return
        item_id = self.resolve_item_id(item_token)
        if item_id is None or self.player.inventory.get(item_id, 0) <= 0:
            print("그 아이템을 보유하고 있지 않습니다.")
            return
        preference = npc.favorite_items.get(item_id, 1)
        self.consume_item(item_id, 1)
        descriptor = self.items.get(item_id)
        item_name = descriptor.name if descriptor else item_id
        print(f"{npc.name}에게 {item_name}을(를) 건넸습니다.")
        self.progress_time(energy_cost=1, time_cost=1)
        self.adjust_relationship(npc, preference)
        self.apply_emotion_shift({EmotionState.AFFECTIONATE: 1}, "따뜻한 미소가 돌아왔습니다.")

    def plant_crop(self, crop_token: str) -> None:
        crop = self.resolve_crop(crop_token)
        if crop is None:
            print("알 수 없는 작물입니다. moonbud/starbean/sungrain 중 선택하세요.")
            return
        seed_id = f"seed_{crop.crop_id}"
        if self.player.inventory.get(seed_id, 0) <= 0:
            print("해당 씨앗이 부족합니다.")
            return
        if self.player.position not in self.farmland_sets.get(self.player.scene, set()):
            print("밭 타일 위에서만 씨앗을 심을 수 있습니다.")
            return
        key = (self.player.scene, self.player.position)
        if key in self.crop_plots:
            print("이미 작물이 자라고 있습니다.")
            return
        self.crop_plots[key] = CropInstance(crop_type=crop, planted_day=self.day)
        self.consume_item(seed_id, 1)
        self.progress_time(energy_cost=2, time_cost=2)
        self.log_event(f"{crop.name} 씨앗을 심었습니다.")
        self.apply_emotion_shift({EmotionState.FRIENDLY: 1}, "흙의 온기가 마음을 달랬습니다.")

    def water_crop(self) -> None:
        if self.player.inventory.get("watering_can", 0) <= 0:
            print("물뿌리개가 필요합니다.")
            return
        key = (self.player.scene, self.player.position)
        crop = self.crop_plots.get(key)
        if not crop:
            print("이 타일에는 물 줄 작물이 없습니다.")
            return
        if crop.watered:
            print("이미 오늘은 충분히 물을 줬습니다.")
            return
        crop.watered = True
        self.progress_time(energy_cost=1, time_cost=1)
        self.log_event(f"{crop.crop_type.name}에 물을 주었습니다.")
        self.apply_emotion_shift({EmotionState.NEUTRAL: 1}, "차분한 물소리가 균형을 잡아 줍니다.")

    def harvest_crop(self) -> None:
        key = (self.player.scene, self.player.position)
        crop = self.crop_plots.get(key)
        if not crop or not crop.ready:
            print("아직 수확할 수 있는 작물이 없습니다.")
            return
        produce_id = crop.crop_type.yield_item
        self.player.inventory[produce_id] = self.player.inventory.get(produce_id, 0) + 1
        descriptor = self.items.get(produce_id)
        item_name = descriptor.name if descriptor else produce_id
        del self.crop_plots[key]
        self.progress_time(energy_cost=2, time_cost=2)
        self.log_event(f"{item_name}을(를) 수확했습니다.")
        self.apply_emotion_shift({EmotionState.AFFECTIONATE: 1}, "수확의 기쁨이 마음을 채웠습니다.")

    def forage(self) -> None:
        options = self.forage_table.get(self.player.scene)
        if not options:
            print("이 지역에서는 채집할 수 있는 것이 없습니다.")
            return
        index = (self.day + self._time_index + len(self.log)) % len(options)
        item_id = options[index]
        self.player.inventory[item_id] = self.player.inventory.get(item_id, 0) + 1
        descriptor = self.items.get(item_id)
        item_name = descriptor.name if descriptor else item_id
        self.progress_time(energy_cost=1, time_cost=1)
        self.log_event(f"{item_name}을(를) 채집했습니다.")
        self.apply_emotion_shift({EmotionState.NEUTRAL: 1, EmotionState.FRIENDLY: 1}, "자연의 향이 마음을 안정시켰습니다.")

    def sleep(self) -> None:
        tile = self.current_scene.tile_at(self.player.position)
        if tile.name != "Home":
            print("휴식은 쉼터(H)에서만 가능합니다.")
            return
        self.log_event("포근한 침대에서 휴식을 취합니다.")
        self.advance_day()
        self.describe_scene()

    # State transitions --------------------------------------------------
    def progress_time(self, energy_cost: int, time_cost: int) -> None:
        if self.must_sleep:
            return
        self.player.energy = max(0, self.player.energy - energy_cost)
        self._time_meter += time_cost
        while self._time_meter >= 4 and self._time_index < len(TIME_SLOTS) - 1:
            self._time_meter -= 4
            self._time_index += 1
            self.log_event(f"시간이 흘러 {self.current_time_slot()}이 되었습니다.")
        if self._time_index == len(TIME_SLOTS) - 1:
            self.must_sleep = True
        if self.player.energy == 0:
            self.must_sleep = True
            print("기력이 바닥났습니다. 지금은 쉬는 것이 좋겠습니다.")

    def advance_day(self) -> None:
        for crop in self.crop_plots.values():
            crop.advance_day()
        self.day += 1
        self.player.energy = 10
        self._time_index = 0
        self._time_meter = 0
        self.must_sleep = False
        for emotion in self.player.emotion_scores:
            if emotion is not EmotionState.NEUTRAL:
                self.player.emotion_scores[emotion] = max(0, self.player.emotion_scores[emotion] - 1)
        self.log_event("새로운 아침이 밝았습니다.")

    def apply_emotion_shift(self, shifts: Mapping[EmotionState, int], note: Optional[str] = None) -> None:
        for emotion, delta in shifts.items():
            self.player.emotion_scores[emotion] = max(
                -12, min(12, self.player.emotion_scores.get(emotion, 0) + delta)
            )
        if note:
            print(note)

    def adjust_relationship(self, npc: NPCProfile, delta: int) -> None:
        current = self.player.relationships.get(npc.npc_id, 0) + delta
        self.player.relationships[npc.npc_id] = current
        state = "상승" if delta >= 0 else "하락"
        print(f"{npc.name}과의 관계가 {state}했습니다. (현재 {current})")

    # Utilities ----------------------------------------------------------
    @staticmethod
    def distance(a: Position, b: Position) -> int:
        return abs(a.x - b.x) + abs(a.y - b.y)

    def consume_item(self, item_id: str, count: int) -> None:
        current = self.player.inventory.get(item_id, 0)
        new_value = max(0, current - count)
        if new_value:
            self.player.inventory[item_id] = new_value
        elif item_id in self.player.inventory:
            del self.player.inventory[item_id]

    def resolve_item_id(self, token: str) -> Optional[str]:
        normalized = token.lower()
        for item_id, descriptor in self.items.items():
            if item_id.lower() == normalized or descriptor.name.lower() == normalized:
                return item_id
        return None

    def resolve_crop(self, token: str) -> Optional[CropType]:
        normalized = token.replace("seed_", "").lower()
        for crop in self.crop_types.values():
            if crop.crop_id == normalized or crop.name.lower() == normalized:
                return crop
        return None

    def resolve_npc(self, token: str) -> Optional[NPCProfile]:
        normalized = token.lower()
        for npc in self.npcs.values():
            if npc.npc_id.lower() == normalized or npc.name.lower() == normalized or npc.short.lower() == normalized:
                return npc
        return None

    def active_npcs(self) -> List[NPCProfile]:
        slot = self.current_time_slot()
        present = []
        for npc in self.npcs.values():
            entry = npc.position_for(slot)
            if entry and entry.scene == self.player.scene:
                present.append(npc)
        return present

# ---------------------------------------------------------------------------
# Data construction helpers
# ---------------------------------------------------------------------------


def build_sections() -> Dict[str, DesignSection]:
    sections = [
        DesignSection(
            key="vision",
            title="비전 & 핵심 기둥",
            body=dedent(
                """
                철학: 죽음은 '끝'이 아니라 '삶의 흐름 전환'이며, 감정은 세계를 바꾸는 1순위 언어다.

                핵심 기둥
                1. 감정 반응형 세계 – 색, 음악, 대사, 이벤트가 감정 상태에 맞춰 동기화된다.
                2. 전생 루프 – 기억은 잊지만 감정 패턴과 인연 경향이 다음 생에도 잔존한다.
                3. 관찰자 모드 – 자연사 후 세계를 조망하며 전생 또는 종결을 선택한다.
                4. 감정의 실타래 – 타일·음계·회상·연출이 결합된 클라이맥스 콘텐츠를 구축한다.
                5. 힐링 중심 페이스 – 긴장보다 낭만·회고·성찰을 최우선으로 디자인한다.
                """
            ),
        ),
        DesignSection(
            key="release_scope",
            title="범위: 1차 출시 & 확장 로드맵",
            body=dedent(
                """
                1차 출시(압축판)
                - 대륙: 솔마라 1개
                - 마을: 2개(로덴델, 브레일) + 인접 힐링 지역/소던전(로렐레 숲, 작은 광산)
                - 시스템: 전생, 감정, 기억, 인연, 일기, 작은 던전, 감정 연출, 관찰자, 진엔딩
                - 플레이타임: 6~10시간, 완결된 루프(전생/감정/관찰자/진엔딩 포함)

                확장 로드맵(향후 DLC/업데이트)
                - 남은 7개 대륙: 바레토스, 자다카르, 엘라리온, 신드랄리스, 원주민 대륙, 현자들의 대륙, 동방 대륙
                - 각 대륙은 고유 축제, 직업, 음식, 시스템 확장을 제공한다.
                - 1차 출시에서는 월드맵/대화/아카이브를 통해 타 대륙을 암시하고 스포일러 없는 티징을 진행한다.
                """
            ),
        ),
        DesignSection(
            key="continents",
            title="세계관: 8개 대륙 개요",
            body=dedent(
                """
                솔마라(Solmara) – 왕국 & 중세 감성
                - 문화: 귀족제, 기사도, 연금술, 대장장이. 성문 안팎의 격차가 존재한다.
                - 직업: 기사, 연금술사, 대장장이, 귀족 정치가, 농부, 여관 주인
                - 축제: 기사 토너먼트(왕국의 수호자 칭호), 왕실 무도회(변장 히든 루트)
                - 음식: 로열 비프 스테이크, 사과 와인

                바레토스(Baretos) – 어둠과 금지 마법의 대륙
                - 문화: 금기 연구, 은밀한 거래, 긴 밤
                - 직업: 네크로맨서, 어둠 연금술사, 밀수업자, 사신 계약자
                - 축제: 망자의 날(망자 교류 정보), 어둠의 시장(금지 아이템)
                - 음식: 암흑 스튜(MP 회복), 망령 위스키(유령 시야)

                자다카르(Zadakar) – 사막과 유적
                - 문화: 부족 사회, 생존 기술, 유물 사냥꾼 허브
                - 직업: 모래 마법사, 유물 사냥꾼, 대상, 생존가
                - 축제: 유적 탐험 경연, 사막의 춤 축제(야간)
                - 음식: 선인장 주스, 바람의 빵

                엘라리온(Elarion) – 자연과 정령
                - 문화: 자연 조화, 엘프·드루이드, 동식물과의 유대
                - 직업: 드루이드, 정령사, 약초학자, 숲 사냥꾼
                - 축제: 정령의 축제(특별 마법 습득), 대자연 감사제
                - 음식: 꽃잎 수프(랜덤 버프), 달빛 과실주(자연과 대화)

                신드랄리스(Syndralis) – 하늘섬과 바람
                - 문화: 공중 도시, 비행 기술, 바람 마법
                - 직업: 바람 마법사, 비공정 조종사, 공중 상인, 날개 제작자
                - 축제: 하늘 항해 대회, 구름 수확제
                - 음식: 구름 솜사탕, 바람의 우유

                원주민 대륙(Indigenous Continent) – 야생 & 정령 부족
                - 문화: 자연과 일체, 부족 연대, 외부와의 단절
                - 직업: 주술사, 동물 조련사, 사냥꾼, 전통 예술가
                - 축제: 대자연의 축제, 정령 대화 의식
                - 음식: 야생 베리 와인, 맹수 스테이크

                현자들의 대륙(Sage Realm) – 철학과 지혜
                - 문화: 지식, 토론 중심, 무력 금지
                - 직업: 현자, 사서, 천문학자, 연금술사
                - 축제: 지혜의 밤(신규 학문 발표), 고대 문헌 개방일
                - 음식: 현자의 차(집중↑), 철학자의 빵(철학 문장)

                동방 대륙(Eastern Continent) – 한중일 혼합, 한국 비중 ↑
                - 문화: 무술, 도술, 무속, 예술 전통
                - 직업: 무도가, 도사, 검호, 서예가, 공예가
                - 축제: 매화 축제, 한밤의 검술 대결
                - 음식: 한방 찻잔떡(체력+랜덤 버프), 동방식 불고기

                ※ 1차 출시에서는 솔마라만 플레이 가능하며, 나머지 대륙은 정보 아카이브와 NPC 대화를 통해 존재감을 드러낸다.
                """
            ),
        ),
        DesignSection(
            key="global_schema",
            title="🗂️ 글로벌 스키마",
            body=dedent(
                """
                공통 열거형
                - Seasons: Spring, Summer, Autumn, Winter
                - Times: Dawn, Day, Dusk, Night
                - Rarity: Common, Uncommon, Rare, Epic, Mythic
                - Biome: City, Farmland, Forest, RiverMarsh, MountainCave, Desert, Oasis, SkyIsland, Tundra, SacredRuins, LibraryCampus, Temple, CoastHarbor, BambooHighland

                상태효과(버프/디버프)
                - Warmth: 체온을 지켜 혹한 저항을 부여한다.
                - Calm: 긴장 완화, 감정 왜곡 저항을 상승시킨다.
                - Focus: 전투/퍼즐 집중도를 올려 상호작용 난도를 낮춘다.
                - SpiritSight: 유령/정령을 가시화해 숨은 오브젝트를 노출한다.
                - Sandstride: 모래 지형 이동 보너스, 스태미나 소비 감소.
                - FeatherStep: 낙하 가속 완화, 점프 감각 향상.
                - Moonbond: 밤중 재생 및 정신력 회복을 촉진한다.
                - Blessing: 모든 저항이 소폭 상승하고 대행운 확률이 열린다.
                - Hex: 감정 왜곡과 음산 시각 이펙트를 일으키는 위험 디버프.
                - Verdancy: 채집량을 늘리고 자연친화 대화 보너스를 제공한다.
                - Nobility: 귀족/행정 상호작용 보너스를 잠시 부여한다.

                데이터 항목 표준형(전 대륙 공통)
                Flora
                - id, name, rarity, biomes, season, time, gather_yield("min-max"), uses(Cooking/Alchemy/Craft/Dye), effects(Status), emotion_shift(+/- Affectionate/Friendly/Sad/Hostile/Neutral), notes.

                Fauna
                - id, name, rarity, biomes, time, behavior(Skittish/Curious/Territorial/Pack), drops[itemId, qty, use], interaction_bonus(petting/music/hostile), emotion_shift, notes.

                Dish
                - id, name, rarity, inputs(itemId × count), effect(Status), duration_sec, side_effect(optional), emotion_shift, notes.

                Brew
                - id, name, rarity, inputs, effect(Status), duration_sec, caution(optional), emotion_shift, notes.

                Festival
                - id, name, season_window, location_biome, minigames, entry_rules(flag/emotion/item), rewards, global_effects(Status), emotion_theme, quest_hooks, notes.
                """
            ),
        ),
        DesignSection(
            key="global_lifeforms",
            title="🌍 아르크 생명체 카테고리 예시",
            body=dedent(
                """
                나무류 🌳
                1) 그로브 하트 트리 – 살아있는 나무로, 마음에 드는 존재에게 가지를 내어주며 보호한다.
                2) 그늘비 나무 – 빗물이 모이면 스스로 잎을 흔들어 작은 물방울을 내보낸다.
                3) 번개 심장목 – 뿌리에 번개 에너지를 저장하여 밤이 되면 빛을 발한다.
                ➕ 추가 아르크 나무
                - 서리속삭임 전나무 – 눈보라 속에서도 얼음종을 울려 위험을 알린다.
                - 은파 동굴목 – 동굴 천장에 매달려 빛을 흡수하고 일주일에 한 번 은빛 꽃가루를 떨어뜨린다.

                꽃류 🌸
                4) 황혼의 장미 – 태양이 질 때만 피어나며 은은한 빛을 내는 신비한 장미.
                5) 달빛 라일락 – 달빛을 흡수해 빛을 머금고 있는 향기로운 꽃.
                6) 별가루 백합 – 떨어진 꽃가루가 하늘에 떠올라 반짝이며 오래된 전설과 연결된다.
                ➕ 추가 아르크 꽃
                - 유성나팔 – 별똥별이 떨어진 자리에 피어나며, 꽃받침이 하모닉 톤을 울린다.
                - 감로 창포 – 새벽 이슬을 응축해 치유 물약의 핵심 성분을 제공한다.

                지상 생물 🐾
                7) 황금빛 늑대 – 달빛을 받으면 투명해지는 늑대.
                8) 나무를 타는 거북이 – 등껍질에서 가지가 뻗어나와 숲처럼 성장하는 거북이.
                9) 별을 먹는 사슴 – 별가루를 섭취하며 몸이 반짝이는 신비한 사슴.
                ➕ 추가 아르크 지상 생물
                - 안개몰이 여우 – 새벽에 안개를 모아 길을 숨기는 능력을 지녔다.
                - 돌숨결 라마 – 호흡으로 작은 바위 조각을 부드럽게 만들어 공예 재료를 제공한다.

                해양 생물 🌊
                10) 심해 그림자 문어 – 완전한 암흑 속에서도 그림자 속을 이동한다.
                11) 물속에서도 사는 고양이 – 아가미와 폐를 함께 지녀 수중과 지상을 오간다.
                12) 바다의 노래뱀 – 파도를 타며 울음소리를 내고, 듣는 자를 환상 속에 빠뜨린다.
                ➕ 추가 아르크 해양 생물
                - 청명 고래치 – 등지느러미가 오르골 톤을 내어 실타래 힌트를 남긴다.
                - 조류직조 해파리 – 조개껍데기와 해초를 엮어 안식처를 만들고 조류 흐름을 정화한다.

                하늘 생물 🦋
                13) 선셋 호버비 – 해 질 무렵만 날아다니며 빛을 모아 반딧불처럼 반짝인다.
                14) 구름 날개 독수리 – 하늘을 날면서 구름과 하나 되어 몸을 숨긴다.
                15) 폭풍의 휘매 – 폭풍과 함께 날아다니며 바람을 자유롭게 다루는 신비한 용.
                ➕ 추가 아르크 하늘 생물
                - 은채 비둘기 – 메아리를 저장해 멀리 떨어진 친구에게 감정을 전달한다.
                - 뇌운 글라이더 – 전기를 흡수해 공중 도시의 발전기를 보조한다.

                벌레류 🐞
                16) 썬더비틀 – 번개 속성을 가진 딱정벌레로 몸에서 정전기를 낸다.
                17) 황금빛 거미 – 황금색 실을 내어 매우 튼튼한 거미줄을 만든다.
                18) 슬로우스팍 – 달팽이와 버섯이 공생하는 생물로 주변에 졸음 효과를 준다.
                ➕ 추가 아르크 벌레류
                - 감각나비 – 날개 무늬가 감정 색상과 동기화되어 NPC 분위기를 예고한다.
                - 운모 풍뎅이 – 광맥 근처에 서식하며 날개를 펄럭여 희귀 광물의 위치를 반짝인다.

                몬스터 및 고위 생명체 👹
                19) 심연의 전령 – 깊은 심해에서 깨어나 사람들의 꿈속에 모습을 드러낸다.
                20) 잿빛 그림자 – 존재하는 듯 존재하지 않는 그림자형 몬스터로 빛을 싫어한다.
                21) 푸른 대지의 거신 – 자연과 하나 된 거대한 생명체로 대륙을 이동하며 역사를 지켜본다.
                ➕ 추가 아르크 몬스터
                - 라일락 관문수호자 – 관찰자 모드에서만 목격되는 존재로, 전생 조건을 시험한다.
                - 사념의 도서관리자 – 현자 대륙의 도서관을 지키며 기억을 대가로 지식을 거래한다.

                ※ 각 카테고리는 향후 1,000종 이상으로 확장할 예정이며, 감정 시스템과 연동되는 생태 반응을 우선 설계한다.
                """
            ),
        ),
        DesignSection(
            key="signature_instruments",
            title="🎼 아르크 고유 악기", 
            body=dedent(
                """
                고정 악기(요청 반영)
                - 스카라혼(Scarahorn): 두 개의 나무 조각을 문질러 바람의 흐름에 따라 음색이 달라지는 진동 악기. 바람 예측과 감정 연출에 사용된다.
                - 루테르음(Lutherum): 전설적인 나무에서 만든 현악기로, 슬픔과 기쁨을 섬세하게 표현한다.
                - 에오스피어(Eosphiere): 공기압을 조절해 다양한 음을 내는 악기로, 과학과 마법의 결합을 상징한다.
                - 픽시아(Pixia): 여러 톤의 구슬이 들어 있는 통을 흔들어 리듬과 미세한 표현을 만드는 악기.
                - 노르기언(Norgion): 금속과 돌을 혼합한 고대 타악기로, 장엄한 전투 음악을 구현한다.

                신규 확장 악기
                - 실타래 리라(Tapestry Lyra): 감정의 실타래 타일에 따라 발광하는 9현 악기로, 타일 순서를 올바르게 맞추면 하모니가 강화된다.
                - 루멘 플루트(Lumen Flute): 랜턴이끼 코어를 삽입해 빛과 음을 동시에 방출하며, SpiritSight 상태의 NPC 대사에 변조를 일으킨다.
                - 사보크 드럼(Savok Drum): 사막 자다카르 부족이 사용하는 모래 충격 드럼으로, Sandstride 버프와 공명한다.
                - 하늘현 챔버(Skystring Chamber): 신드랄리스의 부유선에서 연주되는 휴대형 공기 공명기. FeatherStep 상태일 때 박동감이 증가한다.

                악기 활용 정책
                - 모든 악기는 감정 상태와 연동된 음색 변조 데이터를 가진다.
                - 축제 및 관찰자 컷신에서 악기별 전용 스템을 호출해 정서적 클라이맥스를 조성한다.
                - 추후 DLC에서는 각 대륙별 대표 악기를 최소 3종씩 확장한다.
                """
            ),
        ),
        DesignSection(
            key="content_pack_v1_2",
            title="📦 CONTENT PACK v1.2 — 데이터 파일 안내",
            body=dedent(
                """
                CODEX ingestor용 데이터 묶음
                - data/artifacts/solmara.yaml: 솔마라 18종 유물 풀 스펙. Common~Mythic까지 passive/active/emotion_tuning/획득/강화/오르골 연계를 포함한다.
                - data/artifacts/baretos_teasers.yaml: 바레토스 티징 유물 6종. SpiritSight/Hex/용서 시퀀스용 예비 데이터.
                - data/npc_interactions/solmara_core.json: 핵심 NPC 6명 + 광장 쌍둥이/퇴역 기사 Verb 조건과 관계 변화량, localization 키.
                - data/quests/solmara.yaml: 메인 1종 + 서브 4종 퀘스트 상태머신. cond/do/reward 구조로 CODEX 연동.
                - data/minigames.yaml: cheer_timing/dance_rhythm 등 미니게임 파라미터와 보상 규칙.
                - data/crafting.yaml: 감정 물약 4종, 힐링 요리 2종의 재료/효과/쿨다운 명세.
                - data/config/interaction_config.json: 상호작용 쿨타임, 관계 보정 범위, 일일 선물 제한, 약속 실패 패널티.
                - data/relations.json: 관계/감정 기본 가중치와 Bias 매핑.
                - data/gifts/gifts_solmara.csv: 선물 선호 가중치 매트릭스. 스팸 방지를 위한 50% 감쇠 정책 명시.
                - data/letters_rumors.yaml: 편지 트리거와 일일 루머 풀, 힌트 매핑.
                - Localization/ko/strings.json: 한국어 대사/오르골/관찰자 문자열. dlg.*, orgel.*, obs.* 키 구조로 정리.
                - Localization/ko/strings_npc_ext.json: 시간/날씨/선물 반응 등 확장 대사 200여 줄.
                - data/observer/solmara_packets.yaml: 관찰자 모드 패킷 id·카메라 경로·나레이션 키.
                - data/observer/baretos_packets.yaml: 바레토스 녹턴 카타콤 도입 컷신 패킷.
                - data/orgel/orgel_solmara_01.yaml: 감정의 실타래 ORGEL_SOLMARA_01 타일 순서, 음원, 허용 오차, 보상 플래그.
                - data/orgel/orgel_solmara_02.yaml: 마을/벽난로 감성을 다룬 ORGEL_SOLMARA_02 타일 시퀀스.
                - data/festivals/festival_hooks.json: 토너먼트·무도회 미니게임, NPC 보정, 보상 테이블.
                - data/dungeon_baretos_nocturne.yaml: 바레토스 의식 던전 ‘녹턴 카타콤’ 입장 조건과 퍼즐/보상 구조.
                - data/ecology_solmara.yaml: 솔마라 생물·식물·요리 드롭 요약.
                활용 지침
                1. YAML/JSON/CSV를 그대로 엔진 데이터베이스에 삽입하면 CODEX가 상호 참조 테이블을 생성할 수 있다.
                2. localization 키는 dlg.<npc>.<category>.<state> 패턴을 따르며, 감정 치환자는 {emotion}, {result} 변수를 사용한다.
                3. 상호작용/축제 데이터는 차후 DLC에서도 확장 가능하도록 verb/affects 배열 구조를 유지한다.
                """
            ),
        ),
        DesignSection(
            key="world_system_expansions",
            title="⚙️ 자연재해·무기·도구·라이프 스타일 확장", 
            body=dedent(
                """
                자연재해 시스템
                - 마력 폭풍: 강력한 마법 에너지가 폭주해 지역 지형과 감정 게이트를 일시 변형한다.
                - 천공 균열: 하늘이 갈라지며 차원 존재가 출현, SpiritSight 유저에게 경고 컷신을 제공한다.
                - 대지의 포효: 거대 생명체의 이동으로 발생하는 초대형 지진. 건물과 관계 이벤트 스케줄에 변동을 준다.

                무기 시스템
                - 별의 칼날: 밤하늘의 빛을 흡수해 강력한 참격을 발사하는 검. 감정 상태에 따라 빛의 색이 바뀐다.
                - 뿌리의 채찍: 사용자의 의지로 성장하며 적을 포박하는 채찍. Verdancy 버프와 연동.
                - 용의 숨결: 화살이 날아가며 작은 폭발을 일으키는 마법 활. Focus 상태에서 추가 분기 발생.

                농기구 및 도구
                - 태양 곡괭이: 어둠 속에서도 광물을 채굴할 수 있는 광택 도구.
                - 바람의 삽: 흙을 빠르게 파내며 바람 흐름을 생성, 감정 타일을 드러낸다.
                - 생명의 괭이: 토양의 생명력을 증가시켜 작물 성장을 촉진한다.
                - 정령의 낫: 넓은 범위의 작물을 빠르게 수확, SpiritSight 상태에서 정령이 보조한다.
                - 신비한 연장통: 다양한 도구를 보관하고 필요한 기능을 즉시 호출한다.

                주방 도구
                - 강철 식칼, 튼튼한 도마, 마법 냄비, 단단한 머그컵, 은빛 주전자를 포함해 조리 정확도와 감정 보정치를 지원한다.

                생활·커뮤니티 확장
                - 일상 도구 풀: 이쑤시개부터 대장장이 망치, 처형대, 사냥 덫, 마법 펜던트까지 현실+판타지 공존.
                - 재봉·요리·농업·의료·생활 도구 세트가 각각 세부 시스템과 연결되어 힐링 루틴을 심화한다.
                - 요리/예술/캠핑 콘텐츠, 주택 개조와 상점 운영, 도서관 학습 시스템이 루프별 성장 동기를 제공한다.

                탐험 & 자유도 요소
                - 채광과 보물 찾기, 동물 길들이기, 계절 축제 이벤트가 모두 감정 FSM과 상호작용한다.
                - 축제 기간에는 Nobility/Calm 글로벌 버프가 적용되며, 루머/편지 시스템과 연동된 힌트가 확장된다.
                """
            ),
        ),
        DesignSection(
            key="artifact_schema",
            title="A. 유물 글로벌 스키마 & 라이프사이클",
            body=dedent(
                """
                공통 스키마(Artifact)
                - id: ARK_ART_ 접두를 권장한다.
                - name: 표시명.
                - tier: Common, Uncommon, Rare, Epic, Mythic 중 하나.
                - type: Artifact, Relic, Talisman, Instrument, Document.
                - equip_slot: Emblem, Charm, Trinket, Tool, Book, None.
                - isReincarnationRelated: 전생 루프 가치 여부.
                - passive: 효과 키(id), 수치(value), 단위/해설(notes) 목록.
                - active: has_active, cooldown_sec, charges_per_life, cast_time_sec, duration_sec, effect(id/value/notes).
                - emotion_tuning: Affectionate/Friendly/Sad/Hostile/Neutral 가중치(-3~+3).
                - observer_hooks: 관찰자 모드 packetId와 설명.
                - orgel_synergy: sequenceId, tile_bonus{tileId:{harmony_bias}}.
                - acquire: source(Quest/Dungeon/Festival/Craft/Trade/Drop/Hidden), where(씬/행사), rules(감정/시간/루프 조건).
                - upgrade: method(Alchemy/Smithy/Festival/None), mats, caps(예: passive "+20%", active "-20% CD").
                - flavor: 한국어 로어 텍스트.

                공통 효과 키 예시
                - PASS_EMO_GAIN: 감정 이벤트 가중치 보정(%).
                - PASS_SPIRITSIGHT: 유령/정령 가시화(0/1).
                - PASS_GATE_OVERRIDE: 감정 게이트 관문 완화(단계).
                - PASS_JOURNAL_CLARITY: 일기 키워드 판정 정확도(%).
                - ACT_UNDO_CHOICE: 최근 선택 되돌리기(회당).
                - ACT_OBSERVER_CALL: 관찰자 패킷 호출.
                - ACT_ORGEL_HINT: 감정의 실타래 타일 힌트 표시.
                - ACT_EMO_PURIFY: 감정 왜곡(Hex) 제거.
                - ACT_RELATION_BURST: 관계 랭크 상승(소폭).
                - ACT_GATE_FORCE: 감정 게이트 강제 개방.

                라이프사이클 정책
                - 장착 슬롯: 기본 1슬롯(Emblem/Charm/Trinket 중 택1), 향후 DLC로 2슬롯 확장.
                - 충전/초기화: charges_per_life는 전생 시 리셋, Epic 이상은 자연사 때 +1 충전 보너스.
                - 바운드: Relic은 계정 귀속, Artifact는 거래 가능(확장판에서 활성).
                - 균형: isReincarnationRelated=true 유물은 즉효보다 루프 누적 가치에 중점.
                - 제작/강화: Alchemy/Smithy로 기본 60%까지 상승, 최고치는 축제·히든 요구.
                """
            ),
        ),
        DesignSection(
            key="solmara_resources",
            title="🏰 솔마라 자원 & 축제 데이터",
            body=dedent(
                """
                Biome 요약
                - City(성내/시장), Farmland(밭·목장), Forest(로렐레 숲), RiverMarsh(연못/하구), MountainCave(폐광).

                Flora 7종
                1) SOL_FL_KingsThyme – 왕가의백리향 / Uncommon / City·Farmland / Spring~Summer Day·Dusk / 수확 2-4 / Cooking·Alchemy / Calm, Focus / +Friendly / 연금술 집중 베이스.
                2) SOL_FL_BalmApple – 발메사과 / Common / Farmland / Autumn Day / 수확 1-3 / Cooking·Brew / Calm / +Affectionate / 사과 와인 핵심.
                3) SOL_FL_SilverWheat – 은빛밀 / Common / Farmland / Summer~Autumn Day / 수확 2-5 / Cooking·Craft / 효과 없음 / Neutral / 기사단 건빵 재료.
                4) SOL_FL_Ironcap – 아이언캡버섯 / Uncommon / MountainCave / Spring·Autumn Night·Dawn / 수확 1-2 / Cooking·Alchemy / Warmth / +Friendly / 철 향이 나는 버섯.
                5) SOL_FL_LanternMoss – 랜턴이끼 / Rare / RiverMarsh·MountainCave / All Night / 수확 1-1 / Craft·Alchemy·Dye / SpiritSight / +Sad / 은은한 발광.
                6) SOL_FL_RoyalRose – 로열로즈 / Rare / City / Spring Day / 수확 1-1 / Brew·Craft·Dye / Affectionate / +Affectionate / 무도회 장식.
                7) SOL_FL_MarshMint – 습지민트 / Common / RiverMarsh / Summer Day·Dusk / 수확 2-4 / Cooking·Brew / Calm / +Friendly / 상쾌한 향.

                Fauna 7종
                1) SOL_FA_MeadowLark – 초원종달새 / Common / Farmland·Forest / Dawn·Day / Skittish / 깃털 1-2 (Craft) / 음악에 +Affectionate / +Calm / 피리에 반응.
                2) SOL_FA_MarbleBoar – 대리석멧돼지 / Uncommon / Forest / Dusk·Night / Territorial / 고기 1-3 (Cooking) / 적대 시 +Hostile / +Hostile / 낮은 횃불로 진정.
                3) SOL_FA_RiverOtter – 강수달 / Uncommon / RiverMarsh / Day / Curious·Pack / 진주 0-1 (Craft·Quest) / 쓰다듬기·음악 +Friendly / +Friendly / 반짝이는 것 선호.
                4) SOL_FA_FireflyCluster – 반딧불무리 / Common / Forest·RiverMarsh / Night / Curious / 정수 1-2 (Alchemy·Dye) / 음악 +Affectionate / +Affectionate / 리듬 동기화.
                5) SOL_FA_StoneBeetle – 석갑딱정벌레 / Common / MountainCave / Night / Skittish / 갑각 1-2 (Craft) / 반응 없음 / Neutral / 바위 위장.
                6) SOL_FA_StableCat – 마구간고양이 / Rare / City·Farmland / Night / Curious / 목걸이 0-1 (Quest) / 쓰다듬기 +Calm / +Calm / Sad→Calm 완화.
                7) SOL_FA_CaveMoth – 동굴나방 / Common / MountainCave / Night / Skittish / 가루 1-3 (Dye·Alchemy) / 반응 없음 / Neutral / 랜턴이끼 집결.

                Dish 4종
                - SOL_DI_RoyalSteak: 로열 비프 스테이크 / Uncommon / ME_BoarMeat×2, SOL_FL_KingsThyme×1, SALT×1 / Warmth·Focus 900초 / +Affectionate / 토너먼트 관람 중 대사 강화.
                - SOL_DI_FarmersPotage: 농부의 포타주 / Common / VE_Potato×2, SOL_FL_SilverWheat×1, MILK×1 / Calm 600초 / +Friendly / 여관 특선.
                - SOL_DI_IroncapStew: 아이언캡 스튜 / Uncommon / SOL_FL_Ironcap×1, ME_BoarMeat×1, ONION×1 / Warmth 600초 / +Friendly / 광산 추위 저항.
                - SOL_DI_MintTrout: 민트 송어 구이 / Uncommon / FI_Trout×1, SOL_FL_MarshMint×1, BUTTER×1 / Focus 480초 / Neutral / 퍼즐 집중력 상승.

                Brew 4종
                - SOL_BR_AppleWine: 솔마라 사과 와인 / Uncommon / SOL_FL_BalmApple×2, YEAST×1 / Calm·Affectionate 420초 / 연속 사용 시 Focus -1 단계 / +Affectionate / 무도회 긴장 완화.
                - SOL_BR_RoyalRoseTea: 로열 로즈 티 / Rare / SOL_FL_RoyalRose×1, HONEY×1 / Calm·Blessing 480초 / +Affectionate / 귀족 대화 시 Nobility 임시 부여.
                - SOL_BR_FireflyElixir: 반딧불 엘릭서 / Rare / IN_FireflyEssence×1, SOL_FL_LanternMoss×1 / SpiritSight 300초 / +Sad / 밤 시야 확장과 유령 대화 힌트.
                - SOL_BR_ThymeAle: 타임 에일 / Common / BARLEY×2, SOL_FL_KingsThyme×1 / Calm 300초 / Neutral / 기사단 휴식용.

                Festival 2종
                - SOL_FE_Tournament: 기사 토너먼트 / Summer / City / 미니게임 cheer_timing, betting_lite, stealth_entry / 참가 조건 ticket_or_disguise / 보상 MED_TokenValor, CLO_CapeCrimson / 글로벌 효과 Nobility / 감정 테마 Friendly·Affectionate / 퀘스트 훅 Q_SOL_TOURNAMENT, Q_SOL_DISGUISE / 응원 성공 시 감정 반응 강화.
                - SOL_FE_RoyalBall: 왕실 무도회 / Autumn / City / 미니게임 dance_rhythm, etiquette_quiz, partner_choice / 참가 조건 invite_or_disguise / 보상 ACC_MaskSilk, HINT_BaretosTruth01 / 글로벌 효과 Calm·Affectionate / 감정 테마 Affectionate·Neutral / 퀘스트 훅 Q_SOL_BALL_HIDDEN / 파트너 선택으로 진엔딩 힌트 분기.
                """
            ),
        ),
        DesignSection(
            key="solmara_artifacts",
            title="B. 솔마라 유물 18종 세부 스펙",
            body=dedent(
                """
                Common 3종
                1) ARK_ART_TownCharm – 성문 부적
                   - tier: Common / type: Talisman / slot: Charm / 전생 연계: false
                   - passive: PASS_EMO_GAIN +5% (감정 이벤트 가중)
                   - emotion_tuning: Friendly +1
                   - acquire: Trade – Rodendell_Market (친화 랭크 ≥1)
                   - upgrade: Smithy – MAT_SilverIngot×1
                   - flavor: 성문을 드나드는 상인의 작은 행운.

                2) ARK_ART_ScribeQuill – 서기관의 깃펜
                   - tier: Common / type: Tool / slot: Tool / 전생 연계: false
                   - passive: PASS_JOURNAL_CLARITY +10% (일기 키워드 판정)
                   - emotion_tuning: Neutral +1
                   - acquire: Trade·Quest – Inn_Shop (일기 튜토리얼 완료)
                   - flavor: 생각을 선명히 적어주는 검은 깃.

                3) ARK_ART_FieldBrooch – 들판 브로치
                   - tier: Common / type: Trinket / slot: Trinket / 전생 연계: false
                   - passive: PASS_EMO_GAIN +3% (우호 이벤트 보정)
                   - emotion_tuning: Friendly +1
                   - acquire: Quest – Braile_Farm (목장 소년 이벤트1)
                   - flavor: 햇살에 반짝이는 밀 이삭.

                Uncommon 6종
                4) ARK_ART_LanternMossVial – 랜턴이끼 바이얼
                   - type: Artifact / slot: Emblem / 전생 연계: false
                   - passive: PASS_SPIRITSIGHT 활성(밤 한정)
                   - active: ACT_ORGEL_HINT(가까운 타일 발광) / CD 120초 / charges 3 / duration 20초
                   - emotion_tuning: Sad +1
                   - acquire: Craft·Dungeon – Mine·RiverMarsh (랜턴이끼 + 유리병)
                   - flavor: 작은 빛이 길을 기억한다.

                5) ARK_ART_ThymeSignet – 백리향 인장반지
                   - type: Artifact / slot: Trinket / 전생 연계: false
                   - passive: PASS_EMO_GAIN +8% (집중 선택지)
                   - emotion_tuning: Friendly +1, Neutral +1
                   - acquire: Festival·Trade – Tournament_Stands (응원 미니게임 B랭크)
                   - flavor: 허브 향이 마음을 차분히.

                6) ARK_ART_MintRibbon – 습지민트 리본
                   - type: Talisman / slot: Charm / 전생 연계: false
                   - passive: PASS_EMO_GAIN +6% (긴장 완화 분기)
                   - emotion_tuning: Affectionate +1
                   - acquire: Quest – River_Fishing (민트 송어 구이 제작)
                   - flavor: 상쾌함이 말을 부드럽게 만든다.

                7) ARK_ART_RoseCameo – 로열로즈 카메오
                   - type: Trinket / slot: Trinket / 전생 연계: false
                   - passive: PASS_GATE_OVERRIDE 1 (애정 게이트 난이도 -1)
                   - emotion_tuning: Affectionate +2, Hostile -1
                   - acquire: Festival – RoyalBall (파트너/댄스 A랭크)
                   - flavor: 무도회의 잔향이 머문다.

                8) ARK_ART_OtterCharm – 수달 부적
                   - type: Talisman / slot: Charm / 전생 연계: false
                   - passive: PASS_EMO_GAIN +5% (동물 상호작용 우호)
                   - emotion_tuning: Friendly +1
                   - acquire: Hidden – River_OtterSpot (반짝이는 물건 선물)
                   - flavor: 호기심 많은 친구의 축복.

                9) ARK_ART_GateMedallion – 성문 증표
                   - type: Artifact / slot: Emblem / 전생 연계: false
                   - passive: PASS_GATE_OVERRIDE 1 (성문 검문 완화)
                   - emotion_tuning: Friendly +1, Neutral +1
                   - acquire: Quest – Castle_Gate (순찰 기사 신뢰 이벤트)
                   - flavor: 성문을 지키는 이가 건넨 신뢰의 증표.

                Rare 5종
                10) ARK_ART_TimeCrystal – 시간의 수정
                   - type: Relic / slot: Emblem / 전생 연계: true
                   - passive: PASS_EMO_GAIN +10% (회고·용서 선택지)
                   - active: ACT_UNDO_CHOICE 1회 / CD 600초 / charges 1
                   - emotion_tuning: Sad +1, Affectionate +1
                   - observer_hook: OBS_SOL_TIME_ECHO (되감기 잔상)
                   - orgel_synergy: ORGEL_SOLMARA_01 – E07_Forgiveness harmony_bias +0.3
                   - acquire: Dungeon – MineMini_Final (퍼즐 방 클리어)
                   - upgrade: Festival – MAT_SilverIngot×2, IN_FireflyEssence×1
                   - flavor: 돌이킬 수 없던 마음에도 틈이 생긴다.

                11) ARK_ART_FateStone – 운명의 돌
                    - type: Relic / slot: Emblem / 전생 연계: true
                    - passive: PASS_GATE_OVERRIDE 1 (관계 분기 가드 완화)
                    - active: ACT_RELATION_BURST (친밀 랭크 +1 한시) / CD 900초 / duration 30초 / charges 1
                    - emotion_tuning: Affectionate +1, Hostile -1
                    - orgel_synergy: ORGEL_SOLMARA_01 – E04_Love harmony_bias +0.25
                    - acquire: Quest – RoyalBall (히든 파트너 루트)
                    - flavor: 선택을 반복하면 길이 바뀐다.

                12) ARK_ART_EmotionMirror – 감정의 거울
                    - type: Artifact / slot: Tool / 전생 연계: false
                    - passive: PASS_EMO_GAIN +12% (NPC 감정 HUD 가시화)
                    - emotion_tuning: Neutral +1
                    - acquire: Craft – AlchemistLab (유리 + 룬잉크 + 반딧불 정수)
                    - flavor: 말하지 않아도 보인다.

                13) ARK_ART_KnightPennant – 기사단 페넌트
                    - type: Talisman / slot: Emblem / 전생 연계: false
                    - passive: PASS_EMO_GAIN +10% (응원/토너먼트 반응)
                    - emotion_tuning: Friendly +1, Affectionate +1
                    - acquire: Festival – Tournament (관람 미니게임 S랭크)
                    - flavor: 깃발은 마음을 모은다.

                14) ARK_ART_SteelLocket – 강철 로켓
                    - type: Trinket / slot: Trinket / 전생 연계: true
                    - passive: PASS_EMO_GAIN +8% (슬픔→평온 전환)
                    - active: ACT_EMO_PURIFY (Hex/불협 제거) / CD 300초 / duration 10초 / charges 2
                    - emotion_tuning: Sad +1, Neutral +1
                    - acquire: Hidden – Gate_Sad_Forest (슬픔 게이트 후 벤치)
                    - flavor: 무거운 마음을 잠시 닫아 준다.

                Epic 3종
                15) ARK_ART_OrgelKey – 오르골의 열쇠
                    - type: Instrument / slot: Tool / 전생 연계: true
                    - passive: PASS_EMO_GAIN +15% (실타래 하모니)
                    - active: ACT_OBSERVER_CALL 1회 (소형 컷신 즉시) / charges 1
                    - orgel_synergy: ORGEL_SOLMARA_01 – E01_Lonely +0.1, E09_Observer +0.4
                    - acquire: Quest – Orgel_Path (실타래 1회 완주 히든)
                    - flavor: 음악은 기억을 열쇠처럼 연다.

                16) ARK_ART_RoseMask – 로즈 마스크
                    - type: Talisman / slot: Charm / 전생 연계: false
                    - passive: PASS_GATE_OVERRIDE 2 (무도회 예절 체크 완화)
                    - emotion_tuning: Affectionate +2
                    - acquire: Festival – RoyalBall (변장 루트 + 파트너 호감 B 이상)
                    - flavor: 진짜 얼굴보다 더 진짜인 미소.

                17) ARK_ART_ValorLaurels – 명예의 월계
                    - type: Emblem / slot: Emblem / 전생 연계: true
                    - passive: PASS_EMO_GAIN +12% (용기/책임 선택지)
                    - active: ACT_GATE_FORCE 1회 (우호/애정 게이트 개방) / CD 1200초 / duration 20초 / charges 1
                    - acquire: Festival – Tournament_Final (특별 엔딩 연출)
                    - flavor: 누군가의 박수가 너를 기억하게 한다.

                Mythic 1종
                18) ARK_ART_WhiteLilac – 하얀 라일락
                    - type: Relic / slot: None / 전생 연계: true
                    - passive: PASS_SPIRITSIGHT 상시, PASS_EMO_GAIN +20% (용서·관찰)
                    - active: ACT_OBSERVER_CALL (라일락 대형 컷신) / 무제한 연출 / 내부 게이트 필요
                    - orgel_synergy: ORGEL_SOLMARA_01 – E07_Forgiveness +0.5, E09_Observer +0.5
                    - acquire: Hidden – Rodendell_Garden_Lilac (전생 ≥3, 실타래1, 무도회 힌트 수집)
                    - flavor: 용서는 언제나 빛의 모양을 하고 있다.

                총계 18종 – Common 3, Uncommon 6, Rare 5, Epic 3, Mythic 1.
                """
            ),
        ),
        DesignSection(
            key="core_story_artifacts",
            title="🔮 서사 핵심 유물 15종 로어 & 메커닉",
            body=dedent(
                """
                1) ARK_ART_Core_Gratitude – "너에게 감사해..." (Unbreakable Gratitude)
                   - tier: Mythic / type: Relic / slot: Emblem / 전생 연계: true
                   - 기원: 여신 엘레네시아가 반인반수 소년에게 남긴 마지막 빛. 그녀의 감사 인사가 결정화되어 다섯 조각으로 흩어졌다.
                   - 구조: Joy·Sorrow·Forgiveness·Memory·Promise 조각으로 분해되어 있으며, 각 조각은 NPC의 상처를 치유할 때 공명한다.
                   - passive: PASS_EMO_GAIN +25%(감정 치유), PASS_JOURNAL_CLARITY +20%(회상 기록) – 조각 획득마다 +5%씩 축적.
                   - active: ACT_RELATION_BURST 1회(용서 이벤트 한정) / cooldown 7200초 / charges 1 – 모든 조각을 모아야 발동.
                   - 효과: 조각 장착 시 적대 -5, 잃어버린 기억 조각 반환, 완성 시 관찰자 컷신 "엘레네시아의 미소" 해금.

                2) ARK_ART_Core_LostTime – 잃어버린 시간의 수정 (Crystal of Lost Time)
                   - tier: Epic / type: Relic / slot: Emblem / 전생 연계: true
                   - 기원: 전쟁 속에서 봉인된 고대 시간 신전의 제단 장치.
                   - passive: PASS_EMO_GAIN +12%(회고 선택지), PASS_GATE_OVERRIDE 1(시간 퍼즐) – 사용 후 기억이 희미해져 EmotionState가 Neutral로 리셋.
                   - active: ACT_UNDO_CHOICE 1회 / cooldown 3600초 / charges_per_life 1 – 되돌린 장면은 관찰자 로그에만 남는다.
                   - 리스크: 반복 사용 시 플레이어 일기에서 해당 날의 세부 기록이 흐릿하게 바뀌며, 전생 카운트가 1회 소모된 것처럼 취급된다.

                3) ARK_ART_Core_DevouringRing – 어둠을 삼키는 반지 (Ring of Devouring Darkness)
                   - tier: Rare / type: Talisman / slot: Charm / 전생 연계: false
                   - 기원: 빛을 두려워한 마지막 왕의 그림자 계약.
                   - passive: PASS_EMO_GAIN +15%(밤·Hostile 상호작용), PASS_SPIRITSIGHT 1(완전 암흑 한정) – 낮에는 효과 없음.
                   - active: ACT_GATE_FORCE 1회(어둠 게이트) / cooldown 1800초 / duration 30초 / charges 2.
                   - 리스크: 3일 이상 연속 착용 시 EmotionState.Hostile 가중치 +2, 빛 환경에서 플레이어 에너지 회복 -50%.

                4) ARK_ART_Core_ForgottenSong – 잊혀진 노래의 서 (Codex of Forgotten Melodies)
                   - tier: Epic / type: Document / slot: Book / 전생 연계: true
                   - 기원: 폐허가 된 극장의 지하 보관함, 잊혀진 합창단의 악보.
                   - passive: PASS_EMO_GAIN +15%(음악 상호작용), PASS_JOURNAL_CLARITY +10%(가사 해독).
                   - active: ACT_ORGEL_HINT 1회 / cooldown 900초 / charges 3 – 특정 씬에서만 숨겨진 구절을 드러낸다.
                   - 보상: 모든 악장을 완성하면 해당 지역의 감정 타일이 하모니 편향 +0.2, NPC 대사에 새로운 노랫줄이 추가된다.

                5) ARK_ART_Core_CrimsonMask – 붉은 달의 가면 (Mask of the Crimson Moon)
                   - tier: Epic / type: Talisman / slot: Charm / 전생 연계: true
                   - passive: PASS_GATE_OVERRIDE 2(변장 체크), PASS_EMO_GAIN +10%(관계 잠입 루트).
                   - active: has_active=false – 대신 붉은 달 이벤트 동안 자동으로 대상 NPC의 외형·목소리를 복제한다.
                   - 리스크: 변장 유지 시간이 누적 6시간을 넘으면 플레이어 초상화가 흐릿해지고, 진짜 얼굴을 되찾으려면 관찰자 패킷 "달빛 참회"를 시청해야 한다.

                6) ARK_ART_Core_FrostHeart – 서리의 심장 (Heart of the Frostborn)
                   - tier: Rare / type: Relic / slot: Emblem / 전생 연계: false
                   - passive: Warmth 면역, Focus +10%(냉기 환경) – EmotionState.Affectionate 가중치 -1로 감정이 무뎌진다.
                   - active: ACT_EMO_PURIFY 1회 / cooldown 2400초 / duration 15초 – 과열/감정 폭주를 즉시 냉각.
                   - 스토리: 얼음 정령과 계약한 자만이 심장을 얻을 수 있으며, 사용 후 NPC와의 공감 대사가 차분하게 변주된다.

                7) ARK_ART_Core_EternityGlass – 영원의 모래시계 (Hourglass of Eternity)
                   - tier: Mythic / type: Relic / slot: Tool / 전생 연계: true
                   - passive: PASS_GATE_OVERRIDE 1(시간 정지 던전), PASS_EMO_GAIN +10%(관찰자 힌트).
                   - active: ACT_OBSERVER_CALL 1회(지역 시간 정지) / cooldown 0 / charges 3 – 모래가 모두 떨어질 때까지 씬의 시간과 NPC 이동이 정지.
                   - 리스크: 사용 횟수마다 지속시간이 120초, 90초, 45초로 줄어들고, 마지막 사용 후 유물은 사라져 모래 언덕에 새로운 퀘스트가 생성된다.

                8) ARK_ART_Core_RestlessCandle – 잠들지 않는 자들의 초 (Candle of the Restless)
                   - tier: Rare / type: Artifact / slot: Tool / 전생 연계: true
                   - passive: PASS_SPIRITSIGHT 1(의식 중), PASS_EMO_GAIN +8%(추모 대화).
                   - active: ACT_OBSERVER_CALL 1회(망령 대화) / cooldown 2700초 / duration 60초 / charges 2 – 사망 NPC의 마지막 메시지 호출.
                   - 리스크: 하루에 두 번 이상 사용하면 EmotionState.Sad +3, 에너지 -2. 관찰자 모드에서 위로 컷신을 보면 상태 회복.

                10) ARK_ART_Core_StarCrown – 별을 삼킨 왕관 (Crown of the Starborn)
                   - tier: Epic / type: Relic / slot: Emblem / 전생 연계: true
                   - passive: PASS_EMO_GAIN +18%(밤·하늘 이벤트), Friendly·Affectionate emotion_tuning +1 – 실내에서는 효과가 절반으로 감소.
                   - active: ACT_GATE_FORCE 1회(천문 게이트) / cooldown 3600초 / duration 25초 / charges 2.
                   - 리스크: 별이 보이지 않는 장소에서 에너지 회복 -3, Hostile 가중치 +1(고립감).

                11) ARK_ART_Core_UndyingFlame – 죽지 않는 불꽃 (Flame of the Undying)
                    - tier: Rare / type: Artifact / slot: Tool / 전생 연계: false
                    - passive: Warmth 상시, Blessing +5%(혹한 지역) – 체온 유지로 밤 활동이 쉬워진다.
                    - active: ACT_EMO_PURIFY 1회(화상 정화) / cooldown 1800초 / duration 10초 / charges 3.
                    - 리스크: 장시간 소지 시 플레이어에게 Burn 스택이 쌓여 EmotionState.Sad -1, Hostile +1. 여관 휴식이나 마이라 이벤트로 해소 가능.

                12) ARK_ART_Core_FinalBell – 새벽의 마지막 종 (Final Bell of Dawn)
                    - tier: Mythic / type: Instrument / slot: Tool / 전생 연계: true
                    - passive: PASS_EMO_GAIN +15%(전투/갈등 종료), PASS_GATE_OVERRIDE 1(긴급 탈출).
                    - active: ACT_UNDO_CHOICE 대신 특정 전투·퀘스트를 즉시 종료 / cooldown 5400초 / charges 1 – 울린 뒤 반드시 무언가의 엔딩을 맞아야 한다.
                    - 리스크: 강제 종료된 사건은 다시 열 수 없고, 관찰자 모드에서 결과를 확인해야만 후속 루프에서 다른 선택이 가능하다.

                13) ARK_ART_Core_ShadowContract – 그림자의 계약서 (Contract of the Shadowed Ones)
                    - tier: Epic / type: Document / slot: Book / 전생 연계: true
                    - passive: PASS_EMO_GAIN +12%(위험 선택), PASS_GATE_OVERRIDE 1(암시장/암문).
                    - active: ACT_GATE_FORCE 1회(전투력 상승) / cooldown 0 / duration 60초 / charges 1 – 사용 즉시 플레이어 관계 중 하나가 -20 감소.
                    - 리스크: 계약 대가로 무작위 NPC의 호감도가 하락하며, 파기하려면 바레토스의 의식에서 희생 이벤트를 수행해야 한다.

                14) ARK_ART_Core_FinalBrush – 창조주의 마지막 붓 (The Creator's Final Brush)
                    - tier: Mythic / type: Tool / slot: Tool / 전생 연계: true
                    - passive: PASS_JOURNAL_CLARITY +25%(창작 기록), PASS_EMO_GAIN +10%(예술 상호작용).
                    - active: ACT_ORGEL_HINT 1회(새 경로 스케치) / cooldown 0 / charges 3 – 진심으로 원하는 장면만 물질화된다.
                    - 리스크: 거짓된 소망을 그리면 해당 그림이 사라지고, EmotionState.Sad +2, Friendly -1.

                15) ARK_ART_Core_OblivionThrone – 망각의 의자 (Throne of Oblivion)
                    - tier: Mythic / type: Relic / slot: None / 전생 연계: true
                    - passive: PASS_EMO_GAIN +20%(전생 초기화 루트), Hostile emotion_tuning -2 – 새 삶으로 전환할 준비를 돕는다.
                    - active: ACT_OBSERVER_CALL 1회(신생 컷신) / cooldown 0 / charges 무제한 – 사용할 때마다 현재 캐릭터의 기억이 모두 삭제된다.
                    - 리스크: 착석 즉시 플레이어 진행 로그가 초기화되고, 저장 슬롯에 "새 삶" 플래그가 기록된다. 이전 인연은 끌림 보정만 남는다.

                16) ARK_ART_Core_EndlessMap – 끝없는 길의 지도 (Map of the Endless Path)
                    - tier: Epic / type: Document / slot: Book / 전생 연계: true
                    - passive: PASS_EMO_GAIN +10%(탐험 이벤트), PASS_GATE_OVERRIDE 1(미지 지역).
                    - active: ACT_GATE_FORCE 1회(랜덤 순간이동) / cooldown 0 / charges 2 – 미지의 타일로 이동하나 귀환 포인트는 보장되지 않는다.
                    - 리스크: 실패 시 플레이어가 새로운 지역에 고립되어 1일간 fast travel 불가, 관찰자 모드에서 귀환 루트를 확인해야 한다.
                """
            ),
        ),
        DesignSection(
            key="baretos_resources",
            title="🌑 바레토스 자원 & 의식 데이터",
            body=dedent(
                """
                로어 핵심
                - 진엔딩의 신이 밤이 늘어진 봉인을 내려 인류를 지키고자 했다.
                - 금지 마법 연구는 파괴가 아닌 역전·치유 의식을 완성하기 위한 헌신이었다.
                - 미장센은 어둠 속 촛불·룬의 따뜻함으로 희망을 강조한다.

                Biome
                - CoastHarbor, Temple, SacredRuins.

                Flora 6종
                1) BAR_FL_NightOrchid – 야화난 / Rare / Temple·SacredRuins / All Night / 1-1 / Alchemy·Dye / SpiritSight·Calm / +Sad / 봉인 각인 위에서만 개화.
                2) BAR_FL_GraveMint – 묘지민트 / Uncommon / CoastHarbor·Temple / Autumn Dusk·Night / 1-3 / Brew·Alchemy / Calm / +Friendly / 장송 의식 차 베이스.
                3) BAR_FL_ObsidianFungus – 흑요버섯 / Rare / SacredRuins / All Night / 1-2 / Alchemy·Cooking / Focus·Hex / Neutral / 과용 시 감정 왜곡 위험.
                4) BAR_FL_CandleWaxWeed – 촛밀풀 / Common / CoastHarbor / Summer Night / 2-4 / Craft·Brew / 효과 없음 / Neutral / 촛불 제작 필수.
                5) BAR_FL_RuneSedge – 룬갈대 / Uncommon / CoastHarbor / Spring~Summer Dawn·Night / 2-3 / Craft·Alchemy / Focus / Neutral / 의식진 재료.
                6) BAR_FL_MoonSaltCrystal – 월염결정 / Epic / Temple / All Night / 1-1 / Alchemy / Moonbond·SpiritSight / +Sad / 봉인 해독 핵심.

                Fauna 6종
                1) BAR_FA_LanternFox – 랜턴여우 / Uncommon / CoastHarbor·Temple / Night / Curious / 꼬리 0-1 (Craft) / 음악 +Affectionate / +Calm / 촛불을 따라 이동.
                2) BAR_FA_WispDeer – 위습사슴 / Rare / SacredRuins / Dusk·Night / Skittish / 뿔 0-1 (Alchemy) / 음악 +Calm / +Sad / 접근 시 빛 입자 분출.
                3) BAR_FA_RuneMoth – 룬나방 / Common / Temple / Night / Skittish / 가루 1-3 (Dye·Alchemy) / 반응 없음 / Neutral.
                4) BAR_FA_CandleLizard – 촛불도마뱀 / Common / CoastHarbor / Night / Curious / 오일 1-2 (Craft) / 음악 +Friendly / Neutral / 촛불 주위 순찰.
                5) BAR_FA_SpecterEel – 망령뱀장어 / Rare / CoastHarbor / Night / Territorial / 고기 1-1 (Cooking·Brew) / 상호작용 없음 / +Sad / SpiritSight 상태에서만 등장.
                6) BAR_FA_RavenClerk – 흑까마귀 서기 / Epic / SacredRuins / Dawn·Night / Curious / 금서 0-1 (Quest) / 음악 +Focus / Neutral / 고서 전달 이벤트.

                Dish 2종
                - BAR_DI_ShadowBroth: 그림자 수프 / Uncommon / BAR_FL_ObsidianFungus×1, FO_LanternTail×1 / Focus·Moonbond 540초 / 부작용 Hex 1단 / +Sad / 의식 전 집중식.
                - BAR_DI_EelAshenGrill: 재빛 장어구이 / Rare / FI_SpecterEel×1, BAR_FL_RuneSedge×1 / Warmth·SpiritSight 420초 / +Friendly / 해독 의식 전력 보강.

                Brew 2종
                - BAR_BR_WraithWhiskey: 망령의 위스키 / Rare / BAR_FL_GraveMint×1, RE_CandleOil×1 / SpiritSight 300초 / 주의: 연속 사용 시 Hex 확률 증가 / +Sad / 기억 봉헌 시 사용.
                - BAR_BR_NightOrchidTea: 야화난 차 / Epic / BAR_FL_NightOrchid×1, HONEY×1 / Calm·Blessing 480초 / +Affectionate / 오해 해소 대화 보너스.

                Festival 2종
                - BAR_FE_DayOfDeparted: 망자의 날 / Autumn / Temple / minigame candle_vigil, memory_offering / 입장 SpiritSight_or_Candle / 보상 HINT_BaretosTruth02, ACC_BoneCharm / 글로벌 Calm·SpiritSight / 감정 테마 Sad·Affectionate / 퀘스트 Q_BAR_RECONCILE / 기억 봉헌 시 관찰자 대사 변조.
                - BAR_FE_ShadowMarket: 어둠의 시장 / All / CoastHarbor / minigame haggling_rhythm, token_find / 입장 mask_required / 보상 DO_ForbiddenTome, MAT_RuneInk / 글로벌 Focus / 감정 테마 Neutral / 퀘스트 Q_BAR_TOME_DELIVERY / 금기는 해독임을 암시.
                """
            ),
        ),
        DesignSection(
            key="baretos_artifacts",
            title="C. 바레토스 티징 유물 6종",
            body=dedent(
                """
                1) BAR_ART_BoneCharm – 뼈 부적 / tier Uncommon / type Talisman / slot Charm
                   - passive: PASS_SPIRITSIGHT 활성(망자의 날 기간 한정)
                   - acquire: Festival – BAR_FE_DayOfDeparted (기억 봉헌)
                   - flavor: 작은 촛불이 길을 잇는다.

                2) BAR_ART_RuneInk – 룬 잉크 / tier Rare / type Artifact / slot Tool / 전생 연계 true
                   - passive: PASS_JOURNAL_CLARITY +15% (일기→의식 키워드 연결)
                   - active: ACT_EMO_PURIFY 1회 / CD 600초 / charges 1 / 관찰자 확률 +10%
                   - flavor: 잉크는 봉인의 문장을 해독한다.

                3) BAR_ART_MoonSalt – 월염 소금 / tier Rare / type Relic / slot Trinket / 전생 연계 true
                   - passive: PASS_GATE_OVERRIDE 1 (밤 의식 게이트 완화)
                   - flavor: 바닷빛 염이 달을 품었다.

                4) BAR_ART_WispAntler – 위습 사슴뿔 / tier Rare / type Artifact / slot Emblem
                   - passive: PASS_EMO_GAIN +10% (슬픔→평온 전이)
                   - flavor: 사슴빛 잔광이 마음을 달랜다.

                5) BAR_ART_OrchidTeaSet – 야화난 다기 / tier Epic / type Artifact / slot Tool / 전생 연계 true
                   - passive: PASS_EMO_GAIN +15% (용서·화해 대화)
                   - active: ACT_RELATION_BURST 1랭크 / CD 1200초 / cast 1초 / duration 30초 / charges 1
                   - flavor: 따뜻한 차향이 오해를 녹인다.

                6) BAR_ART_TomeOfReversal – 역전의 서 / tier Epic / type Document / slot Book / 전생 연계 true
                   - passive: PASS_EMO_GAIN +15% (실타래 불협 완화)
                   - active: ACT_UNDO_CHOICE 1회 (실타래 타일 재선택) / CD 900초 / charges 1
                   - flavor: 금기는 파괴가 아닌 치유의 문장.
                """
            ),
        ),
        DesignSection(
            key="expansion_ecology",
            title="🌍 확장 대륙 생태 요약",
            body=dedent(
                """
                자다카르 – 사막·유적·부족
                - Biome: Desert, Oasis, MountainCave 변형.
                - Flora: 선인장꽃(Sandstride), 바람풀(열기 저감), 유적덩굴(성물 제작), 사막세이지(Focus), 사구대추야자(Calm), 태양꽃(FeatherStep).
                - Fauna: 모래여우(Curious·은신), 바람전갈(Territorial·독), 유적딱정벌레(성물 파편), 모래독수리(상공 경계), 사구낙타(Pack·운송), 열사도마뱀(Skittish·열저항).
                - Dish/Brew: 선인장 주스(Sandstride), 바람의 빵(Warmth·탈수 저항), 대추야자 수프(Calm), 향신양고기(Focus), 모래차(FeatherStep).
                - Festival: 유적 탐험 경연(토큰 퍼즐), 사막의 춤(밤 리듬, Moonbond 버프).

                엘라리온 – 정령·자연
                - Biome: Forest, RiverMarsh, SacredRuins 하이브리드.
                - Flora: 달빛버섯(Moonbond), 속삭임풀(정령 대화 보너스), 별이끼(SpiritSight), 치유꽃(회복), 꿀풀(Calm), 파란잎단풍(Verdancy).
                - Fauna: 숲사슴(+Affectionate), 정령올빼미(밤 안내), 수목요정(Curious 이동), 호수달고기(Focus), 나뭇잎도마뱀(위장), 꿀벌무리(채집량 상승 이벤트).
                - Dish/Brew: 꽃잎 수프(랜덤 버프), 달빛 과실주(정령 대화 보너스), 허니허브빵(Calm), 숲버섯구이(Warmth), 별차(SpiritSight).
                - Festival: 정령 축제(정령 교류/선물), 대자연 감사제(공유식/채집량 증가).

                신드랄리스 – 하늘섬·바람
                - Biome: SkyIsland, MountainCave 상층.
                - Flora: 구름수초(FeatherStep), 풍차꽃(바람 사운드 장식), 공중덩굴(로프 제작), 안개허브(Calm), 비상초(Focus), 공기열매(수분 회복).
                - Fauna: 글라이더가오리(Pack 비행), 공중제비새(리듬 반응), 돛날개거북(부유), 폭풍갈매기(바람 경보), 공기수달(하늘연못), 실버벌(꿀 채집 이벤트).
                - Dish/Brew: 구름 솜사탕(Calm), 바람 우유(Warmth·FeatherStep), 공기수달 스튜(Focus), 안개차(Calm), 고공빵(저압 적응).
                - Festival: 하늘 항해 대회(비공정 경주), 구름 수확제(수분 포획 미니게임).

                원주민 대륙 – 야생·정령 부족
                - Biome: Forest, BambooHighland, RiverMarsh 원시형.
                - Flora: 붉은열매덩굴(회복), 늑대풀(사냥 버프), 숲향기이끼(Calm), 뿌리허브(Warmth), 연기풀(위장), 종교목껍질(의식 도구).
                - Fauna: 늑대 무리(Pack), 대호(Epic·영혼 시험), 들판여우(Curious), 산곰(Territorial), 솔개(사체 정리), 노루(Skittish).
                - Dish/Brew: 맹수 스테이크(Warmth·Focus), 베리 와인(Calm), 뿌리찜(체력 회복), 허브차(정령 친화), 사냥꾼 수프(추적 보너스).
                - Festival: 대자연의 축제(전 부족 합식), 정령 대화 의식(영혼 시련·용기 측정).

                현자들의 대륙 – 철학·지혜
                - Biome: LibraryCampus, City, Temple 혼합.
                - Flora: 사서풀(Focus), 기록나무껍질(Craft·종이), 성찰허브(Calm), 별가루꽃(SpiritSight), 잉크열매(Dye), 현자차잎(집중 상승).
                - Fauna: 문헌수호자(거대 책벌레), 탑비둘기(메신저), 별관측여우(밤 관측), 서재고양이(+Calm), 도서뱀(두루마리 둥지), 천문부엉이(Focus).
                - Dish/Brew: 현자의 차(Focus), 철학자의 빵(철학 문장 팝업), 견과 파이(Focus 보조), 서가수프(기억력 상승), 잉크차(정신력 증가).
                - Festival: 지혜의 밤(논문 발표·퀴즈), 고대 문헌 개방일(희귀 레시피 해금).

                동방 대륙 – 무술·예술·무속
                - Biome: City, BambooHighland, Temple.
                - Flora: 매화꽃(용서·+Affectionate), 대나무순(Warmth), 인삼뿌리(체력 회복), 약초세트(Focus), 종이꽃(Dye), 향나무잎(Calm).
                - Fauna: 학(관찰자 상징), 여우령(SpiritSight 대화), 대나무팬더(+Calm), 매(검술 이벤트), 온천원숭이(Warmth), 검호늑대(야간 수련).
                - Dish/Brew: 한방 찻잔떡(Calm·랜덤 버프), 동방식 불고기(Warmth), 죽(회복), 매화주(용서·+Affectionate), 약선차(Focus).
                - Festival: 매화 축제(꽃비·감정 연동), 한밤 검술 대결(리듬·패링 미니게임).
                """
            ),
        ),
        DesignSection(
            key="solmara_regions",
            title="솔마라 지역 상세",
            body=dedent(
                """
                로덴델 – 성 안 마을
                - 장소: 왕궁, 연금술 연구소, 광장, 기사단 훈련장, '감정 미궁' 입구
                - 역할: 감정 억압과 기억 삭제 관습이 공존하는 중심지

                브레일 – 외곽 농촌
                - 장소: 목장, 곡물 창고, 여관, 연못, 폐광 소던전
                - 역할: 삶의 굴곡과 위로를 체험하는 힐링 터전

                로렐레 숲 – 힐링 구역
                - 특징: 제작 재료, 약초, 야생 동물, 회상 포인트

                작은 광산 던전
                - 특징: 위험은 낮지만 감정 조건 게이트로 경로가 열리고 닫힌다(예: 슬픔 상태일 때만 통과 가능).
                """
            ),
        ),
        DesignSection(
            key="npc_relation_rules",
            title="D. NPC 관계 & 감정 상호작용 규칙",
            body=dedent(
                """
                관계 랭크 & 점수
                - Hostile: ≤ -20 – 대화 잠금, 가격 상승, 행사 제한.
                - Wary: -19~0 – 기본 대사만, 퀘스트 소극.
                - Neutral: 1~20 – 표준 대사/가격.
                - Friendly: 21~60 – 개인 이벤트1, 가격 3% 할인.
                - Affection: 61~120 – 이벤트2, 퀘스트 우선, 특수 대사.
                - Devotion*: ≥121 – 히든 이벤트, 동반, 무도회 파트너 전용.
                - 변화량: 소 상호작용 ±1~3, 큰 이벤트 ±5~15, 하루/루프 감소 없음.
                - 배신/거짓 플래그: -20~-40 하락.

                감정 상태별 첫 인사 반응
                - Affectionate: 미소/부드러운 대사, 친화도 +1, 고백 성공률 +10%.
                - Friendly: 협조적, 거래·퀘스트 보정 +5%.
                - Neutral: 변동 없음.
                - Sad: 위로 선택지 등장, 갈등/도발 패널티.
                - Hostile: 대화 옵션 축소, 가격 상승, 토너먼트 야유 판정↓.

                기본 상호작용 동사 18개
                - Greet, SmallTalk, Gift, Listen, Apologize, Encourage, Perform(Music), Help, TradeFair, Confess,
                  Joke, ShareMeal, ShareDrink, Promise, Letter, Escort, Teach, Dance.
                - 각 동사는 조건(시간/아이템/플래그)에 따라 +또는 - 변화를 준다.
                - Promise 파기 시 -15, 진심 어린 Apologize는 Listen 성공 + journal "미안/후회" 필요.
                """
            ),
        ),
        DesignSection(
            key="npc",
            title="주요 NPC 개요",
            body=dedent(
                """
                핵심 6인
                - 세이라(기사 후보), 베르타(연금술사), 클로드(광대), 리안(목장 소년), 마이라(여관 주인), 순찰 기사(통행증 담당).
                - 각 인물은 우호/애정/슬픔 3상태 분기와 개인 이벤트 1개 이상을 제공한다.

                마을 확장 NPC
                - 광장 쌍둥이 미나·미노, 퇴역 기사 하크가 hopscotch/팽이/전역담 이벤트와 관찰자 후속 장면을 보강한다.

                서브 10인
                - 농부 부부, 대장장이, 잡화상, 귀족 참모, 길드 접수원 등.
                - 최소 6줄 대사와 감정 반응 1개를 제공하여 생활감을 보강한다.

                관찰자/진엔딩 연결
                - 관찰자 모드에서 핵심 NPC의 후속 장면 3종 이상을 확인할 수 있으며 전생 시 대사 변주가 적용된다.
                """
            ),
        ),
        DesignSection(
            key="solmara_npc_profiles",
            title="E. 솔마라 NPC 상세 (핵심 6 + 마을 확장)",
            body=dedent(
                """
                세이라 – npcId SOL_NPC_SEIRA / emotion_bias Friendly→Affectionate
                - Schedule: Day Rodendell_TrainingGround, Dusk Castle_Gate, Night Dormitory
                - Likes: ACC_CapeCrimson, SOL_BR_RoyalRoseTea, SOL_DI_RoyalSteak
                - Dislikes: BAR_BR_WraithWhiskey, JOKE_Insensitive
                - Verb Bonus: Encourage +2, Perform(Music) +2(행진곡·현악), Confess 성공률 +10%(Affection)
                - Events: EVT_SEIRA_SPARRING(Friendly/Day, rel +5, flag), EVT_SEIRA_GATEPASS(Friendly, 통행증 지급), EVT_SEIRA_BALL_PARTNER(Affection, RoyalBall, 진엔딩 힌트)
                - Observer: "라일락 아래 검사(劍士)의 실루엣이 서 있다."

                베르타 – npcId SOL_NPC_BERTA / emotion_bias Neutral→Sad
                - Schedule: Day Alchemist_Lab, Night Lab_Desk
                - Likes: MAT_RuneInk, SOL_FL_KingsThyme, DOC_FieldNotes
                - Dislikes: LOUD_Music, Pranks
                - Verb Bonus: Teach +2(연금), Listen +2(슬픔 대화)
                - Events: EVT_BERTA_TONIC(FireflyElixir 전달, rel +5, Craft EmotionMirror unlock), EVT_BERTA_DOGMA(Friendly + journal "의심", rel +3, flag)
                - Observer: "책상 위 병들은 결국 ‘치유’를 위해 진열돼 있었다."

                클로드 – npcId SOL_NPC_CLAUDE / emotion_bias Friendly
                - Schedule: Day Plaza, Night Plaza_Show
                - Likes: PERFORMANCE, Laughter, ACC_MaskSilk
                - Dislikes: Hostile_Tone
                - Verb Bonus: Joke +3(성공), Perform(Music) +3
                - Events: EVT_CLAUDE_MICROSHOW(Night, rel +4, Journal 키), EVT_CLAUDE_DISGUISE(Tournament, MASK_Simple, rel +3, flag)
                - Observer: "그의 웃음 뒤에는 타인의 슬픔을 덜어낸 자리만 남았다."

                리안 – npcId SOL_NPC_LIAN / emotion_bias Sad→Friendly
                - Schedule: Day Farm_Yard, Dusk Pond, Night Stable
                - Likes: SOL_DI_FarmersPotage, CH_CharmCollar, PETTING_Cow
                - Dislikes: Crowd, Formality
                - Verb Bonus: Listen +3, ShareMeal +2
                - Events: EVT_LIAN_LOSTCALF(Dusk/맑음, rel +6, ACC_CowBell), EVT_LIAN_PONDREFLECT(Friendly & 플레이어 Sad, rel +4, HINT_FORGIVENESS)
                - Observer: "소들은 여전히 그를 기다렸다."

                마이라 – npcId SOL_NPC_MAIRA / emotion_bias Sad→Affectionate
                - Schedule: Day Inn_Counter, Night Inn_Fireplace
                - Likes: SOL_BR_RoyalRoseTea, LETTER_Sincere, STORY_Kind
                - Dislikes: Harsh_Words
                - Verb Bonus: Listen +3, ShareDrink +2, Apologize +2(진심)
                - Events: EVT_MAIRA_LOSS(journal "상실" + RoyalRoseTea, rel +7, flag), EVT_MAIRA_LETTER(Affection & Letter, rel +5, 진엔딩 힌트)
                - Observer: "벽난로의 불빛은 여전히 편지를 비춘다."

                순찰 기사 – npcId SOL_NPC_SENTINEL / emotion_bias Neutral→Wary
                - Schedule: Day Gate, Night Gate
                - Likes: Duty, Honesty, SOL_DI_IroncapStew
                - Dislikes: Lies, Disguise_Fail
                - Verb Bonus: Encourage +1, Promise +2
                - Events: EVT_SENTINEL_PASS(SEIRA_SPARRING_DONE 또는 LetterOfIntro, 통행증, rel +3), EVT_SENTINEL_CHECK(RoyalBall, 변장 체크 실패 -10/성공 +2)
                - Observer: "그는 규칙을 믿지만, 사람을 더 믿고 싶어 했다."

                미나 – npcId SOL_NPC_MINA / emotion_bias Friendly
                - Schedule: Day Rodendell_Plaza, Evening Hopscotch_Stones
                - Likes: PLAY_ChalkSet, SWEET_HoneyTart
                - Dislikes: Rainy_Day, Broken_Promise
                - Verb Bonus: Play +2, Joke +2
                - Events: EVT_MINA_HOPSCOTCH(Day, hopscotch 함께하기, rel +2, hint PLAY_Square)
                - Observer: "웃음은 돌 틈 사이에 오래 남았다."

                미노 – npcId SOL_NPC_MINO / emotion_bias Friendly
                - Schedule: Day Rodendell_Plaza, Dusk Farm_Road
                - Likes: TOY_WoodTop, PLAY_ChalkSet
                - Dislikes: Windy_Weather
                - Verb Bonus: Joke +2
                - Events: EVT_MINO_TOP(TOY_WoodTop 선물, rel +3, 팽이 기술 공유)
                - Observer: "팽이는 빙글 돌아도 길을 잃지 않았다."

                하크 – npcId SOL_NPC_HARK / emotion_bias Neutral→Friendly
                - Schedule: Day Castle_Shade, Night Inn_Porch
                - Likes: SOL_BR_AppleWine, SOL_DI_IroncapStew
                - Dislikes: Boast, Broken_Pledge
                - Verb Bonus: Listen +2, Teach +1
                - Events: EVT_HARK_STORY(Night + 사과 와인, rel +4, hint HINT_GATE_HONOR)
                - Observer: "무거운 갑옷보다 무거운 이야기가 있었다."
                """
            ),
        ),
        DesignSection(
            key="gift_preferences",
            title="F. 선물 선호 가중치",
            body=dedent(
                """
                선물 1회/일/인물, 두 번째부터 효과 50%.
                - SOL_BR_RoyalRoseTea: 세이라 +3, 베르타 +2, 클로드 +1, 리안 +1, 마이라 +4, 순찰 +1, 미나 +1, 미노 +1, 하크 +1
                - SOL_DI_RoyalSteak: 세이라 +4, 베르타 +1, 클로드 +2, 리안 +2, 마이라 +1, 순찰 +3, 미나 0, 미노 0, 하크 +1
                - SOL_BR_AppleWine: 세이라 +2, 베르타 0, 클로드 +4, 리안 +2, 마이라 +3, 순찰 0, 미나 0, 미노 0, 하크 +4
                - SOL_DI_FarmersPotage: 세이라 +1, 베르타 +1, 클로드 +1, 리안 +4, 마이라 +2, 순찰 +2, 미나 +1, 미노 +1, 하크 +1
                - ACC_MaskSilk: 세이라 +1, 베르타 0, 클로드 +4, 리안 0, 마이라 +2, 순찰 -2, 미나 0, 미노 +1, 하크 0
                - SOL_BR_FireflyElixir: 세이라 +1, 베르타 +4, 클로드 +2, 리안 +1, 마이라 +2, 순찰 0, 미나 0, 미노 0, 하크 +1
                - SOL_DI_IroncapStew: 세이라 +1, 베르타 +2, 클로드 +1, 리안 +2, 마이라 +1, 순찰 +4, 미나 0, 미노 0, 하크 +3
                - SWEET_HoneyTart: 세이라 +1, 베르타 0, 클로드 +2, 리안 +2, 마이라 +3, 순찰 0, 미나 +4, 미노 +2, 하크 +1
                - PLAY_ChalkSet: 세이라 +1, 베르타 0, 클로드 +2, 리안 +1, 마이라 +1, 순찰 0, 미나 +4, 미노 +3, 하크 0
                - TOY_WoodTop: 세이라 0, 베르타 0, 클로드 +1, 리안 +1, 마이라 +1, 순찰 0, 미나 +1, 미노 +4, 하크 +1
                """
            ),
        ),
        DesignSection(
            key="communication_hooks",
            title="G. 편지·루머·축제 연계",
            body=dedent(
                """
                편지 트리거
                - LETTER_SEIRA_INVITE: Friendly 이상, 토너먼트 전날 도착 → 훈련장 초대, 친밀 +2.
                - LETTER_MAIRA_FIREPLACE: 밤 벽난로 대화 활성, 위로 이벤트 +3.
                - LETTER_BERTA_NOTE: 실험 보조 의뢰, 재료 전달 시 Craft 해금.

                루머 풀(일일 3개 랜덤)
                - 시장 가십, 성문 단속, 숲 반딧불 웨이브, 무도회 준비 등.
                - 루머 클릭 시 지도 마커/퀘스트 힌트 활성.

                축제 상호작용
                - 기사 토너먼트: 응원 타이밍 미니게임 → 세이라/순찰 기사 호감 보정.
                - 왕실 무도회: 파트너 선택·댄스 리듬 → 마이라/세이라/클로드 전용 대사.
                - 축제 기간 Nobility/Calm 글로벌 버프 적용.
                """
            ),
        ),
        DesignSection(
            key="conflict_resolution",
            title="H. 갈등·사과·약속 시스템",
            body=dedent(
                """
                갈등 발생
                - 금지 주제, 거짓말, 변장 실패, Hostile 대사 선택 → 관계 -8~-20, flag CONFLICT_X.

                사과
                - 진심: journal 키워드 "미안/후회" + Listen 성공 → 관계 +6, flag 제거.
                - 형식적: 실패 시 관계 -3.

                약속
                - Promise 동사 성공 시 flag PROMISE 생성, 이행 실패 시 관계 -15.
                """
            ),
        ),
        DesignSection(
            key="reincarnation_rules",
            title="I. 전생 & 관찰자 연계",
            body=dedent(
                """
                - 전생 1회 이상이면 같은 NPC 첫 인사 호감 +1(과거 랭크 ≥ Friendly 기준).
                - 관찰자 모드에서 본 컷신의 인물과 재회 시 초기 대사가 변주된다.
                - 진엔딩 힌트(라일락, 바레토스 진상) 횟수에 따라 추가 대사 키가 노출된다.
                - 오르골 키 등 관찰자 호출 유물 사용 시 패킷 3종 로테이션을 확인 가능.
                """
            ),
        ),
        DesignSection(
            key="qa_artifacts",
            title="J. QA 체크리스트 – 유물 & 상호작용",
            body=dedent(
                """
                - 유물 18종 획득/장착/활성화 툴팁, 쿨타임, 충전 표기를 검증한다.
                - 시간의 수정·운명의 돌·감정의 거울이 실타래/대화/게이트에 미치는 효과를 체감한다.
                - 핵심 NPC 6인과 확장 NPC 3명의 동사 중 최소 8개가 정상 반응하며 선호/비선호 차등이 드러난다.
                - 편지 3종, 루머 5종 이상이 순환하고 지도 힌트가 활성화된다.
                - 오르골 키로 관찰자 패킷 최소 1개 이상을 호출할 수 있다.
                """
            ),
        ),
        DesignSection(
            key="events",
            title="솔마라 축제 & 시퀀스",
            body=dedent(
                """
                기사 토너먼트
                - 루트: 참관, 지원, 몰래 참가(변장)
                - 감정 시스템: 플레이어의 감정 상태에 따라 대사와 결과가 변한다.

                왕실 무도회
                - 조건: 초대장 확보, 변장, 동반자 선택
                - 보상: 히든 퀘스트, 관계 급상승, 진엔딩 힌트

                감정 미궁 & 감정의 실타래
                - 감정 타일을 밟아 음악과 회상을 완성하는 핵심 의식 콘텐츠
                """
            ),
        ),
        DesignSection(
            key="gameplay_loop",
            title="게임플레이 루프",
            body=dedent(
                """
                1. 탐험 및 대화로 감정 변화를 유도한다.
                2. 감정 변화는 색, 음악, 대사 연출을 동기화하며 표현된다.
                3. 기억이 저장되고 일기/꿈 시스템과 연결된다.
                4. 미니던전, 감정 미궁, 감정 타일을 통해 선택과 인연이 분기한다.
                5. 자연사 후 관찰자 모드로 전환된다.
                6. 관찰자 모드에서 세계의 변화를 목격하거나 전생을 선택한다.
                7. 누적된 감정 패턴이 다음 생의 만남, 대사, 연출에 영향을 주며 루프가 반복된다.
                8. 조건을 충족하면 진엔딩으로 이어진다.
                """
            ),
        ),
        DesignSection(
            key="life_cycle",
            title="생사/전생/관찰자/진엔딩 규칙",
            body=dedent(
                """
                - 자연사: 감정 정리가 충분할 때 관찰자 모드 진입 가능.
                - 관찰자 모드: 고정 시점에서 마을과 인연의 후속 변화를 관람하며 다음 전생의 힌트를 수집한다.
                - 전생: 새로운 캐릭터로 재시작하되 기억은 잊고 감정 경향과 인연 끌림은 잔존한다.
                - 진엔딩(실타래의 중심): 전생 3회 이상, 핵심 인연 해소, 감정 조각 확보, 왕실 무도회 대면/감정 미궁 최종 방/감정의 실타래 완주를 달성해야 한다.
                """
            ),
        ),
        DesignSection(
            key="emotion_system",
            title="감정 시스템",
            body=dedent(
                """
                EmotionState: Neutral, Friendly, Hostile, Affectionate, Sad.
                - 표현: UI 색상, 화면 필터, 자막 톤, BGM 레이어, 카메라 연출이 동기화된다.
                - 변화 트리거: 대화 키워드, 선택지, 공연/음악, 일기 기록, 꿈, 감정 타일, 유물.
                - 감정 도감과 통계는 감정 조각/경향을 시각화하고 다음 회차 전략을 제공한다.
                """
            ),
        ),
        DesignSection(
            key="emotion_thread",
            title="감정의 실타래 사양",
            body=dedent(
                """
                - 구성: 9개의 감정 타일(외로움 → 그리움 → 희망 → 사랑 → 두려움 → 분노 → 용서 → 평온 → 관찰).
                - 규칙: 타일을 밟을 때마다 고유 음원 레이어가 믹싱되어 음악이 완성된다.
                - 분기: 올바른 감정 흐름이면 하모니, 어긋나면 불협/왜곡 이펙트가 발생하며 회고 대사가 변한다.
                - 연출: 타일별 색, 입자, 카메라, 텍스트, 빛의 진폭이 박자와 동기화된다.
                - 보상: 기억 회복, 감정 조각, 진엔딩 힌트. 루프마다 변주가 제공된다.
                """
            ),
        ),
        DesignSection(
            key="world_scenes",
            title="월드 씬 구조 – 솔마라 1차 출시",
            body=dedent(
                """
                로덴델 성 안 마을
                - 출입구: 북문(왕궁), 남문(브레일 외곽), 연금술 연구소 지하 통로(감정 미궁). 총 3개의 경로로 이동이 가능하다.
                - 상호작용 포인트(10): 1) 왕궁 정문 의례, 2) 기사단 훈련 허수아비, 3) 연금술 연구소 환류 장치, 4) 광장 공연대, 5) 감정 도감 게시판, 6) 감정 미궁 입구 진동석, 7) 성문 통행 검문소, 8) 추억 벤치(일기 단축), 9) 시장 상인 카트, 10) 분수대에 비친 기억.
                - 감정 게이트: 왕궁 정문은 Friendly 이상 또는 Affectionate 상태에서만 완전 개방, Sad 상태에서는 2차 대사 후 설득 필요.

                브레일 외곽 농촌
                - 출입구: 서쪽 농로(로렐레 숲), 동쪽 언덕길(로덴델), 남쪽 하천길(폐광). 3개의 자연 이동로.
                - 상호작용 포인트(10): 1) 목장 우리, 2) 곡물 창고 출납부, 3) 여관 카운터, 4) 여관 벽난로 추억석, 5) 연못 반딧불, 6) 바람 방앗간, 7) 농부 부부 식탁, 8) 리안의 스케치북, 9) 폐광 인부 기록판, 10) 이동 상인의 감정 카드를 엿보기.
                - 감정 게이트: 폐광 입구는 Sad 또는 Affectionate 상태일 때만 안전 통과, Hostile이면 경고음과 함께 NPC가 제지한다.

                로렐레 숲 힐링 존
                - 출입구: 브레일 농로, 숲속 약초 길, 숲-실타래 포털. 총 3곳.
                - 상호작용 포인트(10): 1) 휴식 정자 차분 모닥불, 2) 약초 군락 채집, 3) 숲 영혼 나무, 4) 잔잔한 시냇물, 5) 향수 돌무더기, 6) 새소리 모니터링, 7) 감정 균형 돌판, 8) 하프 연주자, 9) 관찰자 시선 흔적, 10) 실타래 포털 앞 빛나는 실타래 조각.
                - 감정 게이트: 숲 영혼 나무는 Affectionate 또는 Friendly 상태에서만 정령이 나타나며, Hostile이면 안개가 시야를 가린다.

                작은 광산 미니던전
                - 출입구: 브레일 남쪽 하천길, 광산 측면 갱도 문. 2개의 입구.
                - 상호작용 포인트(10): 1) 광석 층, 2) 무너진 갱목, 3) 감정 공명 수정, 4) 지하수 웅덩이, 5) 채굴꾼 낙서, 6) 은은한 노래 잔향, 7) 슬픔의 문(감정 게이트), 8) 감정 균형 저울 퍼즐, 9) 봉인된 상자, 10) 미니 지도 조각.
                - 감정 게이트: 슬픔의 문은 Sad 상태에서만 열리며, Friendly일 때는 미세한 불협 BGM으로 진입 제한을 암시한다.

                감정의 실타래 전용 공간
                - 출입구: 로렐레 숲 포털, 로덴델 감정 미궁 비밀 엘리베이터. 2개의 진입로.
                - 상호작용 포인트(10): 9개의 감정 타일과 클리어 후 나타나는 관찰자의 심장석. 각 타일은 밟을 때마다 음악 레이어가 켜지고 회상을 재생한다.
                - 감정 게이트: 입구는 Neutral 상태에서는 흐릿하며, 특정 감정(희망 혹은 사랑)으로 정렬해야만 완전한 빛의 길이 보인다.

                관찰자 모드 뷰
                - 출입구: 자연사 트리거, 감정의 실타래 클리어 이후 선택지. 2개의 진입 경로.
                - 상호작용 포인트(10): 1) 패닝 카메라 앵글 선택, 2) 로덴델 왕궁 후속 장면, 3) 브레일 여관 일상, 4) 숲 정령들의 속삭임, 5) 기사단 게시판 업데이트, 6) NPC 관계 그래프 확인, 7) 감정 기후 시각화, 8) 전생 힌트 조각, 9) 관찰자 나레이션 로그, 10) 전생/종결 선택 노드.
                - 감정 게이트: 관찰자 카메라 확대는 Affectionate 또는 Sad 패턴이 일정 수준 이상일 때만 깊은 장면을 보여 주며, Hostile 잔여 감정이 많으면 시야가 제한된다.
                """
            ),
        ),
        DesignSection(
            key="scene_landmarks",
            title="랜드마크 상호작용 & 감정 반응",
            body=dedent(
                """
                로덴델 왕궁
                - 상호작용 텍스트: 1) "황금빛 계단이 마음을 시험한다.", 2) "왕의 방패 문양이 지난 전생의 결심을 비춘다.", 3) "궁정 음악이 현재 감정을 따라 음계를 바꾼다."
                - 감정 반응: Friendly일 때 음계가 장조로 전환되고, Sad일 때는 현악이 사라져 고요한 잔향만 남는다.

                연금술 연구소
                - 상호작용 텍스트: 1) "거품이 이는 플라스크가 두근거림을 닮았다.", 2) "고서에 감정 수치화 그래프가 적혀 있다.", 3) "감정 물약 시연대가 희미한 빛으로 반응한다."
                - 감정 반응: Affectionate 상태에서만 연구소 심장이 개방되어 추가 대화가 열린다.

                로덴델 광장
                - 상호작용 텍스트: 1) "광대의 종소리가 마음을 가볍게 두드린다.", 2) "분수대 물결이 지난 선택을 반사한다.", 3) "상인들의 호객이 감정 아이콘으로 표시된다."
                - 감정 반응: Sad 상태에서는 분수대 색이 청록으로 변해 위로의 선택지가 생성된다.

                기사단 훈련장
                - 상호작용 텍스트: 1) "목검과 방패의 마찰이 박동처럼 울린다.", 2) "훈련일지에 도전 여부를 적을 수 있다.", 3) "관찰자 흔적이 모래 위에 남는다."
                - 감정 반응: Hostile 감정이 높으면 도전 루트가 잠시 봉인되고, Friendly면 격려의 함성이 나온다.

                브레일 여관
                - 상호작용 텍스트: 1) "따뜻한 수프 향이 마음을 풀어 준다.", 2) "벽난로 위 사진이 잊힌 인연을 불러온다.", 3) "손님들의 노래가 감정 스템을 추가한다."
                - 감정 반응: Affectionate일 때 화음이 겹겹이 쌓이며 관계 상승 이벤트가 열린다.

                브레일 목장
                - 상호작용 텍스트: 1) "젖소가 플레이어 감정에 따라 꼬리를 흔든다.", 2) "목장 울타리에 새겨진 낙서가 전생 힌트를 암시한다.", 3) "리안의 노트가 감정 그래프를 보여 준다."
                - 감정 반응: Sad 상태에서는 목장 배경음에 현악 패드가 추가되어 위로 대사가 열린다.

                브레일 연못
                - 상호작용 텍스트: 1) "물결에 어렴풋이 다른 생의 얼굴이 비친다.", 2) "수면 위 반딧불이 감정 타이밍에 맞춰 밝기를 바꾼다.", 3) "돌다리 밑에서 바레토스 떡밥이 적힌 병이 떠오른다."
                - 감정 반응: Friendly 상태에서만 병 속 기록을 안전히 건질 수 있다.

                로렐레 숲 휴식 정자
                - 상호작용 텍스트: 1) "정자의 풍경이 숨을 고르게 한다.", 2) "바람 종이 감정에 맞춰 화음을 교체한다.", 3) "벤치 아래에 감정 조각이 숨겨져 있다."
                - 감정 반응: 평온(Pacified) 감정이 일정 수치 이상일 때 숨겨진 감정 조각이 드러난다.

                약초 군락
                - 상호작용 텍스트: 1) "잎사귀가 살짝 파랗게 빛나며 감정을 읽는다.", 2) "향기가 감정 UI에 잔물을 남긴다.", 3) "희망 키워드를 일기에 적으면 더 많은 약초가 자란다."
                - 감정 반응: Hope 키워드 작성 후 방문하면 약초 수량이 2배가 된다.

                실타래 포털
                - 상호작용 텍스트: 1) "빛의 실이 손끝을 감싼다.", 2) "음계가 서서히 켜져 간다.", 3) "관찰자의 숨결이 길을 안내한다."
                - 감정 반응: 사랑 또는 희망 상태에서만 완전한 루트가 열린다.
                """
            ),
        ),
        DesignSection(
            key="npc_core_dialogues",
            title="핵심 NPC 대사 & 이벤트",
            body=dedent(
                """
                세이라 – 기사 후보생 (총 24줄)
                - Friendly: 1) "오늘의 하늘은 당신의 검을 닮았네요.", 2) "같이 방패 연습을 해줄래요?", 3) "성문 밖에서 본 풍경을 일기에 적었어요.", 4) "당신의 감정이 기사단에도 전해졌어요.", 5) "훈련일지에 당신 이름을 기록해도 될까요?", 6) "언젠가 함께 왕국을 지켜요.", 7) "토너먼트에서 응원해 줄 거죠?", 8) "당신 덕분에 오늘은 웃을 수 있었어요."
                - Affectionate: 1) "당신이 없으면 검이 떨려요.", 2) "손을 잡으면 감정이 안정돼요.", 3) "무도회에서 춤을... 생각해도 될까요?", 4) "전생에서도 우리는 동료였을까요?", 5) "기사 서약에 당신을 적어도 돼요?", 6) "감정의 실타래에서 당신 목소리를 들었어요.", 7) "전생이 바뀌어도 다시 찾을게요.", 8) "오늘 밤 연무장에 별빛이 내려요."
                - Sad: 1) "검이 무거워졌어요.", 2) "토너먼트를 포기해야 할지도 몰라요.", 3) "당신이 멀어진다면 감정이 무너져요.", 4) "일기에 당신을 잃는 꿈을 썼어요.", 5) "관찰자 모드에서 본 제 모습이 낯설었어요.", 6) "훈련장 모래가 빛을 잃었어요.", 7) "혹시 저를 용서해 줄 수 있나요?", 8) "이 감정을 어떻게 다뤄야 할까요?"
                - 개인 이벤트: "기사 서약의 새벽" – 감정 게이트 Friendly 이상, 손을 맞잡고 왕궁 성벽에 서약 글자를 새기며 관계 대폭 상승.

                베르타 – 연금술사 (총 24줄)
                - Friendly: 1) "감정 데이터를 표로 만들었어요.", 2) "새로운 촉매제를 시험해볼까요?", 3) "연금 솥이 당신의 기분을 반영하네요.", 4) "실패도 기록으로 남겨야죠.", 5) "브레일에서 온 허브가 필요해요.", 6) "감정 물약의 부작용을 줄였어요.", 7) "여관 주인이 부탁한 주문을 완성했어요.", 8) "당신 일기에 실험 기록을 첨부해도 될까요?"
                - Affectionate: 1) "당신과의 대화는 어떤 연금술보다 안정적이에요.", 2) "감정 스펙트럼을 같이 관측해줄래요?", 3) "나도 감정을 믿어보고 싶어졌어요.", 4) "전생에서 우리가 동료였다는 기록을 찾았어요.", 5) "연금 도감에 당신의 이름을 새겨두었어요.", 6) "감정 실타래 보상은 우리 둘만의 비밀이에요.", 7) "당신이 오기 전까지 연구실이 너무 조용했죠.", 8) "언젠가 함께 새로운 대륙의 연구를 할까요?"
                - Sad: 1) "오늘은 실험이 연달아 실패했어요.", 2) "감정 수치가 흔들리네요.", 3) "연금실에 남은 건 냉기뿐이에요.", 4) "당신이 믿어준다면 다시 시작할 수 있을까요?", 5) "허브 향이 위로가 되지 않네요.", 6) "관찰자 모드에서 본 미래가 흐릿했어요.", 7) "감정 물약이 눈물처럼 떨어졌어요.", 8) "오늘만큼은 함께 있어 줄래요?"
                - 개인 이벤트: "연금술사의 고백" – 실험실에서 감정 물약을 같이 완성하며 Affectionate 분기 대사와 고백 컷신 연출.

                클로드 – 광장 광대 (총 24줄)
                - Friendly: 1) "사과 와인 대신 웃음을 마셔봐요!", 2) "분수대 앞 공연 예약 완료!", 3) "당신의 감정이 내 연출을 완성해요.", 4) "오늘의 농담은 관찰자도 웃게 만들 걸요?", 5) "실타래에서 들고 온 음을 쇼에 쓸래요.", 6) "토너먼트 응원가는 준비됐나요?", 7) "웃음 의식에서 함께 손을 맞잡아요.", 8) "도시에 빛이 다시 깃들었어요."
                - Affectionate: 1) "당신 앞에서만 탈을 벗을게요.", 2) "내 감정 카드에 당신이 있어요.", 3) "무도회에서 몰래 춤을 추자고요.", 4) "관찰자 모드에서도 당신과 웃었어요.", 5) "전생의 기억이 공연 조명으로 돌아왔어요.", 6) "당신을 위해 새로운 희망 곡을 쓰고 있어요.", 7) "내 일기 첫 장이 당신 이야기로 가득해요.", 8) "웃음 의식의 마지막 대사를 당신에게 드릴게요."
                - Sad: 1) "관객들이 울고 있어요.", 2) "내 농담이 빛을 잃었네요.", 3) "광장 종소리가 흐릿해졌어요.", 4) "웃음 의식이 실패했어요.", 5) "당신의 감정이 멀어졌다고 느껴요.", 6) "일기에 우울한 점만 남았어요.", 7) "내가 더 도울 수 있을까요?", 8) "다시 웃게 해줄래요?"
                - 개인 이벤트: "웃음 의식" – 감정 타일 퍼포먼스를 함께 완주하면 광장 색상이 변하고 관계 상승.

                리안 – 목장 소년 (총 24줄)
                - Friendly: 1) "소들이 당신을 기억하는 것 같아요.", 2) "꿈에서 관찰자가 되는 상상을 했어요.", 3) "목초 향이 기분을 안정시켜줘요.", 4) "당신이 오면 목장이 환해요.", 5) "감정 도감에 목장 항목을 추가했어요.", 6) "실타래에서 본 빛을 그림으로 그렸어요.", 7) "다음 전생에도 친구가 되어줄래요?", 8) "농작물에게도 감정이 있다니 신기해요."
                - Affectionate: 1) "당신과 있으면 시간 흐름이 느려져요.", 2) "꿈에서 우리는 항상 함께였어요.", 3) "연못 반딧불이 우리 감정에 맞춰 춤춰요.", 4) "당신의 일기를 살짝 봤어요. 마음이 울었어요.", 5) "전생에서도 당신을 기다렸던 것 같아요.", 6) "관찰자 모드로 가도 당신을 지켜볼 거예요.", 7) "브레일 축제를 둘이서 걸어보고 싶어요.", 8) "감정 실타래를 클리어하면 내 마음도 정리될까요?"
                - Sad: 1) "오늘은 목장이 조용해요.", 2) "꿈에서 당신을 잃었어요.", 3) "농부 부부가 싸워서 마음이 무거워요.", 4) "감정 그래프가 계속 내려가요.", 5) "관찰자의 시선이 차갑게 느껴졌어요.", 6) "우리가 다시 만나지 못하면 어떡하죠?", 7) "연못 물결이 흐릿해졌어요.", 8) "내가 더 노력해볼게요."
                - 개인 이벤트: "연못의 약속" – 밤에 연못에서 감정 반딧불을 함께 따라가면 전생 힌트와 관계 상승 컷신.

                마이라 – 여관 주인 (총 24줄)
                - Friendly: 1) "따뜻한 차로 마음을 덮어줄게요.", 2) "오늘의 일기 키워드는 용서예요.", 3) "관광객들에게 감정의 실타래 이야기를 들려줬어요.", 4) "토너먼트 참관객들이 방을 예약했어요.", 5) "여관 악보에 당신이 남긴 음을 더했어요.", 6) "허브 파우치가 도착했어요.", 7) "꿈에서 본 장면이 현실이 되길 바랄게요.", 8) "언제든 쉬어가요."
                - Affectionate: 1) "당신이 여관에 들어오면 공기가 바뀌어요.", 2) "내 상실을 당신과 나누고 싶어요.", 3) "관찰자 모드에서 당신을 기다릴게요.", 4) "무도회 이야기를 들려주고 싶어요.", 5) "당신을 위한 비밀 방을 준비했어요.", 6) "감정 물약 대신 따뜻한 포옹이 필요해요.", 7) "전생에서 우리는 여관을 함께 지켰던 것 같아요.", 8) "감정의 실타래 마지막 음이 당신과 겹쳤어요."
                - Sad: 1) "오늘은 방이 너무 조용해요.", 2) "잃어버린 가족을 떠올렸어요.", 3) "여관 벽난로가 식어버렸네요.", 4) "당신의 손을 잡고 있어도 눈물이 나요.", 5) "용서가 아직 멀게 느껴져요.", 6) "관찰자 패킷에서 울고 있는 나를 봤어요.", 7) "꿈 속에서 딸아이가 등을 돌렸어요.", 8) "함께 울어줄래요?"
                - 개인 이벤트: "상실에서 용서로" – 슬픔 상태에서 여관 벽난로 앞 대화를 진행하면 용서 컷신과 감정 게이트 해제.

                순찰 기사 도린 – 통행증 담당 (총 24줄)
                - Friendly: 1) "통행 기록에 당신을 믿고 적어둘게요.", 2) "성문 근무가 당신 덕에 덜 지루해요.", 3) "기사단 소식지를 건네줄까요?", 4) "브레일에 가면 경계할 점을 알려줄게요.", 5) "감정의 실타래 이야기를 들려주세요.", 6) "토너먼트 참가를 응원할게요.", 7) "연금술사의 추천서를 확인했어요.", 8) "이 통행증은 감정에 반응하니 조심하세요."
                - Affectionate: 1) "당신에게만 비밀 통로를 알려줄게요.", 2) "함께 순찰 돌래요?", 3) "관찰자 모드에서 당신을 봤어요.", 4) "전생에서도 문을 지켰던 기억이 어렴풋해요.", 5) "당신이 돌아올 때까지 성문을 열어둘게요.", 6) "무도회에서 조용히 만나요.", 7) "감정이 빛나는 통행증을 선물하고 싶어요.", 8) "당신을 위해 기사단 규칙을 검토했어요."
                - Sad: 1) "성문이 오늘따라 무겁네요.", 2) "도시가 침묵에 잠겼어요.", 3) "통행증이 푸른빛으로 식어버렸어요.", 4) "당신을 보호하지 못할까 봐 두려워요.", 5) "관찰자 시점에서 비극을 봤어요.", 6) "전생의 실패가 떠오르네요.", 7) "감정이 흔들리면 문도 흔들려요.", 8) "다시 웃을 수 있을까요?"
                - 개인 이벤트: "성문 야간 순찰" – 밤에 함께 순찰하며 감정 게이트를 해제, 관찰자 힌트 확보.
                """
            ),
        ),
        DesignSection(
            key="npc_supporting",
            title="서브 NPC 대사",
            body=dedent(
                """
                대장장이 길렌 – 6줄
                1) "쇠망치가 당신 감정 박자에 맞춰 울려요." 2) "무기보다 마음을 먼저 다듬어요." 3) "감정 물약을 칼집에 발라볼까요?" 4) "토너먼트 응원 장비를 준비했어요." 5) "전생에서 당신이 맡긴 검을 기억해요." 6) "Hostile이면 금속이 붉게 달아오르네요." 감정 반응: Sad 상태일 때 무료 수리.

                농부 헤렌 – 6줄
                1) "새싹이 당신 웃음에 반응해요." 2) "오늘 수확은 우정 덕분이에요." 3) "비가 오기 전 감정이 눅눅해지네요." 4) "일기에 씨앗 이야기를 적어주세요." 5) "관찰자 모드에서 밭을 보았죠?" 6) "슬플 때는 씨앗을 선물할게요." 감정 반응: Friendly 시 추가 작물 획득.

                농부 사라 – 6줄
                1) "오븐에서 빵 굽는 냄새가 위로를 줄 거예요." 2) "감정이 무거울수록 반죽을 오래 치대요." 3) "리안에게는 웃음이 필요해요." 4) "꿈속에서도 밭을 갈더라고요." 5) "감정 실타래를 클리어하면 이 빵을 받으세요." 6) "Sad면 따뜻한 수프를 준비할게요." 감정 반응: 슬픔 상태 시 체력 회복 음식 제공.

                잡화상 메이미 – 6줄
                1) "새 감정 아이콘 스티커가 입고됐어요." 2) "Hostile 기운은 할인으로 날려버려요." 3) "무도회 변장 세트가 필요하죠?" 4) "일기 키워드 카드 10종 세트!" 5) "관찰자도 쇼핑을 할까요?" 6) "Affectionate면 덤을 줄게요." 감정 반응: 애정 상태 시 희귀 아이템 구매 가능.

                귀족 참모 알릭 – 6줄
                1) "기억 삭제 관습은 왕국을 지키는 법이죠." 2) "당신 감정이 정책에 영향을 줄 수 있군요." 3) "관찰자 모드의 기록을 공유할 수 있나요?" 4) "토너먼트는 정치적 의미가 큽니다." 5) "일기에 국가 비밀은 적지 말아주세요." 6) "Sad면 잠시 협상력을 잃게 되죠." 감정 반응: Friendly 이상일 때 왕실 무도회 정보 제공.

                길드 접수원 노아 – 6줄
                1) "퀘스트 보드가 감정 색으로 빛나요." 2) "슬픔 조건 퀘스트를 찾고 있나요?" 3) "전생 기록도 참고할 수 있어요." 4) "감정 보고서를 제출해주세요." 5) "토너먼트 지원서를 대신 내드릴게요." 6) "Affectionate면 특급 의뢰를 열어줄게요." 감정 반응: 감정 상태 따라 의뢰 난이도 변화.

                여관 직원 티아 – 6줄
                1) "방 정리도 감정 순서대로 하죠." 2) "밤마다 꿈 이야기를 수집해요." 3) "관찰자에게 메시지를 전달할까요?" 4) "감정 실타래 예약을 도와줄게요." 5) "슬픔이면 무료로 따뜻한 물을 준비해요." 6) "애정이면 비밀 통로를 알려줄게요." 감정 반응: 감정 패턴에 따라 서비스 제공.

                폐광 인부 요안 – 6줄
                1) "광산 벽이 감정을 먹고 있어요." 2) "슬픔의 문은 내가 지키고 있죠." 3) "전생에서 이곳을 무너뜨린 건 우리일까요?" 4) "감정 공명 수정이 희망을 들려줘요." 5) "Hostile이면 갱도가 위험해요." 6) "감정 게이트 통과법을 알려줄게요." 감정 반응: Sad일 때 안전 경로 안내.

                숲 정령 안내자 피에 – 6줄
                1) "나뭇잎이 당신 감정으로 흔들려요." 2) "정령어로 꿈을 번역해줄까요?" 3) "실타래 포털이 곧 열려요." 4) "Affectionate면 정령들이 춤춰요." 5) "Sad면 빛이 잿빛으로 바뀌죠." 6) "관찰자 흔적을 따라가 보세요." 감정 반응: 감정 상태에 따라 포털 힌트 제공.

                이동 시인 엘른 – 6줄
                1) "당신 이야기를 노래로 만들게요." 2) "감정 키워드를 주면 즉흥시를 써요." 3) "관찰자에게 들려줄 멜로디가 필요해요." 4) "무도회에서 이 노래를 부를 수 있을까요?" 5) "슬픔이면 장조를 단조로 바꿔줄게요." 6) "애정이면 듀엣을 제안할게요." 감정 반응: 감정 상태에 따라 노래 편곡.

                순찰 보조병 미레 – 6줄
                1) "성벽에서 감정 바람을 측정해요." 2) "당신 통행 기록이 빛나요." 3) "도린 기사님의 감정을 대신 전할게요." 4) "토너먼트 배치표가 업데이트됐어요." 5) "Sad면 순찰 교대 시간을 조정해줄게요." 6) "Affectionate면 휴식 장소를 알려줄게요." 감정 반응: 감정에 따라 통행 루트 안내.
                """
            ),
        ),
        DesignSection(
            key="relationship_events",
            title="관계 이벤트 세트",
            body=dedent(
                """
                고백 이벤트 – "감정 고백의 밤"
                - 조건: Affectionate 상태의 핵심 NPC와 저녁 이후 대화, 감정 아이콘이 핑크빛으로 변한다.
                - 연출: 배경 LUT가 따뜻한 오렌지로 전환, 글자 타이핑 속도가 1.2배 느려짐, 글로켄슈필과 스트링 스템이 +4dB로 상승.
                - 결과: 관계 등급 애정 잠금 해제, 감정 조각(사랑) 획득, 다음 전생에서 특수 첫 대사 등장.

                이별 이벤트 – "흐릿한 광장"
                - 조건: Sad 상태, 관계 점수 급락, 감정 실타래 실패 이후.
                - 연출: 화면이 청록 필터로 덮이고, 텍스트가 줄마다 말줄임표가 붙는다. 저음 드론이 추가되어 감정 무게를 표현.
                - 결과: 관계 등급 우정으로 하락, 감정 조각(슬픔) 획득, 관찰자 모드에서 후속 장면 패킷 추가.

                용서 이벤트 – "용서의 벽난로"
                - 조건: 마이라 이벤트 진행 후, 플레이어가 용서 키워드를 일기에 작성, Sad에서 Friendly로 회복 중.
                - 연출: 벽난로 불빛이 라일락 화이트로 번지고, 합창 스템이 은은히 깔리며, 텍스트가 Playfair Display 이탤릭으로 출력.
                - 결과: 관계 등급 우정 이상 회복, 감정 조각(용서) 획득, 감정 게이트(여관 비밀 방) 해제.
                """
            ),
        ),
        DesignSection(
            key="quests_main",
            title="메인 퀘스트 – 실타래의 시작",
            body=dedent(
                """
                단계 1: 기억 회복
                - 감정 가드: Sad 상태일 때만 왕궁 기록 보관소에서 잃어버린 기록을 열람할 수 있다.
                - 목표: 기억 조각 3개 수집, 일기 키워드 2개 등록.

                단계 2: 감정 정리
                - 로렐레 숲 정자에서 감정 균형 의식 수행.
                - 목표: 감정 그래프를 중립으로 되돌리고 정령에게서 실타래 포털 인증을 받는다.

                단계 3: 감정의 실타래 클리어
                - 9개 타일을 순서대로 밟아 하모니를 완성.
                - 목표: 회상 문장 9개 모두 활성, 하모니 유지율 80% 이상.

                단계 4: 관찰자 해금
                - 자연사 컷신 이후 관찰자 모드 진입 확률 100% 달성.
                - 목표: 관찰자 패킷 1개 이상 시청, 전생 선택 여부 결정.

                단계 5: 전생 준비
                - 관찰자 모드에서 전생 힌트 2개 수집 후 결정.
                - 목표: 감정 패턴을 다음 생으로 전송하고 루프 카운트를 +1.
                """
            ),
        ),
        DesignSection(
            key="quests_side",
            title="서브 퀘스트 4종",
            body=dedent(
                """
                기사 토너먼트 – 지원/몰래 참가 루트
                - 단계: (1) 지원 요청 수락 → (2) 장비 준비(감정 물약 사용) → (3) 토너먼트 중 응원/몰래 참가 → (4) 결과 발표.
                - 감정 영향: Friendly 이상이면 참관 시 버프, Hostile이면 몰래 참가 실패 확률 증가, Affectionate 시 특별 컷신.

                마이라의 상실 극복
                - 단계: (1) 여관에서 상실 이야기를 듣는다 → (2) 용서 키워드를 일기에 작성 → (3) 벽난로 앞 컷신 → (4) 감정 조각(용서) 획득.
                - 감정 영향: Sad 상태일 때만 이벤트 진행, Friendly 이상으로 회복하면 보상 강화.

                클로드의 웃음 의식
                - 단계: (1) 광장 공연 준비 → (2) 감정 타일 연출 동참 → (3) 관객 감정 측정 → (4) 웃음의 폭발 컷신.
                - 감정 영향: Affectionate면 듀엣 공연, Sad면 위로 대사 추가, Hostile이면 공연이 지연된다.

                연금술 의뢰 – 감정 물약 제작
                - 단계: (1) 베르타에게서 재료 목록 수령 → (2) 숲/광산에서 재료 채집 → (3) 연금술 테이블에서 조합 → (4) 감정 물약 5종 납품.
                - 감정 영향: 감정 상태에 따라 성공률 변동, 실패 시 미약 효과 발동(랜덤 감정 변동).
                """
            ),
        ),
        DesignSection(
            key="emotion_thread_assets",
            title="감정의 실타래 자산",
            body=dedent(
                """
                타일별 자산 세트
                - 외로움: 피아노 원샷, 현 패드 지속 스템, 회상 "누군가의 빈 의자", 보상 – 기억 조각, 감정 조각 파편.
                - 그리움: 첼로 원샷, 코러스 지속, 회상 "바람에 흔들리는 편지", 보상 – 관계 힌트, 관찰자 노트.
                - 희망: 하프 원샷, 브라이트 패드 지속, 회상 "새벽빛이 문을 두드린다", 보상 – 감정 버프, BGM 스템 해금.
                - 사랑: 글로켄슈필 원샷, 스트링 멜로디 지속, 회상 "맞잡은 손의 체온", 보상 – 감정 조각(사랑), Affectionate 버프.
                - 두려움: 베이스 드럼 원샷, 저음 드론 지속, 회상 "어둠이 속삭이는 경고", 보상 – 감정 인사이트, 게이트 힌트.
                - 분노: 타이코 원샷, 디스토션 패드 지속, 회상 "불꽃이 튀는 순간", 보상 – Hostile 완화 아이템, 감정 보고서.
                - 용서: 벨 트리 원샷, 합창 지속, 회상 "포옹으로 풀리는 매듭", 보상 – 용서 감정 조각, NPC 이벤트 해금.
                - 평온: 플루트 원샷, 워터 피아노 지속, 회상 "호수 위 잔잔한 숨", 보상 – 평온 물약, 관찰자 시야 확장.
                - 관찰: 실로폰 원샷, 라일락 신스 지속, 회상 "별빛 아래 흐르는 세계", 보상 – 관찰자 패킷, 전생 힌트.

                오류 처리
                - 순서가 어긋나면 반음 충돌 효과(-4dB), 화면 수평 쉬프트 0.03, 텍스트 속도 0.6배.
                - 세 번 이상 실패 시 감정 균형 이벤트 발동, 정렬 힌트 제공.

                클리어 보상
                - 기억 조각 2개, 진엔딩 힌트 1개, 감정 경험치 200, 전생 영향치 +1.
                """
            ),
        ),
        DesignSection(
            key="emotion_gates",
            title="감정 게이트 3종",
            body=dedent(
                """
                숲 – 정령 나무 게이트
                - 조건: Affectionate 또는 Friendly.
                - 피드백: 감정 조건 충족 시 정령 불꽃이 머리 위에 떠오르고 길이 열림. 실패 시 푸른 안개가 화면을 덮고, Sad 스템이 재생.

                광산 – 슬픔의 문
                - 조건: Sad.
                - 피드백: 문이 푸른빛으로 맥동하며, 충족 시 저음이 잦아든다. 다른 감정일 경우 금속 문이 붉은 불꽃으로 차단.

                성 내부 – 왕궁 봉인문
                - 조건: Affectionate + 용서 감정 조각 소지.
                - 피드백: 문양이 핑크빛으로 반짝이고 천장에서 빛줄기가 떨어진다. 조건 미달 시 문양이 회색으로 변하며 가녀린 현음이 끊긴다.
                """
            ),
        ),
        DesignSection(
            key="observer_mode",
            title="관찰자 모드 패킷",
            body=dedent(
                """
                패킷 A – "성벽 위의 서약" (약 18초)
                - 카메라: 성벽을 부드럽게 따라가며 별빛 강조.
                - 나레이션: "그대가 남긴 서약은 아직도 성벽을 따뜻하게 한다."
                - 하이라이트: 세이라와 도린의 후속 장면, 전생 선택 시 힌트 제공.

                패킷 B – "여관의 새벽" (약 22초)
                - 카메라: 여관 내부를 패닝, 벽난로와 손님들의 감정을 클로즈업.
                - 나레이션: "마이라의 용서는 아직 길을 찾는 중이다."
                - 하이라이트: 여관 일기 업데이트, 용서 이벤트 진행 상황 반영.

                패킷 C – "숲의 숨결" (약 20초)
                - 카메라: 로렐레 숲을 드론처럼 훑으며 실타래 포털이 깜박인다.
                - 나레이션: "정령들은 네가 남긴 노래를 계속 부른다."
                - 하이라이트: 감정의 실타래 재진입 힌트, 감정 키워드 추천.

                자연사 후 진입 확률은 감정 정리 정도에 따라 60~100%로 변하며, 패킷을 모두 시청하면 전생 버튼이 빛난다.
                """
            ),
        ),
        DesignSection(
            key="items_crafting",
            title="아이템 & 제작",
            body=dedent(
                """
                소비 아이템
                1) 사과 와인 – 툴팁: "솔마라식 단맛." 효과: Friendly +5, 체력 회복.
                2) 로열 스테이크 – 툴팁: "왕궁의 만찬." 효과: 체력 대회복, 감정 고정 30초.
                3) 허브 파우치 – 툴팁: "숲 향이 배어 있다." 효과: Sad 완화, 꿈 변주.
                4) 감정 물약·우호 – 툴팁: "초록빛 마음 안정." 효과: Friendly로 전환.
                5) 감정 물약·애정 – 툴팁: "따뜻한 불빛." 효과: Affectionate 버프.
                6) 감정 물약·슬픔 – 툴팁: "눈물의 진정." 효과: Sad 상태 진입.
                7) 감정 물약·적대 – 툴팁: "불꽃 경고." 효과: Hostile 일시 강화, 게이트 힌트 획득.
                8) 감정 물약·평온 – 툴팁: "호수의 숨." 효과: 평온 버프, BGM 스템 감쇠.
                9) 허브 티 세트 – 툴팁: "여관의 정성." 효과: 꿈 시퀀스 확률 상승.
                10) 곡물 간식 – 툴팁: "브레일 농부의 선물." 효과: 스태미나 회복, Friendly +2.

                장비 아이템
                11) 초급 검 – 툴팁: "기사단 입문용." 효과: 전투 수치 소폭 상승.
                12) 초급 방패 – 툴팁: "감정을 막아준다." 효과: 감정 폭주 저항.
                13) 솔마라 망토 – 툴팁: "왕국 문장." 효과: 관찰자 패킷 확률 +5%.
                14) 연금술사 장갑 – 툴팁: "세밀한 감각." 효과: 제작 성공률 증가.
                15) 정령 브로치 – 툴팁: "숲의 인장." 효과: 숲 감정 게이트 완화.
                16) 감정 메트로놈 – 툴팁: "리듬 유지." 효과: 감정 실타래 실패 허용 +1.

                퀘스트/기타 아이템
                17) 기사 토너먼트 초대장 – 툴팁: "왕실 인장." 효과: 축제 참여.
                18) 변장 가면 – 툴팁: "클로드 제작." 효과: 몰래 참가 루트 활성.
                19) 성내 통행증 – 툴팁: "도린 서명." 효과: 왕궁 출입 허용.
                20) 연금 촉매제 – 툴팁: "베르타 전용." 효과: 감정 물약 제작 필수.

                제작 시스템
                - 연금술 테이블에서 재료 2개 조합: 허브 + 감정 공명 수정 = 감정 물약 5종.
                - 실패 시 미약 효과: 30초 동안 감정 UI 왜곡, 감정 경험치 +5.
                - 픽셀 아이콘: 24×24 해상도, 감정 팔레트와 일치하는 색상 사용.
                """
            ),
        ),
        DesignSection(
            key="festivals_hidden",
            title="축제 & 히든 시퀀스",
            body=dedent(
                """
                기사 토너먼트
                - 루트: 관람, 지원, 몰래 참가.
                - 연출: 경기장 BGM 스템이 감정에 따라 교체, 관중 대사가 감정 아이콘으로 표시, 결과에 따라 보상(훈련 토큰/명예 증표/비밀 장비) 차등.

                왕실 무도회
                - 접근: 초대장 확보 또는 변장 가면으로 은밀 입장.
                - 동반자 선택: 핵심 NPC 중 관계 최고치 대상 1명.
                - 보상: 진엔딩 힌트 키워드 "봉인의 온기", 감정 조각(사랑/희망) 중 상황에 따라 지급.
                - 히든: 변장 루트 성공 시 바레토스 관련 서고에 접근.
                """
            ),
        ),
        DesignSection(
            key="lore_distribution",
            title="스토리 & 로어 배치",
            body=dedent(
                """
                메인 메시지
                - 죽음은 흐름의 전환, 감정은 세계의 언어, 전생은 실타래.

                바레토스 떡밥
                1) 여관 벽 신문 스크랩 "밤이 길어진 대륙의 기록" – 관찰자 노트에 저장.
                2) 연금술 연구소 비망록 "봉인은 회생의 반대말이 아니었다" – 감정 보고서에 기록.
                3) 감정의 실타래 회상 "촛불과 룬의 따뜻함" – 관찰자 패킷 업데이트.

                로그 저장
                - 모든 로어 인터랙션은 일기 로그와 관찰자 아카이브에 동시에 기록되어 전생에도 확인 가능.
                """
            ),
        ),
        DesignSection(
            key="production_assets",
            title="아트·사운드 생산물",
            body=dedent(
                """
                타일셋
                - 솔마라 지면/길/벽/실내 기본 60~80타일.
                - 자연 오브젝트 20종, 장식 20종, 경계 타일 자연스러운 블렌딩.

                캐릭터 도트
                - 플레이어 베이스 1, 핵심 NPC 6, 서브 NPC 10(바리에이션 포함).
                - 각 캐릭터는 Idle/Walk 2룩, 감정 오버레이 1세트.

                UI
                - HUD(감정 아이콘/색줄기), 대화창, 일기, 감정 실타래 전용 UI.
                - 마우스 및 키보드 대응, 폰트/패딩 일관.

                오디오
                - BGM 4곡(솔마라 낮/밤/숲/던전) – 스템 구조 준수.
                - SFX 60종: 발걸음/문/물/입자/감정 타일 9원샷 포함.
                - 감정 이벤트마다 스템 음량 변화 체감 가능하게 믹싱.
                """
            ),
        ),
        DesignSection(
            key="text_localization",
            title="텍스트 & 로컬라이즈",
            body=dedent(
                """
                텍스트 분량
                - 일반 대사/묘사 2,000~3,000자.
                - 핵심 NPC 대사 120줄, 서브 NPC 대사 60줄.
                - 감정의 실타래 회상 9문장, 관찰자 나레이션 3문장.

                언어 파일
                - ko/en 2개 언어, 키 네이밍 규칙 `category.subject.context`.
                - 감정 상태, 전생 회차 변수를 플레이스홀더로 제공.
                """
            ),
        ),
        DesignSection(
            key="accessibility",
            title="옵션 & 접근성",
            body=dedent(
                """
                - 색약 팔레트 2종(적록/청황), 적용 시 즉시 LUT 교체.
                - 블룸/CRT 강도 슬라이더, 카메라 흔들림 ON/OFF.
                - 텍스트 크기 3단, 타이핑 속도 3단, 설정 저장/로드.
                - 장음 자동 감쇠(-3dB/60s)와 UI 사운드 볼륨 별도 슬라이더.
                """
            ),
        ),
        DesignSection(
            key="save_progression",
            title="저장 & 진행",
            body=dedent(
                """
                자동저장 포인트
                - 로덴델/브레일 마을 입구, 여관 휴식, 감정의 실타래 시작/완료.

                저장 데이터 필드
                - 감정 상태, 관계 점수, 감정 실타래 진행도, 플래그(퀘스트/이벤트), 루프 카운트.
                - 재접속 시 진행 손실 없음, 루프 카운트를 HUD에 표시.
                """
            ),
        ),
        DesignSection(
            key="steam_package",
            title="스팀 스토어 패키지",
            body=dedent(
                """
                스크린샷 10장
                - 낮/밤/숲/던전/실타래/대화/축제/관찰자/관계 이벤트/전생 UI.

                트레일러 60~90초
                - 감정 연출 → 감정의 실타래 → 관찰자 루프 순으로 구성.

                설명(ko/en)
                - 장르, 철학, 플레이 루프, 전생·관찰자·실타래 핵심 요약.

                장점 5줄
                - 감정 반응, 전생 루프, 힐링 연출, 음악 레이어, 철학 서사.

                태그
                - Story Rich, Emotional, Pixel Graphics, Relaxing, Choices Matter.
                """
            ),
        ),
        DesignSection(
            key="expansion_teasers",
            title="바레토스 확장 티징",
            body=dedent(
                """
                티징 오브젝트 3개
                - 검은 양초, 봉인문, 룬 조각. 상호작용 시 저주가 아닌 헌신임을 암시.

                로그 2개
                - "밤의 이유" – 바레토스의 길어진 밤이 선택적 희생임을 전한다.
                - "봉인의 진실" – 봉인이 구원의 의식이라는 단서.

                모든 상호작용은 로어 텍스트를 표시하고 관찰자 아카이브에 저장되어 세계관 오해 → 진상 구조를 안내한다.
                """
            ),
        ),
        DesignSection(
            key="diary_dream",
            title="일기 & 꿈 시스템",
            body=dedent(
                """
                - 일기: 감정과 사건을 기록하고 작성 순간 진정 이펙트를 제공한다. 감정 키워드 10종(사랑, 슬픔, 우정, 분노, 용서, 희망, 두려움, 평온, 향수, 관찰)을 태그로 등록하면 관련 NPC 반응과 꿈 시퀀스를 즉시 갱신한다.
                - UI: 좌우 페이지 넘김, 감정 아이콘, 음영 변화, 작성 중에는 사운드가 -3dB로 감쇠된다.
                - 꿈: 반복 꿈 테마 2종(왕궁의 잔향, 촛불이 깃든 숲길)이 기본 제공되며, 일기 키워드에 따라 연출이 변주된다. 전생과 인연을 연결하는 힌트를 제공하고 일부는 예지몽으로 작동한다.
                - 꿈 해석: 회차가 진행될수록 나레이션이 누적되고, 관찰자 모드에서 수집한 힌트가 꿈 텍스트로 되먹임된다.
                """
            ),
        ),
        DesignSection(
            key="relationships",
            title="NPC 관계 & 대화",
            body=dedent(
                """
                - 관계 등급: 적대 ↔ 무관심 ↔ 우정 ↔ 애정.
                - 대사 패턴: 감정, 관계, 회차에 따라 문장군, 이모지, 접근성이 변화한다.
                - 특수 이벤트: 고백, 이별, 용서, 사과 등은 감정 변동과 컷신 연출을 동반한다.
                """
            ),
        ),
        DesignSection(
            key="quests",
            title="퀘스트 & 던전",
            body=dedent(
                """
                - 퀘스트: 감정 조건으로 활성화되며 인연, 일기, 꿈과 교차한다(예: '슬픔' 상태일 때만 시작).
                - 던전: 힐링형 퍼즐/경로 찾기를 중심으로 하며 감정 게이트(색, 음, 타이틀)로 분기한다.
                - 메인 루프: 기억 회복 → 감정 정리 → 실타래 완주 → 자연사(관찰자) → 전생 선택.
                - 서브 루프: 기사 토너먼트, 여관 주인 마이라의 상실 극복, 광대 클로드의 웃음 의식 등.
                """
            ),
        ),
        DesignSection(
            key="codex",
            title="CODEX 1~150 시스템 목록",
            body=dedent(
                """
                CODEX는 감정/기억/전생/관계 시스템을 1~150까지 태그화한 내부 사양이다.
                - 명령 `systems <start> <end>`로 원하는 구간을 확인한다(예: `systems 1 30`).
                - 각 항목은 확장 개발 시 우선순위와 연계 포인트를 제시한다.
                """
            ),
        ),
        DesignSection(
            key="data_spec",
            title="데이터 스펙",
            body=dedent(
                """
                CharacterData
                - name, age, traits[], position, isPlayerControlled, memories[], emotion, job, jobHistory[], wasLoved, diedTragically, currentEmotionExpression

                NPCMemory
                - eventDescription, timestamp, emotionImpact(EmotionState)

                Quest
                - id, title, description, type, status, region, requiredEmotion, requiredNPCs[], rewardItems[], unlockConditionSummary

                Artifact/Relic
                - name, description, effect/passiveEffect, isReincarnationRelated, affectReincarnation

                Village/RegionEconomy/PoliticalReputation
                - 확장판에서 활성화되는 세계/경제/정치 지표
                """
            ),
        ),
        DesignSection(
            key="state_machines",
            title="상태 & 흐름 머신",
            body=dedent(
                """
                감정 FSM
                - 입력: 대화, 타일, 음악, 일기, 유물
                - 전이: 감정 증감, 최소/최대 클램프
                - 표현: UI, 색, 음, 문장 반영

                전생 FSM
                - 상태: 죽음 → (조건) 관찰자 or 전생 → 초기화(기억 없음, 경향 유지) → 새로운 시작

                퀘스트 FSM
                - Inactive → Active → Completed/Failed, 감정/인연 조건으로 가드

                감정의 실타래 FSM
                - Idle → Step(타일) → LayerUp(음) → FlowCheck(하모니/불협) → SceneBeat(회상) → Clear/Loop
                """
            ),
        ),
        DesignSection(
            key="ui_audio",
            title="UI/오디오 연동 규칙",
            body=dedent(
                """
                색상 규칙
                - Affectionate: 따뜻한 핑크/주황
                - Sad: 청록
                - Hostile: 적
                - Friendly: 녹
                - Neutral: 회색
                - 신성/관찰자: 라일락 화이트 계열

                오디오 규칙
                - 감정 이벤트마다 BGM 스템 볼륨 ±6dB 조절
                - 감정 타일은 원샷 + Sustain 레이어로 구성

                텍스트 연출
                - 감정에 따라 말줄임표, 속도, 이탤릭, 쉼표 빈도를 변화시킨다.
                """
            ),
        ),
        DesignSection(
            key="testing",
            title="테스트 & 수용 기준",
            body=dedent(
                """
                - 10분 내 감정 변화(색/음/대사)가 최소 3회 발생하고 플레이어가 인지한다.
                - 감정의 실타래 1회 클리어 시 음악 완성감과 회상 출력이 동시에 발생한다.
                - 자연사 후 관찰자 패킷 1개 이상이 재생되고 전생 루프가 정상 작동한다.
                - 감정 가드 퀘스트 1개 이상이 조건 충족/미충족을 명확히 표현하며 정상 작동한다.
                - 왕실 무도회 히든 2경로(초대장/변장)에 모두 접근 가능하다.
                """
            ),
        ),
        DesignSection(
            key="art_bible",
            title="🎨 아트 & 연출 바이블 v1.0",
            body=dedent(
                """
                0) 아트 철학(5원칙)
                - 감정이 1순위: 감정 상태가 색, 빛, 입자, 타이포를 지배한다.
                - 픽셀+현대 연출 하이브리드: 픽셀 도트 기반에 소프트 조명, 입자, 심도, 글로우를 더한 HD-2D.
                - 절제된 디테일: 단순 타일을 레이어와 색 변주로 풍성하게 만든다.
                - 연출은 '의식'처럼: 컷씬보다 의식/순례 느낌의 미니멀 연출을 지향한다.
                - 시스템 친화적: 애니 프레임, 타일 규격, 팔레트, 네이밍을 일관되게 유지한다.

                1) 그림체/그래픽 스펙
                - 화면/카메라: 1920×1080(내부 320×180 ×6 업스케일), 정적 탑다운, 3~5단 패럴랙스, 감정 반응형 카메라 드리프트
                - 업스케일 필터: Nearest + CRT-블룸(강도 0.15), ON/OFF 토글 제공
                - 타일/스프라이트: 기본 타일 32×32, 변형 32×64/64×64, 캐릭터 48×48(히트박스 32×32), 아이템 UI 24×24
                - 팔레트: Neutral #B8BDC6/#6E7581, Friendly #9ED56B/#5FA742, Affectionate #FF9AA2/#FFB3C1, Sad #8FD3FF/#4AA3D0, Hostile #FF6B6B/#B23A48, 신성/관찰자 #EDE9FE/#C2B5FF. 감정 변화 시 강조색 10~20% 밝기/채도 조정 및 LUT 전환.
                - 선/음영: 1px 라인, 배경 외곽선 최소, 2단 셰이드 + 하이라이트. 메탈/유리는 디더링 최소화와 2~3프레임 반짝임.

                2) 애니메이션 바이블
                - 캐릭터 루프: Idle 4f/0.7s, Walk 6f/0.6s, Run 8f/0.6s, Interact 6f/0.5s, Emote(감정별) 4f/0.4s, Sit/Rest 4f/0.8s, PlayInstrument 8f/0.8s
                - 감정 오버레이: 머리 위 잔광, 작은 입자, 8f 루프 1.2s
                - 환경 오브젝트: 수면 파장 8f/1.2s, 나뭇잎 6f/1.0s, 등불 6f/1.2s, 감정 타일 활성 8f/0.8s
                - 컷씬 동작: 카메라 3단 줌(0.6s/1.0s/1.6s), 감정 팔레트 페이드(0.6s), 텍스트 타이핑 24~36cpm(슬픔일수록 느리게)

                3) VFX/라이팅
                - 글로우: 신성/관찰자/용서에 라일락 화이트 발광(반경 8~24px)
                - 입자: 사랑=꽃잎, 슬픔=물방울, 적대=불티, 우호=씨앗, 중립=먼지
                - 라이팅: 2D 라이트 스프라이트 + 멀티플라이 섀도우, 밤에는 블루 쉐이드 강화
                - 스크린 이펙트: 감정 왜곡 시 수평 크로매틱 쉬프트(0.04), 적대 시 미세 흔들림(1px)

                4) UI/UX 디자인
                - 레이아웃: HUD 최소화(좌상단 감정 아이콘/색줄기, 우상단 미니 로그 3줄). 일기 풀스크린, 대화 하단 카드, 감정 도감 카드 그리드.
                - 타이포: 한글 Pretendard/나눔스퀘어, 영문 Inter/Roboto, 감정 강조 자막 Playfair Display 이탤릭, 픽셀 제목 Press Start 2P(옵션)
                - 상태/색상 규칙: Hover는 강조색 20% 업, Press는 암부 15% 다운, 경고=Hostile, 힐링=Affectionate/Sad 파스텔

                5) 오디오 바이블
                - BGM 스템: A(패드/환경), B(하모니), C(리듬), D(멜로디). 감정 이벤트로 스템 볼륨 ±6dB 전환.
                - 감정-악기 매핑: 사랑 Soft Strings/Glockenspiel, 슬픔 Felt Piano/Clarinet/Reverse Pad, 우호 Nylon Guitar/Shaker, 적대 Low Taiko/Dist. Perc/Dissonant Pad, 용서/관찰자 Choir/Celesta/Bell Tree
                - SFX 톤: UI 목재/종이/만년필, 발자국 재질 구분(슬픔 시 하이컷), 감정 타일 음계 C–E–G–B–D, 불협 시 반음 충돌

                6) 지역별 아트 가이드
                - 솔마라: 금빛 베이지, 솔마라 레드, 청록 억제. 깃발, 방패 문양, 연금술 기호, 성문 그림자. 석조+목조 건축, 붉은 기와, 낡은 배너, 기사/귀족/농부 의복.
                - 바레토스: 밤이 늘어진 대지, 금지 마법 연구. 색상 보랏빛 잿검(#3E2D4D), 초록괴광(#6FFFC3). 검은 양초, 의식진, 봉인문, 가면. 촛불·룬 글로우 조명, 장막/두건/문신.
                - 엘라리온: 포레스트 그린, 실버문 블루. 띠잎, 정령 표식, 자연 브릿지. Rim Light와 생명 입자 강조.

                7) 캐릭터 설계 규칙
                - 실루엣으로 직업을 구분하며 모자/망토/도구로 아이덴티티를 명확히 한다.
                - 표정은 눈 2~3px, 입 1~2px로 최소화하고 감정은 색·입자·자막으로 보강한다.
                - 직업별 액세서리는 도시마다 색/문양 차이를 둔다.
                - 관찰자 모드 초상은 라일락 화이트 윤곽선과 얇은 노이즈를 사용한다.

                8) 환경 타일셋 스펙(솔마라 기준)
                - 지면: 흙/잔디/돌길 각 6변형
                - 절벽/벽: 32×64 모듈 8종(모서리 포함)
                - 집: 기본 3형(소/중/대), 지붕 4색, 창/문 6종
                - 실내: 목재 바닥 3종, 러그 4종, 책장/난로/테이블/침대 세트
                - 장식: 배너 6, 가로등 2, 화분 4, 우물 1
                - 자연: 나무 4, 관목 6, 꽃 6, 바위 6, 작은 연못 2

                9) 감정의 실타래 아트/사운드
                - 타일 수 9, 감정 순서 고정(외로움→관찰)
                - 각 타일: Idle/Active 스프라이트, 12f 잔광 입자, LUT 파라미터, 원샷 음원(1~2s) + 지속 Stem(4~8bar), 회상 텍스트 1문장, 투명 오버레이(손, 초상 등)
                - 불협 로직: 순서 오류 시 반음 충돌(-4dB), 화면 수평 쉬프트 0.03, 텍스트 타이핑 속도 0.6배

                10) 내러티브/로어
                - 세계 철학: 죽음은 흐름의 전환, 감정은 세계의 언어, 전생은 실타래를 잇는다.
                - 바레토스 진상: 진엔딩의 신이 세계 붕괴를 막기 위해 봉인형 저주를 내렸고, 그들은 금지 마법으로 인류 구원을 시도했다. 희생과 오해로 악의 이미지가 씌워졌으며, 진엔딩 접근 시 구원자의 서사가 드러난다.
                - 1차 출시 메인 흐름: 성의 질서와 감정 억압, 기억 삭제 관습을 파고들며 일기/실타래/미궁으로 감정 정리를 수행한다. 전생을 반복하며 인연의 끌림과 거부를 경험하고, 히든 힌트는 왕실 무도회와 감정 미궁에 분산된다.

                11) 퀘스트 구조
                - 메인: 기억 회복 → 감정 정리 → 실타래 완주 → 자연사 → 관찰자 → 전생 선택
                - 서브: 기사 토너먼트 보조/몰래 참가, 마이라의 상실 극복(슬픔→용서), 클로드의 웃음 의식(우호/사랑 상승)

                12) 접근성 옵션
                - 색약 보정 팔레트 2종, 카메라 흔들림 OFF, CRT/블룸 강도 슬라이더
                - 텍스트 크기 3단, 타이핑 속도 설정, 장음 자동 감쇠(-3dB/60s)

                13) 제작 수량 & 로드맵(1인 개발)
                - 배경 타일 300~400, 캐릭터 베이스 12(주요 NPC 10 + 플레이어 변형), UI 아이콘 120~160, 이펙트 프리셋 감정 8 + 범용 12, 사운드 BGM 6곡(Stem), SFX 80~100, 타일 원샷 9
                - 기간 예시: 월1~2 배경/타일/UI → 월3 NPC/퀘스트/실타래 v1 → 월4 사운드/연출/관찰자 → 월5 밸런싱/튜토/로컬라이즈/스팀 페이지
                """
            ),
        ),
        DesignSection(
            key="accessibility",
            title="접근성 & 옵션",
            body=dedent(
                """
                - 색약 보정 팔레트 프리셋 2종 제공
                - 카메라 흔들림 토글, CRT/블룸 강도 슬라이더
                - 텍스트 크기 3단계, 타이핑 속도 설정
                - 청각 피로 최소화를 위한 장음 자동 감쇠(–3dB/60s)
                """
            ),
        ),
        DesignSection(
            key="roadmap",
            title="1인 제작 로드맵",
            body=dedent(
                """
                월 1~2: 솔마라 배경, 타일, 기본 UI 구축
                월 3: NPC, 애니메이션, 퀘스트, 감정의 실타래 v1 완성
                월 4: 사운드, 연출 통합, 관찰자/자연사 루프 정책 정리
                월 5: 밸런싱, 튜토리얼, 로컬라이제이션, 스팀 페이지 준비
                """
            ),
        ),
    ]

    return {section.key: section for section in sections}


def build_system_entries() -> List[SystemEntry]:
    """Construct the CODEX 001~150 list based on the confirmed spec."""

    def make_entries(prefix: str, items: List[Tuple[str, str]], start_index: int) -> List[SystemEntry]:
        entries = []
        for offset, (name, description) in enumerate(items):
            code = f"CODEX-{start_index + offset:03d}"
            entries.append(SystemEntry(code=code, name=name, description=description))
        return entries

    core_structure: List[Tuple[str, str]] = [
        ("Emotion Architecture", "감정 상태 정의와 색/음/텍스트 동기화 파이프라인."),
        ("Memory Ledger", "회차별 기억 스냅샷을 저장하고 감정과 연결한다."),
        ("Reincarnation Loop", "죽음 이후 감정 경향을 유지하며 새 삶을 시작하는 루프."),
        ("Relationship Bonds", "NPC 호감도와 호칭 변화를 관리하는 시스템."),
        ("Emotion Compendium", "감정별 설명, 효과, 획득 조건을 정리한 도감."),
        ("Expression Layer", "UI, 필터, 카메라 연출을 감정에 맞춰 갱신한다."),
        ("Life Retrospective", "현재 생애를 요약해 플레이어에게 전달하는 회상."),
        ("Bond History", "인연별 상호작용 타임라인."),
        ("Emotion Analytics", "감정 분포와 통계를 시각화."),
        ("Bond Tier Ladder", "적대/무관심/우정/애정 단계 판정."),
        ("Emotion Traits", "감정 성향 특성과 패시브 효과."),
        ("Life Stage Clock", "생애 진행도와 자연사 시점을 계산."),
        ("Observer Unlock", "관찰자 모드 진입 조건 체크."),
        ("Core Dialogue Engine", "감정 반응형 문장군 선택."),
        ("Emotion Influence Map", "지역별 감정 온도 측정."),
        ("Memory Mosaic", "감정 조각을 조합해 장면을 복원."),
        ("Life Title System", "플레이어 생애 타이틀 부여."),
        ("Emotion Gatekeeper", "감정 조건 퀘스트 활성화 가드."),
        ("Relationship Forecast", "감정 경향으로 다음 대사 예측."),
        ("Emotion Burst", "감정 급상승 이벤트 처리."),
        ("Reincarnation Seed", "다음 생 시작 시 감정 패턴 시드 결정."),
        ("Bond Memory Sync", "인연과 공유한 기억을 기록."),
        ("Emotion Inventory", "획득한 감정 조각과 상태 저장."),
        ("Life Journal", "일기 작성과 감정 태그 연결."),
        ("Dream Archive", "꿈 테마 데이터베이스."),
        ("Emotion Classifier", "텍스트/행동을 감정 범주로 분류."),
        ("Narrative Anchor", "핵심 서사 이벤트와 감정 조건 연결."),
        ("Emotion Threshold", "감정 변동 상한/하한 로직."),
        ("Bond Decay", "시간 경과에 따른 관계 변화."),
        ("Emotion Reminder", "이전 생에서 반복된 감정 패턴 알림."),
    ]

    living_exploration: List[Tuple[str, str]] = [
        ("Crafting Circuits", "제작 시스템과 감정 재료 연동."),
        ("Herbalism Tracks", "약초 채집과 감정 회복 효과."),
        ("Farming Cycles", "농사 루프와 계절 감정 변화."),
        ("Fishing Repose", "낚시 활동과 힐링 연출."),
        ("Gentle Hunts", "사냥과 감정 균형 체크."),
        ("Micro Dungeons", "작은 던전과 감정 퍼즐."),
        ("Hidden Caverns", "감정 조건으로 개방되는 비밀 던전."),
        ("Relic Discovery", "유물 발견과 기억 회상."),
        ("Street Performance", "거리 공연과 감정 전염."),
        ("Quote Collector", "철학 명언 수집과 감정 반응."),
        ("Dream Weaving", "꿈 조형 미니게임."),
        ("Performance Feedback", "공연 후 감정 반응 기록."),
        ("Philosophy Counsel", "상담 이벤트와 감정 정리."),
        ("Relic Equip", "유물 장착과 감정 패시브."),
        ("Town Tips", "생활 팁과 감정 안정."),
        ("Guided Counseling", "NPC 상담 누적 기록."),
        ("Dream Ending Flags", "꿈 기반 진엔딩 조건 추적."),
        ("Emotion Sharing", "NPC와 감정 공유 세션."),
        ("Instrument Jam", "악기 연주와 감정 레이어."),
        ("Emotion Growth", "감정 레벨업 및 특성 부여."),
        ("Memory Recall", "기억 재현 의식."),
        ("Cooking Comfort", "음식 제작과 감정 버프."),
        ("Nature Sketch", "풍경 스케치와 감정 치유."),
        ("Letter Exchange", "서신 시스템과 감정 반응."),
        ("Observation Diary", "관찰자 모드 노트."),
        ("Pet Companion", "동물 동료와 감정 공명."),
        ("Village Pulse", "마을 정서 온도 UI."),
        ("Emotion Recipe", "감정 재료 조합법."),
        ("Travel Stories", "여행담 공유와 감정 변동."),
        ("Soulful Cooking", "감정 기반 요리 컷신."),
        ("Meditation Nook", "명상 포인트와 감정 회복."),
    ]

    emotion_branches: List[Tuple[str, str]] = [
        ("Dream-Reality Bridge", "꿈과 현실이 재회하는 이벤트."),
        ("Emotion Shards", "감정 조각 수집과 조합."),
        ("Dialogue Patterning", "회차별 대사 패턴 변형."),
        ("Life Epilogue", "생애 후기 생성."),
        ("Worldline Drift", "세계선 변화 추적."),
        ("Death Memory Vault", "사망 시 기억 보관."),
        ("Confession Sequence", "고백 이벤트 연출."),
        ("Farewell Ritual", "이별 의식 컷신."),
        ("Forgiveness Arc", "용서 이벤트와 감정 회복."),
        ("Emotion Report", "감정 요약 리포트."),
        ("Turning Point", "전환점 이벤트 핸들러."),
        ("Interaction Ledger", "상호작용 히스토리."),
        ("NPC Notebook", "NPC별 노트와 감정 선호."),
        ("Behavior Forecast", "행동 예측과 감정 확률."),
        ("Diary Resonance", "일기 키워드 반응."),
        ("Memory Rewind", "기억 되새김 컷신."),
        ("Choice Weighting", "선택 가중치와 감정 영향."),
        ("Town Emotion Thermometer", "마을 정서 온도 그래프."),
        ("Prophecy Echo", "예언 반응과 감정 변화."),
        ("Relationship Timeline", "관계 타임라인 UI."),
        ("Emotion Graph", "감정 그래프 시각화."),
        ("Memory Link", "기억 상호 연결."),
        ("Life Replay", "생애 리플레이 뷰어."),
        ("Emotion Contagion", "감정 전염 시스템."),
        ("UI Tint Sync", "UI 색 변화 자동화."),
        ("Music Stem Sync", "음악 스템 동기화."),
        ("Life Digest", "생애 다이제스트 요약."),
        ("Last Will", "유언 생성."),
        ("Life Tarot", "감정 기반 타로 시스템."),
        ("Emotion Probability", "감정 선택 확률 계산."),
        ("Accumulated Branch", "감정 누적 분기 로직."),
        ("True Ending Adjudicator", "진엔딩 판정."),
    ]

    meta_expansion: List[Tuple[str, str]] = [
        ("Life Comparison", "회차별 인생 비교 리포트."),
        ("Reincarnation NPC Tracker", "전생에서 만난 NPC 추적."),
        ("Emotion Ratio Matrix", "감정 비율 행렬 분석."),
        ("Emotion Legacy", "감정 유산 전달."),
        ("Fate Tree", "운명 트리 시각화."),
        ("Composite Emotion Detector", "복합 감정 감지."),
        ("Dialogue Sentiment Analyzer", "대화 감정 분석."),
        ("Rebirth Memory Scatter", "전생 기억 조각 분산."),
        ("Regional Emotion Spread", "지역 감정 전염도."),
        ("Memory Guide", "회상 안내자 NPC."),
        ("Bond Visualization", "인연 시각화 그래프."),
        ("Event Emotion Tracker", "사건 감정 추적."),
        ("Chronicle Compiler", "연대기 생성."),
        ("Memory Soundtrack", "회상 음악 추천."),
        ("Multi-Emotion Sync", "복수 감정 동기화."),
        ("World Emotion Map", "세계 정서 맵."),
        ("Emotion Variance Analysis", "감정 편차 분석."),
        ("Hidden Emotion Vault", "비밀 감정 저장소."),
        ("Pattern Recognition", "반복 감정 패턴 인식."),
        ("Emotion Resonance", "감정 공명 효과."),
        ("Worldline Transfer", "세계선 전이 시스템."),
        ("Emotion Quest Split", "감정 퀘스트 세분화."),
        ("Confession Diversifier", "고백 이벤트 다변화."),
        ("Emotion Mask", "감정 가면 장착."),
        ("Trauma Tracker", "트라우마 기록."),
        ("Dwelling Reflection", "거주지 감정 반영."),
        ("Indoor Weather", "실내 감정 날씨."),
        ("Emotion Graffiti", "감정 그래피티 생성."),
        ("Life Dialogue Editor", "인생 대사 편집기."),
        ("Emotion Highlights", "감정 하이라이트 모음."),
        ("Emotion Personification", "감정 의인화 연출."),
        ("NPC Apparition", "NPC 환영 시스템."),
        ("Dream Expedition", "꿈 탐험 모드."),
        ("AI Scenario Generator", "AI 보조 시나리오 생성."),
        ("Emotion Sync Dialogue", "감정 동기 대화."),
        ("Emotion Input Narrative", "감정 입력형 전개."),
        ("NPC Emotion Learning", "NPC 감정 학습."),
        ("Blended Choices", "감정 블렌딩 선택지."),
        ("Emotion Mythology", "감정 신화 데이터."),
        ("Emotion-to-Relic", "감정→유물 승화."),
        ("Emotion Projection NPC", "감정 투사 NPC."),
        ("Emotion Leveling", "감정형 레벨업."),
        ("Auto Journal", "자동 일기 작성."),
        ("Empathy Events", "공감 이벤트."),
        ("Emotion Mismatch Alert", "감정 불일치 알림."),
        ("Friendship Festival", "우정 축제."),
        ("Dream Card", "드림카드 수집."),
        ("Scenario Remixer", "시나리오 리믹서."),
        ("Emotion Stamps", "감정 스탬프."),
        ("Emotion Branch Timeline", "감정 분기 타임라인."),
        ("Remaster Sequence", "리마스터 연출."),
        ("Emotion Interview", "감정 인터뷰."),
        ("Emotion Redefinition", "감정 재정의 절차."),
        ("Background Sync", "배경 동기화."),
        ("Emotion Whitepaper", "감정 백서 자동 생성."),
        ("AI Narration", "AI 나레이션 보이스."),
        ("Climax Orchestration", "클라이맥스 연출 모듈."),
        ("Memory Gallery", "회상 일람 뷰어."),
        ("Closure Dialogue", "종료 대사 생성."),
        ("Emotion Film", "감정+삶 영상 요약."),
    ]

    entries: List[SystemEntry] = []
    entries.extend(make_entries("core", core_structure, 1))
    entries.extend(make_entries("life", living_exploration, len(entries) + 1))
    entries.extend(make_entries("emotion", emotion_branches, len(entries) + 1))
    entries.extend(make_entries("meta", meta_expansion, len(entries) + 1))
    return entries


# ---------------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------------


def run_atlas_cli(atlas: DesignAtlas) -> None:
    print("\n=== Design Atlas Browser ===")
    print("타이핑 'help'로 명령을 확인하고, 'quit'으로 나갑니다.\n")

    while True:
        try:
            raw = input("atlas> ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            break

        if not raw:
            continue

        lowered = raw.lower()
        if lowered in {"quit", "exit"}:
            break
        if lowered == "help":
            print(
                dedent(
                    """
                    사용 가능한 명령
                    - list: 섹션 키와 제목을 확인합니다.
                    - show <key>: 해당 섹션을 출력합니다.
                    - systems <start> <end>: CODEX 항목 범위를 출력합니다.
                    - search <keyword>: 섹션과 시스템에서 키워드를 찾습니다.
                    - quit: 뷰어를 종료합니다.
                    """
                ).strip()
            )
            continue
        if lowered == "list":
            for key, title in atlas.list_sections():
                print(f"{key} – {title}")
            continue

        tokens = raw.split()
        command = tokens[0].lower()
        args = tokens[1:]

        try:
            if command == "show" and args:
                section = atlas.get_section(args[0])
                print(atlas.render_section(section))
            elif command == "systems" and len(args) == 2:
                start = int(args[0])
                end = int(args[1])
                entries = atlas.system_range(start, end)
                print(atlas.render_systems(entries))
            elif command == "search" and args:
                keyword = " ".join(args)
                results = atlas.search(keyword)
                if not results["sections"] and not results["systems"]:
                    print("검색 결과가 없습니다.")
                else:
                    if results["sections"]:
                        print("[섹션]")
                        for hit in results["sections"]:
                            print(f"- {hit}")
                    if results["systems"]:
                        print("[CODEX]")
                        for hit in results["systems"]:
                            print(f"- {hit}")
            else:
                print("알 수 없는 명령입니다. 'help'를 참고하세요.")
        except (KeyError, ValueError) as exc:
            print(f"오류: {exc}")


def main() -> None:
    atlas = DesignAtlas()
    pixel_game = ArcPixelGame()

    while True:
        print(
            dedent(
                """
                ================================
                We Called This Is Real – 선택 메뉴
                1) Solmara Pixel Prototype
                2) Design Atlas Browser
                3) Quit
                """
            ).rstrip()
        )
        try:
            choice = input("mode> ").strip().lower()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            break

        if not choice:
            continue
        if choice in {"1", "pixel", "game", "play"}:
            pixel_game.run()
        elif choice in {"2", "atlas", "design"}:
            run_atlas_cli(atlas)
        elif choice in {"3", "quit", "exit", "q"}:
            print("행복한 개발 되세요! ✨")
            break
        else:
            print("알 수 없는 선택입니다. 1, 2, 3 중에서 골라 주세요.")


if __name__ == "__main__":  # pragma: no cover - manual run utility
    main()
