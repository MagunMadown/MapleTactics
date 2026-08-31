# Union Asset Audit

## Scope and search method

- Searched the current project for: `Union`, `Maple Union`, `Legion`, `유니온`, `공격대`, `공격대원`, `공격대 배치`, `전투지도`, `Union Coin`, `Preset`, `attackerSetting`, `unionRaid`, `UIWindow6`, `battle map`, `union board`, `union grade`, and `union preset`.
- Project `.ui` files were inspected through `UIBuilder`; other tracked production files were searched through Git.
- No Union-related name, resource path, or verified Union RUID is currently referenced by project production files. Generic comments containing “battle map” were the only textual matches and are unrelated to Union assets.
- The connected `msw-mcp` exposes official resource search, but project policy requires the validated `msw-search` resource wrapper. Searches used both `resource_pack` and individual `sprite` modes, then `getResource`/resource tags to verify exact names, source paths, and RUIDs.
- A RUID is listed only when the 32-character ID was returned and verified by resource detail/tag lookup. Semantic candidates without a Union-specific name or source path are not accepted as Union assets.

## Asset results

| Asset Purpose | Search Keyword | Resource Name | RUID | Source | Status | Notes |
|---|---|---|---|---|---|---|
| Existing Union assets in project | All requested English/Korean terms | — | — | Current project (`RootDesk`, `map`, and all `.ui` via UIBuilder) | NOT_FOUND | No production reference to Union/Legion/attackerSetting/unionRaid/UIWindow6 was found. |
| Union main window frame | `UIWindow6.img/attackerSetting`, `attackerSetting`, `Maple Union UI` | — | — | MSW official resource index | MANUAL_RESOURCE_SEARCH_REQUIRED | Exact path search returned no result. Semantic `attackerSetting` hits were unrelated mob/minimap sprites after tag verification. |
| Dark blue/gray Union panel backgrounds | `Maple Union UI`, `attackerSetting`, `union board` | — | — | MSW official resource index | MANUAL_RESOURCE_SEARCH_REQUIRED | No result had a verified Union UI source path. Existing project panels are generic and should not be treated as real Union artwork. |
| Union grid / battle-map frame | `UIWindow6.img/attackerSetting`, `공격대 배치`, `유니온 전투지도`, `union battle map frame` | — | — | MSW official resource index | MANUAL_RESOURCE_SEARCH_REQUIRED | Search produced unrelated item/skill/map-background results; no verified `ui/uiwindow6.img` grid frame was returned. |
| Union rank badge / emblem | `유니온 등급`, `노비스 유니온`, `베테랑 유니온`, `마스터 유니온`, `그랜드 마스터 유니온`, `슈프림 유니온`, `Union rank emblem` | — | — | MSW official resource index | MANUAL_RESOURCE_SEARCH_REQUIRED | No candidate had a Union rank name/source path. Candidate `22adc...` was verified as `effect/basiceff.img/MainNotice/EventUandI/Appear/7`, not Maple Union. |
| Union Coin icon | `유니온 코인`, `Union Coin icon` | `유니온 코인` (`sprite-136452`) | `95632823c5e44dab89b9859ff439165b` | MSW official resource index; `item/etc/0431.img`, `04310229/info/iconRaw` | FOUND_IN_MSW | Exact Korean name, sprite type, item category, 28×28. This is the only verified requested UI icon ready for direct reuse. Not currently referenced by the project. |
| Union tab/button frames | `attackerSetting`, `union board`, `Maple Union UI` | — | — | MSW official resource index | MANUAL_RESOURCE_SEARCH_REQUIRED | No exact Union tab/button frame was returned. |
| Union preset button (normal/selected/pressed) | `유니온 프리셋`, `union preset`, `Union preset button`, `UIWindow6` | — | — | MSW official resource index | MANUAL_RESOURCE_SEARCH_REQUIRED | No verified Union-specific preset button path was found. See the rejected generic Coordi preset candidates below. |
| Union preset coupon icon | `유니온 코인`, `유니온 프리셋` | `유니온 프리셋 쿠폰` (`sprite-127058`) | `3575be5e97b04c5fa67662e006aee13b` | MSW official resource index; `item/consume/0243.img`, `02436884/info/iconRaw` | FOUND_IN_MSW | Exact item icon, 32×24. It is a coupon/envelope icon, not a preset UI button. Not currently referenced by the project. |
| Selected/hover grid effects | `attackerSetting`, `공격대 배치`, `union board`, `selected grid`, `hover grid` | — | — | MSW official resource index | MANUAL_RESOURCE_SEARCH_REQUIRED | No verified `ui/uiwindow6.img` selection/hover effect was found. |
| Character/block slot backgrounds | `공격대원`, `공격대 배치`, `union block slot`, `attackerSetting` | — | — | MSW official resource index | MANUAL_RESOURCE_SEARCH_REQUIRED | Semantic results lacked Union names/source paths. |
| Historical attacker-setting path | `UIWindow6.img/attackerSetting` | — | — | MSW official resource index | MANUAL_RESOURCE_SEARCH_REQUIRED | Exact query returned zero results. The path may not be indexed as searchable text or may require manual Maker resource browsing. |
| Historical Union Raid UI path | `UIWindow6.img/unionRaid` | — | — | MSW official resource index | MANUAL_RESOURCE_SEARCH_REQUIRED | Exact query returned zero results. |
| Union Raid thematic background | `unionRaid`, `유니온 전투지도` | `sprite-9094183` (`map/back/mapleunion.img`, `back/4`) | `83f4c25c940e49aca6f240619ba4ff6c` | MSW official resource index | FOUND_IN_MSW | Verified tags include `유니온 레이드`; 432×460 lava/volcano background. This is map scenery, not the Union management-window frame. |
| Union Raid thematic prop/background | `unionRaid`, `유니온 전투지도` | `sprite-9091020` (`map/back/mapleunion.img`, `back/21`) | `2aefbe890905430ca0afe18a5a9bc96f` | MSW official resource index | FOUND_IN_MSW | Verified tags include `유니온 레이드`; 168×160 battle-preparation props. Not a Union UI frame. |
| Generic preset button, normal (rejected as Union-specific) | `Union preset button` | `sprite-12953449` | `631aa017e7644d5e97fd70a7f21703b9` | MSW official resource index; `ui/uiwindow4.img`, `Equip/Cash/BtCoordiPreset/normal/0` | FOUND_IN_MSW | Exact source is Cash equipment/coordi preset UI, not Maple Union. Do not use as evidence that the real Union preset asset was found. |
| Generic preset button, pressed (rejected as Union-specific) | `Union preset button` | `sprite-12953432` | `a6fa6d6ad3de40e4951281b5ff746a29` | MSW official resource index; `ui/uiwindow4.img`, `Equip/Cash/BtCoordiPreset/pressed/0` | FOUND_IN_MSW | Same non-Union Coordi preset family. Useful only as an explicitly approved fallback, not as the preferred real-Union reference. |

