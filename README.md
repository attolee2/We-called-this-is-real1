# We Called This Is Real – Design Atlas

**키워드: 감정 · 전생 · 관찰자 모드 · 힐링 픽셀 샌드박스**

이 저장소는 솔마라 1차 출시를 준비하는 1인 개발자를 위한 설계 사전을
제공합니다. `game.py`는 텍스트 기반 명령어 인터페이스로 비전, 세계관,
감정 시스템, CODEX 1~150 사양, 🎨 아트 & 연출 바이블까지 모두 열람할 수
있도록 구성되었습니다.

## 실행 방법

1. Python 3.10 이상을 준비합니다.
2. 다음 명령으로 도구 모음을 실행합니다.

   ```bash
   python game.py
   ```

3. 나타나는 메뉴에서 원하는 모드를 선택합니다.

   | 입력 | 설명 |
   | --- | --- |
   | `1` | Solmara Pixel Prototype – 감정/농사/대화가 있는 텍스트 기반 샌드박스 |
   | `2` | Design Atlas Browser – 전체 설계 사전 열람 |
   | `3` | 프로그램 종료 |

### Solmara Pixel Prototype 기본 명령

| 명령 | 설명 |
| --- | --- |
| `help` | 가용 명령을 확인합니다. |
| `look` / `map` | 현재 지도를 ASCII 픽셀 스타일로 표시합니다. |
| `move <n/s/e/w>` | 한 칸 이동합니다. WASD 축약(`n/s/e/w`)도 지원합니다. |
| `travel [지역]` | 출입구 타일에서 다른 씬으로 이동합니다. |
| `talk <NPC>` | 인접한 NPC와 대화하여 감정/관계를 변화시킵니다. |
| `gift <아이템> <NPC>` | 인벤토리의 아이템을 선물합니다. |
| `plant <작물>` | 밭에서 씨앗을 심습니다. (moonbud/starbean/sungrain) |
| `water` / `harvest` | 작물에 물을 주거나 수확합니다. |
| `forage` | 주변에서 약초/자원을 채집합니다. |
| `inventory` / `log` | 보유 아이템과 당일 활동 로그를 확인합니다. |
| `sleep` | 쉼터에서 휴식해 다음 날로 넘어갑니다. |

### Design Atlas Browser 기본 명령

   | 명령 | 설명 |
   | --- | --- |
   | `help` | 사용 가능한 명령을 보여줍니다. |
   | `list` | 섹션 키와 제목을 확인합니다. |
   | `show <key>` | 특정 섹션의 전체 내용을 출력합니다. |
   | `systems <start> <end>` | CODEX 1~150 시스템 항목을 범위로 조회합니다. |
   | `search <keyword>` | 섹션과 CODEX에서 키워드를 동시에 검색합니다. |
   | `quit` | 프로그램을 종료합니다. |

## 포함된 설계 항목

- 비전 & 핵심 기둥, 철학, 페이스 가이드
- 1차 출시 범위와 7개 대륙 확장 로드맵
- 솔마라 6개 씬 구조, 출입구/상호작용/감정 게이트 세부 설계
- **Solmara Pixel Prototype** – 로덴델·브레일·로렐레 숲 지형, 감정 게이트, 농사/대화/선물 시스템이 구현된 텍스트 기반 픽셀 샌드박스
- 글로벌 열거형·상태효과·유물 스키마와 Flora/Fauna/Dish/Brew/Festival 데이터 표준
- 아르크 생명체 카테고리 예시(나무·꽃·지상·해양·하늘·벌레·몬스터 확장)와 고유 악기 컬렉션, 자연재해·무기·생활 도구·커뮤니티 시스템 확장 지침
- 솔마라 자원·요리·주류·축제 상세, 바레토스 의식 생태, 6개 확장 대륙 생태 요약, 생태 데이터시트(생물/식물/요리 드롭)
- 솔마라 유물 18종 풀 스펙과 바레토스 티징 유물 6종, 전생 연계 정책
- 스토리 핵심 유물 15종의 기원·능력·리스크 설계(엘레네시아의 조각부터 끝없는 길의 지도까지)
- 핵심 NPC 6명 + 광장 쌍둥이 남매/퇴역 기사 상호작용 확장(감정 분기 3종, 개인 이벤트)
- 관계 랭크/감정 규칙, 상호작용 동사 18종, 선물 가중치, 편지·루머·축제 연계, 갈등/사과/약속/전생 규칙, QA 체크리스트
- 메인/서브 퀘스트 플로우, 관계 이벤트(고백/이별/용서)
- 감정/기억/전생/관찰자 루프, 감정의 실타래 사양과 자산(ORGEL_SOLMARA_01/02)
- 아이템 20종, 제작/감정 게이트/관찰자 패킷/축제/히든 루트
- 데이터 스펙, 상태 머신, UI/오디오 연동 규칙
- CODEX 1~150 시스템 목록 (감정·생활·확장 기능 전부 포함)
- 🎨 아트 & 연출 바이블 v1.0, 생산물 수량, 스팀 패키지/확장 티징
- 접근성 옵션, 저장/테스트/수용 기준

