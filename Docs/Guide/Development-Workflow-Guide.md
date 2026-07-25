# MapleTactics 공동 개발 워크플로 가이드

## 0. 목적

이 문서는 사람 개발자와 AI 개발 도구가 같은 구조와 순서로 MapleTactics를 확장하기 위한
작업 규칙이다. 상태 소유권과 데이터 규격은
[`Architecture-Standard-v0.1.md`](./Architecture-Standard-v0.1.md)를 기준으로 하며,
이 문서는 실제 작업을 어디서 시작하고 어떤 파일을 수정하며 어떻게 검증할지를 정한다.

규칙의 우선순위는 다음과 같다.

1. MSW 플랫폼과 Maker 규칙
2. `Architecture-Standard-v0.1.md`
3. 이 문서
4. 기능별 Guide
5. 개별 구현 메모

규칙이 충돌하면 상위 문서를 따른다. 구현과 문서가 다르면 임의로 한쪽을 선택하지 말고
현재 Maker 동작과 상태 소유자를 확인한 뒤 같은 작업에서 문서도 갱신한다.

## 1. 작업 시작 전 필수 읽기

모든 작업자는 다음 순서로 문서를 읽는다.

1. [`Architecture-Standard-v0.1.md`](./Architecture-Standard-v0.1.md)
2. 이 문서
3. 작업 영역별 Guide

| 작업 영역 | 추가로 읽을 문서 |
|---|---|
| 외부 화면에서 전투 진입 | [`Battle-Integration-API.md`](./Battle-Integration-API.md) |
| Stage·Wave 데이터 | [`Stage-Authoring-Guide.md`](./Stage-Authoring-Guide.md), [`Battle-Wave-Guide.md`](./Battle-Wave-Guide.md) |
| Skill·Effect Step | [`Skill-Authoring-Guide.md`](./Skill-Authoring-Guide.md) |
| 새 EffectType | [`Effect-Executor-Guide.md`](./Effect-Executor-Guide.md) |
| Turn·행동 큐 | [`Battle-Turn-Guide.md`](./Battle-Turn-Guide.md) |
| Cooldown | [`Cooldown-Runtime-Guide.md`](./Cooldown-Runtime-Guide.md) |
| 전투 코어 사용법 | [`Battle-Core-Quick-Guide.md`](./Battle-Core-Quick-Guide.md) |

## 2. 현재 병렬 개발 가능 범위

| 영역 | 상태 | 병렬 개발 규칙 |
|---|---|---|
| UI·HUD·모션·이펙트 교체 | 가능 | 서버 판정 상태를 직접 변경하지 않는다. |
| Enemy Definition·Spawn Pool | 가능 | Dataset과 Repository 계약만 사용한다. |
| Stage 1 밸런스 | 가능 | 공용 Session 코드가 아니라 데이터에서 변경한다. |
| 기존 `DAMAGE`·`PUSH` 조합 Skill | 제한적 가능 | 현재는 호환 Definition이 있으므로 실제 Skill Dataset 전환 상태를 먼저 확인한다. |
| Stage 2 이상 | 조건부 | `StageDefinitions` 실제 Dataset 행과 Validator 검증을 먼저 준비한다. |
| 새 적 AI·패턴 | 조건부 | 현재 Intent가 Session에 있으므로 담당자를 한 명으로 제한하거나 Intent 분리 후 병렬화한다. |
| 직업·아이템·증강 | 대기 | Modifier 계약과 실행 파이프라인을 먼저 구현한다. |
| `BattleSessionComponent` 변경 | 제한 | 전투 코어 담당자 또는 사전 영향도 검토를 통과한 작업만 허용한다. |

### 2.1 현재 부족한 항목

기준일은 `2026-07-26`이다. 아래 항목은 규격만 있거나 호환 구현에 의존하므로 완료된
기능으로 취급하지 않는다.

