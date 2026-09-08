# 소비 아이템 전투 인벤토리 구현 보고서

2026-09-08 · MapleTactics · `codex/consumable-items`

로컬 구현과 오프라인 검사를 마쳤다. **Maker Refresh / Build / Play / Logs는 도구 미연결로 NOT RUN**이다. 아래 PASS는 실제 mLua 메서드를 Lua 5.4에서 실행한 오프라인 결과이며, 네이티브 렌더링·RPC·입력 검증을 의미하지 않는다. 커밋·푸시는 하지 않았다.

## 1. 현재 구조 감사

| 책임 | 기존 소유자 | 결과 |
|---|---|---|
| 런 소유량·용량·초과 재화·중복 키 | PlayerRunInventoryComponent | id~count, InventoryRevision, AppliedRewardKeys/AppliedUseKeys 재사용 |
| 런 보상·사용 진입점 | RunManagerLogic | GrantRunReward / CanUseRunConsumable / ConsumeRunConsumable 재사용 |
| 사용 인증·효과 순서 | BattleSessionComponent | 소유자·맵·EntryId·런·턴·인벤토리 revision 검증 |
| 정의·효과 | ConsumableDefinitions / ConsumableDefinitionRepositoryLogic / ConsumableEffectRouterLogic | 이전 단계의 요청된 5종과 서버 효과 API 유지 |
| HP / 쿨다운 | BattleUnitComponent / SkillRuntimeStateComponent | ApplyHealing / ReduceCooldown으로 기존 런 HP·쿨다운 갱신 |
| 적 드롭 | EnemyDropDefinitionRepositoryLogic / BattleDropComponent | 사망 → 확률 판정 → Pending → 바닥 → 셀 수거 또는 승리 자동 수거 |
| 바닥 표시 | BattleDropPresentationComponent / BattleDropPickup 모델 | 모델·부유 연출 유지, SpriteRUID 선택 변경 |
| Union | PlayerRunUnionEffectComponent / RunManagerLogic | 새 런의 InventorySlotBonus 캡처·전달 경로 재사용 |
| 소비 HUD | BattleConsumableHudComponent / BattleConsumableHUD.ui | 기존 최소 HUD를 개별 슬롯 방식으로 확장 |

새 인벤토리·드롭·HP·턴·Union 시스템을 만들지 않았다. 조사한 13개 맵의 TileMapMode는 0이며 맵·Body·모델을 변경하지 않았다.

## 2. Shogun 스타일 인벤토리

**1칸 = 실제 아이템 1개**, 기본 3칸 + Union 0~2칸 = 최대 5칸이다. 저장 형식은 유지한다. `red_potion~2|orange_potion~1`은 빨강 / 빨강 / 주황 3칸이다. 숫자 스택을 한 아이콘에 붙이지 않는다.

GetConsumableGrantSpace는 종류 수 대신 전체 수량을 계산한다. MaxStack은 슬롯당 1이며, 동일 종류도 총 용량만큼 여러 칸을 차지할 수 있다. 표시 순서는 정의 행 순서(빨강·주황·하양·모래·만병통치약)다. 획득 순서·드래그 정렬 저장은 추가하지 않았다.

획득과 상점 구매는 기존 용량 계산을 공유한다. 초과 1개당 기본 gold 1이며 OverflowCurrencyId / OverflowCurrencyPerItem 설정을 존중한다. 이전 종류별 스택 방식으로 초과 보유한 런은 첫 정규화 때 스냅샷 순서대로 용량만큼 보존하고 초과분에 같은 재화 정책을 적용한다. 반복 정규화는 재화를 다시 지급하지 않는다.

potion_hp_small 수량은 orange_potion으로 합산한 뒤 용량 정책을 적용한다. GetSnapshot, 보상·구매·사용, HUD 조회가 정규화를 사용한다.

## 3. HUD

