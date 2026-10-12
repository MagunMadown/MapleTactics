# 튜토리얼 오류 수정·전투 세션 책임 분리 검증

검증일: 2026-10-11\
브랜치: `codex/battle-session-responsibility-split`\
비교 기준: `2cec83a`\
API 기준: 사용자가 승인한 프로젝트 `CoreVersion 26.10.0.0`

튜토리얼 표시 오류를 수정하고 `NEXT_WORK_PLAN.md`의 BS-01~07 구현을 반영했다. 자동 회귀와 Maker에서 실행한 경로는 통과했다. 실제 포인터 드래그, 모든 전투맵의 화면·이동 체감, 모바일·다중 계정·발행 환경 검증은 남아 있다. 전체 GDD/Phase 완료를 뜻하지 않는다. 변경은 아직 커밋하지 않은 작업 트리에 있다.

## 1. 수정한 문제

기존 튜토리얼 회귀는 안내 함수가 이전 파일에 있다고 가정하고 4단계 계약을 검사했다. 로더를 현재 진입/규칙/표시 담당 로직으로 연결하고, 10단계·3웨이브·총 4마리·시작 포션·피해 제한 및 해제·완료 저장 계약으로 갱신했다. 실제 구현을 예전 계약으로 되돌리지 않았다.

Maker에서는 9단계 슬롯 이동 후 안내가 슬롯 1·2만 강조하고 키 안내도 1~6을 축약하는 오류를 재현했다. `TutorialPresentationLogic`은 실제 스킬 슬롯 1~6을 찾아 프레임과 키를 강조하도록 수정했다. 기존 강조 템플릿을 복제해 새 슬롯에 붙이고, 누락된 템플릿/대상은 안전하게 처리하며 결과·맵 이탈 시 색상과 크기를 복원한다. `KeyGuideHudComponent`는 안내 단계 1~9에서 여섯 키를 각각 표시하고 자유전투에서는 기존 축약 표시를 사용한다. `.ui/.model/.map` 변경은 없다.

## 2. 전투 세션의 최종 경계

`BattleSessionComponent`의 물리적 줄 수는 **7,320 → 2,745**다. 마지막 개행 뒤의 빈 토큰은 줄 수에 포함하지 않았다. 공개 메서드 **288개**의 반환형·이름·인자·ExecSpace를 유지했다. 단계별로 옮긴 **120개 본문**은 `self`를 `session`으로 바꾸는 차이를 제외하고 동일했다. 모든 추출 본문의 동일성을 주장하는 수치는 아니다. 비교 내역은 [source-boundary-verification.json](source-boundary-verification.json)에 있다.

| 작업 | 실제 구현 소유자 |
|---|---|
| BS-01 사망·승패·웨이브 정산 | `Resolvers/BattleOutcomeLogic` — 중복 사망, 드롭 정산, 지연 클리어, 보스 소환수 정리 |
| BS-02 제어·이동 규칙 | `Resolvers/BattleMovementLogic`, 기존 `PushEffectExecutorLogic`, `MoveSelfEffectExecutorLogic` — 밀치기/당기기/회전/돌진/강제 재배치 |
| BS-03 상태·특수 효과 | `EnemySpecialEffectExecutorLogic`, `CombatModifierEffectExecutorLogic`, `EffectRouterLogic` — 분류·실행·독 안개 생성/진행/정리 |
| BS-04 큐·퀵바 | `Skills/BattleQueueLogic`, `BattleQuickbarLogic` — 예약/취소/실행/재정렬 및 슬롯 데이터 |
| BS-05 모션·표시 | `BattleMotionCompletionLogic`, `BattleMovementPresentationLogic`, `BattleCombatPresentationLogic` — 완료 영수증/게이트, 이동·타격·효과·카메라 표시 |
| BS-06 진입·결과·DTO·소모품 | `BattleEntryLogic`, `BattleResultLogic`, `BattleConsumableLogic`, 기존 `BattleUiStateLogic` — Gateway/Run/소모품 구현 재사용 |
| BS-07 남은 기능·전체 경계 | `BattleActionLogic`, `EnemyBossMechanicLogic`, 기존 스킬/타깃/적 계획/증강/연습 담당 로직 — 즉시 행동, 보스 착지·페이즈, 좌표·쿨다운·테스트 설정 |

세션은 호출과 인자/결과 전달, 상태 동기화, 생명주기 및 RPC 요청 검증을 소유한다. `senderUserId`는 RPC 경계에 남겼고 내부 로직에는 명시적인 수신자 인자를 전달한다. 소유권·현재 맵·진입·턴·셀·요청 순서·결과 준비 검증을 유지했다. 새 `@Logic`은 세션을 인자로 받아 처리하며 전투별 상태를 전역 필드에 저장하지 않는다. 새 14개 `.mlua`의 `.codeblock`은 Maker Refresh로 생성했다.

