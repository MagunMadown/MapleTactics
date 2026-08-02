# 스테이지 클리어 보상 제작 가이드

## 게임에서 보이는 동작

마지막 웨이브를 끝내고 승리가 확정되면 `StageRewardDefinitions`에 등록된 보상이 런
인벤토리에 지급된다. 같은 전투 결과가 네트워크나 화면 전환 때문에 다시 전달돼도 보상은
한 번만 증가한다. 패배에는 클리어 보상을 지급하지 않는다.

## 표 작성

`RootDesk/MyDesk/03_Data/StageRewardDefinitions.csv`에 한 보상당 한 행을 추가한다.

| 열 | 의미 |
|---|---|
| `SchemaVersion` | 현재 `1` |
| `StageRewardEntryId` | 전체 표에서 유일한 보상 행 ID |
| `StageId` | `StageDefinitions`에 존재하는 Stage ID |
| `RewardType` | `CURRENCY` 또는 `CONSUMABLE` |
| `RewardRefId` | 재화 또는 소모품 ID |
| `Amount` | 1 이상의 지급량 |
| `Enabled` | `true`인 행만 적용 |

현재 Stage 1 기본값은 다음과 같다.

```csv
1,stage01_clear_gold,stage01,CURRENCY,gold,5,true
```

## 데이터 제한

- `CURRENCY`는 `CurrencyDefinitions.Category=RUN_SCOPED`인 재화만 허용한다.
- 현금성·계정 영구 재화는 Stage 보상표에서 사용할 수 없다.
- `CONSUMABLE`은 활성화된 `ConsumableDefinitions` 행만 참조할 수 있다.
- 존재하지 않는 Stage, 중복 Entry ID, 0 이하 수량은 전투 시작 전체 검증에서 차단된다.

## 실행과 멱등성

전투 코드는 직접 인벤토리를 수정하지 않는다.

```lua
local result = _RunManagerLogic:ApplyStageClearRewards(playerEntity, stageId, battleRecordKey)
```

실제 지급은 `PlayerRunInventoryComponent.GrantRunReward(...)`가 수행한다. 보상 키는
`stage:{RunSequence}:{StageId}:{EntryRequestId}:{StageRewardEntryId}` 형식이며, 같은 키를
다시 처리하면 `DUPLICATE_REWARD_IGNORED`로 성공 처리하되 수량을 올리지 않는다.

`RecordBattleResult(...)`는 승리일 때 모든 보상을 먼저 지급한 뒤 진행 노드를 확정한다.
중간 실패 후 재시도하면 이미 지급된 행은 무시되고 남은 행만 처리할 수 있다.

## UI 계약

최종 결과 화면은 보상표를 다시 계산하지 않는다. 다음 공개 Snapshot을 갱신해 표시한다.

```text
GetBattleUiState().RunInventory.CurrencySnapshot
GetBattleUiState().RunInventory.ConsumableSnapshot
GetBattleUiState().RunInventory.Revision
```

별도 결과 화면에서는 `_RunManagerLogic:GetRunRewardSnapshot(playerEntity)`를 사용한다. 현재 HUD는
기능 검증용이며 최종 보상 연출과 카드 배치는 이 Snapshot 위에서 교체한다.

## 새 보상 종류를 추가할 때

1. `PlayerRunInventoryComponent`에 필드를 직접 추가하기 전에 새 상태 소유자가 필요한지 결정한다.
2. Repository에는 행 변환과 기본 타입 검사만 둔다.
3. 참조·정책 검사는 `StageRewardContentValidatorLogic`과 `ContentReferenceResolverLogic`에 둔다.
4. 실제 상태 변경은 `RunManagerLogic` Facade를 거쳐 해당 상태 소유자의 메서드로 수행한다.
5. 정상 지급, 중복 재처리, 잘못된 참조를 함께 Maker에서 검증한다.