## STEP 6 UI shell asset usage

`TO_REPLACE_WITH_OFFICIAL_RESOURCE` means STEP 6 intentionally uses a project-existing Maple-style fallback because no exact `UIWindow6.img/attackerSetting` or `UIWindow6.img/unionRaid` management-UI sprite was verified. These rows are implementation substitutions, not claims that an official Union asset was found.

| Asset Purpose | Search Keyword | Resource Name | RUID | Source | Status | Notes |
|---|---|---|---|---|---|---|
| Union Points icon | `유니온 코인` | `유니온 코인` (`sprite-136452`) | `95632823c5e44dab89b9859ff439165b` | MSW official resource index; `item/etc/0431.img`, `04310229/info/iconRaw` | FOUND_IN_MSW | Used directly in the STEP 6 lobby entry button and current-points panel. Exact name and RUID were already verified in this audit. |
| Union main window and dark panel shell | `UIWindow6.img/attackerSetting`, `Maple Union UI` | Project generic solid UI sprite | `2860136c06ab075439721c027de365af` | Existing project use in `ui/CharacterSelectionUI.ui` | TO_REPLACE_WITH_OFFICIAL_RESOURCE | Reused only as a tintable nine-slice-style shell. Replace with a verified Union main frame/panel family when Maker resource browsing supplies exact metadata. |
| Union board/grid frame | `attackerSetting`, `공격대 배치`, `union board` | Project generic solid UI sprite | `2860136c06ab075439721c027de365af` | Existing project use in `ui/CharacterSelectionUI.ui` | TO_REPLACE_WITH_OFFICIAL_RESOURCE | Used for the four-region board, region blocks, and core frame. It is not presented as the original Maple Union board artwork. |
| Union rank emblem frame | `유니온 등급`, `Union rank emblem` | Project generic frame with text rank code | `2860136c06ab075439721c027de365af` | Existing project use plus runtime text | TO_REPLACE_WITH_OFFICIAL_RESOURCE | Temporary `N/V/M/GM/S` text emblem. No emblem RUID is fabricated; replace the whole frame when a verified rank-badge family is available. |
| Preset/apply/reset button frames | `유니온 프리셋`, `Union preset button` | Project generic solid UI sprite | `2860136c06ab075439721c027de365af` | Existing project use in `ui/CharacterSelectionUI.ui` | TO_REPLACE_WITH_OFFICIAL_RESOURCE | Display-only disabled shells in STEP 6. The rejected Coordi preset RUIDs were deliberately not used. |
| Grid selected/hover effects | `selected grid`, `hover grid`, `attackerSetting` | — | — | STEP 6 display-only shell | MANUAL_RESOURCE_SEARCH_REQUIRED | No selection/hover state is drawn in STEP 6. Purchasing/placement interaction remains outside this step. |