| 우선순위 | 부족한 항목 | 현재 영향 | 완료 조건 |
|---|---|---|---|
| P0 | `StageDefinitions` 실제 Dataset 없음 | Stage 2부터 호환값 없이 시작할 수 없음 | `.userdataset/.csv` 페어 생성, `stage01` 이관, `source=DATASET`, fallback 비활성 검증 |
| P0 | `SkillDefinitions`, `SkillEffectSteps` 실제 Dataset 없음 | 신규 Skill을 데이터만으로 대량 제작할 수 없음 | 두 Dataset 페어 생성, 호환 Skill 4개 이관, 회귀 검증, fallback 비활성 |
| P0 | Enemy Intent가 Session에 남아 있음 | 여러 적 패턴 개발자가 Session에서 충돌할 수 있음 | Intent 상태 소유자와 Resolver 분리, 기존 적 행동 회귀 검증 |
| P1 | `BattleSessionComponent`가 2,600줄 이상 | 이동·공격·Spawn·Intent 변경 충돌 가능성이 큼 | 행동 조정·Intent·Spawn 책임을 공개 계약 단위로 단계적 분리 |
| P1 | 공용 Client 전투 상태 접근 API 없음 | HUD마다 `BattleTurnState`·`BattleWaveState` 조회 코드를 반복함 | 공용 Client accessor 도입 또는 표준 조회 코드 확정 |
| P1 | Modifier 실행 파이프라인 없음 | 직업·아이템·증강을 일관된 방식으로 추가할 수 없음 | Modifier Context, 적용 순서, 중첩 규칙과 빈 파이프라인 구현 |
| P1 | StageId → 실제 Map/Instance 연결 없음 | 로비에서 Stage별 전투 맵으로 자동 이동할 수 없음 | Map Flow 계약과 Gateway 연동 |
| P2 | 자동 회귀 테스트 없음 | 현재 회귀 검증이 Maker 수동 스크립트와 로그에 의존함 | 최소 Stage 시작·강제 증원·Wave 전환·Skill Cooldown 검증 자동화 |
| P2 | 전투 코어 담당자와 잠금 수단 미지정 | Session 동시 수정 제한을 문서만으로 강제할 수 없음 | 팀 작업 도구에서 Owner와 `[CORE-LOCK]` 절차 운영 |

현재 Gate 상태:

| Gate | 상태 | 비고 |
|---|---|---|
| Gate A | 열림 | UI·Presentation, Enemy 데이터, Stage 1 조정 |
| Gate B | 닫힘 | Stage·Skill 실제 Dataset 3종이 아직 없음 |
| Gate C | 닫힘 | Enemy Intent 분리 전 |
| Gate D | 닫힘 | Modifier 계약 구현 전 |

### 2.2 부족 항목을 다루는 규칙

- P0 항목을 우회하기 위한 새 하드코딩이나 compatibility fallback을 추가하지 않는다.
- 부족 항목을 해결하는 작업은 구조 변경으로 분류하고 Architecture와 본 표를 함께 갱신한다.
- Gate가 열리면 `상태`, 완료 로그, fallback 제거 여부를 같은 변경에서 기록한다.
- 새 기능 개발 중 추가 구조 공백을 발견하면 임시 구현 전에 이 표에 영향과 완료 조건을
  먼저 추가한다.

## 3. 공통 설계 규칙

### 3.1 상태는 한 곳만 소유한다

- Turn·Phase·행동 큐는 `BattleTurnComponent`가 소유한다.
- Wave·증원 예약·Wave Timer는 `BattleWaveComponent`가 소유한다.
- 보드 Registry와 Cell 점유는 `BoardStateComponent`가 소유한다.
- 유닛 HP·Cell·Facing·IsDead는 `BattleUnitComponent`가 소유한다.
- Skill Cooldown은 각 유닛의 `SkillRuntimeStateComponent`가 소유한다.
- 전투 결과와 전체 흐름 조정은 `BattleSessionComponent`가 담당한다.

Session의 기존 Turn/Wave `@Sync` 필드는 호환 Snapshot이다. 신규 기능은 이 필드를 직접
대입하지 않는다. 반드시 소유 컴포넌트의 공개 메서드를 호출하고 필요한 경우 Session의
`PublishTurnStateSnapshot()` 또는 `PublishWaveStateSnapshot()` 경계에서 복사한다.

### 3.2 호출 방향을 지킨다

```text
UI / 외부 시스템
→ Request 또는 Gateway API
→ BattleSession 조정
→ Turn / Wave / Board / Unit 상태 API
→ Resolver / SkillExecution
→ EffectRouter
→ Executor
→ 동기화 상태
→ UI 표시
```

