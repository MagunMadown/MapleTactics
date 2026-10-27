# 런 유물 발동 가이드

## 정의와 획득

RelicDefinitions의 선택 열 AcquisitionType/AcquisitionSourceId는 새 런에서 정의·가격과 함께 캡처한다. 열이 없거나 종류가 비면 GENERAL/빈 출처다.

| 종류 | 출처 | 허용 경로 |
|---|---|---|
| GENERAL | 빈 값 | 기존 공용 상점·시작 유물·직업 보스 추첨 |
| REGION_SHOP | 활성 RegionId | 지정 지역의 기념 슬롯, 이후 기존 판매/되사기 |
| BOSS_CLEAR | BOSS StageId | 해당 보스 확정 지급, 런당 1회 |

보스 출처는 유물 간 중복될 수 없다. 이 유물은 상점 구매·판매·시작 추첨에 넣지 않는다. 일반 GrantRelic(id,key)는 GENERAL만 지급한다. 출처가 필요한 서버 경로는 GrantRelicFrom(id,key,kind,source)를 사용하며 캡처 정의·미보유·IsOpen·직업·영수증을 함께 검사한다. 결과 ITEM 표시 경로는 동일하다.

## 오르비스 6종 발동 계약

수치와 획득 목록은 [오르비스 구현 가이드](Orbis-Content-Implementation.md#오르비스-기념-유물-2026-10-24)를 따른다.

- 별조각: 등록 슬롯이 2개 이상인 큐의 마지막 공격 스킬에서 첫 직접 타격에 +1. 광역/다단/반복을 합쳐 큐당 한 번이다. 마지막 슬롯이 비공격이거나 실행되지 않으면 발동하지 않는다. 반복 시전은 슬롯 수를 늘리지 않는다.
- 달조각: 승인된 일반 TURN만 충전하며 중첩하지 않는다. 다음 공격 시전이 소비하고 양수 직접 명중 시 그 스킬 쿨다운을 1 줄인다. 빗나가도 충전은 소비한다. 이동·장전·비공격 스킬은 보존하고, 혼란·스킬 강제 방향 전환은 충전하지 않는다.
- 태양조각: 동일 시전의 양수 직접 피해를 받은 고유 적 ID가 2개 이상이면 HP 1, 큐당 한 번이다. 같은 적 다단·독·화상·충돌은 대상 수를 늘리지 않는다. 사망 정산보다 먼저 회복하고 공통 HP 동기화로 다음 전투에 승계한다.
- 돌조각: 제자리에서 소비 행동 두 번을 완료하면 다음 직접 피해 −1(최소 0)을 준비한다. 전체 큐는 한 행동이고 무료/거절 요청은 세지 않는다. 모든 셀 변경은 미완성 진행만 초기화한다. 준비된 방어는 이동해도 유지한다. 완전 방어 뒤·치명상 생존 앞에 적용하며, 완전히 막힌 피격과 상태 피해에는 소비하지 않는다.
- 왕관: 전멸 뒤 다음 웨이브의 실제 적 출현에 HP 1. 첫 웨이브·겹치는 강제 증원·최종 승리에는 발동하지 않는다. 같은 웨이브의 중복 통지는 한 번으로 처리한다.
- 깃털: 첫 유효 해로운 상태를 막고 다음 소비 플레이어 행동 종료까지 상태 면역을 유지한다. 봉인·행동 정지(빙결/기절)·중독·화상·동상·혼란을 막는다. 피해는 막지 않는다. 같은 적 턴의 연속 적용을 전부 막고 무료/거절 입력은 면역을 끝내지 않는다.

회복은 최대 HP에서 멈추며 죽은 플레이어를 살리지 않는다. 웨이브 전환은 전투 상태를 초기화하지 않는다. 전투 키 RunSequence:StageId:EntryRequestId가 바뀔 때 초기화하며 동일 키 재초기화/결과 재처리로 재충전하지 않는다. 유물 판매 후 재계산은 해당 유물의 남은 충전을 제거한다.

## 구현 소유권과 검사

PlayerRunRelicEffectComponent.ContentRelicState가 전투 상태를 소유한다. ContentRelicTriggerLogic은 상태 없는 판정기다. BattleSession은 기존 담당 로직을 연결하고 HP/쿨다운/인벤토리 원본은 각 컴포넌트가 변경한다.

새 효과나 획득 종류를 만들면 Repository/Validator와 Balance Studio의 RELIC_SPECIAL_EFFECTS/#vocabCatalog를 함께 갱신한다. node tools/check-balance-vocab.cjs와 node --test tools/balance-schema.test.cjs를 실행한다. 전용 실제 Lua 검사는 Artifacts/orbis-content/verify-relics.py이며 ORBIS_LUA_PATH에 lupa 설치 경로를 지정한다. Maker 실제 입력·원시 실행 결과는 relic-maker-verification.json에 따로 기록한다. 자연 완주 평가는 기능 검사와 구분한다.

## 준비·발동 표시

일반·직업 유물 12효과 유형을 포함한 전투용 상태 줄의 문구·영수증·초기화와 검증 범위는 [유물 피드백 가이드](Run-Relic-Feedback-Guide.md)를 따른다. 로컬 Lua/UI 검사는 통과했으며 이번 HUD의 Maker 화면·입력 검증은 대기 상태다.