1920×1080 기준 좌측 상단 `(32, 180)`, 기존 LeftRunInfo 아래에 배치했다. 폭 312/408/504, 높이 220이며 88×88 슬롯은 한 줄이다. 아이콘은 52×52다. 확장되지 않은 4·5번째 칸은 숨긴다. 기존 HP HUD·스킬 바·큐·적 의도·웨이브 UI 파일은 변경하지 않았다.

빈 칸 표시, hover/선택 시 이름·효과 설명·사용 불가 사유, 사용 불가 아이콘의 흐림 처리를 구현했다. 설명을 읽을 수 있도록 hover는 유지하고 실행은 차단한다. 숫자 1~5 단축키는 추가하지 않았다. 기존 H 키의 주황 포션 어댑터는 유지한다.

시간의 모래 선택창은 `(32, 416)`에 배치한다. 쿨다운이 남은 보유 스킬만 4행 단위로 표시하고 이전·다음·취소를 제공한다. 취소는 사용 요청을 보내지 않는다.

OnUpdate는 인벤토리·용량·쿨다운·HP·턴·사용 결과 signature와 맵/EntryId/RunSequence를 확인한다. 변경 때만 DTO를 요청하고 데이터/상호작용 상태 변경 때만 다시 그린다. 불일치한 지연 DTO는 재조회하며 이전 런·전투 데이터는 거부한다. 획득·초과 전환은 InventoryRevision, 실패는 receipt, 시작·복구·스테이지 변경은 context로 반영한다. 승리 화면에서는 숨기고 자동 수거 결과는 다음 전투에서 표시한다.

UIBuilder로 기존 UUID 8개를 유지했다. 구조·바인딩·버튼 크기·가로 배치·피벗 검사와 UI lint는 PASS다. 실제 줄바꿈·시각적 겹침·hover 입력은 Maker 검증이 남는다.

## 4. 소비 아이템 사용

| ID | 효과 | 대상 / 실패 조건 |
|---|---|---|
| red_potion | HP +2 | 자신 / 최대 HP이면 실패 |
| orange_potion | HP +4 | 자신 / 최대 HP이면 실패 |
| white_potion | HP +6, MaxHP 제한 | 자신 / 최대 HP이면 실패 |
| time_sand | 쿨다운 -2, 최소 0 | 보유 쿨다운 스킬 / 취소·미보유·쿨다운 0이면 소비 없음 |
| all_cure_potion | 해로운 상태 제거 인터페이스 | 현재 상태이상 시스템이 없어 실패·소비 없음. UtilityGuardActive 보존 |

전부 BATTLE_FREEPLAY / ConsumesTurn=false / ConsumeOnUse=true / TurnCost=0이다.

SubmitConsumableUse → RequestUseConsumable → TryUseRunConsumable → 기존 효과 Router → 성공 시 Consume 순서다. UseKey와 RewardKey로 성공 효과·차감·보상의 재실행을 막는다. 큐·턴 번호·적 턴·쿨다운 턴 진행을 호출하지 않는다. 효과 없음으로 실패한 정상 인벤토리는 수량이 변하지 않는다.

## 5. potion_hp_small 이전 조사

현재 ConsumableDefinitions / EnemyDropDefinitions / ShopEntries / StageRewardDefinitions에는 이전 ID가 없다. 실행 스크립트에서는 Repository의 별칭과 Inventory의 이전 처리에만 남는다. 생성 메타데이터 검색에서도 활성 참조를 찾지 못했다.

현재 사용 가이드 3개와 Data Dictionary의 정의·API 예시는 갱신했다. 과거 Phase1 / Implementation Plan / Union 감사·설계 / Current-Development-Status의 당시 검증 기록은 유지했다. 테스트의 이전 ID는 호환 이전 입력이다. 현재 ShopEntries는 장비 상품이며 소비 아이템 상품은 없다. 이번 작업에서 상품·보상 행을 추가하지 않았다.

## 6. EnemyDropDefinitions 변경 전후

