# 보스 Phase 제작 가이드

보스도 일반 적과 같은 `EnemyDefinitions`, `EnemyPatternSteps`, `SkillDefinitions` 규격을 사용한다.
보스 전용 코드를 Session에 추가하지 않고 `BossPhaseDefinitions`가 HP 구간과 Pattern 교체만 선언한다.

## 데이터 흐름

```text
StageDefinitions(StageType=BOSS)
→ StageEnemyWaves(WaveTableId)
→ EnemySpawnPools
→ EnemyDefinitions(IsBoss=true)
→ BossPhaseDefinitions
→ EnemyPatternSteps
→ SkillDefinitions / SkillEffectSteps
```

## BossPhaseDefinitions 스키마

| 열 | 타입 | 규칙 |
|---|---|---|
| `SchemaVersion` | integer | 현재 `1` |
| `EnemyDefinitionId` | string | `IsBoss=true`인 Enemy 참조 |
| `PhaseIndex` | integer | 1부터 연속 |
| `PhaseId` | string | 같은 보스 안에서 유일 |
| `HpRatioLE` | number | `(0, 1]`, PhaseIndex가 커질수록 감소 |
| `PatternId` | string | 유효한 Enemy Pattern 참조 |
| `Enabled` | boolean | `true` 행만 사용 |

첫 Phase는 `HpRatioLE=1.0`이어야 하며 `EnemyDefinitions.PatternId`와 같은 Pattern을 사용한다.
현재 예시는 다음과 같다.

```csv
1,region_01_guardian_boss,1,OPENING,1.0,region_01_boss_phase_01,true
1,region_01_guardian_boss,2,ENRAGED,0.5,region_01_boss_phase_02,true
```

## 실행 규칙

- Phase 상태는 적 Entity의 `BossPhaseStateComponent`가 소유한다.
- 피해 적용 후 HP가 임계값을 넘으면 다음 Pattern을 초기화한다.
- 플레이어 턴 시작 때 이미 고정된 적 행동은 그대로 실행한다.
- Phase 전환 전에 고정된 옛 행동이 끝나면 옛 Pattern Step 진행만 `PATTERN_SUPERSEDED`로 폐기한다.
- 다음 플레이어 턴부터 새 Phase Pattern을 계획한다.
- 공격 타이밍은 각 `SkillDefinitions.ActionDuration`을 사용한다.

## UI 계약

`GetBattleUiState().EnemyIntents[]`는 다음 값을 제공한다.

- `BossPhaseId`
- `BossPhaseIndex`
- `BossPhaseRevision`
- 현재 고정 행동의 `PatternId`, `CommandType`, `TileId`, `TelegraphTurnsRemaining`

Phase가 바뀌어도 현재 고정 행동의 PatternId는 옛 Pattern일 수 있다. 이는 오류가 아니라
플레이어가 이미 확인한 적 Queue를 바꾸지 않기 위한 규칙이다.

## 검증 체크리스트

1. 전체 Validator에서 `bossPhaseOwners`가 증가한다.
2. 생성 로그에 `OPENING`, `index=1`, `hpRatio=1.0`이 남는다.
3. 임계 HP에서 `ENRAGED`, `index=2`로 한 번만 전환된다.
4. 이전 계획 완료는 오류가 아니라 `PATTERN_SUPERSEDED`로 기록된다.
5. 새 턴의 EnemyIntent가 Phase 2 Pattern을 사용한다.
6. 예고 행동 뒤 실제 스킬이 실행되고 피해가 적용된다.
7. Build/Runtime Warning·Error가 0인지 확인한다.
