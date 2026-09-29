# MapleTactics 팀 개발 빠른 시작 가이드

## 0. AI 코딩 도구 설정 (최초 1회, clone 직후)

Claude Code / Codex / Cursor / GitHub Copilot용 스킬·훅·MCP 설정(`.claude/`, `.codex/`,
`.agents/`, `.mcp.json`)은 저장소에 커밋돼 있지 않다(`.gitignore` 처리됨) — 전부 공식 CLI
`@maplestoryworlds/ai-cli`(`mswai`)가 `skills-lock.json`(추적됨, 버전 고정 lockfile)을 기준으로
생성하는 산출물이다. AI 도구로 이 저장소를 열기 전에 한 번 실행한다.

```bash
npm i -g @maplestoryworlds/ai-cli
cd MapleTactics
mswai init          # AGENTS.md는 이미 있으므로 보존, hooks + skills + MCP 설정만 생성
mswai status         # 각 에이전트 plugin/mcp 상태 확인
```

`msw-mcp` MCP 서버는 개인별 API 키가 필요하다 — 발급 후 아래처럼 주입하거나, 생성된
`.mcp.json`(또는 `.cursor/mcp.json` / `.codex/config.toml`)의 `Authorization` 헤더에 안내된
발급 URL로 직접 키를 받아 교체한다.

```bash
mswai mcp --mcp-var MSW_MCP_TOKEN=<발급받은 키>
```

이후 CLI가 업데이트되면 `npm i -g @maplestoryworlds/ai-cli@latest && mswai update`로 동기화한다.
`AGENTS.md`·`CLAUDE.md`·`.cursorrules`·`skills-lock.json`은 저장소에 계속 커밋돼 있으니 직접
clone/pull로 받아진다 — `mswai init`은 이 파일들이 아니라 나머지 도구별 산출물만 다시 만든다.

## 1. 먼저 읽을 문서

새 작업자는 다음 순서만 먼저 읽는다.

1. [`Current-Development-Status.md`](./Current-Development-Status.md)
2. [`Architecture-Standard-v0.1.md`](./Architecture-Standard-v0.1.md)
3. [`Development-Workflow-Guide.md`](./Development-Workflow-Guide.md)
4. 담당 기능 Guide

이 문서는 진입점이다. 세부 규칙과 예외는 위 문서를 기준으로 한다.

## 2. 핵심 구조

```text
CSV/UserDataSet
→ Repository: 문자열을 타입 값으로 변환
→ Domain Validator: 행 규칙과 참조 검사
→ State Owner Component: 플레이어·전투별 mutable state 소유
→ Stateless Resolver/Router: 계산과 타입 분기
→ Facade/Gateway: 외부 시스템과 Client Request 진입점
→ DTO/Snapshot: UI가 읽는 전용 상태
```

가장 중요한 규칙은 상태를 가진 객체를 하나로 유지하는 것이다. UI, Resolver, Handler가 상태
필드를 직접 수정하지 않는다.

## 3. 담당 영역과 수정 위치

| 작업 | 주 수정 위치 | 직접 수정하지 않을 곳 |
|---|---|---|
| Stage·Wave·Enemy 배치 | `03_Data/*.csv` | `BattleSessionComponent`의 ID 분기 |
| Skill 추가 | `SkillDefinitions`, `SkillEffectSteps` | SkillId별 새 Session 조건문 |
| Enemy Pattern 추가 | `EnemyDefinitions`, `EnemyPatternSteps` | 적 Entity 직접 Cell 변경 |
| Drop·Reward 추가 | Drop/Reward CSV | 인벤토리 Snapshot 직접 연결 |
| Job·Augment 추가 | Job/Augment CSV와 전용 Handler | Player 클래스 깊은 상속 |
| Run Shop 상품 추가 | `ShopEntries.csv` | UI에서 가격·보상 계산 |
| 전투 UI | Battle DTO 소비 | 서버 전투 상태 직접 수정 |
| Run/Shop UI | Run/Shop DTO와 Request API | NodeDefinitions 직접 판정 |