`OnUpdate`의 진입 정책은 `BattleEntryLogic.UpdateEntryPolicy`로 옮기고 초기 반환 순서와 0.15초 폴링을 유지했다. 세션의 표시 갱신과 생명주기 연결은 남겼다. 일반 이동은 기존 `PlayerGridMovementLogic`의 클라이언트 루트 이동, 0.5초 착지 유예와 0.05 월드 단위 허용 오차를 계속 공유한다. 로비/전투용 재생 구현을 복제하지 않았다.

## 3. 자동 회귀

최종 코드에서 **18개 모음 모두 종료 코드 0**. 기존 전투 194개 그룹 + 새 분리 회귀 91개 그룹 = **285개 그룹**이며 튜토리얼 2개 모음은 별도로 집계한다. `new-player-tutorial`이 내부 실행하는 Union 10개 그룹을 285개에 중복 합산하지 않았다. [regression-results.json](regression-results.json)에 각 명령의 stdout/stderr와 종료 코드가 있다.

| `Artifacts/tests/` 모음 | 그룹 | 결과 |
|---|---:|---|
| utility-skill-execution-test.py | 18 | 통과 |
| battle-damage-test.py | 19 | 통과 |
| skill-execution-test.py | 21 | 통과 |
| grid-movement-latency-test.py | 37 | 통과 |
| battle-motion-gate-test.py | 33 | 통과 |
| battle-ui-state-test.py | 11 | 통과 |
| enemy-plan-snapshot-test.py | 12 | 통과 |
| enemy-planning-test.py | 14 | 통과 |
| enemy-turn-execution-test.py | 21 | 통과 |
| hud-map-lifecycle-test.py | 8 | 통과 |
| battle-outcome-test.py | 12 | 통과 |
| battle-control-movement-test.py | 20 | 통과 |
| battle-status-effects-test.py | 14 | 통과 |
| battle-queue-test.py | 14 | 통과 |
| battle-entry-result-test.py | 15 | 통과 |
| battle-session-boundary-test.py | 16 | 통과 |
| new-player-tutorial-test.py | 별도 모음 | 통과 |
| tutorial-dodge-highlight-test.py | 별도 모음 | 통과 |

공통 fixture `battle_refactor_fixture.py`가 실제 담당 로직의 Lua 본문을 로드한다. 새 회귀는 중복 정산·yield 중 재진입·잘못된 소유권·오래된 콜백·두 세션의 상태 분리·예약/재정렬·강제 이동 취소·진입/결과 실패 후 재시도 등을 검사한다. 단순 위임 문자열 검사로 동작 검증을 대체하지 않았다.

재실행 예시(저장소 루트에서 실행):

```bash
LUPA_PATH=/private/tmp/mapletactics-landing-lupa python3 Artifacts/tests/battle-session-boundary-test.py
LUPA_PATH=/private/tmp/mapletactics-landing-lupa python3 Artifacts/tests/new-player-tutorial-test.py
node tools/check-balance-vocab.cjs
git diff --check
```

표의 각 Python 파일을 같은 방식으로 실행한다. Lupa의 임시 설치 경로는 이번 머신 기준이며 다른 머신에서는 설치된 경로로 바꾼다. Balance vocabulary 검사와 diff 공백 검사는 통과했다. 닫힌 값·CSV·카탈로그 변경은 없다.

## 4. LSP·Maker 빌드

수정/신규 production `.mlua` **26개**의 LSP 진단을 확인했다. 25개는 오류 0, 경고 0이다. `TutorialPresentationLogic`의 다음 2개 오류는 변경 전 본문과 위치·메시지가 동일하다. 임시 기준 파일의 이름 때문에 추가된 script-name mismatch는 기준 비교에서 제외했다. [lsp-verification.json](lsp-verification.json)에 비교 근거가 있다.

- 9행: `'TextGUIRendererComponent' type is unavailable.`
- 195행: `'BattleUnitPresentationComponent' type not found.`

이 때문에 **LSP 전체 오류 0으로 판정하지 않는다**. 타입을 `any`로 바꾸어 진단을 숨기지도 않았다. 실제 Maker Refresh 후 빌드 오류는 0이었다. 응답 count 1,040 중 보존한 Warning은 기존 `IsPCPlatform()` 폐기 예정 경고 1건이다. [final-build-verification.json](final-build-verification.json)은 그 경고를 보존한다. 빈 빌드 콘솔만으로 성공을 판정하지 않고 아래 실제 실행 로그도 확인했다.

