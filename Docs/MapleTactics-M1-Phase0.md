# MapleTactics M1 Phase 0 — 기술 검증

> 🔖 **AI 안내 — 재개 시**: `msw-planning`을 먼저 로드하고 Roadmap·GDD·존재하는 Phase 문서·`Archive/As-built.md`를 확인한다. 구현이나 `⬜/🟡/✅` 상태 변경·Phase 완료 처리 전에는 스킬의 `references/build-management.md`를 **전체** 읽는다. 현재 항목 판정은 Phase 문서, GDD §9는 그 상태의 미러다.

Status: 🟡 In progress — 실행 근거 확인, 오류 위치 진단 보완·실제 UI 입력 대기
Last updated: 2026-10-12
목적: MSW의 맵·셀·RPC·데이터·큐 경계가 실제로 동작하는지 증명한다. 기존 Phase 1 진행을 미착수로 되돌리지 않는다.

## Skills to reference (this Phase)

- `msw-general`: `platform.md`, `platform-maple.md`, `workspace.md`, `entity.md`, `authoring.md`, `builder-protocol.md`, `builder-protocol-map.md`
- 모델 Body를 검사할 때: `model.md`, `builder-protocol-model.md`
- `msw-scripting`: `SKILL.md`, `verify-checklist.md`
- `msw-combat-system`: `SKILL.md`
- `msw-ui-system`: `SKILL.md`, `component-api.md`, `runtime-patterns.md`

## 현재 맵·운영 계약

- `map01`은 초기 프로토타입 이름이며 현재 맵 파일이 아니다. 일반전 기준은 `henesys_battle`, 보스전은 `henesys_boss`, 연습은 `skill_test`, 대기는 `lobby`다. 실제 StageId→MapId는 `StageMapRoutes.csv`를 따른다.
- 2026-10-12 MapBuilder 읽기 결과: 맵 26개 모두 MapleTile(0)·Static Map, 이 중 전투 세션 맵 20개. MapleTile 물리 엔티티의 요구 Body는 `RigidbodyComponent`다. 모든 모델의 구성 검증 완료를 뜻하지 않는다.
- `SectorConfig.config`의 현재 `sector01.maxUserNo=1`을 유지한다. 플레이어당 Instance Room/Map 격리를 이미 구현한 것으로 기록하지 않는다.
- 일반 이동은 서버가 셀·점유·턴·요청을 검증하고 소유 클라이언트의 `PlayerGridMovementLogic`이 루트를 재생한다. 로비와 전투는 같은 시간·홉·착지 검사 정책을 쓴다.
- 프로젝트 API 기준은 사용자 승인 `Environment/config`의 CoreVersion 26.10.0.0이다.
- SideViewRectTile 전환은 현재 작업에 포함하지 않는다. 이번 문서 정리는 맵 타입·Body·설정 파일을 변경하지 않았다.

## 현재 상태 체크리스트

| ID | 상태 | 작업 | 확인된 범위·남은 확인 |
|---|---|---|---|
| P0-01 | ✅ | 맵/Body·격리 계약 | 26개 MapleTile/Static 맵·1명 운영, Player/DefaultPlayer 상속 및 스폰 77행·적 모델 50개 대조; 공통 Body 없는 적 배치 경로 연결 |
| P0-02 | ✅ | 논리 셀 이동 | 20개 맵 41/41 이동·착지와 로비/전투 공통 경로 검증 |
| P0-03 | ✅ | 서버 Command 왕복 | Maker의 INVALID_SENDER, 실제 클라이언트의 오래된 entry/context 및 중복 요청 무변경 확인; 실제 다른 계정 시험은 별도 |
| P0-04 | ✅ | 큐 재타깃 | 기존 Maker Push 이후 Miss와 실제 제어 API, 최신 제어/큐 회귀 통과 |
| P0-05 | 🟡 | UserDataSet 로드·검증 | 실제 Dataset 정상 로드·복제본 Range/중복 거절·원본 보존 확인; 기본 진단의 Column/Value 누락 보완 필요 |
| P0-06 | 🟡 | 통합 검증 | 관련 build/runtime·회귀 통과; P0-05 Column/Value 진단 보완과 실제 UI 포인터 검증 대기 |

