# Region 06 슬리피우드 전반전 구현 가이드

## 1. 범위

슬리피우드 전반전은 외곽 숲 3개 일반 Stage와 포장마차 보스 Stage로 구성한다. 물리 맵은
Stage마다 복제하지 않고 아래 두 개만 사용한다.

| 물리 MapId | 사용하는 Stage | 역할 |
|---|---|---|
| `sleepywood_ant_tunnel` | `region_06_stage_01`~`03` | 슬리피우드 외곽 일반전 공용 맵 (호환성을 위해 MapId 유지) |
| `sleepywood_food_cart_boss` | `region_06_stage_04` | 포장마차 전용 보스맵 |

Stage의 규칙·적·웨이브는 CSV가 결정하고, 맵은 배경·전투 셀·전투 컴포넌트만 소유한다.

## 2. Stage와 적 구성

| Stage | 표시명 | 주요 적 | Wave 수 |
|---|---|---|---:|
| `region_06_stage_01` | 6-1 슬리피우드 외곽 | 드레이크 | 3 |
| `region_06_stage_02` | 6-2 드레이크의 숲 | 드레이크, 카파 드레이크 | 4 |
| `region_06_stage_03` | 6-3 어두운 숲길 | 드레이크, 카파 드레이크, 다크 드레이크 | 4 |
| `region_06_stage_04` | 6-4 지하 휴게소 | 휴면 포장마차 + 뿔버섯 1마리 | 1 (동시 등장) |

- 드레이크(HP 7)와 카파 드레이크(HP 9)는 접근 후 1칸 물기를 준비한다. 큐 준비 1턴, 쿨다운 1턴이다.
- 다크 드레이크(HP 6)는 2칸 암흑 브레스를 사용한다. 큐 준비 1턴, 쿨다운 3턴이며 6-3의 두 번째 Wave에 등장한다.
- 세 종류 모두 대기·이동·피격·사망 모션을 CSV로 설정한다. 일반/카파는 원본 공격 모션이 없어 이동 모션을 짧게 재생하고, 다크는 원본 `attack1`·투사체·명중 효과를 쓴다.
- 기존 버섯 정의는 삭제하지 않는다. 보스 입장 시 뿔버섯 1마리가 함께 등장한다.
- 뿔버섯의 `AGGRO` 특성은 제거했다. 일반 적의 기본 공격 후 후퇴 규칙을 따르며, 후퇴 칸이 막혀 있으면 이동하지 못한다. 같은 EnemyDefinition을 사용하는 모든 전투에 적용된다.
- 포장마차는 HP 38로 시작하며, 1페이즈 `DORMANT`에서는 이동·공격 없이 피해만 받는다.
- HP 19 이하에서 2페이즈 `DINNER_RUSH`로 한 번 전환한다. 이후 철판 내려치기, 2칸 끓는 기름, 전방 1~5칸을 덮는 포장마차 레이저를 사용한다.
- 포장마차 레이저는 피해 5, 재사용 대기시간 5턴, Queue 준비 2턴이며 준비 중
  플레이어 피해 스킬을 1회 적중시키면 끊기는 기존 `CAST_INTERRUPTIBLE` 계약을 사용한다.
- 1페이즈는 3턴 간격으로 잡몹을 1마리씩 보충한다. 추가 소환 Pool의 가중치는 뿔버섯 3 : 좀비버섯 1이며, 현재 순환 선택 방식에서는 연속 4회 소환마다 각각 3마리·1마리가 선택된다(Seed에 따라 시작 순서는 달라짐). 최초 잡몹을 포함해 살아 있는 일반 적은 최대 2마리다. 빈 칸이 없으면 보류하고, 플레이어에게서 가장 먼 빈 칸에 생성한다. 새 적도 기존 SPAWN_WAIT 규칙을 따른다.
- 포장마차는 `HOLD_POSITION` 특성을 유지하므로 플레이어 쪽으로 접근하지 않는다.
- 2페이즈에서 추가 증원은 없다. 기존 잡몹은 살아 있으면 계속 전투한다.
- 첫 Wave는 `SpawnCount=2`이며, 전용 Pool의 포장마차·뿔버섯 가중치가 각각 1이다. 현재 순환 가중치 선택에서는 연속 두 슬롯이 각 적을 정확히 한 번 선택한다(Seed에 따라 좌우 순서만 달라짐). 이 보장을 유지하려면 Pool 후보·가중치·SpawnCount를 함께 검토한다.
- 휴면 대기·이동·피격은 `cfa8628b0600429da10170ac92e912c3`, 휴면 사망은 `3462ebeccf2149afaa3c91405f7cfb20`이다. 2페이즈는 `EnemyDefinitions`의 원래 활성 모션으로 복원한다.
- 레이저 `CasterMotionRuid=91f105e9a3954188a919e2e7720a414b`는 본체와 빔을 포함한다. 중복 발사 이펙트(`CastEffectRuid`)는 비워 두며 피격 효과는 유지한다.
- 포장마차 `EnemyDefinitions.AttackMotionRuid`는 비워 둔다. 현재 공통 공격 모션이 스킬 모션보다 우선하므로, 이 칸을 채우면 철판·기름·레이저가 모두 같은 모션으로 재생된다. 세 공격의 모션은 각각 `EnemySkillDefinitions.CasterMotionRuid`로 수정한다.