## STEP 7 interaction asset usage

| Asset Purpose | Search Keyword | Resource Name | RUID | Source | Status | Notes |
|---|---|---|---|---|---|---|
| Upgrade node states and hover | `Union node`, `attackerSetting`, `unionRaid` | Project generic solid UI sprite | `2860136c06ab075439721c027de365af` | Existing project fallback | TO_REPLACE_WITH_OFFICIAL_RESOURCE | Runtime tint, outline, and button transitions distinguish LOCKED, PURCHASED INACTIVE, ACTIVE, MAX LEVEL, hover, and selected states. No RUID was fabricated. |
| Major purchase confirmation frame | `Union major confirm`, `UIWindow6` | Project generic solid UI sprite | `2860136c06ab075439721c027de365af` | Existing project fallback | TO_REPLACE_WITH_OFFICIAL_RESOURCE | Lightweight confirmation only; replace when a verified official Union dialog/frame asset is available. |

STEP 7 introduced no new or guessed resource identifier. The verified Union Coin resource remains `95632823c5e44dab89b9859ff439165b`.

## Rejected or insufficient search hits

- `mob/9020100.img` was returned for several Union terms because its names include `유니온 PVP 플레이어 AI`. It is a resource pack/mob result, not a Union management UI asset, and its pack path is not a sprite RUID.
- `skill/3214.img/skill/32141004` is `유니온 오라`, a combat skill resource, not Maple Union meta-progression UI.
- `22adc5a5767542bf94f73c90b7a322e3` visually resembles an emblem but its verified source is the U&I event notice effect, not a Union rank badge.
- Semantic `attackerSetting` hits resolved to unrelated mob sprites and map minimap canvases.
- Generic “Preset” hits from `ui/uiwindow4.img/Equip/Cash/BtCoordiPreset` belong to the equipment/coordination preset UI, not `UIWindow6` Union UI.

## Planned asset usage (no implementation yet)