추가 검증: [2026-10-12 정상 런·경로 검증](../Artifacts/normal-run-validation-20261012/verification.md). 정적 모델 대조, 실제 클라이언트 RPC 및 제어 전투 경로를 구분한다.

근거: [튜토리얼·세션 통합](../Artifacts/tutorial-session-refactor/verification.md), [20개 맵 이동](../Artifacts/tutorial-session-refactor/movement-feel-verification/verification.md), [보조 로직 정리](../Artifacts/tutorial-session-refactor/auxiliary-logic-cleanup/verification.md), [문서 대조 기록](../Artifacts/plan-reconciliation-20261012/verification.md).

`🟡`는 구현이 존재하지만 위 완료 기준의 일부 증거가 남았다는 뜻이다. 이번 문서 대조를 새 Maker 실행으로 표현하지 않는다.

## 작업 상세

### P0-01 맵/Body 계약

상태: ✅ Tested

- 목표: 맵 타입, 현재 전투 격리 정책, 물리 엔티티의 Body를 문서·모델과 일치시킨다.
- 확인: MapBuilder의 26개 맵 mode/Static Map, Sector 최대 인원 1. Player/DefaultPlayer 상속과 스폰 CSV 77행·적 모델 50개를 연결했다. 적 모델에는 native Movement/Body가 없고 논리 보드와 BattleMovementPresentationLogic.PlaceEntity의 Transform 경로를 사용한다. 플레이어의 Rigidbody 존재와 실제 일반 이동도 Maker에서 확인했다.
- 구현: 실제 MapId와 모델 구성을 builder로 읽고 운영 범위를 기록한다.
- 데이터/UI: 없음.
- 의존성: 기존 MapleTile 유지 정책. 사용자에게 새로운 모드 전환을 요구하지 않는다.
- 완료: map mode, Static/Instance 운영 정책, 대상 모델 Body, 이동 API의 근거를 모두 연결한다.

### P0-02 논리 셀 이동

상태: ✅ Tested

- 목표: CellIndex는 서버 원본이고 월드 이동은 승인 목적 셀에서 파생된다.
- 구현: `BattleUnitComponent`·`BoardStateComponent`, 일반 이동은 공통 `PlayerGridMovementLogic`과 로비/전투 호출부.
- 데이터: `StageDefinitions`의 CellCount/CellStartX/CellSpacing/UnitY.
- UI: CellIndex 표시 가독성은 Phase 1 사용자 검토에 남는다.
- 의존성: 현재 MapleTile 계약.
- 근거: 20개 맵의 이동·착지 41/41, 양끝·대표 점유 거절, 정밀 이벤트 40개. 보조 정리 후 로비/전투 착지 4/4·보정 0.
- 완료 범위: 서버 목적 셀·최종 위치 일치와 공통 이동 계약. 사람의 렌더 체감·GPU FPS 검증은 아니다.

### P0-03 서버 Command 왕복

상태: ✅ Tested

- 목표: Client 입력→Server 검증→Client 표시와 요청 소유권·순서 검증을 증명한다.
- 구현: Session RPC와 기존 HUD/공통 이동 요청·응답.
- 데이터: request/entry/context 식별자.
- UI: 실제 키·클라이언트 RPC는 확인했고 포인터 경로는 별도 대기다.
- 의존성: P0-02.
- 근거: 정상 이동·장전·실행의 Maker 왕복과 실제 Lua의 잘못된 소유권·중복·오래된 요청 거절 회귀.
- 추가 근거: Maker 서버 문맥의 무송신자 RequestMove는 INVALID_SENDER로 거절됐다. 실제 클라이언트의 오래된 entry/context 요청은 무변경, 승인 이동 뒤 같은 요청 번호도 셀/턴 무변경이었다. IsValidPlayerRequest의 다른 UserId 거절도 확인했다. 다른 실제 계정에서 보낸 RPC나 다중 인스턴스 시험으로 확대하지 않는다.