문서 정리 후 편집 모드에서 Refresh를 다시 호출했다. 빌드 콘솔은 0건, 기존 normal 콘솔은 Info 153건·Warning/Error 0건이었다. 새 Play 라운드를 실행한 결과는 아니다. Balance vocabulary와 diff 공백 검사도 다시 통과했으며 [final-checks.json](final-checks.json)에 저장했다.

## 5. Maker 실행 검증

Maker MCP로 `stop → refresh → logs(build) → play → keyboard_input/클라이언트 RPC/실제 API → logs(normal) → stop`을 수행했다. 입력에 따른 경로와 검증 스크립트가 실제 API를 직접 호출한 경로를 구분한다. 일부 JSON은 전체 응답의 count/counts와 선별 로그를 함께 보존하며, 최종 로비·연습 전투 JSON은 해당 라운드의 전체 로그다. 이전 단계 검증을 최종 코드 전체 검증으로 바꾸어 표현하지 않는다.

### 최종 코드 튜토리얼

[final-tutorial-runtime-verification.json](final-tutorial-runtime-verification.json)에 21:17~21:28 최종 재플레이를 기록했다. 완료 계정의 자동 진입 제외와 명시적 `BeginEntry(true)` 허용을 실제 API로 확인했다. 1~9단계는 `D → Alpha1 → A → D → Space → Alpha2 → Space → F1 → Alpha1 → S` 등의 실제 키 입력으로 이동·장전·회피·실행·포션·가드 순서와 큐 유지를 확인했다. 9단계 예약 취소도 키로 확인했다.

슬롯 1→3, 2→6은 실제 클라이언트 재정렬 RPC로 이동했다. `caps=6`, 실제 슬롯 문자열 `||brandish|||divine_swing` 및 활성 안내 키가 새 슬롯을 따라가는 로그를 확인했다. `Alpha3/Alpha6/Space`로 9단계를 마치고 10단계 자유전투를 진행했다. 최종 로그는 `step=10`, `wave=3`, `kills=4`, `phase=BattleEnded`, `result=Victory`, HP 6이다. 결과 확인은 실제 클라이언트 `RequestContinueResult` RPC로 수행했고 `[Tutorial] completion saved`, `saved=true map=lobby`를 확인했다. 쿨다운 중 장전 거절과 빈 큐 실행 거절도 정상 규칙으로 유지됐다.

첫 완료 저장은 앞선 [tutorial-input-verification.json](tutorial-input-verification.json)의 격리 키 `UnionProfile:VerifyTutorial20261011A`에서 `isolatedBefore=false → 4 kills → saved=true`로 확인했다. 최종 재플레이는 같은 키의 `isolatedBefore=true`에서 시작했다. 실제 계정의 완료 기록을 초기화하지 않았다. 앞선 [outcome-defeat-verification.json](outcome-defeat-verification.json)은 실제 피해/결과 API로 패배·로비 복귀·재도전 안내를 확인한 것이며 Retry 버튼 포인터 입력 검증은 아니다.

최종 튜토리얼 응답에는 Info 2,803, Warning 1, Error 1이 있었다. Warning은 기존 UnionReward migrated run id 로그다. Error는 **로비 복귀 후 검증용 MakerScript가 존재하지 않는 전투 세션 `s`를 읽은 오류**다. 제품 호출 스택은 없으며 세션 존재 여부를 검사하도록 관찰 코드를 고쳤다. 따라서 이 응답 전체를 오류 0이라고 하지 않는다.

### 최종 로비·연습 전투

| 시나리오 | 실행·양성 증거 | 결과 |
|---|---|---|
| 로비 경계 이동 | 실제 `A` 반복 입력으로 왼쪽 경계 도달·추가 이동 차단. 서버/클라이언트 X `-34.088600158691`; 이동/착지 대기 없음, 튜토리얼 활성 키 0 | [final-lobby-runtime-verification.json](final-lobby-runtime-verification.json): Info 35, Warning/Error 0 |
| 순간이동 후 일반 이동 | `skill_test`의 실제 설정 API로 플레이어 0·적 4·마법사 유틸리티 준비. 실제 `S`로 0→3 순간이동, `A`로 3→2 일반 이동. 서버/클라이언트 cell 2·X 0, PlayerTurn·turn 5, move/landing false | [final-practice-runtime-verification.json](final-practice-runtime-verification.json): Info 133, Warning/Error 0 |
| 일반 모드 진입·DTO | 같은 최종 연습 라운드에서 entry 9500001·HP 10·wave 1·소모품 항목 0 및 진행 DTO 확인. `TutorialActive=false`, `TutorialStep=0` | `[VerifyEntry] NORMAL_MODE_PASS tutorial=false step=0` |
| 보스 착지 겹침 | 실제 보스 API 검증. 더미의 보스 속성을 일시 적용하고 원래 값 복원. 플레이어 0→1 밀림 후 적 4→0 착지, takeoff 때 고정한 landing 0 유지 | `[VerifyBoundary] BOSS_LANDING_PASS player=1 enemy=0 frozenLanding=0` |