이번 단계 직전 작업 트리의 포션 6행은 모두 orange_potion이었다. 더 이전 Git 기준의 potion_hp_small 교체도 미커밋 상태로 남아 있다. 비교 기준은 `Artifacts/tests/fixtures/EnemyDropDefinitions-before-shogun.csv`에 보관했다.

| DropEntryId | 적 | 이전 → 현재 | 확률 전 → 후 | 수량 전 → 후 | 근거 |
|---|---|---|---|---|---|
| early_potion | early_mushroom | orange → red | 250 → 250 (25%) | 1~1 → 1~1 | 초반 일반 버섯 |
| guard_potion | guard_mushroom | orange → orange | 150 → 150 (15%) | 1~1 → 1~1 | 수비형. 현재 활성 SpawnPool에는 없음 |
| region_01_mushmom_potion | region_01_guardian_boss | orange → white | 1000 → 1000 (100%) | 1~1 → 1~1 | 지역 1 머쉬맘 보스 |
| region_kerning_wraith_potion | region_kerning_wraith | orange → orange | 200 → 200 (20%) | 1~1 → 1~1 | 커닝 일반 레이스 |
| region_kerning_ligator_potion | region_kerning_ligator | orange → orange | 250 → 250 (25%) | 1~1 → 1~1 | 커닝 리게이터 증원 |
| region_kerning_dyle_potion | region_kerning_dyle | orange → white | 1000 → 1000 (100%) | 1~1 → 1~1 | 지역 2 다일 보스 |

red/orange/white는 각각 red_potion/orange_potion/white_potion이다. TriggerType은 모두 기존 ANY_KILL이다. 전체 14행 중 이번 단계에서는 포션 참조 3개만 변경했다. 골드 8행과 모든 SchemaVersion·DropEntryId·EnemyDefinitionId·TriggerType·DropType·ChancePermille·MinAmount·MaxAmount·Enabled·행 순서를 보존했다. 한 행을 포션별로 분할하지 않았다.

비활성 prototype fallback의 early_potion도 빨강으로 맞췄으며 확률·수량·활성화 설정은 유지했다. 결정적 seed는 DropEntryId를 사용하므로 참조 교체가 성공·수량 판정을 바꾸지 않는다. Union ItemDropRate의 기존 보정도 유지한다.

## 7. Ground Presentation

ResolveSpriteRuid가 DropRefId → ConsumableDefinitionRepositoryLogic:GetDefinition → IconKey를 조회한다. ShowDrop 모델·위치·부유 연출·레이어·수거 시 제거 경로를 유지한다. parent는 기존 전투 맵이다.

| 아이템 | 현재 IconKey |
|---|---|
| 빨간 포션 | 234aca1a4ce946119b68e3717991e775 |
| 주황 포션 | 2debf574d6d04f7083e980dbc8f462d9 |
| 하얀 포션 | 289c7bdcbdc8484ab7bad688b2519ca7 |
| 시간의 모래 | 3fd4b286ba544158aa863c2f02983495 |
| 만병통치약 | 47a72a6182e94c099f777402ffd81c3e |

5종은 이전 단계에서 확보한 서로 다른 RUID를 사용한다. 정의·아이콘 누락 때만 기존 ConsumableSpriteRuid를 fallback으로 사용하고 `ICONRESOURCE REQUIRED` 경고를 남긴다. 현재 누락된 IconKey는 없다. 실제 리소스 로딩과 이미지 외형은 Maker에서 미확인이다.

## 8. Union 연동

RunManagerLogic.InitializeNewRunOwnedState → PlayerRunUnionEffectComponent.CaptureForRun → Inventory.ResetForRun 경로를 유지한다. InventorySlotBonus 0/1/2는 3/4/5칸이며 잘못된 보너스도 0~2로 제한한다. 기존 INVENTORY_SLOT 최대 레벨은 2다.

