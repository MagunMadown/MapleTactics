# Shogun식 큐·턴 흐름 마이그레이션 계획

## 0. 목표

현재의 `타일 여러 개 등록 → 즉시 전체 실행 → 적 라운드` 프로토타입을 다음 규칙으로
마이그레이션한다.

```text
플레이어 Command 1회
→ 턴 소비 Command면 모든 생존 적이 SpawnOrder 순으로 Command 1회 실행
→ 다음 플레이어 턴
```

플레이어의 등록 큐는 이동·회전·적 라운드를 지나도 유지한다. `EXECUTE_QUEUE`만 등록 큐를
실행 큐로 동결하고, 모든 타일을 순서대로 실행한 뒤 적 라운드로 넘긴다.

## 1. 고정 결정

- 기본 큐 용량은 `3`, 최소 `1`, 현재 UI 최대 지원값은 `6`이다.
- 유효 용량은 `BaseQueueCapacity + QueueCapacityBonus`를 최소·최대값으로 Clamp한다.
- 직업·Skill·증강·유물·아이템·Stage Rule은 고유 Modifier ID로 용량을 증감한다.
- Modifier가 제거되어 현재 등록 수가 유효 용량보다 커져도 기존 타일을 삭제하지 않는다.
- 초과 상태에서는 추가 등록만 막고 실행·개별 제거·전체 비우기는 허용한다.
- 일반 `QUEUE_TILE`, `MOVE`, `TURN`, `EXECUTE_QUEUE`는 턴을 소비한다.
- `FreePlay` 타일 등록과 큐 편집은 턴을 소비하지 않는다.
- Turn과 Queue Item은 1:1 관계가 아니다. 한 Turn에 FreePlay 등록·제거·정렬이 여러 번
  일어날 수 있고, 하나의 등록 큐는 여러 Turn과 적 라운드에 걸쳐 유지될 수 있다.
- 등록 큐는 플레이어 턴과 적 라운드 사이에 유지한다.
- Stage 종료·패배·전투 Reset에서는 큐를 초기화한다.
- Wave 전환은 같은 Stage의 연속 전투이므로 등록 큐를 보존하고 실행 상태만 초기화한다.

## 2. 상태 소유권

### BattleTurnComponent

- Phase, TurnNumber, 입력 잠금
- 플레이어 등록 큐와 실행 큐
- 기본·보너스·유효 큐 용량
- 큐 용량 Modifier Snapshot과 Revision
- UI가 읽는 Turn State Revision

### BattleSessionComponent

- Client Request 검증
- 플레이어 Command 실행 조정
- 턴 소비 여부에 따른 EnemyRound 진입
- Skill 실행·Cooldown·Wave·승패 연결
- Client UI용 읽기 전용 Snapshot 조립

### 향후 EnemyAttackQueueComponent

- 적별 등록 큐와 실행 큐
- 적별 Queue Revision
- `EnemyPatternRunnerComponent`가 준비한 다음 Command 실행

## 3. 큐 용량 API

```text
ConfigureQueueCapacity(base, min, max, reason)
UpsertQueueCapacityModifier(modifierId, sourceType, sourceId, addValue)
RemoveQueueCapacityModifier(modifierId)
RecalculateQueueCapacity(reason)
GetQueueCapacityState()
```

허용 SourceType은 `JOB`, `SKILL`, `AUGMENT`, `RELIC`, `ITEM`, `STAGE_RULE`이다.
Modifier ID는 `SourceType:SourceId:EffectId`처럼 호출자가 결정적으로 생성한다.

## 4. 플레이어 상태 전이

```text
PlayerTurn
├─ QUEUE_TILE 일반 → 등록 큐 유지 → EnemyRound
├─ QUEUE_TILE FreePlay → 등록 큐 유지 → PlayerTurn
├─ MOVE → 등록 큐 유지 → EnemyRound
├─ TURN → 등록 큐 유지 → EnemyRound
├─ EXECUTE_QUEUE → 전체 순차 실행 → 등록 큐 비움 → EnemyRound
├─ REMOVE_QUEUE_ITEM → PlayerTurn 유지
├─ REORDER_QUEUE → PlayerTurn 유지
└─ CLEAR_QUEUE → PlayerTurn 유지
```