최종 검증 후 Maker는 실제 `stop` 호출로 편집 모드에 돌려놓았다. 로비/연습 전투에서 최종 셀·위치·상태를 확인한 결과이며 모든 맵의 카메라·이름표·HP 표시 체감이나 GPU FPS 측정 결과는 아니다.

### 단계별 보강 검증과 관찰 오류

- [control-api-verification.json](control-api-verification.json): 실제 push/pull/회전/HEAVY/경계/부호 있는 이동·강제 취소 API, 이후 새 `A` 입력의 서버·클라이언트 cell 2 확인. 앞선 입력 시점의 조기 관찰 assertion 2건은 따로 분류했다.
- [status-runtime-verification.json](status-runtime-verification.json): 실제 Router 경로의 frostbite/seal/confusion 저항·독 안개 2회 tick/만료·이동 독·stun, `[VerifyStatus] ROUTER_PASS`. 응답 Info 628, Warning/Error 0.
- [queue-runtime-verification.json](queue-runtime-verification.json): 실제 키·슬롯 RPC 후 3/6 키 사용, 안내 여섯 키와 자유전투 축약 두 키, Wave 3 전이. 실제 포인터 드래그가 아니다.
- [motion-runtime-verification.json](motion-runtime-verification.json): receipt/epoch 완료 게이트와 표시 경로. 당시 `A`는 cell 0 경계에서 거절됐고 공격도 miss 경로였다. 승인된 이동/순간이동의 근거는 최종 연습 라운드를 사용한다.
- [entry-runtime-verification.json](entry-runtime-verification.json): 일반 연습 진입의 entry/HP/wave/진행·소모품 DTO. 실제 서비스 실패 주입은 아니다.
- [lobby-observer-correction.json](lobby-observer-correction.json): 검증 스크립트가 로비 범위의 기본값을 실제 맵 override로 잘못 가정해 assertion 2건 발생. 실제 MinX `-35.06`, MaxX `-17.14`로 관찰 기준을 바로잡고 최종 경계 라운드를 다시 실행했다.
- [practice-observer-correction.json](practice-observer-correction.json): 검증 스크립트가 `TutorialActive` 대신 없는 `TutorialMode`를 검사해 assertion 1건 발생. 올바른 필드로 수정한 최종 라운드에서 통과했다.

이전 관찰/설정 오류 자료도 삭제하지 않았다. 단순히 로그를 지우고 전체 실행이 무오류였다고 보고하지 않는다.

## 6. 남은 사용자 검증과 작업 상태

`NEXT_WORK_PLAN.md`에서 TUT-01~03과 BS-01/02/03/06은 ✅, TUT-04/05와 BS-04/05/07은 🟡다. 모든 구현과 자동/실행 검증 결과를 기록한 상태이며 다음 실제 입력·실기기 검사가 남아 있다.

1. PC 포인터로 슬롯 1→3·2→6 드래그, 큐 예약 취소·재정렬, 결과 버튼·메뉴 다시 하기·패배 Retry 버튼을 조작한다. 새 슬롯 프레임/키 안내가 따라가고 복귀 시 사라지는지 확인한다. Maker `mouse_input`은 PC 마우스 `KeyDownEvent`를 발생시키지 않고 native CUA drag도 `noWindowsAvailable`로 실패해 RPC까지만 검증했다.
2. 로비와 **각 전투맵**에서 좌/우 단발·연속·빠른 반전·착지 직후 입력·점유 셀·경계·맵 전환을 비교한다. 스킬/강제 이동 후 복귀와 카메라·이름표·HP 표시 떨림을 화면에서 확인한다. 이번 `skill_test` 결과를 다른 전투맵의 체감 통과로 확장하지 않는다.
3. 실제 저장/전송 실패 재시도, 다중 계정·인스턴스, 모바일·발행 환경을 확인한다. 실패·오래된 결과·세션 분리의 오프라인 계약은 통과했지만 실제 서비스 장애와 네트워크 조건은 주입하지 않았다.

GDD·Phase·Roadmap의 게임 전체 기능 검증 상태는 이 구조 분리 결과만으로 올리지 않았다. 모든 실제 완료 기준을 만족할 때 남은 🟡를 ✅로 갱신한다.