Union 효과는 기존 계약대로 새 런 시작 때 캡처한다. 진행 중 계정 보너스를 바꿔 런 상태를 재계산하는 시스템은 추가하지 않았다. 현재 런 ConsumableCapacity가 변경되면 HUD가 감지한다. 시작 포션도 StartingPotionBonus / orange_potion / 시작 보상 키를 유지하며 같은 초과 정책을 적용한다.

## 9. 테스트 A~P

| 항목 | 양수 결과 | 오프라인 | Maker |
|---|---|---|---|
| A 기본 슬롯 | 3칸, 실제 아이템 3개 제한 | PASS | NOT RUN |
| B Union +1 | 4칸 표시·수용 | PASS | NOT RUN |
| C Union +2 | 5칸 표시·수용, 축소 시 추가 칸 숨김 | PASS | NOT RUN |
| D 중복 아이템 | 빨강 / 빨강 / 주황 개별 아이콘, 같은 y | PASS | NOT RUN |
| E 획득 반영 | 셀 수거 뒤 아이콘 0 → 1 | PASS | NOT RUN |
| F 가득 참 | 3개 보존, gold +1, 바닥 엔티티 제거 | PASS | NOT RUN |
| G 빨간 포션 | HP 5 → 7, 1개 소비, 큐·턴 유지 | PASS | NOT RUN |
| H 하얀 포션 | HP 8 → 10, 1개 소비 | PASS | NOT RUN |
| I 최대 HP | 실패, 요청/수량/리비전 불변 | PASS | NOT RUN |
| J 시간의 모래 | 선택 스킬 3 → 1, 다른 쿨다운 유지 | PASS | NOT RUN |
| K 선택 취소 | 취소 버튼 호출, 수량·턴 불변 | PASS | NOT RUN |
| L 만병통치약 | 상태 없음 사유, 수량·버프 보존 | PASS | NOT RUN |
| M 드롭 메서드 연결 | seeded 사망 → Pending 2건 → 포션 SpriteRUID → 수거 → HUD | PASS | NOT RUN |
| N 승리 자동 수거 | 남은 1칸 충전, 초과 2개 gold +2, Pending/표시 제거 | PASS | NOT RUN |
| O 중복 요청 | 사용·사망·보상 재전송 효과/지급 불변 | PASS | NOT RUN |
| P 확률 보존 | CSV 14행 모든 필드 비교, 허용한 RefId 3개만 차이 | PASS | 해당 없음 |

추가 검사: 주황 +4, 모래 1→0, 미보유/쿨다운 0 거절, 타인·이전 진입·다른 맵·이전 리비전 거절, 적 턴·처리 중·전투 종료 거절, 상점 차감 전 검증, 이전 ID·초과 이전 멱등성, DTO·런/스테이지 변경, 5종 바닥 아이콘, 대상 목록·이벤트 해제.

**기존 회귀 23/23 + Shogun 통합 10/10 = 33/33 PASS**. UIBuilder 구조 검사 PASS, UI lint clean, git diff --check PASS. 엔티티·서비스·RPC 운송·네이티브 입력은 mock이다.

| 증거 | 파일 |
|---|---|
| 기존 회귀 | Artifacts/tests/consumables_test.py |
| 드롭·HUD 통합 | Artifacts/tests/consumables_shogun_test.py |
| UI 구조 | Artifacts/tests/consumable-ui-check.cjs |
| 오프라인 stdout, Maker 로그 아님 | Artifacts/tests/consumables-shogun-results.txt |
| 변경 전 드롭 CSV | Artifacts/tests/fixtures/EnemyDropDefinitions-before-shogun.csv |

재실행: lupa가 설치된 Python으로 `python Artifacts/tests/consumables_shogun_test.py`, Node로 `node Artifacts/tests/consumable-ui-check.cjs`. 이번 환경에서는 LUPA_PATH에 기존 임시 설치 경로를 지정했다.

## 10. Maker Runtime