- UI는 HP, Turn, Wave를 직접 계산하지 않는다.
- Repository는 Runtime Entity나 Timer를 보관하지 않는다.
- Executor는 다른 Executor를 직접 호출하지 않는다.
- Presentation은 서버 판정 결과를 변경하지 않는다.
- 일반 콘텐츠 추가를 위해 Session 조건문을 늘리지 않는다.

### 3.3 MSW 파일 규칙을 지킨다

- `.mlua`는 `RootDesk/MyDesk/` 아래에 둔다.
- `.mlua`와 Maker가 생성한 `.codeblock` 페어를 함께 전달한다.
- `.codeblock`은 직접 수정하지 않는다.
- `.model`, `.map`, `.ui`는 전용 Builder를 사용한다.
- `Global/`과 `Environment/`는 읽기 전용이다.
- Runtime Spawn의 parent는 nil이 아니라 대상 Map Entity를 전달한다.
- 현재 전투 맵은 `MapleTile(TileMapMode=0)`이며 동적 플레이어 Body는
  `RigidbodyComponent` 규칙을 따른다.

## 4. 파일과 책임 소유권

| 경로 또는 파일 | 주 담당 | 허용되는 변경 | 금지되는 변경 |
|---|---|---|---|
| `BattleSessionComponent.mlua` | 전투 코어 | 공개 명령 조정, 승패, Spawn 연결 | 콘텐츠 하나를 위한 하드코딩, Turn/Wave 원본 상태 재도입 |
| `BattleTurnComponent.mlua` | Turn·Queue | Phase와 큐 정책 | 피해·타깃·Wave 규칙 |
| `BattleWaveComponent.mlua` | Wave | Wave 상태와 Timer 정책 | 적 Definition 해석, 실제 피해 |
| `BoardStateComponent.mlua` | Board | Registry와 점유 조회 | 전투 승패, Skill 규칙 |
| `BattleUnitComponent.mlua` | Unit | 유닛 Runtime 상태와 최소 상태 API | Stage 전역 상태 |
| `SkillRuntimeStateComponent.mlua` | Skill Runtime | Cooldown 저장·검사·감소 | Skill 효과 계산 |
| `03_Data/Repositories/` | 콘텐츠 데이터 | 조회·변환·검증 | Runtime Entity와 Timer 저장 |
| `01_Combat/Skills/` | Skill 실행 | Definition 실행과 Effect Context 조정 | UI 표시, Stage 하드코딩 |
| `01_Combat/Resolvers/` | 판정·Router | 결정적 계산과 Effect 라우팅 | 장기 Runtime 상태 |
| `05_UI/`과 `ui/` | UI | 상태 표시와 Request 전송 | 서버 전투 상태 직접 대입 |
| `Docs/Guide/` | 공동 규격 | API·책임·작업 절차 갱신 | 실제 구현과 다른 미래 상태를 구현됨으로 표기 |

같은 작업에서 두 명 이상이 `BattleSessionComponent.mlua`를 수정하지 않는다. Session 변경이
필요한 작업은 먼저 공개 메서드 추가만으로 해결 가능한지 검토하고, 불가능할 때만 담당자가
수정한다.

전투 코어 담당자가 아직 지정되지 않은 동안에는 다음 임시 절차를 사용한다.

1. 작업 Task 또는 PR 제목에 `[CORE-LOCK] BattleSession`을 붙인다.
2. 영향도 양식과 수정 예정 메서드를 먼저 기록한다.
3. 같은 잠금을 가진 진행 중 작업이 있으면 병합 또는 순서를 합의하기 전까지 수정하지 않는다.
4. 완료 시 잠금을 해제하고 인수인계에 변경 API와 남은 호환 항목을 기록한다.

## 5. 기능 개발 표준 순서

### 5.1 작업 분류

작업을 시작할 때 다음 중 하나로 분류한다.

- 콘텐츠 추가: 기존 스키마와 Executor만 사용
- 기존 기능 확장: 공개 API와 Repository 필드 확장
- 새 규칙 추가: 새 EffectType, Resolver 또는 상태 소유자 필요
- 구조 변경: 상태 소유권이나 호출 방향 변경

콘텐츠 추가가 Session 수정으로 이어지면 분류가 잘못된 것이다. 먼저 Definition이나
Executor 조합으로 해결 가능한지 다시 검토한다.