1. **Directly approved for later prototyping:** the verified Union Coin icon `95632823c5e44dab89b9859ff439165b`.
2. **Conditional thematic use:** Union Raid background resources `83f4...` and `2aef...` may support a raid-themed backdrop, but they must not substitute for the management-window frame or grid.
3. **Manual search remains mandatory before UI implementation:** main frame, dark blue/gray panels, grid/battle-map frame, rank badge/emblem, Union-specific tabs/buttons/preset states, grid hover/selected effects, and character/block slot backgrounds.
4. **Do not use yet:** generic Coordi preset buttons. They are recorded only to prevent a future false-positive identification.
5. **No replacement art was created.** If manual Maker resource browsing still cannot locate the exact `UIWindow6` families, the next design step should explicitly decide between licensed/available MSW substitutes and newly authored art.

## Manual resource search checklist

Search inside Maker/MSW resource browsing with path-oriented terms and inspect metadata/source paths, not thumbnails alone:

- `ui/uiwindow6.img/attackerSetting`
- `ui/uiwindow6.img/unionRaid`
- `UIWindow6 attackerSetting`
- `UIWindow6 unionRaid`
- `공격대 배치`
- `공격대원`
- `유니온 전투지도`
- `유니온 등급`
- `유니온 프리셋`

For every manually found item, record its exact displayed resource name, 32-character sprite RUID, resource type, original path/subPath, dimensions, and normal/hover/pressed relationship before it is admitted to implementation.

## STEP 9 resource re-search and final board usage

STEP 9 repeated the validated MSW resource search in both `resource_pack` and `sprite` modes with `유니온`, `공격대`, `공격대원`, `공격대 배치`, `전투지도`, `Union emblem`, `Union coin`, `Union board`, `Union grid`, `Union button`, `Union rank`, `Union background`, `Union frame`, `attackerSetting`, `unionRaid`, and `UIWindow6`. Exact searches for `UIWindow6.img/attackerSetting` and `UIWindow6.img/unionRaid` again returned zero results. Consequently, the only verified official Union management UI resource used by STEP 9 is the Union Coin icon.

| Asset Purpose | Search Keyword | Resource Name | RUID | Source | Status | Notes |
|---|---|---|---|---|---|---|
| Union Points icon | `유니온 코인`, `Union coin` | `유니온 코인` (`sprite-136452`) | `95632823c5e44dab89b9859ff439165b` | MSW official resource index; `item/etc/0431.img`, `04310229/info/iconRaw` | FOUND_IN_MSW | Verified 28×28 sprite. Used in the lobby entry and the prominent current-points display. |
| Connected board cells, paths, and region frames | `Union grid`, `Union board`, `공격대 배치`, `전투지도` | Project generic solid UI sprite | `2860136c06ab075439721c027de365af` | Existing project UI fallback plus UIBuilder layout | TO_REPLACE_WITH_OFFICIAL_RESOURCE | Ninety-six dark grid cells, region panels, connectors, and node frames are code-native UI layout using an existing tintable sprite. This is not claimed as official Union artwork. |
| Center Union Core | `Union core`, `Union emblem`, `Union rank` | Project generic frame with server-driven rank text | `2860136c06ab075439721c027de365af` | Existing project fallback | TO_REPLACE_WITH_OFFICIAL_RESOURCE | Shows the current data-driven Union rank. No emblem RUID was fabricated. |
| Rank-locked region overlay | `Union rank`, `union board` | Project generic panel and text | `2860136c06ab075439721c027de365af` | Existing project fallback plus runtime text | TO_REPLACE_WITH_OFFICIAL_RESOURCE | Locked regions remain visible and dimmed; their required rank name comes from `UnionRankDefinitions.csv`. |
| Major node frames | `Union major node`, `Union grid` | Project generic panel with gold outline | `2860136c06ab075439721c027de365af` | Existing project fallback | TO_REPLACE_WITH_OFFICIAL_RESOURCE | `STARTING_SKILL` and `STARTING_RANDOM_RELIC` use larger footprints and gold emphasis. Cell footprint is visual only. |
| Selected, hover, and purchase feedback | `selected grid`, `hover grid`, `Union button` | Project generic button states and runtime outline | `2860136c06ab075439721c027de365af` | Existing project fallback plus `ButtonComponent` transitions | TO_REPLACE_WITH_OFFICIAL_RESOURCE | Selection uses cyan outline; a successful purchase briefly pulses gold. No new feedback framework was introduced. |
| Exact Union management-window families | `UIWindow6.img/attackerSetting`, `UIWindow6.img/unionRaid` | — | — | MSW official resource index | MANUAL_RESOURCE_SEARCH_REQUIRED | Both exact path queries returned zero results in both search modes. Maker resource browsing remains required. |

