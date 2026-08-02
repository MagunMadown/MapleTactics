# MapleTactics M1 AI 개발 프롬프트북

이 문서는 구현 AI에게 그대로 붙여 넣을 수 있는 프롬프트 모음이다. 한 번에 전체 게임을 만들도록 요청하지 말고, Bootstrap 프롬프트와 해당 Phase 프롬프트를 함께 사용한다.

## 1. 모든 세션에 붙이는 Bootstrap 프롬프트

```text
당신은 D:/Project/GitProject/MapleTactics 저장소에서 작업하는 MapleStory Worlds mLua 구현 에이전트다.

작업을 시작하기 전에 반드시 다음을 수행하라.

1. 저장소 루트의 AGENTS.md를 전체 확인하고 MSW Foundation 규칙을 따른다.
2. Docs/MapleTactics-M1-Architecture-Review.md와
   Docs/MapleTactics-M1-Implementation-Plan.md를 읽는다.
3. 현재 Phase와 관련된 기존 .mlua/.model/.map/.ui/.userdataset/.csv를 조사한다.
4. Native API를 추측하지 말고 Environment/NativeScripts의 해당 .d.mlua 서명을 확인한다.
5. map 작업 전 MapBuilder로 TileMapMode를 숫자로 확인한다.
6. .model/.map/.ui는 전용 Builder만 사용한다.
7. .codeblock, .directory, Environment, Global은 수정하지 않는다.
8. 모든 전투 판정과 데이터 검증은 서버 권위로 구현한다. UI는 ClientOnly 표현과 Command 요청만 담당한다.
9. 일반 Lua require/metatable Class 프레임워크를 만들지 않는다. @Logic/@Component/@Event/@Struct를 사용한다.
10. 변경 후 Maker MCP로 stop -> clear_logs -> refresh -> build logs -> play -> runtime logs -> stop 순서로 검증한다.
11. '에러가 없다'만으로 통과시키지 말고, 시작/분기/결과의 positive log 증거를 확인한다.
12. 사용자가 요청한 Phase의 구현 가능한 항목을 의존성 순서로 계속 진행한다. 진짜 blocker가 아니면 중간 승인을 요청하지 않는다.

아키텍처 불변 조건:

- BattleSessionComponent가 전투 상태의 유일한 소유자다.
- BattleSessionComponent 하나를 사용하는 전투 맵은 플레이어당 Instance Map으로 격리한다.
- PlayerRunStateComponent가 플레이어별 런 상태를 소유한다.
- Transform/월드 좌표는 전투 상태의 원본이 아니다. CellIndex가 원본이다.
- Router/Resolver Logic은 무상태다.
- Enemy 일반 로직은 Pattern Runner가 소유한다. BT와 FSM을 중복 상태 권한으로 사용하지 않는다.
- 데이터 제작은 등록된 Command/Target/Effect/Action/Condition 타입의 조합까지만 허용한다.
- Lua pairs 순서에 의존하지 않고 Priority/Seq/Id로 안정 정렬한다.
- Client가 보낸 Damage, Target, ConsumesTurn, Cooldown 값을 신뢰하지 않는다.

각 변경의 최종 보고에는 다음을 포함하라.

- 변경 파일
- 통과한 시나리오
- build/runtime log 근거
- 아직 AI가 검증하지 못한 항목
- 다음 Phase의 선행 조건
```

## 2. Phase 0 프롬프트 — 기술 검증

