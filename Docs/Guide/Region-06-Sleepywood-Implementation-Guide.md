# Region 06 슬리피우드 전반전 구현 가이드

## 1. 범위

슬리피우드 전반전은 개미굴 3개 일반 Stage와 포장마차 보스 Stage로 구성한다. 물리 맵은
Stage마다 복제하지 않고 아래 두 개만 사용한다.

| 물리 MapId | 사용하는 Stage | 역할 |
|---|---|---|
| `sleepywood_ant_tunnel` | `region_06_stage_01`~`03` | 개미굴 일반전 공용 맵 |
| `sleepywood_food_cart_boss` | `region_06_stage_04` | 포장마차 전용 보스맵 |

Stage의 규칙·적·웨이브는 CSV가 결정하고, 맵은 배경·전투 셀·전투 컴포넌트만 소유한다.

## 2. Stage와 적 구성

| Stage | 표시명 | 주요 적 | Wave 수 |
|---|---|---|---:|
| `region_06_stage_01` | 6-1 개미굴 입구 | 뿔버섯 | 3 |
| `region_06_stage_02` | 6-2 버섯 군락 | 뿔버섯, 좀비버섯 | 4 |
| `region_06_stage_03` | 6-3 깊은 개미굴 | 뿔버섯, 좀비버섯, 주니어 부기 | 4 |
| `region_06_stage_04` | 6-4 지하 휴게소 | 포장마차 | 보스 + Phase 2 증원 |

- 뿔버섯은 접근 후 1칸 찌르기로 기본 근접 대응을 학습시킨다.
- 좀비버섯은 2칸 독 포자를 사용하며 재사용 대기시간은 3턴이다.
- 주니어 부기는 2칸 저주탄을 사용하며 6-3에서 한 Wave만 등장한다.
- 포장마차는 철판 내려치기, 2칸 끓는 기름, 전방 1~5칸을 덮는 포장마차 레이저를 사용한다.
- 포장마차 레이저는 피해 5, 재사용 대기시간 5턴, Queue 준비 2턴이며 준비 중 서로 다른
  플레이어 피해 스킬을 2회 적중시키면 끊기는 기존 `CAST_INTERRUPTIBLE` 계약을 사용한다.
- 포장마차는 `HOLD_POSITION` 특성을 유지하므로 플레이어 쪽으로 접근하지 않는다.
- 포장마차는 HP 50%에서 Phase 2로 전환하며 좀비버섯 증원 Wave를 호출한다.

## 3. 데이터 수정 위치

| 수정 목적 | 데이터 |
|---|---|
| Stage 이름·유형·Queue 용량 | `StageDefinitions.csv` |
| 물리 맵 연결 | `StageMapRoutes.csv` |
| Wave 수·적 수·강제 증원 조건 | `StageEnemyWaves.csv` |
| 적 HP·공격력·모션·ModelId | `EnemyDefinitions.csv` |
| Wave용 적 후보와 가중치 | `EnemySpawnPools.csv` |
| 적 스킬 사거리·쿨다운·아이콘·이펙트 | `EnemySkillDefinitions.csv` |
| 실제 피해 단계 | `SkillEffectSteps.csv` |
| 적 행동 순서 | `EnemyPatternSteps.csv` |
| 보스 HP 임계와 패턴 교체 | `BossPhaseDefinitions.csv` |
| 클리어 보상·적 드롭 | `StageRewardDefinitions.csv`, `EnemyDropDefinitions.csv` |
| REST/BATTLE 노드 흐름 | `NodeDefinitions.csv` |

새 스킬을 추가할 때 `EnemySkillDefinitions.EffectSetId`와
`SkillEffectSteps.EffectSetId`를 반드시 동일하게 만든다. 전체 Validator는 존재하지 않는 효과
세트와 사용처 없는 효과 세트를 모두 거절한다.

## 4. Node 연결

현재 하단 경로는 다음 순서로 이어진다.

```text
nautilus_stage04_boss
→ nautilus_reward_after_stage04
→ sleepywood_stage01 → sleepywood_rest_after_stage01
→ sleepywood_stage02 → sleepywood_rest_after_stage02
→ sleepywood_stage03 → sleepywood_rest_after_stage03
→ sleepywood_stage04_boss
```

REST 화면·보상 선택 구현은 다른 기능 소유 영역이며, 이 문서는 연결 ID 계약만 정의한다.

## 5. 직접 테스트

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