### STEP 9 rejected semantic candidates

- `6b6e2bc2418440b2b41cf29c7812ff24` is `ui/uiwindow2.img`, `SkillZero/main/skillBlank`; it is a generic skill blank, not a Union grid cell.
- `5f8252d0fb044b159f07185c5c634a19` is `ui/uiwindowevent.img`, `goldenChariotEvent/cover`; it is unrelated event UI.
- `3160b729001245c8a3ad0d22797c3495` is from `ui/basic.img` cursor paths; it is not a Union selection effect.
- `f397621fbda74148818c7aebcefcfa83` is `ui/uiwindowstring.img`, `Zero_Weapon/Bt_Fire/disabled/0`; it is not a Union button.
- `6a912712dc194e299f148003b887733a` is `ui/uiwindowstring.img`, `TDillustDig.../BtQNo/normal/0`; it is unrelated UI.
- `69bf8e0f2d834ec1bc0e303217ee796f` is `ui/uiwindow4.img` character-preset UI; it is not a Union preset or board button.

The STEP 6/7 preset rows above are retained as historical audit evidence only. STEP 8 removed preset and activation-loadout UI, and STEP 9 does not use those resources or controls.

## STEP 8.5 Lobby Union NPC resource audit

The official MSW resource index was searched in `resource_pack` NPC mode before selecting an appearance. Searches covered `유니온`, `메이플 유니온`, `공격대`, `공격대 관리자`, `유니온 관리자`, `Union`, `Maple Union`, `Union NPC`, `Legion`, `attackerSetting`, and `unionRaid`. No result was verified as an official Maple Union management NPC. Administrator/receptionist/strategist fallback searches then covered `관리자`, `접수원`, `전략가`, `연합 관리자`, and `나인하트`.

| Asset Purpose | Search Keyword | Resource Name | RUID | Source | Status | Notes |
|---|---|---|---|---|---|---|
| Official Maple Union NPC | `유니온`, `메이플 유니온`, `공격대 관리자`, `유니온 관리자`, `Maple Union`, `Union NPC`, `attackerSetting`, `unionRaid` | — | — | MSW official resource index | NOT_FOUND | Results were unrelated NPCs, Union Aura content, Union PVP mobs, or semantic name matches. None had a verified Maple Union NPC identity. |
| Lobby Union administrator fallback | `전략가`, `나인하트` | `나인하트`, `npc/1530070.img`, `stand` | `c2919dc57fac457c9ce94fe32f8b69d2` | MSW official resource index | FOUND_IN_MSW | Verified `animationclip`, NPC category, 52×80. Resource tags contain Korean name `나인하트`, source path `npc/1530070.img`, and `stand` subpath. Used directly by the Lobby `SpriteRendererComponent`; the in-game role label remains `유니온 관리자`. |
| Generic manager alternative | `유니온 관리자` | `매니저`, `npc/1530402.img`, `stand` | `f1882a2e14da47e9938f23f9cfba275f` | MSW official resource search result | FOUND_IN_MSW | Exact pack name was returned, but it was not selected because the verified strategist presentation fits the Union facility more closely. |
| Existing project NPC presentation | Existing `StaticNPC` entities | `StaticNPC` component composition and NameTag frame | `9bf18287398c44699c20fc5123d1a1ae` (NameTag) | `map/new_skill_stage.map` | FOUND_IN_PROJECT | Reused the existing StaticNPC component convention: SpriteRenderer, Rigidbody for MapleTile, State/StateAnimation, ChatBalloon, and NameTag. |

