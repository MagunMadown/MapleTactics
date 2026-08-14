# 콘텐츠 전체 검증 가이드

## 무엇을 막는가

표를 수정한 뒤 전투 도중 조용히 실패하는 대신, 콘텐츠 제작 단계에서 잘못된 행과 연결을
찾는 것이 목적이다. 현재 전체 검사는 다음 데이터를 한 번에 확인한다.

- Stage Definition과 다음 Stage 참조
- Skill Definition과 Effect Step 묶음
- Weapon, Job, Augment, Node Graph, Enemy Pattern의 전용 Validator
- Enemy Drop 전체 데이터
- Stage Reward와 Stage·런 재화·소모품 참조
- Shop Definition/Entry와 SHOP Node·스킬·소모품·런 재화 참조

## 자동 실행 시점

`BattleSessionComponent`는 다음 두 경계에서 전체 검사를 자동 실행한다.

1. 맵 전투 세션의 `OnBeginPlay` 초기화 직후, 플레이어 등록·Stage 시작 전
2. Gateway 입장이나 Stage 재구축의 `RebuildBattleState`가 상태를 지우기 전

통과하면 `ContentValidationState=VALID`이 되고 기존 전투 흐름을 그대로 시작한다. 실패하면
`BLOCKED` 상태를 유지하며 플레이어 턴과 적 스폰을 시작하지 않는다. 데이터 오류를
`BattleResult=Defeat`로 바꾸지 않으므로 게임 결과·보상 기록과도 섞이지 않는다.

## 수동 실행 API

Server에서 다음 Facade만 호출한다.

```lua
local result = _ContentValidatorLogic:ValidateAllContent()
```

`ContentValidatorLogic`은 외부 진입점만 제공한다. `ContentIntegrityValidatorLogic`은 Dataset을
순회하고 전용 Validator 결과를 모으며, 각 Job·Augment·Pattern의 세부 규칙을 다시 구현하지
않는다.

## 결과 계약

| 필드 | 의미 |
|---|---|
| `Success` | 전체 통과 여부 |
| `Reason` | 성공은 `OK`, 실패는 `CONTENT_INTEGRITY_FAILED` |
| `ErrorCount` | 발견한 오류 수 |
| `Errors` | 구조화된 오류 목록 |
| `ErrorSnapshot` | 로그와 간단한 디버그 UI용 `|` 구분 문자열 |
| `Checked*Count` | Dataset 종류별 검사 수 |

각 `Errors` 원소는 `DataSetName`, `RowIndex`, `ContentId`, `DetailReason`을 가진다. 따라서
비개발자도 어떤 표의 몇 번째 행을 고쳐야 하는지 확인할 수 있다.

```text
StageDefinitions[1]stage01=NEXT_STAGE_NOT_FOUND:missing_stage
SkillEffectSteps[2]orphan_effects#1=ORPHAN_EFFECT_SET
```

## 현재 전체 연결 검사

- 중복 `StageId`, `SkillId`, `EffectSetId + StepIndex`
- 존재하지 않는 `NextStageId`
- Skill이 참조하지 않는 고아 Effect Set
- 누락 Dataset과 빈 주요 ID
- 각 전용 Validator의 schema, enum, 범위, 참조 규칙

## 개발 규칙

1. 새 콘텐츠 종류의 행 규칙은 전용 Validator에 둔다.
2. 표와 표 사이의 연결 또는 전체 중복 검사는 `ContentIntegrityValidatorLogic`에 등록한다.
3. UI와 BattleSession에서 같은 검사를 복제하지 않는다.
4. 새 Dataset을 추가하면 정상 행, 중복 행, 누락 참조 실패를 함께 검증한다.
5. 배포 전 또는 개발용 시작 절차에서 `ValidateAllContent()`를 한 번 호출한다.

## UI 상태 계약

UI는 Dataset이나 Validator를 직접 읽지 않고 `GetBattleUiState().ContentValidation`만 읽는다.

| 필드 | 의미 |
|---|---|
| `State` | `NOT_RUN`, `VALID`, `BLOCKED` |
| `IsReady` | 전투 명령을 표시·활성화해도 되는지 |
| `Reason` | 전체 검사 결과 코드 |
| `ErrorCount` | 오류 개수 |
| `ErrorSnapshot` | 표·행·ID·원인을 포함한 디버그 문자열 |
| `Revision` | 재검사로 상태가 갱신된 횟수 |

`RevisionKey`에도 Validation Revision이 포함되므로 최종 UI는 별도 폴링 규칙 없이 기존 DTO
갱신 방식으로 오류 패널을 다시 그릴 수 있다. 현재 HUD는 기능 검증용이며, 최종 오류 화면의
레이아웃과 문구는 이 DTO 위에서 교체한다.