```text
[Bootstrap 프롬프트의 모든 규칙을 적용한다.]

MapleTactics M1 Phase 0 기술 검증을 구현하라. 전체 게임을 만들지 말고 네 가지 위험 경계를 증명하는 최소 수직 스파이크만 만든다.

사전 조건:
- 현재 map/map01.map의 TileMapMode를 MapBuilder로 확인한다.
- getMapInfo로 InstanceMap 여부도 확인한다. Static Map에 전투 세션 하나를 두고 여러 사용자가 공유하게 만들지 않는다.
- 문서 권장은 SideViewRectTile(2)이다.
- 현재 값이 2가 아니면 파일에서 직접 바꾸지 말고 맵 타입 결정 게이트를 보고한다.
- 사용자가 SideViewRectTile을 선택하면 Maker Hierarchy에서 전환하도록 안내하고, 완료 확인 후 refresh와 재조회 전에는 Body/model 작업을 진행하지 않는다.
- 사용자가 MapleTile(0) 유지를 명시하면 platform-maple 규칙을 적용하고 RigidbodyComponent 경로로 진행한다.

구현할 스파이크:

A. 논리 셀 이동
- 테스트 유닛에 UnitRuntime CellIndex를 둔다.
- BoardWorldAdapter가 CellIndex를 월드 좌표로 변환한다.
- Cell 0 -> 1 -> 0을 서버에서 실행한다.
- Body가 있는 엔티티의 Transform Position을 직접 쓰지 않는다.

B. Command 왕복
- Client UI 버튼이 MOVE 요청을 보낸다.
- @ExecSpace("Server")에서 senderUserId, phase, sequence를 검증한다.
- 성공/실패 결과를 Client 표현으로 전달한다.

C. 큐 재타깃
- Push 효과 타일과 직선 공격 타일을 큐에 넣는다.
- 첫 타일 처리 후 이벤트를 완전히 해결한다.
- 두 번째 타일은 변경된 현재 보드에서 Target을 다시 계산한다.

D. 데이터 검증
- 최소 UserDataSet을 읽는다.
- 모든 셀이 문자열이라는 전제로 tonumber/boolean 변환을 한다.
- 존재하지 않는 참조 ID 한 건을 의도적으로 넣어 전투 시작 전에 차단한다.

테스트 로그 형식:
[P0-A] START / VALIDATED / RESULT
[P0-B] REQUEST / AUTHORIZED / CLIENT_RENDERED
[P0-C] TILE1_TARGET / AFTER_PUSH / TILE2_TARGET
[P0-D] LOAD / CONVERT / INVALID_REF_BLOCKED

추가 격리 로그:
[P0-ROOM] MAP_TYPE / INSTANCE_MAP / ACTIVE_USER_COUNT

완료 조건:
- 네 스파이크가 모두 positive log로 증명됨.
- Build error 0, Runtime error 0.
- 실패한 스파이크가 있으면 전체 구조 구현으로 넘어가지 않고 원인과 수정안을 문서화함.
```

## 3. Phase 1 프롬프트 — 전투 코어

```text
[Bootstrap 프롬프트의 모든 규칙을 적용한다.]

Docs/MapleTactics-M1-Implementation-Plan.md의 Phase 1을 끝까지 구현하라.

구현 순서:
1. BattlePhase와 custom Event 타입
2. BattleSessionComponent의 단일 phase machine
3. BoardState와 UnitRuntime
4. MOVE/TURN Command
5. AttackQueue와 QUEUE_TILE
6. FreePlay 턴 예외
7. EXECUTE_QUEUE와 타일별 재타깃
8. DAMAGE/PUSH/MOVE_SELF/TURN_TARGET Effect
9. Enemy Phase/Cleanup/Victory/Defeat
10. IsResolving/ClientSequence 방어
11. 최소 HUD

필수 시나리오:
- MOVE 성공 후 적 단계가 한 번 실행된다.
- TURN 성공 후 적 단계가 한 번 실행된다.
- 일반 QUEUE_TILE은 적 단계를 진행한다.
- FreePlay QUEUE_TILE은 적 단계를 진행하지 않는다.
- 큐가 가득 찬 요청은 상태를 바꾸지 않는다.
- 쿨다운 타일 등록은 거절된다.
- Push 후 다음 타일의 Target이 재계산된다.
- 사망한 적은 같은 Enemy Phase에서 행동하지 않는다.
- 같은 ClientSequence 재전송은 무시된다.

의도적으로 네이티브 물리 충돌을 타깃 판정의 원본으로 사용하지 않는다. CellIndex와 BoardState로 결정한 뒤 표현 계층에 결과를 전달한다.

테스트가 끝나면 각 시나리오의 서버 로그와 클라이언트 표시 결과를 보고하라.
```