## 4. 공개 API 사용 원칙

외부 화면과 다른 시스템은 다음 Facade를 사용한다.

```lua
-- 다음 콘텐츠 선택
_RunManagerLogic:RequestSelectNextContent(nodeId, requestId)

-- Run Shop
_RunShopLogic:RequestOpenShop(shopId)
_RunShopLogic:RequestPurchaseOffer(shopEntryId, requestId)
_RunShopLogic:RequestCloseShop(requestId)

-- Client DTO
local flowUi = _RunManagerLogic:GetLocalRunFlowUiState()
local shopUi = _RunShopLogic:GetLocalShopUiState()
```

Client는 피해량, 가격, 보상 수량, 다음 Node를 보내거나 계산하지 않는다. 서버에는 ID와 증가하는
`requestId`만 보낸다. 동일 Run에서 requestId를 재사용하지 않는다.

## 5. 새 콘텐츠 추가 절차

1. 기존 타입 조합으로 가능한지 확인한다.
2. 해당 CSV/UserDataSet 행을 추가한다.
3. Repository가 읽는 열 이름과 타입을 확인한다.
4. 전용 Validator를 통과시킨다.
5. `_ContentValidatorLogic:ValidateAllContent()` 전체 Gate를 통과시킨다.
6. 정상 경로와 잘못된 참조 실패 경로를 Maker에서 검증한다.
7. 관련 Guide와 구현 계획 체크 항목을 같은 작업에서 갱신한다.

새 EffectType, ActionType, RewardType처럼 원시 타입을 추가할 때만 Router/Executor/Validator를
함께 확장한다. 특정 Content ID를 Router나 Session에 하드코딩하지 않는다.

## 6. UI 개발 규칙

- 현재 HUD는 최종 디자인이 아니라 디버그·기능 검증용이다.
- `.ui` 파일은 UIBuilder로만 수정한다.
- UI Component 접근과 연출은 ClientOnly에서 수행한다.
- 버튼은 Request API만 호출하고 결과는 DTO RevisionKey 변화로 다시 그린다.
- `Commands.Can*`가 false이면 버튼을 비활성화한다.
- Snapshot 구분자 `|`, `~`를 임의로 변경하지 않는다.

## 7. Git 작업 규칙

- 브랜치 하나는 기능 Slice 하나를 기본으로 한다.
- 데이터 규격, 전투 런타임, Run Flow, 최종 UI를 한 커밋에 섞지 않는다.
- `.mlua`와 Maker가 생성한 `.codeblock` 페어를 함께 포함한다.
- `.codeblock`, `.directory`를 직접 수정하거나 생성하지 않는다.
- 문서만 수정한 커밋과 기능 구현 커밋을 구분한다.
- 다른 작업자의 변경을 정리한다는 이유로 되돌리거나 덮어쓰지 않는다.

권장 커밋 메시지:

```text
feat(data): ...
feat(combat): ...
feat(run): ...
feat(ui): ...
docs: ...
fix(...): ...
```

## 8. Maker 검증 순서

```text
stop
→ clear runtime logs
→ refresh
→ build Warning/Error 확인
→ play
→ 정상 경로 실행
→ 실패·중복 경로 실행
→ server/client runtime logs 확인
→ stop
```

Warning/Error가 없다는 사실만으로 완료가 아니다. 검증 중에는 요청한 분기가 실행됐다는
positive log와 예상값을 확인하고 작업 기록에 남긴다. 기능 완료 전에는 임시 반복 로그를
삭제한다. [`Runtime-Logging-Guide.md`](./Runtime-Logging-Guide.md)를 따른다.

## 9. 인수인계 템플릿

```text
변경 결과:
상태 소유자:
추가·변경한 공개 API:
추가·변경한 Dataset/ID:
수정 허용 파일:
수정 금지 파일:
Maker Build 결과:
정상 경로 로그:
실패·중복 경로 로그:
남은 제한:
후속 작업:
```

작업 목표와 상태 소유자를 한 문장으로 설명할 수 없다면 구현 전에 영향도 분석부터 진행한다.