### 2026-09-19 포장마차 검증 기록

- Maker 직접 진입 테스트에서 포장마차와 좀비버섯이 함께 생성되고, 휴면 상태에서는 보스가 WAIT를 유지하는 것을 확인했다.
- HP 38 → 20에서는 1페이즈 유지, 19에서 2페이즈 전환을 확인했다. 이후 24로 회복해도 2페이즈가 유지됐다.
- 레이저 캐스팅 상태와 중단 필요 타격 수 2를 확인했다. 별도의 EnemyTurn 실행 테스트에서 전용 모션 `91f105e9a3954188a919e2e7720a414b` 재생 및 실제 피해 5(플레이어 HP 10 → 5)를 로그로 확인했다.
- 콘텐츠 정합성 검증 통과 및 전투 검증 시점의 빌드·런타임 Error 0건. 이후 대기 모션 복원 확인용 진단 스크립트가 클라이언트에서 서버 전용 BoardState를 조회하여 nil 오류를 냈으므로, 복원 확인은 이번 검증 완료 항목에 포함하지 않는다. 전체 전투를 자연 진행하여 클리어하는 밸런스 테스트와 캐스팅 중단 입력 테스트도 별도로 필요하다.

### 2026-09-20 조정

- `BossPhaseDefinitions`의 `ReinforcementPoolId`, `ReinforcementIntervalTurns`, `ReinforcementMaxAlive`로 페이즈별 증원을 설정한다. 빈 PoolId는 증원 비활성화다. 웨이브 진행과 별개이며 라운드 종료 후 다음 계획 생성 전에만 처리한다.
- 현재 포장마차 1페이즈만 `region_06_food_cart_adds / 3 / 2`를 사용한다. 2페이즈는 증원 비활성화이며 남아 있는 잡몹은 자동 제거하지 않는다.
- 킹크랑 양쪽 페이즈와 포장마차의 CAST_INTERRUPTIBLE ParamA를 1로 통일했다. 피해 0, 빗나감, 피해 없는 밀치기는 기존 규칙대로 중단에 포함되지 않는다.
- 노틸러스·슬리피우드 적 스킬은 HudIconBackgroundColor(`#RRGGBBAA`)로 근접/원거리/독/마법/범위/캐스팅을 구분한다. 철판·독 포자·레이저의 HudIconRuid는 정적 스킬 아이콘으로 교체했다. 이펙트 배율은 기존 대비 20% 증가(최소 0.65, 최대 1.2)하며 피해·범위는 변경하지 않았다.
- 외곽·포장마차 맵의 기존 바닥 보강 오브젝트를 전투 발판 윗면에 정렬했다. 숨겨졌던 보스맵 보강 바닥을 표시한다. 원본 타일 배열·Foothold·UnitY·이동 로직은 변경하지 않았다.

## 3. 데이터 수정 위치

| 수정 목적 | 데이터 |
|---|---|
| Stage 이름·유형·Queue 용량 | `StageDefinitions.csv` |
| 물리 맵 연결 | `StageMapRoutes.csv` |
| Wave 수·적 수·강제 증원 조건 | `StageEnemyWaves.csv` |
| 적 HP·공격력·모션 | `EnemyDefinitions.csv` |
| Wave용 적 후보·ModelId·가중치 | `EnemySpawnPools.csv` |
| 적 스킬 사거리·쿨다운·아이콘·이펙트 | `EnemySkillDefinitions.csv` |
| 실제 피해 단계 | `SkillEffectSteps.csv` |
| 적 행동 순서 | `EnemyPatternSteps.csv` |
| 보스 HP 임계·패턴·페이즈별 모션 덮어쓰기 | `BossPhaseDefinitions.csv` |
| 클리어 보상·적 드롭 | `StageRewardDefinitions.csv`, `EnemyDropDefinitions.csv` |
| REST/BATTLE 노드 흐름 | `NodeDefinitions.csv` |