### P0-04 큐 재타깃

상태: ✅ Tested

- 목표: 각 타일은 실행 순간의 CellIndex/Facing을 다시 판정한다.
- 구현: `BattleQueueLogic`→`SkillExecutionLogic`/Target Resolver→효과 실행기, HP/셀 상태는 Unit/Board 소유.
- 데이터/UI: 실제 스킬 데이터와 현재 기본 큐 3, 슬롯 6.
- 의존성: P0-02.
- 근거: Phase 1 Slice 9/10.5의 Maker Push 이후 베기 Miss, 통합 검증의 실제 제어 API, 최신 제어 20개·큐 14개 회귀.
- 완료 범위: Push 전후 셀과 순차 재타깃·경계/점유 계약. 실제 큐 드래그는 Phase 1의 포인터 확인으로 남는다.

### P0-05 UserDataSet 로드/검증

상태: 🟡 Implemented (untested)

- 목표: 문자열 변환과 참조 무결성, 제작자가 이해할 오류 위치를 증명한다.
- 구현: 실제 Definition Repository·Validator·Content Gate.
- 데이터: 정상 행과 고의 오류 행. UI는 없음.
- 근거: Phase 1 구현 기록의 Stage/Skill/Drop 실제 Dataset 로드, 누락 Stage·중복/없는 Drop 참조 차단 이력.
- 2026-10-12 Maker: WarriorSkillDefinitions 6행 la_mancha_spear의 Range=3 정상 검증, JSON 복제본 Range=0과 MatchCount=2를 각각 INVALID_SKILL_RANGE/DATA_DUPLICATE_SKILL_ID로 거절했다. 원본 Range=3·TestOverrideCount=0을 확인했다. 고의 오류의 Error 로그 2건은 정상 런 오류와 분리한다.
- 미충족 계약: ContentIntegrityValidatorLogic.AddError의 기본 DTO는 DataSetName/RowIndex/ContentId/DetailReason만 제공하며 Column/Value는 없다. 검사 스크립트가 출력한 column=Range/injected=0은 기본 진단 구현의 증거가 아니다. P0-05에서 기본 DTO·직렬화·관련 호출부/회귀에 열과 값을 연결해야 한다.
- 전체 데이터 오류 위치 계약은 아직 완료가 아니다. prototype의 startup gate 완화도 전체 콘텐츠 검증 통과로 취급하지 않는다.

### P0-06 통합 검증

상태: 🟡 Implemented (untested)

- 목표: P0-01~05의 완료 기준을 모아 최종 PASS/FAIL을 판정한다.
- 구현: 기존 실행 기록·회귀·문서 상태 대조.
- 데이터: 없음. UI: 실제 버튼/포인터 경로.
- 의존성: P0-01~05.
- 근거: 튜토리얼/세션/이동/보조 정리의 Maker·회귀 결과가 있다.
- 남은 완료 기준: P0-05의 Column/Value 진단 구현·검증과 실제 UI 입력. 양쪽 20전투 진행·기록 UI 및 재시작의 정상 로그는 확인했으나 오류 0이나 파일 존재만으로 전체 Phase를 완료하지 않는다.

## 판정 규칙

- 이 문서는 이미 실행된 기능을 미착수로 되돌리거나 새로운 맵 전환을 지시하지 않는다. 확인되지 않은 근거는 위 🟡 항목으로 남긴다.
- 실제 실패가 발견되면 해당 기능을 수정·재검증하고 의존 항목의 상태도 갱신한다.
- CoreVersion과 맵 타입은 현재 승인 기준을 따르고, 새로운 변경은 별도 범위다.
- 모든 항목이 ✅일 때만 GDD §9 미러→As-built→Roadmap→Phase 문서 정리 순서의 완료 절차를 수행한다. 현재는 그 조건을 만족하지 않으므로 Phase 0 문서를 유지한다.