No NPC RUID was guessed. If an official Maple Union NPC becomes discoverable through manual Maker browsing later, replace only the selected stand animationclip and display identity; the shared Lobby interaction route does not depend on the fallback character.

## Union Battle Map visual rework

The visual-rework pass repeated exact and semantic searches in both `resource_pack` and `sprite` modes. `UIWindow6.img/attackerSetting` and `UIWindow6.img/unionRaid` again returned no exact management-UI asset. The board therefore combines the two verified Union-specific MSW resources with Maple-style frame resources already registered in this project. Project resources below are reported only as `FOUND_IN_PROJECT`; public resource metadata could not be verified and they are not claimed as official Union artwork.

| Asset Purpose | Search Keyword | Resource Name | RUID | Source | Status | Notes |
|---|---|---|---|---|---|---|
| Union Points icon | `유니온 코인`, `Union coin` | `유니온 코인` (`sprite-136452`) | `95632823c5e44dab89b9859ff439165b` | MSW official resource index; `item/etc/0431.img` | FOUND_IN_MSW | Verified exact Union resource. Retained in the right-side currency panel. |
| Battle-map thematic backdrop | `unionRaid`, `유니온 전투지도` | `sprite-9094183` (`map/back/mapleunion.img`, `back/4`) | `83f4c25c940e49aca6f240619ba4ff6c` | MSW official resource index | FOUND_IN_MSW | Verified Union Raid background. Used at low opacity behind the continuous board; it is not represented as a management-window frame. |
| Main Maple-style outer frame | Existing project Collection UI | Collection outer frame | `7995ae69d68d431cac74097bc100b4b7` | `ui/CollectionUI.ui` | FOUND_IN_PROJECT | Replaces the flat dark dashboard shell. Exact public resource metadata is unverified. |
| Header frame | Existing project Collection UI | Collection header frame | `5d241898526c4415a055b977e3c77fa2` | `ui/CollectionUI.ui` | FOUND_IN_PROJECT | Reused for the Union title bar. |
| Board and panel section frame | Existing project Collection UI | Collection section frame | `360816ef52c648b788f50821e360e732` | `ui/CollectionUI.ui` | FOUND_IN_PROJECT | Used as the common Maple-style board-section frame. |
| Inner board/detail frame | Existing project Collection UI | Collection inner panel | `c24adedc9faa457daf4e4aae7cd663bb` | `ui/CollectionUI.ui` | FOUND_IN_PROJECT | Used for the board, right panel, and selected-upgrade detail. |
| Currency/effects info frame | Existing project Collection UI | Collection metadata panel | `b5f829660fbc4a58aaac8b8f4e22775f` | `ui/CollectionUI.ui` | FOUND_IN_PROJECT | Used for compact right-side information blocks. |
| Union core/rank frame | Existing project Collection UI | Collection preview frame | `a7928ea51274446898d8453eb96ee06f` | `ui/CollectionUI.ui` | FOUND_IN_PROJECT | Used to emphasize the non-purchasable center Union Core. |
| Upgrade node frame | Existing project Collection UI | Collection card frame | `89e93d0c2c8049138f3c217ce7c648cb` | `ui/CollectionUI.ui` | FOUND_IN_PROJECT | Runtime tint and outline communicate available, purchased, maximum, locked, major, and selected states. |
| Button/dialog control frame | Existing project Collection UI | Collection button frame | `e22dca176e7c48b39d5b40554b546e22` | `ui/CollectionUI.ui` | FOUND_IN_PROJECT | Used for close, refresh, purchase, and confirmation controls. |
| Core ornament | Existing project Collection UI | Collection ornament | `886d7a11f39941c785419ae68d90683d` | `ui/CollectionUI.ui` | FOUND_IN_PROJECT | Used inside the Union Core without claiming it is an official Union emblem. |
| Exact Union main window, rank badge, grid cells, tabs, buttons, and selection effects | `UIWindow6.img/attackerSetting`, `UIWindow6.img/unionRaid`, `Union board grid`, `유니온 등급 엠블럼`, `유니온 버튼` | — | — | MSW official resource index | MANUAL_RESOURCE_SEARCH_REQUIRED | Exact and semantic API searches found no verifiable management-UI family. Replace the project frame family only after Maker resource browsing yields exact names and RUIDs. |