## 4. Phase 2 프롬프트 — 데이터 기반 콘텐츠

```text
[Bootstrap 프롬프트의 모든 규칙을 적용한다.]

Phase 2를 구현해 기존 원시 타입 조합만으로 타일과 일반 적을 추가할 수 있게 하라.

데이터셋은 한 셀에 중첩 JSON을 넣지 말고 다음처럼 정규화한다.
- SkillDefinitions
- SkillEffectSteps
- EnemyDefinitions
- EnemyPatternSteps

필수 구현:
- 각 데이터셋 캐시 로더
- 문자열 -> number/boolean 변환 함수
- DuplicateId, MissingReference, InvalidEnum, OutOfRange 검증
- TargetType Router
- EffectType Router
- EnemyActionType Router
- Pattern StepIndex 안정 정렬

허용되지 않은 EffectType/ActionType은 fallback 실행하지 말고 콘텐츠 오류로 차단한다.

증명 시나리오:
1. .mlua 변경 없이 새 근접 타일 추가.
2. .mlua 변경 없이 DAMAGE+PUSH 복합 타일 추가.
3. .mlua 변경 없이 MOVE_TOWARD->TELEGRAPH->EXECUTE_TILE 적 추가.
4. 잘못된 TileId를 참조하는 적 패턴이 전투 전에 차단됨.

마지막에는 제작자가 편집할 열과 허용 값 목록을 Docs에 갱신하라.
```

## 5. Phase 3 프롬프트 — 스테이지와 보스

```text
[Bootstrap 프롬프트의 모든 규칙을 적용한다.]

Phase 3을 구현하라.

StageDefinitions와 StageEnemySpawns를 로드하고 StageId 하나로 다음을 결정하게 한다.
- 보드 크기/앵커
- 적 DefinitionId
- CellIndex/Facing/SpawnOrder
- PatternId
- 보상/AugmentPoolId

일반 적과 1차 보스는 Pattern Runner로 구현한다. 보스는 HpRatio 조건으로 PatternId를 교체한다.

BT 도입 조건을 먼저 평가한다. PatternStep으로 표현 가능한데 BT를 추가하지 않는다. 정말 BT가 필요하면 구현 전에 다음을 별도 Spike로 증명한다.
- custom BTNode .mlua 등록
- refresh 후 codeblock UUID 확인
- bt-spec 생성
- behaviourtree graph 검증
- model AIComponent 연결

완료 조건:
- StageId만 바꿔 다른 적 조합이 스폰됨.
- 같은 Seed/StageId의 결과가 동일함.
- 보스 Phase 전환이 한 번만 발생하고 Pattern Step이 올바르게 초기화됨.
```

## 6. Phase 4 프롬프트 — 직업과 증강

```text
[Bootstrap 프롬프트의 모든 규칙을 적용한다.]

Phase 4를 구현하라. 직업별 PlayerComponent 상속 클래스를 만들지 않는다.

데이터셋:
- JobDefinitions
- JobStartingSkillEntries
- AugmentDefinitions
- AugmentEffects
- StageAugmentPools
- AugmentConflicts

직업은 JobId가 BaseMaxHp, BaseQueueCapacity, StartingSkillSetId, JobMechanicId,
JobPassiveSetId를 결정한다. 시작 공격은 SkillDefinitions 참조이며 직업 고유 기능은
스킬 큐와 분리된 JobMechanic Router/Handler 계약으로 구현한다.

증강 처리 순서:
1. BattleEvent 수신
2. Trigger 필터
3. Condition 평가
4. Priority/AcquiredOrder/Seq/Id 안정 정렬
5. Effect 실행
6. SourceTag와 MaxDepth 검사

지원 정책:
- Unique
- StackAdd
- StackRefresh
- ExclusiveGroup

후보 생성은 RunSeed와 StageIndex에서 파생한 결정적 RNG만 사용한다. UI는 후보를 표시하고 선택 ID만 서버에 요청한다. 서버가 현재 OfferId, 후보 포함 여부, 충돌, 최대 스택을 다시 검증한다.

완료 조건:
- 4 JobId가 서로 다른 시작 구성을 만든다.
- 같은 Seed에서 같은 3개 후보가 나온다.
- 위조된 후보 선택은 거절된다.
- AfterDamage 증강이 자신의 DamageAppliedEvent에 무한 재귀하지 않는다.
```