## CONTENT PACK v1.2 데이터 파일

| 파일 | 설명 |
| --- | --- |
| `data/artifacts/solmara.yaml` | 솔마라 18종 유물 전체 스펙 (스키마 필드 포함) |
| `data/artifacts/baretos_teasers.yaml` | 바레토스 확장 티징 유물 6종 |
| `data/npc_interactions/solmara_core.json` | 핵심 NPC 6명 + 광장 쌍둥이/퇴역 기사 상호작용 조건/대사 키 |
| `data/quests/solmara.yaml` | 메인/서브 퀘스트 상태머신 cond/do/reward 정의 |
| `data/minigames.yaml` | 토너먼트/무도회 미니게임 파라미터와 보상 규칙 |
| `data/crafting.yaml` | 감정 물약·힐링 요리 제작 재료 및 지속시간 |
| `data/config/interaction_config.json` | 상호작용 쿨타임/관계 보정/랭크 조건 |
| `data/relations.json` | 관계/감정 기본 가중치와 Bias 매핑 |
| `data/gifts/gifts_solmara.csv` | 선물 선호도 매트릭스 (일 1회, 감쇠 규칙 포함) |
| `data/letters_rumors.yaml` | 편지 트리거와 루머 힌트 매핑 |
| `Localization/ko/strings.json` | 한국어 대사/오르골/관찰자 로컬라이즈 문자열 |
| `Localization/ko/strings_npc_ext.json` | NPC 시간/날씨/편지 확장 대사 세트 |
| `data/observer/solmara_packets.yaml` | 관찰자 모드 컷신 패킷 (카메라 경로/나레이션 키) |
| `data/observer/baretos_packets.yaml` | 바레토스 티징 관찰자 패킷(OBS_BAR_CATACOMB_INTRO) |
| `data/orgel/orgel_solmara_01.yaml` | 감정의 실타래 ORGEL_SOLMARA_01 타일·룰 정의 |
| `data/orgel/orgel_solmara_02.yaml` | 타운 & 벽난로 감성 ORGEL_SOLMARA_02 시퀀스 |
| `data/festivals/festival_hooks.json` | 토너먼트/무도회 미니게임, NPC 보정, 보상 |
| `data/dungeon_baretos_nocturne.yaml` | 바레토스 의식 던전 ‘녹턴 카타콤’ 입장/퍼즐/보상 |
| `data/ecology_solmara.yaml` | 솔마라 생물·식물·요리 드롭 테이블 요약 |

## 다음 단계 제안

1. **게임 플레이 프로토타입 연동** – 아틀라스 데이터를 JSON으로 덤프해
   엔진(예: Godot, Unity, RPG Maker)에서 참조하도록 만듭니다.
2. **픽셀/오디오 구현** – 팔레트, 애니메이션, 스템 구조를 기반으로 아트와
   사운드를 제작합니다.
3. **관찰자 UI 시각화** – 전생 루프에서 관찰자 경험을 강화할 HUD와
   타임라인을 설계합니다.
4. **확장 데이터 설계** – 나머지 7개 대륙을 위한 데이터 시트를 작성해 DLC
   혹은 업데이트 플랜과 연결합니다.

행복한 개발 되세요! :sparkles:
