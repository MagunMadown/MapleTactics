# 런 상점 제작 가이드

## 범위

이 상점은 한 로그라이크 Run에서 획득한 `RUN_SCOPED` 골드로 런 능력치 유물을 구매하는
시스템이다. 영구 상품·캐시 결제·DB 구매 횟수를 사용하는 WorldShop과 분리한다.

데이터 사전 §20.1~20.2의 `ShopDefinitions`/`ShopEntries`와
`ShopNodeBindings`가 이 시스템의 기준 규격이다.
§20.3의 `ShopItemDefinitions`는 Meta/World Shop용 `PLANNED` 스키마이며 런 상점에서 읽지 않는다.

현재 `RunShopUI`는 서버 DTO와 Request API만 사용하며 Dataset을 직접 읽지 않는다.

## 기본 흐름

```text
Node 선택 → OPEN_SHOP
→ RequestOpenShop
→ OfferSnapshot 표시
→ RequestPurchaseOffer
→ 서버 가격/참조/잔액/구매 제한 검증
→ 골드 차감 + 보상 지급 원자적 확정
→ Shop/Inventory Revision 갱신
→ RequestCloseShop
→ 현재 SHOP 노드 완료
→ 다음 노드 선택 또는 RUN_COMPLETED
```

## ShopDefinitions

`ShopDefinitions.csv`는 재사용 가능한 상점 카탈로그를 정의한다.

| 열 | 의미 |
|---|---|
| `SchemaVersion` | 현재 `2` |
| `ShopId` | 상점 카탈로그 고유 ID |
| `DisplayName` | 화면 표시 이름 |
| `MapId` | 상점 진입 목적지 맵 |
| `Enabled` | 활성 여부 |

## ShopNodeBindings

`ShopNodeBindings.csv`는 고유한 런 그래프 방문 노드를 상점 카탈로그에 연결한다.
하나의 `ShopId`를 여러 `NodeId`에서 재사용할 수 있지만 `(NodeGraphId, NodeId)`는 중복될 수 없다.

| 열 | 의미 |
|---|---|
| `SchemaVersion` | 현재 `1` |
| `NodeGraphId`, `NodeId` | `NodeDefinitions`의 고유한 SHOP 노드 |
| `ShopId` | `ShopDefinitions`의 상점 카탈로그 |
| `Enabled` | 활성 여부 |

## ShopEntries

| 열 | 의미 |
|---|---|
| `ShopEntryId` | 전체 상점에서 유일한 상품 ID |
| `ShopId` | 소속 상점 |
| `DisplayName` | 상품 표시 이름 |
| `RewardType` | 공통 `shop_relic`은 `ITEM` |
| `RewardRefId`, `RewardAmount` | 지급 대상과 수량 |
| `PriceCurrencyId`, `PriceAmount` | RUN_SCOPED 가격 재화와 수량 |
| `DisplayOrder` | 오름차순 표시 순서 |
| `MaxPurchasesPerRun` | 현재 규격은 `1`만 지원 |
| `Enabled` | 활성 여부 |

현재 33종 유물은 모두 1골드다. `RelicDefinitions`에 같은 RewardRefId와 세 보너스(0 이상의 정수)를 등록한다. 기존 ItemCategory·IconImageRUID는 유지한다. 미보유 활성 유물 중 한 개만 진열하며 재열기·구매 후 재추첨하지 않는다. 전체 보유 시 빈 상점에서도 퇴장할 수 있다.
기존 스킬·포션 상품 예시는 초기 프로토타입 기록이다. 현재 `ShopEntries.csv`는 장비 상품이며 소비 아이템 상품은 없다. 소비 아이템 추가 시 현재 5종 ID와 기존 구매 API를 사용하고, 총 수량 3~5칸 및 초과 재화 정책을 따른다. 이번 소비 HUD 작업에서는 상품 행을 추가하지 않았다.

## 서버 API

```lua
_RunShopLogic:RequestOpenSelectedShop()
_RunShopLogic:RequestPurchaseOffer(displayedOfferId, requestId)
_RunShopLogic:RequestCloseShop(requestId)
```

서버 직접 통합과 테스트에서는 `OpenShop(player, shopId)`와
`PurchaseOffer(player, shopEntryId, requestId)`를 사용한다. Client가 가격이나 지급 내용을
인자로 보내지 않으며 서버가 새 런에 캡처한 현재 진열 행과 비교한다. 정의·가격 변경은 다음 새 런부터 반영한다.

구매는 선택 사항이다. 아무 상품도 구매하지 않은 상태에서도 `RequestCloseShop()`으로 상점을
건너뛸 수 있다. 서버는 `RunManagerLogic.CompleteCurrentContent()`를 통해 현재 SHOP 노드만
완료하며 BATTLE/BOSS 완료는 허용하지 않는다.

## UI DTO

```lua
local ui = _RunShopLogic:GetLocalShopUiState()
```

주요 값:

- `OfferSnapshot`: `OfferId~DisplayName~RewardType~RewardRefId~RewardAmount~CurrencyId~Price~Order~IconImageRUID~ItemCategory~AttackBonus~MaxHpBonus~DefenseBonus~EffectDescription`
- `PurchasedOfferIds`: 현재 런에서 구매 완료한 Offer ID 목록
- `CurrencySnapshot`, `ConsumableSnapshot`, `SkillSnapshot`, `ItemSnapshot`, `NodeId`
- `LastPurchase.OfferId/Success/Reason`
- `Completion.RunState/RunFlowState/LastCompletedContentType/LastCompletedContentId`
- `RevisionKey`, `Commands.CanPurchase/CanClose/CanSkip`

UI는 표를 직접 읽거나 잔액을 차감하지 않는다. Snapshot은 `|`, 필드는 `~` 구분이므로 ID와
표시 이름에 두 문자를 넣을 수 없다.

## 구매 안전성

- 서버가 현재 Run의 선택된 SHOP 전환 상태를 확인한다.
- 가격 재화는 `RUN_SCOPED`만 허용한다.
- 상품 참조는 전체 콘텐츠 검증에서 확인한다.
- `RunSequence + ShopEntryId` 구매 키로 같은 상품을 한 Run에서 한 번만 지급한다.
- `RunSequence + VisitSequence + requestId`로 성공한 Client 요청 재전송을 무시한다.
- 상점 완료도 `RunSequence + requestId`를 사용하며 동일 종료 요청은
  `DUPLICATE_CONTENT_COMPLETION_IGNORED`로 처리한다.
- 골드 차감과 유물 지급은 `PlayerRunInventoryComponent.ApplyShopPurchase` 한 경계에서 처리한다.
- 잔액 부족이나 잘못된 상품은 인벤토리를 변경하지 않는다.
- 종료가 확정되면 Shop State는 `CLOSED`가 되고 구매·닫기·건너뛰기 명령이 비활성화된다.

## 확장 규칙

1. 상품 추가는 ShopEntries와 RelicDefinitions에 동일 ID의 행을 추가한다. 능력치 변경은 RelicDefinitions 세 수치를 수정하고 새 런에서 확인한다.
2. 새 RewardType은 전용 상태 소유자와 원자적 거래 경계를 먼저 설계한다.
3. Run당 2회 이상 구매나 재입고가 필요하면 숫자를 먼저 풀지 말고 Shop State의 구매 수량
   Snapshot과 Validator를 함께 확장한다.
4. 메타 재화·현금성 상품은 이 시스템에 넣지 않고 WorldShop 계층으로 분리한다.
5. 상점 이후 흐름을 바꿀 때는 Shop Logic에 다음 목적지를 하드코딩하지 않고
   `NodeDefinitions.NextNodeIds`를 수정한다.
6. 새 방문 지점은 `ShopDefinitions → ShopEntries → ShopNodeBindings → NodeDefinitions` 순서로
   추가한다. 재방문은 새 고유 `NodeId`를 만들고 기존 `ShopId`에 바인딩한다.

경로는 shop_upper/shop_lower NodeId로 구분하며 두 바인딩의 ShopId는 shop_relic이다. 퇴장 UI도 NodeId로 다음 경로를 선택한다.