`OpenPlayerTurn()`은 행동 잠금과 실행 큐만 정리한다. 등록 큐는 초기화하지 않는다.
등록 큐 전체 초기화는 `ResetTurnState()` 또는 명시적인 `ClearQueuedSkills()`만 수행한다.

## 5. UI 읽기 계약

UI는 `BattleSessionComponent.GetBattleUiState()`가 반환한 DTO만 표시 판단에 사용한다.
서버는 모든 Request를 다시 검증하므로 Client의 `Can...` 값은 표시 편의용이다.

주요 필드:

```text
Success, Reason, RevisionKey
Phase, TurnNumber, IsProcessing, BattleResult
Commands.CanMove/CanTurn/CanQueue/CanExecute/CanClear/CanRemove/CanReorder
LastCommand.Type/Success/Reason/Revision
PlayerQueue.BaseCapacity/BonusCapacity/EffectiveCapacity
PlayerQueue.Count/RemainingSlots/IsFull/IsOverCapacity
PlayerQueue.QueuedTileIds/ExecutingTileIds/ExecutingIndex
EnemyIntents
CooldownSnapshot/CooldownRevision
```

UI는 동기화 필드를 직접 변경하지 않고 기존 `Request...` API만 호출한다.

## 6. 구현 Slice

### Slice 1 — 용량과 지속 큐

- 기본 3·최소 1·최대 6 설정
- Flat ADD Modifier 등록·교체·제거
- 플레이어 턴 재개 시 등록 큐 유지
- 큐가 있어도 이동·회전 허용

### Slice 2 — 턴 소비

- 일반 타일 등록 후 EnemyRound
- FreePlay 등록은 PlayerTurn 유지
- 이동·회전 후 큐 유지
- 실행 큐 전체 완료 후 EnemyRound
- 매 턴 Cooldown 진행 회귀

### Slice 3 — UI DTO

- 공통 Snapshot 함수
- Command Availability 제공
- 기존 HUD의 중복 상태 조합 제거

### Slice 4 — 큐 편집

- 개별 제거 — 서버 API/Request/DTO 구현 완료
- 순서 변경 — 서버 API/Request/DTO 구현 완료
- 실행 중 편집 거절 — 구현·Maker 회귀 완료
- HUD 슬롯별 제거·정렬 조작 — 시각 UI Slice로 분리

### Slice 5 — 적별 큐

- 적 엔티티별 Attack Queue
- 모든 적의 Prepared Command 동시 공개
- 일반 적 준비 후 다음 행동에 실행
- `QUICK` 적의 준비·즉시 실행 예외

## 7. 회귀 시나리오

1. 기본 용량이 3이고 네 번째 등록이 `QUEUE_FULL`인지 확인한다.
2. `AUGMENT +1` 적용 후 4칸, 제거 후 3칸으로 복구되는지 확인한다.
3. 4개가 등록된 상태에서 보너스를 제거해도 큐가 보존되고 추가 등록만 거절되는지 확인한다.
4. `기본 베기 등록 → 적 행동 → 이동 → 적 행동 → 밀치기 등록 → 적 행동 → 실행` 순서를 확인한다.
5. 이동·회전 후 등록 큐 문자열과 순서가 유지되는지 확인한다.
6. 큐 실행 중 각 타일이 현재 Cell/Facing으로 타깃을 다시 계산하는지 확인한다.
7. FreePlay 등록에는 적 행동과 Turn 증가가 없는지 확인한다.
8. 실행 중 재입력과 중복 Client Request가 거절되는지 확인한다.
9. 전투 Reset·Victory·Defeat에서 큐가 초기화되는지 확인한다.
10. 다음 Wave 진입 전후 등록 큐가 같은 순서와 개수로 보존되는지 확인한다.

## 8. 완료 조건

- Maker Build error 0.
- Runtime error 0.
- 각 회귀 시나리오에 시작·상태·완료 positive log가 존재한다.
- HUD와 `GetBattleUiState()`가 같은 Queue/Phase/Turn을 표시한다.
- GDD, Data Dictionary, Architecture, Turn Guide와 실제 동작이 일치한다.

## 9. 2026-08-01 구현·검증 기록

완료:

- Slice 1 기본/보너스/유효 용량과 Modifier 추가·제거 API
- Slice 2 일반 타일 등록의 턴 소비, 적 라운드 뒤 등록 큐 유지, 큐 보유 중 이동
- Slice 3 `GetBattleUiState()`와 HUD DTO 전환
- Maker Build: Warning 0, Error 0
- Maker Runtime: Error/Fatal 0
- 실제 로그: 용량 `3 → 4 → 3`, 등록 후 `EnemyTurn`, 다음 `PlayerTurn`의 큐 1개 유지,
  이동 후 큐 1개 유지, 실행 후 큐 0개와 다음 Turn 진입
- Client DTO: 기본 3/보너스 0/유효 3 및 `CanMove/CanTurn/CanQueue` 반환
- 무료 편집: Turn 3에서 `basic_slash|heavy_slash → heavy_slash|basic_slash` 정렬 후
  2번 `basic_slash` 제거, Turn 3/PlayerTurn 유지
- 실행 잠금: 실행 중 제거 요청이 `ACTION_PROCESSING`으로 거절됨
- Client DTO: `PlayerQueue.Items[{Index, SkillId}]`, `CanRemove`, `CanReorder` 반환
- FreePlay 호환 스킬 `quick_slash` 등록: Turn 1/PlayerTurn 유지, `ConsumesTurn=false`
- `quick_slash → basic_slash` 혼합 등록: 일반 등록 직후 EnemyTurn, 적 라운드 후
  Turn 2/PlayerTurn과 `quick_slash|basic_slash` 순서 유지
- 혼합 큐 전체 실행: 실행 목록 순서 유지, 완료 후 Turn 3/PlayerTurn과 큐 0 확인
- FreePlay 회귀 Maker Build Error/Warning 0, Runtime Error/Fatal 0
- OverCapacity 회귀: `AUGMENT +1`로 유효 용량 4에서 4개 등록 후 Modifier를 제거해도
  `count=4/effective=3/IsOverCapacity=true`로 기존 큐 보존
- 초과 상태의 추가 등록은 `QUEUE_FULL`로 거절되고, 순서 변경·개별 제거·전체 실행은 허용
- 초과 큐 전체 실행 후 Turn 2/PlayerTurn과 큐 0, 개별 제거 시 Turn/Phase 유지 확인
- OverCapacity 회귀 Maker Build Error/Warning 0, Runtime Error/Fatal 0
- 전투 경계 정책 구현: Wave 전환은 `ClearActionState()`로 등록 큐를 보존하고,
  Victory·Defeat·Reset은 등록 큐와 실행 상태를 함께 초기화
- 경계 회귀: Wave 1→2에서 큐 1개 보존, Victory `2→0`, Reset `1→0`, Defeat `1→0`
- 경계 회귀 Maker Build Error/Warning 0
- 명령 결과 계약: 모든 유효 플레이어 RPC 결과를 `LastCommand`와 Revision으로 동기화
- 실행 잠금 회귀: 첫 실행 `EXECUTING`, 같은 프레임의 두 번째 실행과 등록·이동·비우기·
  제거·정렬은 모두 `ACTION_PROCESSING`
- 실제 Client 중복 RPC 회귀: 실행 2회 전송 중 첫 요청만 성공, 두 번째 요청은
  `LastCommand={EXECUTE_QUEUE,false,ACTION_PROCESSING}`로 Client DTO에 반영되고 Revision 증가
- 명령 잠금 회귀 Maker Build Error/Warning 0, Runtime Error/Fatal 0

후속 회귀:

- 실제 `SkillDefinitions` UserDataSet 생성 후 `FreePlay=true` CSV 행의 무턴 등록 재검증
- HUD 슬롯별 제거·정렬 버튼 또는 드래그 조작
- Slice 5 적별 공격 큐와 다중 Intent DTO

### 2026-08-01 FreePlay 검증 준비

- `quick_slash` 호환 Definition 추가: `FreePlay=true`, 기본 베기 모션·효과 재사용
- Dataset의 boolean 셀은 native boolean과 `true`/`1`/`yes` 문자열을 모두 지원
- 기존 `basic_slash`, `heavy_slash`, `push`, `slash_push_combo`는 `FreePlay=false` 유지
- Maker 회귀 통과: 무료 등록은 턴 유지, 일반 등록은 적 라운드 진행, 혼합 큐 실행 후 정상 초기화