## Territory-board rework verification (2026-08-28)

This pass supersedes the earlier floating-node presentation rows. The validated MSW resource wrapper was run again with `유니온 공격대 배치`, `attackerSetting`, `unionRaid`, `UIWindow6 union`, and `Union battle map`, followed by exact resource-detail lookup for every reused Union RUID. All searches returned `exactMatch=false`; semantic results outside the verified Union Raid background family were rejected.

| Asset Purpose | Search Keyword | Resource Name | RUID | Source | Status | Notes |
|---|---|---|---|---|---|---|
| Union Points icon | `유니온 코인` | `유니온 코인` (`sprite-136452`) | `95632823c5e44dab89b9859ff439165b` | MSW official resource detail; sprite/item, 28×28 | FOUND_IN_MSW | Exact Korean resource name was returned. Still used in the right-side Union Points panel. |
| Continuous battle-map backdrop | `unionRaid`, `Union battle map` | `sprite-9094183` | `83f4c25c940e49aca6f240619ba4ff6c` | MSW official resource detail; sprite/background, 432×460 | FOUND_IN_MSW | Verified resource detail and retained at low opacity behind the 96-cell board. Resource detail has no display name; it is not claimed as the `UIWindow6` management frame. |
| Union Raid thematic prop candidate | `유니온 공격대 배치`, `unionRaid` | `sprite-9091020` | `2aefbe890905430ca0afe18a5a9bc96f` | MSW official resource detail; sprite/background, 168×160 | FOUND_IN_MSW | Verified candidate but not used in the territory board because it would compete with cell readability. |
| Territory cells and transparent path hit areas | `공격대 배치`, `attackerSetting`, `Union board grid` | Project tintable UI sprite | `2860136c06ab075439721c027de365af` | Existing project UI | FOUND_IN_PROJECT | Used for all 96 connected cells and invisible territory-level click surfaces. The old collection-card node RUID is no longer used by board upgrades. Runtime color/outline shows purchased, next, selected, and rank-locked states. |
| Floating upgrade card frame | Existing board audit | Collection card frame | `89e93d0c2c8049138f3c217ce7c648cb` | Existing project UI | NOT_FOUND | Removed from the current Union board presentation. Upgrade selection is now a transparent territory hit area plus a short label; no visible per-upgrade panel remains on the grid. |
| Official Union management window/frame | `UIWindow6.img/attackerSetting`, `attackerSetting`, `UIWindow6 union` | — | — | MSW official resource search | MANUAL_RESOURCE_SEARCH_REQUIRED | No exact management-window, rank-emblem, grid-cell, or selected-cell family was verified. Semantic `attackerSetting` and `UIWindow6 union` hits were unrelated sprites. |
| Official Union selected/hover cell effects | `attackerSetting`, `Union board cell`, `공격대 배치` | — | — | MSW official resource search | MANUAL_RESOURCE_SEARCH_REQUIRED | Current gold outline and muted regional fill are project-native runtime presentation and remain temporary until exact official resources are found. |