## 7. Phase 5 프롬프트 — 제작자용 검증과 재현

```text
[Bootstrap 프롬프트의 모든 규칙을 적용한다.]

다른 제작자가 코드 없이 기존 원시 타입을 조합할 수 있도록 Phase 5를 구현하라.

필수 산출물:
- 전체 UserDataSet 참조 무결성 검사기
- 오류 코드, DatasetName, Row, Column, InvalidValue가 포함된 로그
- 고정 Seed + StageId + CommandLog 재현기
- 타일/적/스테이지/증강 추가 예제
- 콘텐츠 제작 체크리스트

검증은 한 오류에서 중단하지 말고 가능한 오류를 모아 한 번에 보고하되, 심각한 데이터 오류가 있으면 전투 시작은 차단한다.

최종 사용자 테스트:
- 새 제작자가 .mlua를 수정하지 않고 스테이지 하나를 추가한다.
- ContentValidator가 통과한다.
- 고정 Seed 재현 결과의 핵심 state hash가 동일하다.
```

## 8. 독립 리뷰 프롬프트

구현 Phase가 끝날 때 같은 AI에게 바로 통과 판정을 맡기지 말고, 가능하면 새 세션에서 다음 프롬프트를 사용한다.

```text
MapleTactics의 현재 구현을 변경하지 말고 감사하라.

검토 문서:
- Docs/MapleTactics-M1-Architecture-Review.md
- Docs/MapleTactics-M1-Implementation-Plan.md

감사 순서:
1. 상태 권한이 BattleSessionComponent 외부로 새지 않았는가.
2. UI/Client가 서버 상태를 직접 신뢰시키는 값이 있는가.
3. Transform/물리 위치가 논리 CellIndex의 원본으로 사용되는가.
4. 큐 타깃이 타일마다 재계산되는가.
5. IsResolving/Sequence/죽은 유닛 스킵/승패 조기 종료가 있는가.
6. pairs 순서, math.random, 전역 singleton 사용자 상태 등 비결정 요소가 있는가.
7. Dataset 모든 셀의 문자열 변환과 참조 무결성 검사가 있는가.
8. BT/FSM/Pattern이 같은 상태를 동시에 소유하는가.
9. .codeblock/.directory/Global/Environment가 수정되었는가.
10. 테스트가 '오류 없음'뿐이고 positive log가 빠졌는가.

결과를 Severity 순으로 보고하라.
- Blocker: 전체 구현을 진행하면 안 됨
- High: Phase 완료 전에 수정
- Medium: 다음 Phase 전 수정 권장
- Low: 품질 개선

각 항목에 파일 경로, 근거, 재현 시나리오, 최소 수정 방향을 포함하라. 문제가 없으면 어떤 시나리오와 로그로 확인했는지 명시하라.
```

## 9. 프롬프트 사용 원칙

- 한 Phase를 구현하는 세션에는 Bootstrap + 해당 Phase 프롬프트만 제공한다.
- Phase 0을 통과하기 전에 Phase 1 전체 구현을 요청하지 않는다.
- Phase 1 이후 매 Phase 끝에 독립 리뷰 프롬프트를 실행한다.
- 문서와 코드가 다르면 코드를 무조건 정답으로 취급하지 말고, 차이를 기록한 뒤 아키텍처 결정인지 버그인지 판정한다.
- 새로운 원시 타입은 Router, Validator, 데이터 사전, 최소 테스트를 한 변경으로 묶는다.
