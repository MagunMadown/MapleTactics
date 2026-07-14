# MapleTactics

## 폴더 구조

```
MyDesk (= LocalWorkspace의 RootDesk)
├─ 00_Core
│   ├─ Managers/        # TurnManager, CombatManager, RegenManager (Service 확장)
│   ├─ Events/          # EventType: OnTurnStart, OnAttackExecute, OnEnemySpawn
│   └─ Constants/        # StructType, ItemType 등 공용 타입 정의
│
├─ 01_Combat
│   ├─ Components
│   │   ├─ Player/       # AttackQueueComponent, MoveComponent, TileSlotComponent
│   │   ├─ Enemy/        # EnemyCooldownComponent, RegenTriggerComponent
│   │   └─ Shared/       # TurnConsumerComponent (이동/회전/타일추가 시 턴 소모 처리)
│   └─ AI
│       ├─ BTNodes/      # BTNodeType: 결정→장착→준비→공격 4단계 노드
│       ├─ States/       # StateType: Idle/Telegraph/Attack/Retreat, Bait Cycle 판정
│       └─ Patterns/     # 보스 전용 스크립트, 예: Kowa_Pattern.lua
│
├─ 02_Deck
│   ├─ Components/       # TileComponent, EnchantmentComponent(무료 플레이 등)
│   └─ Models/            # Tile_Sword, Tile_Shield 등 무기 타일 모델
│
├─ 03_Data
│   ├─ DataSet/           # Weapons, Enchantments, EnemyStats (스탯 테이블)
│   └─ TileDataSet/       # 맵 노드 배치, 타일 레이아웃
│
├─ 04_Roguelike
│   ├─ RunManager/        # 시드, 진행도, 맵 노드 선택 로직
│   └─ MapGeneration/
│
├─ 05_UI
│   ├─ HUD/               # 대기열 표시, 쿨다운 게이지, 적 의도 아이콘
│   └─ Popup/             # 보상 선택, 게임오버
│
├─ 06_Characters
│   ├─ Player/
│   └─ Enemies/           # Ashigaru, Archer, Boss별 하위 폴더
│
├─ 07_Effects
└─ 99_Test                # 디버그용 씬/스크립트 (Component Enable 테스트 등)
```