No RUID was fabricated in this pass. The UI uses the verified Union Coin and Union Raid backdrop, then falls back to the project’s existing Maple-style frame/cell family for the unavailable management UI resources.

## NEW STEP 6 allocation UI asset verification (2026-08-31)

이 섹션은 위 Territory-board 기록을 대체하는 현재 production UI 자산 감사다. 검증된 msw_resource_api.cjs로 MapleStory blue UI panel, MapleStory UI button을 sprite + etc + topK 3으로 검색했고, 유니온 코인은 RUID 상세 조회를 다시 수행했다.

| Asset Purpose | Search/Source | RUID | Verification | Current Use |
|---|---|---|---|---|
| Union Coin | exact detail 유니온 코인, sprite-136452, sprite/item, 28×28 | 95632823c5e44dab89b9859ff439165b | FOUND_IN_MSW | 우측 Union Coin 요약 |
| Outer frame | existing CollectionUI.ui frame family | 7995ae69d68d431cac74097bc100b4b7 | FOUND_IN_PROJECT | 메인 창 |
| Header frame | existing CollectionUI.ui frame family | 5d241898526c4415a055b977e3c77fa2 | FOUND_IN_PROJECT | 제목 바 |
| Section frame | existing CollectionUI.ui frame family | 360816ef52c648b788f50821e360e732 | FOUND_IN_PROJECT | 스탯/직업 패널 |
| Summary inner frame | existing CollectionUI.ui frame family | c24adedc9faa457daf4e4aae7cd663bb | FOUND_IN_PROJECT | 우측 요약 |
| Metadata panel | existing CollectionUI.ui frame family | b5f829660fbc4a58aaac8b8f4e22775f | FOUND_IN_PROJECT | Coin/Point/Effect/Future 카드 |
| Rank frame | existing CollectionUI.ui frame family | a7928ea51274446898d8453eb96ee06f | FOUND_IN_PROJECT | Union Rank |
| Stat/job card | existing CollectionUI.ui frame family | 89e93d0c2c8049138f3c217ce7c648cb | FOUND_IN_PROJECT | 4×2 스탯과 5직업 카드 |
| Button frame | existing CollectionUI.ui frame family | e22dca176e7c48b39d5b40554b546e22 | FOUND_IN_PROJECT | 닫기, [+], 무료 초기화 |

### Search candidates not admitted

- d7c38171ece441f7984b39b06b3507e4, b9bc39d744cc4f2b8a342300e55605df: 132×168 sprite/etc 후보지만 이름과 Union 출처가 없어 사용하지 않았다.
- f084b761427e4f0da59b531274907c99, b760aafccbb143dfbc1775a356fee766: 108×28 sprite/etc 버튼 후보지만 비정상적으로 큰 원본 pivot과 Union 출처 부재로 사용하지 않았다.
- 7578d43ff51a4ce0a86ed67db56622f1: 232×52 sprite/etc 후보지만 Union 전용 자산임을 검증할 수 없어 사용하지 않았다.
- style-4-blue 문서의 패널/버튼 RUID들은 transaction-flow 구조 참고용으로만 검토했다. 현재 public batch detail에서 notFound였으므로 이번 UI에 사용하지 않았다.

Battle Map/Union Raid backdrop 83f4c25c940e49aca6f240619ba4ff6c와 96-cell용 generic sprite는 현재 배분 UI에서 제거됐다. 신규 RUID를 추측하거나 제작하지 않았다.

### Maker visual verification

실제 Play 카메라에서 0 진행, 요구된 혼합 직업 상태, MAX_HP 배분 후 상태, Reset 후 상태를 캡처했다. 4×2 Stat grid가 시각적 주 영역이고, 하단 5직업 strip과 우측 Rank/Coin/Point/Effect 요약이 분리되어 보였다. Korean Maple font는 카드명·잠금·준비 중·포인트 요약에서 렌더링됐고, Battle Map/96-cell/Block Shop/Legacy purchase 표현은 화면에 없었다.