### 5.2 영향도 작성

구현 전에 최소한 다음 내용을 기록한다.

```text
목표:
단일 상태 소유자:
입력 API:
변경 파일:
읽기만 하는 파일:
추가 또는 변경하는 Definition:
기존 저장 데이터 영향:
UI 영향:
검증할 성공 경로:
검증할 실패 경로:
```

구조 변경 작업은 `호출자 → 변경 API → 상태 소유자 → UI 소비자` 순서로 영향도를 적는다.

### 5.3 데이터와 계약을 먼저 만든다

1. ID와 스키마를 정의한다.
2. Repository 변환과 Validation을 추가한다.
3. 기존 API로 실행할 수 있는지 확인한다.
4. 필요한 경우에만 Resolver 또는 Executor를 추가한다.
5. Session은 새 구현을 조정하는 최소 호출만 추가한다.
6. 마지막에 UI와 Presentation을 연결한다.

### 5.4 작은 기능 단위로 완료한다

한 작업은 다음 범위를 넘기지 않는 것을 권장한다.

- Definition 한 종류
- 공개 API 한 경계
- EffectType 한 종류
- HUD 표시 한 묶음
- Stage 한 개의 검증 가능한 Slice

대규모 구조와 콘텐츠를 한 작업에서 동시에 변경하지 않는다.

## 6. 영역별 추가 절차

### 6.1 Stage 개발

1. `StageDefinitions`에 Stage 행을 추가한다.
2. `StageEnemyWaves`, `EnemySpawnPools`, `EnemyDefinitions` 참조를 연결한다.
3. `ContentValidatorLogic.ValidateStageById()`를 통과시킨다.
4. `BattleSessionComponent`를 수정하지 않고 `StartStageById()`로 실행한다.
5. Wave 전멸 전환과 강제 증원 조건을 각각 검증한다.

Stage 2부터는 `stage01` 전용 compatibility fallback을 복사하지 않는다.

### 6.2 Skill 개발

1. `SkillDefinitions`에 Skill 행을 추가한다.
2. `SkillEffectSteps`에 `StepIndex` 순서로 Effect를 추가한다.
3. 기존 `DAMAGE`와 `PUSH` 조합으로 구현 가능한지 확인한다.
4. `ContentValidatorLogic.ValidateSkillById()`를 통과시킨다.
5. Cooldown 0과 1 이상을 각각 검증한다.
6. 모션과 UI는 `SkillId` 또는 Profile ID로 연결한다.

스킬마다 새 클래스를 만들거나 Session에 `if skillId == ...` 분기를 추가하지 않는다.

### 6.3 새 EffectType 개발

1. Effect Context 입력과 결과를 문서로 정한다.
2. 원자적인 Executor 하나를 추가한다.
3. `EffectRouterLogic`에 등록한다.
4. 단일 Step과 복수 Step 조합을 검증한다.
5. 실패 Reason과 로그를 추가한다.
6. [`Effect-Executor-Guide.md`](./Effect-Executor-Guide.md)를 갱신한다.

### 6.4 UI 개발

1. 읽을 상태 컴포넌트를 정한다.
2. UI 변경 요청은 Session 또는 Gateway 공개 API로 보낸다.
3. `.ui`는 UI Builder로 수정한다.
4. 해상도와 Anchor/Pivot을 확인한다.
5. ClientOnly API와 서버 상태 변경을 섞지 않는다.

### 6.5 전투 코어 변경

다음 중 하나에 해당할 때만 전투 코어 변경으로 분류한다.

- 상태 소유자가 바뀐다.
- 공개 Request/API 의미가 바뀐다.
- Turn·Wave 전환 순서가 바뀐다.
- 기존 저장 데이터와 호환되지 않는다.
- 세 영역 이상이 동시에 영향을 받는다.

전투 코어 변경은 구현 전에 Architecture 문서와 영향도 표를 먼저 갱신한다.

## 7. 현재 구조의 개발 Gate

### Gate A — 현재 바로 가능

- UI·Presentation 교체
- Enemy Definition과 Spawn Pool 추가
- Stage 1 데이터 조정
- 기존 Effect 조합의 기능 검증

### Gate B — 실제 Dataset 전환 후

- Stage 2 이상 병렬 제작
- 신규 Skill 대량 제작