새 스킬을 추가할 때 `EnemySkillDefinitions.EffectSetId`와
`SkillEffectSteps.EffectSetId`를 반드시 동일하게 만든다. 전체 Validator는 존재하지 않는 효과
세트와 사용처 없는 효과 세트를 모두 거절한다.

## 4. Node 연결

현재 하단 경로는 다음 순서로 이어진다.

```text
ellinia_stage04_battle
→ shop_ellinia_nautilus (SHOP, 월드맵에서 선택)
→ nautilus_stage01_battle → … → nautilus_stage04_boss
→ shop_nautilus_sleepywood (SHOP, 월드맵에서 선택)
→ sleepywood_stage01_battle → sleepywood_reward_after_stage01
→ sleepywood_stage02_battle → sleepywood_reward_after_stage02
→ sleepywood_stage03_battle → sleepywood_reward_after_stage03
→ sleepywood_stage04_boss
→ sleepywood_reward_after_stage04
→ sleepywood_stage05_battle → sleepywood_reward_after_stage05
→ sleepywood_stage06_battle → sleepywood_reward_after_stage06
→ sleepywood_stage07_battle → sleepywood_reward_after_stage07
→ sleepywood_stage08_boss
```

REST 화면·보상 선택 구현은 다른 기능 소유 영역이며, 이 문서는 연결 ID 계약만 정의한다.
6-5 이후는 아래 후반전(신전) 절을 따른다.

보스 클리어의 계속 버튼 → 월드맵 상점 마커 → 기존 `shop` 맵 → 출발 버튼 → 월드맵 다음 지역 마커 순서로 진행한다.
두 SHOP 노드는 `ShopNodeBindings.csv`의 `shop_relic`에 연결된다. 상점 종료는 런 종료가 아니며,
후속 지역 선택 중에도 헤네시스 양쪽 상점 마커와 연결선은 유지한다. 이전 상점은 방문 완료 또는 잠김으로 표시하며 재입장을 허용하지 않는다.
다음 지역은 `CONTINUE_RUN`으로 기존 직업·스킬·증강·유물·재화를 유지한다. 최종 종료 여부는
특정 상점 이름이 아니라 서버의 `RunState == Completed`로 판단한다.

## 5. 외곽 맵 작업 규칙

- `darkwood.img`의 원본 슬리피우드/조용한 습지 배경과 나무를 사용한다.
- 배경·장식만 변경하며 기존 654개 타일, 48개 Foothold, 6개 BattleCell 좌표는 유지한다.
- 같은 물리 맵을 쓰므로 6-1~6-3 모두 외곽 배경이 적용된다. 포장마차 보스맵은 변경하지 않는다.

## 6. 직접 테스트

1. Maker에서 `sleepywood_ant_tunnel`을 열고 Play하면 MapId 기준 공통 테스트 진입기가
   `region_06_stage_01`을 자동 선택한다.
2. 보스만 확인하려면 `sleepywood_food_cart_boss`를 열고 Play한다.
3. 6-2·6-3은 런 Node 흐름으로 진입하는 것이 기본이다. 직접 확인할 때만 공용 맵 루트의
   `BattleSessionComponent.PrototypeTestStageOverride`를 대상 StageId로 바꾸고, 테스트 후
   빈 문자열로 되돌린다. 운영용 `StageId`는 수정하지 않는다.
4. Build Console Error 0, Runtime Error 0, `[ContentIntegrity] valid`를 확인한다.
5. 일반전에서는 Wave 구성과 원거리 예고를, 보스전에서는 Phase 2·포장마차 레이저의 전체 범위·2턴 준비·중단을 확인한다.

공통 진입 규칙과 테스트 키는
[Battle-Prototype-Test-Guide.md](Battle-Prototype-Test-Guide.md)를 따른다.

### 2026-09-15 확인 결과

- Maker 빌드 Error 0, 테스트 구간 Runtime Error 0. 기존 Console 이력과 구분하여 확인했다.
- 전체 콘텐츠 Validator 통과: Stage 24, Skill 72, EnemyPattern 40, Shop 1 / Entry 33.
- 엘리니아 보스 강제 클리어 → 상점 선택 → `shop` → 출발 → 노틸러스 `CONTINUE_RUN` 진입 확인.
- 노틸러스 보스 강제 클리어 → 상점 선택 → `shop` → 출발 → 슬리피우드 `CONTINUE_RUN` 진입 확인.
- 노틸러스 클리어 시 도시 `COMPLETED` / 상점 `AVAILABLE`, 상점 출발 시 슬리피우드 `AVAILABLE` 확인.
- 6-1 드레이크 생성·이동 턴·물기 큐 준비, 6-3 진입 및 두 번째 Wave 다크 드레이크 생성 확인.
- 신규 모델 3종 구조 검증 통과. 전 구간 완주·세부 전투 난이도·배경의 시각적 선호도는 별도 플레이 피드백 대상으로 남긴다.

