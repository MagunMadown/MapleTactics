# 런 콘텐츠 전환 가이드

## 게임 흐름

전투가 끝나면 `NodeDefinitions`가 다음 후보를 만든다. 플레이어가 후보 하나를 선택하면 서버가
ContentType에 맞는 전환 명령을 준비한다.

```text
전투 승리
→ AWAITING_NODE_SELECTION
→ 노드 선택
→ ContentType Handler
→ READY
→ 상점·이벤트·휴식 UI 또는 다음 전투 어댑터가 소비
→ 비전투 콘텐츠 완료
→ 다음 노드 선택 또는 RUN_COMPLETED
```

현재 `prototype_run`에서는 `stage01_battle` 승리 뒤 `shop_after_stage01`이 제공되고, 선택하면
`AWAITING_SHOP / OPEN_SHOP / RUN_SHOP` 상태가 된다. 상점을 닫거나 구매 없이 건너뛰면 현재
SHOP 노드의 `NextNodeIds`가 비어 있으므로 `RUN_COMPLETED`로 종료된다.

현재 전투 결과 HUD는 이 후보를 선택하거나 `OPEN_SHOP` Route를 여는 소비기가 아니므로
실제 화면 전환은 하지 않는다. 대신 승리 시 디버그 HUD 상태 줄에 Run Flow DTO의 첫 다음 콘텐츠를 읽어
`이동 이벤트 · 상점으로 이동합니다`를 표시한다. 내부 NodeId는 DTO에만 유지한다. 다음 후보·상점 서버
계약까지는 구현되어 있지만 실제 상점 화면과 StageId→MapId Adapter는 미구현이다.

## 책임 분리

| 객체 | 책임 |
|---|---|
| `NodeDefinitionRepositoryLogic` | 다음 노드와 ContentType 후보 계산 |
| `RunManagerLogic` | 사용자 요청 인증, 후보 선택 검증, Handler 호출 |
| `PlayerRunStateComponent` | 플레이어별 선택·전환 Snapshot 소유 |
| `RunContentFlowRouterLogic` | ContentType을 전용 Handler에 연결 |
| Content Handler | 화면·Gateway가 소비할 Route DTO 생성 |
| UI·Map Flow Adapter | READY 상태를 실제 화면 또는 맵 전환으로 실행 |

BattleSession은 SHOP, EVENT, REST 화면을 직접 알지 않는다.

비전투 콘텐츠 완료는 `RunManagerLogic.CompleteCurrentContent()` 하나가 소유한다. SHOP은
`RunShopLogic.CloseShop()`이 이 Facade를 호출하며, EVENT와 REST도 후속 소비기에서 같은
완료 경계를 사용한다. BATTLE/BOSS는 이 경계로 완료할 수 없고 반드시 전투 결과 기록을 거친다.

## 현재 Handler 계약

| ContentType | FlowState | RouteAction | UiRouteId | Map 전환 |
|---|---|---|---|---|
| `BATTLE`, `BOSS` | `AWAITING_BATTLE` | `PREPARE_BATTLE_ENTRY` | `BATTLE_LOADING` | 필요 |
| `SHOP` | `AWAITING_SHOP` | `OPEN_SHOP` | `RUN_SHOP` | 현재 불필요 |
| `EVENT` | `AWAITING_EVENT` | `OPEN_EVENT` | `RUN_EVENT` | 현재 불필요 |
| `REST` | `AWAITING_REST` | `OPEN_REST` | `RUN_REST` | 현재 불필요 |

여기서 Map 전환 여부는 현재 기본값이다. 실제 콘텐츠가 별도 맵을 사용하게 되면 Handler의
Route DTO와 Map Flow Adapter를 함께 확장한다.

## UI 요청과 조회

노드 선택 요청은 Client에서 다음 Facade만 호출한다.

```lua
_RunManagerLogic:RequestSelectNextContent("shop_after_stage01", requestId)
```

`requestId`는 해당 UI 세션에서 증가시킨다. 서버는 `RunSequence:requestId`를 선택 키로 사용해
동일 요청을 `DUPLICATE_SELECTION_IGNORED`로 처리한다.

Client UI는 다음 DTO만 읽는다.

```lua
local ui = _RunManagerLogic:GetLocalRunFlowUiState()
```

주요 값:

- 후보: `AvailableNodeIds`, `AvailableContentTypes`, `AvailableContentIds`
- 전환: `Transition.State`, `RouteAction`, `UiRouteId`, `DestinationType`, `DestinationId`
- 명령: `Commands.CanSelectNode`, `Commands.CanConsumeTransition`
- 완료: `Commands.CanCompleteContent`
- 갱신: `RevisionKey`

후보 문자열 세 개는 `|`로 구분하며 같은 인덱스가 하나의 선택지다. UI는 NodeDefinitions를
직접 읽거나 ContentType을 다시 판정하지 않는다.

## 확장 규칙

1. 새 ContentType은 독립 Handler를 만든다.
2. Router에는 ContentType과 Handler 연결만 추가한다.
3. Handler는 플레이어 상태나 UI Entity를 직접 변경하지 않고 Route DTO만 반환한다.
4. 실제 화면과 맵 이동은 별도 Adapter가 `Transition.State=READY`를 소비한다.
5. 정상 선택, 허용되지 않은 노드, 동일 요청 재전송, Client DTO를 함께 검증한다.

현재 SHOP은 전환 준비·거래·완료까지 구현됐다. EVENT/REST 소비기, 실제 최종 상점 화면,
StageId→MapId 이동은 후속 시스템이 이 계약 위에 구현한다. 상세 상점 계약은
[`Run-Shop-Authoring-Guide.md`](./Run-Shop-Authoring-Guide.md)를 따른다.

## Region 1 연동 경계

현재 `StageDefinitions`에는 `region_01_stage_01`부터 `region_01_stage_04`까지 존재하지만,
통합된 `NodeDefinitions`는 아직 1-1 전투 뒤 기존 상점으로 가는 최소 그래프만 가진다.
따라서 1-2~1-4는 데이터/직접 진입 테스트는 가능하되 정식 Run 경로에서는 아직 선택되지 않는다.

REST/증강 담당자가 그래프를 연결할 때 다음 규칙만 지키면 전투 코드를 수정할 필요가 없다.

```text
BATTLE(StageId=region_01_stage_01)
→ REST
→ BATTLE(StageId=region_01_stage_02)
→ REST
→ BATTLE(StageId=region_01_stage_03)
→ REST
→ BATTLE(StageId=region_01_stage_04, StageType=BOSS)
```

- `NodeType`으로 BATTLE/REST를 구분하며 NodeId 문자열을 파싱하지 않는다.
- 신규 보스 Node도 `NodeType=BATTLE`을 쓰고 보스 여부는 `StageDefinitions.StageType=BOSS`에서 읽는다.
- BATTLE의 `ContentId`는 StageId, REST의 `ContentId`는 NodeId다.
- REST 완료는 `CompleteCurrentContent(player, "REST", requestId)` 경계만 사용한다.
- 전투 팀은 다른 팀의 NodeId, REST 데이터, `NextNodeIds`를 임의로 변경하지 않는다.
