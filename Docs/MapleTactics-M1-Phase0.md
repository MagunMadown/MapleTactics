# MapleTactics M1 Phase 0 — 기술 검증

Status: Not started  
목적: 전체 구조 구현 전에 MSW에서 실패 가능성이 높은 경계만 최소 코드로 증명한다.

## Skills to reference (this Phase)

- `msw-general`: `platform.md`, 확정 맵 타입의 `platform-*.md`, `workspace.md`, `entity.md`, `authoring.md`, `builder-protocol.md`, `model.md`
- `msw-scripting`: `SKILL.md`, `verify-checklist.md`
- `msw-combat-system`: `SKILL.md`
- `msw-ui-system`: `SKILL.md`, `component-api.md`, `runtime-patterns.md`

## Phase Gate

현재 `map01`은 MapleTile(0)이다. 권장 최종 모드는 SideViewRectTile(2)이다.

현재 `map01`은 Static Map이다. M1의 실제 전투 맵은 플레이어당 Instance Map 하나를 기본으로 한다. Static Map은 개발 스파이크에만 사용하거나 세계 최대 인원을 1명으로 고정해야 한다.

- 사용자가 권장 모드를 수락하면 Maker Hierarchy에서 직접 전환한다.
- AI는 `.map`의 TileMapMode를 직접 수정하지 않는다.
- 전환 후 `refresh`하고 MapBuilder로 `TileMapMode=2`를 확인한다.
- 사용자가 MapleTile 유지를 선택하면 모든 테스트 모델은 RigidbodyComponent를 사용하고 BoardWorldAdapter에 foothold 높이 매핑을 포함한다.

## 작업 체크리스트

### P0-01 맵/Body 계약

상태: Not started

- 목표: 맵 타입, 전투 격리, 유닛 Body를 확정한다.
- 구현: MapBuilder로 map01 정보 읽기, 테스트 유닛 model 구성.
- 데이터: 없음.
- UI: 없음.
- 의존성: 사용자 맵 전환 결정.
- 완료: Map mode, InstanceMap 정책, Body type, movement API가 로그와 문서에 기록됨.

### P0-02 논리 셀 이동

상태: Not started

- 목표: CellIndex가 원본이고 월드 위치가 파생임을 증명한다.
- 구현: UnitRuntime, BoardWorldAdapter, Cell 0 -> 1 -> 0 이동.
- 데이터: CellWidth, OriginWorldPosition 테스트 값.
- UI: 현재 CellIndex 텍스트 선택 사항.
- 의존성: P0-01.
- 완료: Body/Movement SetWorldPosition을 사용하고 각 이동의 expected/actual 로그 일치.

### P0-03 서버 Command 왕복

상태: Not started

- 목표: Client 입력, Server 검증, Client 표시 경계를 증명한다.
- 구현: MOVE Request, senderUserId 검증, ClientSequence 중복 방지, 결과 전달.
- 데이터: 없음.
- UI: 테스트 버튼과 결과 텍스트.
- 의존성: P0-02.
- 완료: 정상 요청 성공, 위조 사용자/중복 요청 차단, Client 표시 로그 확인.

### P0-04 큐 재타깃

상태: Not started

- 목표: 각 타일이 현재 상태에서 대상을 다시 계산함을 증명한다.
- 구현: Push Tile -> Forward Attack Tile, 이벤트 즉시 해결.
- 데이터: 테스트 타일 2개.
- UI: 큐 2칸 표시 선택 사항.
- 의존성: P0-02.
- 완료: Push 전/후 셀과 두 번째 타깃이 positive log로 확인됨.

### P0-05 UserDataSet 로드/검증

상태: Not started

- 목표: 문자열 변환과 참조 무결성 검증을 증명한다.
- 구현: 테스트 정의/효과 데이터 로드, tonumber/boolean 변환, MissingReference 수집.
- 데이터: 정상 행과 고의 오류 행.
- UI: 없음.
- 의존성: 없음.
- 완료: 정상 행 로드, 고의 오류 행 차단, Dataset/Row/Column/Value 로그 확인.

### P0-06 통합 검증

상태: Not started

- 목표: Phase 0 최종 PASS/FAIL.
- 구현: 테스트 로그 정리와 문서 상태 갱신.
- 데이터: 없음.
- UI: 버튼 경로 수동 입력.
- 의존성: P0-01~05.
- 완료: build error 0, runtime error 0, 모든 시나리오 positive log 존재.

## 판정 규칙

- 하나라도 실패하면 Phase 1을 시작하지 않는다.
- 실패 원인이 맵 타입/Body이면 문서의 핵심 결정을 먼저 수정한다.
- 실패 원인이 API 서명 추측이면 `.d.mlua`를 다시 확인하고 코드를 수정한다.
- 짧은 UI/이펙트가 캡처되지 않아도 create/destroy 로그가 있으면 실행 증거로 사용할 수 있다.
- Phase가 모두 Tested가 되면 GDD 로드맵에 Phase 0 완료를 반영하고 구현 사실을 `Archive/As-built.md`에 기록한다.