| 작업 | 결과 |
|---|---|
| 도구 검색 | refresh / play / logs / diagnose 도구 없음 |
| Stop / Clear Logs / Refresh | NOT RUN |
| Build / diagnose | NOT RUN |
| Play / 실제 마우스 클릭·hover | NOT RUN |
| 서버·클라이언트 정상 로그 | NOT RUN |
| 화면·줄바꿈·리소스 실물 | NOT RUN |

새 HUD의 .codeblock을 수동 생성하지 않았다. Maker Refresh에서 스크립트 등록·메타데이터 생성·UI binding 인식을 확인해야 한다. 런타임 ‘오류 0’ 또는 ‘플레이 성공’을 주장하지 않는다.

연결 후 Stop → Clear Logs → Refresh → build logs → Play → normal logs 순서로 검증한다. A~O 행동과 함께 `[BattleConsumableHUD] ready/rendered`, `[EnemyDropRoll] success`, `[BattleDrop] pending added`, `[BattleDropPresentation] shown/removed`, `[RunInventory] reward applied`, `[BattleConsumable] used/cooldown`의 실제 양수 값·순서를 남겨야 한다.

## 11. 남은 작업

- Maker 등록·빌드·플레이와 A~O 실제 입력/화면/서버 로그 검증.
- 아이콘 5개는 지정 완료. 네이티브 로딩·크기·외형 확인 후 필요한 경우 RUID 교체.
- 빨강·주황·하양 모두 활성 적 드롭 경로가 있다. guard_mushroom 행은 있으나 현재 SpawnPool에서 자연 출현하지 않는다.
- 시간의 모래·만병통치약 드롭 확률은 추가하지 않았다. 향후 콘텐츠 밸런스에서 결정한다.
- 상태이상 시스템이 생기면 RemoveNegativeStatusEffects 구현과 만병통치약 HUD 사용 가능 판정을 연결한다.
- 실제 해상도·모바일·긴 설명·다른 HUD와의 시각적 겹침 확인 및 디자인 다듬기.

## 12. Git 및 파일 범위

브랜치 `codex/consumable-items`. **커밋 없음 / 푸시 없음 / PR 생성·머지 없음**. 이번 요청은 로컬 구현 범위로 처리했다.

이번 단계 수정:

- RootDesk/MyDesk/04_Roguelike/RunManager/PlayerRunInventoryComponent.mlua
- RootDesk/MyDesk/01_Combat/Components/Shared/BattleSessionComponent.mlua
- RootDesk/MyDesk/01_Combat/Components/Shared/BattleDropPresentationComponent.mlua
- RootDesk/MyDesk/02_UI/BattleConsumableHudComponent.mlua — 이전 단계 생성, Git 미추적
- RootDesk/MyDesk/03_Data/ConsumableDefinitions.csv
- RootDesk/MyDesk/03_Data/EnemyDropDefinitions.csv
- RootDesk/MyDesk/03_Data/Repositories/EnemyDropDefinitionRepositoryLogic.mlua
- ui/BattleConsumableHUD.ui — 이전 단계 생성, Git 미추적
- Docs/Guide/Battle-Integration-API.md, Development-Workflow-Guide.md, Run-Shop-Authoring-Guide.md
- Docs/MapleTactics-M1-Data-Dictionary.md, 이 보고서
- 기존 오프라인 검사 2개 및 HUD 생성 보조 스크립트

이번 단계 추가: Shogun 통합 검사, 변경 전 CSV fixture, 검사 stdout, `.builder-work/` UI·데이터·가이드 갱신 보조 스크립트.

이전 단계에서 수정된 BattleUnitComponent / SkillRuntimeStateComponent / ConsumableEffectRouterLogic / ConsumableDefinitionRepositoryLogic / RunManagerLogic은 유지했다. 사용자 수정 파일 `ui/BattleUnitHpHUD.ui`, `.codex/config.toml`, hook은 시작·종료 hash가 같음을 확인했다. 그 밖의 기존 미추적 파일도 보존했다. `.codeblock` / `.directory` / Global / Environment / 맵 / 모델은 수정하지 않았다.