필요한 실제 Dataset:

- `StageDefinitions`
- `SkillDefinitions`
- `SkillEffectSteps`

Dataset 전환이 끝나면 compatibility fallback을 끄고 누락 행이 Validation 실패가 되는지
확인한다.

### Gate C — Intent 분리 후

- 다수의 적 패턴 개발자 투입
- 보스 Phase와 복합 적 행동
- 적 공격 준비 큐의 독립 UI 확장

### Gate D — Modifier 계약 구현 후

- 직업별 패시브
- 아이템 효과
- 증강 효과
- 상태이상과 조건부 수치 변경

Gate가 열리기 전에 해당 콘텐츠를 각자 다른 방식으로 구현하지 않는다.

## 8. AI 작업 요청 규격

다른 AI에 작업을 맡길 때 다음 템플릿을 사용한다.

```text
작업 목표:
작업 분류: 콘텐츠 추가 / 기능 확장 / 새 규칙 / 구조 변경
반드시 읽을 문서:
단일 상태 소유자:
수정 허용 파일:
수정 금지 파일:
사용할 공개 API:
추가할 Definition 또는 ID:
호환 유지 대상:
Maker 검증 항목:
완료 후 갱신할 Guide:
```

AI에 “전투 기능 추가”처럼 넓은 요청만 전달하지 않는다. 상태 소유자와 수정 허용 파일을
명시하지 못했다면 구현보다 영향도 분석을 먼저 요청한다.

AI가 지켜야 할 최소 규칙:

- 기존 파일과 Guide를 읽기 전에 새 구조를 만들지 않는다.
- Session의 호환 Snapshot을 원본 상태로 사용하지 않는다.
- `.codeblock`을 직접 수정하지 않는다.
- `.map`, `.model`, `.ui`를 원시 JSON으로 수정하지 않는다.
- Maker 실행 없이 “동작 확인”이라고 보고하지 않는다.
- 기존 사용자 변경을 덮어쓰지 않는다.

## 9. Git과 인수인계

### 9.1 작업 단위

- 한 브랜치는 하나의 기능 Slice를 다룬다.
- 구조 변경과 콘텐츠 대량 추가를 같은 커밋에 섞지 않는다.
- `.mlua`가 새로 생기면 Maker가 만든 `.codeblock` 페어도 함께 포함한다.
- 관련 Guide와 구현 계획 체크 항목을 같은 작업에서 갱신한다.

### 9.2 인수인계 내용

```text
변경 결과:
상태 소유자:
추가·변경한 공개 API:
추가·변경한 Dataset/ID:
호환 Snapshot 또는 fallback:
Maker Build 결과:
Maker Runtime 성공 경로:
Maker Runtime 실패 경로:
남은 제한:
```

## 10. 검증 기준

모든 구현 작업은 다음 순서로 검증한다.

1. Maker 편집 모드에서 Workspace Refresh
2. Build Console의 Error와 Warning 확인
3. Play 시작
4. 정상 경로 실행
5. 잘못된 ID·상태·입력의 실패 경로 실행
6. 서버와 클라이언트 Runtime Error 확인
7. Reset 또는 Map 종료 시 Timer와 Runtime Entity 정리 확인
8. Play 종료 후 편집 모드 복귀
9. 관련 Guide와 구현 계획 갱신

성공 로그에는 최소한 Definition ID, 상태 전환, 결과를 포함한다. 실패 로그에는 Reason ID와
입력 ID를 포함한다.

## 11. 완료 조건

기능은 다음 조건을 모두 만족해야 완료다.

- 상태 소유자가 하나다.
- 공개 API를 통해서만 상태가 변경된다.
- 데이터 작업이면 ID와 참조가 Validator를 통과한다. 해당하지 않으면 `N/A` 사유를
  인수인계에 기록한다.
- 정상 경로와 실패 경로가 Maker에서 검증됐다.
- Reset과 종료 시 Timer·Entity가 정리된다.
- UI가 서버 판정 상태를 직접 변경하지 않는다.
- `.mlua/.codeblock` 페어와 관련 데이터가 전달 대상에 포함됐다.
- Architecture 또는 기능별 Guide가 현재 구현과 일치한다.
- 다음 개발자가 수정해야 할 위치와 금지 영역을 문서만 보고 판단할 수 있다.