### 2026-09-20 추가 검증 결과

- 새 Play에서 정식 진입 요청으로 6-4를 시작하고 턴 명령 3회를 실행했다. 3턴째 1페이즈 증원 생성과 증원 몬스터의 `SPAWN_WAIT`를 확인했다.
- 별도 서버 기능 검사에서 잡몹 생존 상한 2마리 제한, 2페이즈 전환 후 증원 중단, 실제 공격 피해 처리 1회로 캐스팅 `INTERRUPTED` 전환을 확인했다.
- 새 실행 구간 Runtime Error 0, Build Error 0. 콘텐츠 Validator는 Stage 28 / Skill 80 / EnemyPattern 45를 통과했다.
- 보스맵의 바닥 보강 오브젝트 상단과 전투 셀 상단 좌표가 일치함을 확인했다. 배경·아이콘의 최종 시각적 선호도 및 전체 전투 밸런스는 별도 플레이 확인 대상으로 남긴다.

## 7. 후반전(신전)

슬리피우드 후반전은 신전 일반 Stage 3개와 주니어 발록 보스 Stage로 구성하며, 6-4 포장마차 보스
다음 REST에서 이어진다.

| 물리 MapId | 사용하는 Stage | 역할 |
|---|---|---|
| `sleepywood_temple_battle` | `region_06_stage_05`~`07` | 신전 일반전 공용 맵 (`kerning_city_battle` 복제) |
| `sleepywood_temple_boss` | `region_06_stage_08` | 주니어 발록 전용 보스맵 |

| Stage | 표시명 | 주요 적 | Wave 수 |
|---|---|---|---:|
| `region_06_stage_05` | 6-5 신전 입구 | 와일드카고 2 → 와일드카고 2 → 타우로스피어 2 (6마리) | 3 |
| `region_06_stage_06` | 6-6 신전 회랑 | 와일드카고 2 → 타우로스피어 2 → 타우로마시스 2 (6마리) | 3 |
| `region_06_stage_07` | 6-7 신전 제단 | 타우로스피어 2 → 타우로마시스 2 → 와일드카고 1 → 타우로마시스 2 (7마리) | 4 |
| `region_06_stage_08` | 6-8 주니어 발록 | 주니어 발록 | 보스 (Phase 2 와일드카고 증원) |

- 와일드카고는 `QUICK` 근접이며 방향 전환 → 1턴 예고 돌진(최대 3칸) → 들이받기를 순환한다. 타우로스피어는 2칸 찌르기와 1턴 예고 휩쓸기 뒤 한 칸 물러난다. 타우로마시스는 `HEAVY` 근접이며 내려찍기 → 1턴 예고 대지 가르기(전방 1~2칸) → 포효(공격력 +1, 2회)를 순환한다.
- 주니어 발록은 할퀴기, 전방 3칸 화염구 투사체, 1턴 예고 불꽃 휩쓸기(격노 시 강화)를 사용한다. Phase 2에서는 할퀴기를 연속 2회 사용하고 3턴마다 와일드카고를 증원한다(살아 있는 일반 적 최대 2).
- 2026-09-28 난이도 상향: 페리온·노틸러스보다 약 1.2배 어렵게 마릿수(5/5/5 → 6/6/7), HP(약 1.2배), 공격력, 패턴을 올렸다. 수치는 [Stage-Authoring-Guide.md](Stage-Authoring-Guide.md)의 신전 표를 따른다.
- 신전 배틀맵은 발판 높이가 달라 6-5~6-7이 `CellStartX=-2.9027`, `UnitY=-1.93`을 사용한다.
- 신전 적의 피격음·사망음과 스킬별 적중음은 `EnemyImpactPresentations.csv`에 있다.

세부 수치·패턴은 [Stage-Authoring-Guide.md](Stage-Authoring-Guide.md)의 슬리피우드 후반전 절과
[Boss-Phase-Authoring-Guide.md](Boss-Phase-Authoring-Guide.md)의 주니어 발록 예시를 따른다.
