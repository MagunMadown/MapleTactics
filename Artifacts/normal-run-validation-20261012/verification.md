# 정상 진행·상점·개인 기록 검증 — 2026-10-12

판정: 상점/경로/기록의 도구 기반 기능 검증은 통과했다. P0-05 기본 오류 위치 진단의 Column/Value 계약은 미충족이며, Phase 0/1과 M1은 완료 상태로 바꾸지 않는다.

## 환경과 검사 범위

- 브랜치 `codex/battle-session-responsibility-split`, 기준 HEAD `2cec83a`. 사용자 승인 CoreVersion 26.10.0.0의 프로젝트 정의를 사용했다.
- MapBuilder 기존 대조는 26개 MapleTile(0)·Static Map, 전투 세션 맵 20개·운영 최대 1명이다. Player/DefaultPlayer 상속, 적 모델 50개와 스폰 77행은 [모델/배치 대조](model-body-audit.json)에 보존했다. 적의 논리 셀/Transform 배치와 native 물리 Body를 구분했다.
- I/J는 일반 키 입력으로 헤네시스 1·2전투 승리, 3전투 패배까지 진행했다. 전체 20전투 검사는 NORMAL 진입 뒤 Maker 서버에서 실제 `ApplyDamage`를 호출해 진행을 가속했다. HP·승패·웨이브/클리어 플래그를 직접 바꾸거나 prototype 강제 클리어로 대체하지 않았다.
- 상점·다음 노드·결과·기록 조작은 실제 UI 버튼 이벤트와 클라이언트 RPC를 사용했다. 물리 PC 포인터, 일반 전술 입력만으로 전체 완주, 밸런스·화면 체감 검증으로 확대하지 않는다.

## 경로와 기록

| 라운드 | 실제 진행 | 기록과 확인 |
|---|---|---|
| L 상단 | 헤네시스→커닝시티→페리온→슬리피우드, 20전투, 발록→로비 | RunId 61, Schema 3, COMPLETED, Clear 20, 지역 4/4/4/8 모두 완료, 총 1턴/피격 0 |
| M 최종 소스 상단 경계 | 새 NORMAL 런의 헤네시스 4전투→상점 구매→커닝시티 승인, 이후 포기·로비 복귀 | 현재 응답 가드에서 구매·다음 지역 승인 확인. 이전 상단 버튼 pending=true를 재현 조건으로 보존 |
| M 최종 소스 하단 | 새 런→헤네시스→엘리니아→노틸러스→슬리피우드, 20전투, 발록→로비 | RunId 63, Sequence 3, Schema 3, COMPLETED, Clear 20, 지역 4/4/4/8 모두 완료, 총 0턴/피격 0 |

L의 상단 전체 검사는 마지막 응답 문맥 가드 추가 전 결과다. 추가 후에는 M 상단 경계를 다시 실행하고 M 하단 전체를 실행했다. 마지막 수정의 영향 범위를 위와 같이 구분한다.

두 완주 기록에서 Conditions.Captured/ObservedStart=true, NORMAL/ACCOUNT_APPLIED, balance_2026_10_06 및 지역별 클리어/턴/피격 합계와 전체 합계가 일치했다. 슬리피우드 포장마차 중간 보스에서 지역을 끝내지 않고 8번째 최종 보스까지 진행했다. Maker 기록은 RankEligible=false, RankExclusionReason=MAKER_TEST로 공개 등록하지 않았다.

실제 RunHistoryUI에서 최근 행 선택, Clear 20 표시, Regions 경로·완료 배지·페이지 2의 슬리피우드 8전투/턴/피격 문구를 확인했다. Skills/Relics/Augments/Regions 전환은 페이지 1로 복원되고 완료 배지는 Regions에서만 표시됐다. M 로그는 `HISTORY_UI_DONE run=63 clears=20`까지 완료했다.

근거: [상단 진행](upper-route-evidence.json), [하단 진행](lower-route-evidence.json), [하단 기록 UI](lower-history-ui-evidence.json), [최종 소스 상단/새 런/경로 가드](final-route-guard-evidence.json).

## 상점과 새 런

- L은 자연 획득 골드로 페리온 이후 상점에서 work_gloves 40골드를 구매했다. M 최종 소스 반복 런은 첫 상점에서 자연 획득 35골드로 squishy_shoes를 구매하고 커닝시티로 진입했다.
- K 별도 계약 검사는 기존 GrantRunReward로 25골드를 지급했다(35→60). work_gloves 40 구매(60→20), 동일 요청 재전송의 DUPLICATE_PURCHASE_IGNORED와 재열기 보존, 다른 40골드 상품의 INSUFFICIENT_CURRENCY 거절, 빨간 포션 10 구매(20→10), 닫기/재개/퇴장을 확인했다. 이 지급 조건은 일반 수입/경제 밸런스 근거에서 제외한다.
- L/M 전체 경로의 나머지 상점은 구매 없이 출발할 수 있었다. 같은 방문의 재열기는 추첨/가격/판매 상태를 보존하고, 다음 노드 방문은 방문 순번을 증가시켰다.
- 새 런에서 상점 방문 순번 0·영수증/구매 목록 비움, 이전 구매 유물 제거 및 공격/체력/방어 보너스 0을 확인했다. 계정의 기본 보유 유물은 별도로 유지됐다.
- 상단 방문의 RequestPending=true가 남은 상태에서 하단의 반대 경로 요청을 거절해도 선택 경로·활성 다음 노드가 하단으로 유지됐다.

[K 계약 검사와 수정 전 응답 오류](k-before-route-response-fix.json), [반복 방문의 문맥 오류](l-repeat-before-context-guard.json)를 보존했다. 유물 50종 전체 효과를 이번 구매 사례로 검증했다고 판정하지 않는다.

## 재현된 오류와 최소 수정

1. `PlayerGridMovementLogic.OnUpdate`: PresentationProbeRemaining이 없는 요청 상태에서 nil 산술 오류가 났다. 공통 경로의 재탐색 시간에 기존 0.5초 기본값을 적용했다. 누락 상태 회귀와 J 일반 입력 재검증에서 같은 오류가 재발하지 않았다. 누락 상태가 최초 생성된 원인까지 확정한 결과는 아니다.
2. `WorldMapFutureRegionButtonComponent.HandleEntryResult`: 비활성 또는 이전 방문 버튼이 다른 경로의 거절을 받고 현재 월드맵을 바꿨다. pending 요청·현재 POST_SHOP_ROUTE 모드·SelectedRouteId가 해당 버튼과 맞을 때만 실패 UI를 복원한다. 자신의 거절은 재시도 가능하게 유지했다. 회귀 3경우와 M의 실제 이전 pending 상태/하단 잠금 거절을 통과했다.

이번 검증 시작 시점의 MSW 원본 1,366파일을 해시로 비교한 결과 새 변경은 위 두 .mlua뿐이다. CSV·.model·.map·.ui·.config·.codeblock을 수동 수정하지 않았다. 기존 미커밋 분리 작업은 보존했다. [원본 비교](protected-source-check.json), [수정 해시](source-changes.json), [수정 전 이동 오류](before-fix-evidence.json), [수정 후 일반 입력](j-runtime-evidence.json).

## Phase 0 데이터와 RPC

- 실제 서버 문맥의 무송신자 RPC는 INVALID_SENDER로 거절됐다. 클라이언트의 오래된 entry/context와 중복 요청은 셀/턴을 바꾸지 않았다. 다른 UserId 판정은 확인했으나 실제 두 계정/인스턴스 시험은 아니다.
- 실제 WarriorSkillDefinitions 6행 la_mancha_spear Range=3의 Bundle/ValidateSkillById는 성공했다. JSON 복제본의 Range=0은 INVALID_SKILL_RANGE, MatchCount=2는 DATA_DUPLICATE_SKILL_ID로 거절됐다.
- 검사 종료 `DATA_CLONE_PASS originalRange=3 overrides=0`, `DATA_CLONE_DONE`을 확인했다. 두 ContentValidation Error 로그는 고의 오류 거절의 예상 결과이며 정상 진행 오류와 분리한다.
- 기본 ContentIntegrityValidatorLogic.AddError DTO에는 DataSetName/RowIndex/ContentId/DetailReason만 있고 Column/Value가 없다. 직렬화도 `WarriorSkillDefinitions[6]la_mancha_spear=INVALID_SKILL_RANGE`다. 검사 스크립트의 보충 column/injected 출력은 기본 계약이 구현됐다는 근거가 아니다.
- P0-05/06은 🟡를 유지한다. 기본 오류 DTO·직렬화·관련 검증 호출부에 Column/Value 연결 및 회귀/Maker 검증이 필요하다. 이번 검증 요청에서 해당 구조를 새로 구현하지 않았다.

근거: [원본을 바꾸지 않은 데이터 검사](data-clone-evidence.json), [검사 스크립트](server-data-clone-checks.lua).

## 최종 검사와 보존

- Python 회귀 20개 모음 모두 exit 0. 전투/코어 16개 모음 합계 296그룹(이동 38, HUD/상점/경로 11 포함), 튜토리얼 2개·상점 hover/scroll 2개가 추가로 통과했다. 최종 경로 문맥 가드 후 관련 HUD 11그룹을 다시 통과했다.
- Balance schema 74/74, vocabulary exit 0. 새 닫힌 값이나 데이터를 추가하지 않았다. [회귀 결과](regression-results.json), [최종 오프라인 검사](final-offline-checks.json).
- L 전체 정상 로그 Error 0/Warning 19, M 최종 소스 진행·기록 UI까지 Error 0/Warning 22. 경고는 유니온 milestone 문맥 정규화와 고의 잘못된 요청의 거절이다. 데이터 음수 검사 직후의 예상 Error 2건은 별도 파일로 보존했다.
- 실행 전 수집한 빌드에는 Info 1,024개와 기존 IsPCPlatform 폐기 예정 Warning 1개, Error 0이었다. 마지막 Stop→Clear→Refresh→build 확인→Play→로그→Stop 라운드에서는 build Error/Warning 0, 정상 로그 165건 Error/Warning 0과 `FINAL_RESTART_DONE map=lobby players=1 storageKeys=default overrides=0`을 확인했다. 새 LSP diagnose 도구는 없어 실행했다고 보고하지 않는다.
- 검증 저장은 NormalRunVerify20261012 계열 격리 키를 사용했다. 기존 유니온/개인 기록 키를 삭제·초기화하지 않았다. 종료 전 격리 프로필이 캐시에 남은 채 기본 키로 바꾸지 않고 Play를 종료한 후 재시작했다. UnionProfile/RunResultLatestV1/RunResultHistoryIndexV1/RunResultRecordV1: 기본값과 테스트 override 0을 실제 서버에서 확인했다. [재시작 증거](final-restart-evidence.json).
- M 초기 관찰 스크립트의 잘못된 사용자 컴포넌트 접근, yield 중 서버 스크립트 교체로 취소된 정산, 이전 검사 assertion 오류는 제품 오류/성공 판정에서 제외했다. 실제 포기 경로로 복구한 뒤 독립 런에서 다시 검사했다. yield가 끝나고 ROUTE_*_DONE이 나올 때까지 관찰 스크립트를 교체하지 않았다.

## 남은 범위

P0-05 Column/Value 오류 위치 진단, 일반 전술 입력만으로 양쪽 전체 완주, 실제 PC 포인터·슬롯/큐 드래그·상점/기록 표시 판단, 모바일·실제 다중 계정/인스턴스·발행·저장/네트워크 장애와 50종 유물 전체 효과는 남는다. 사용자 유예한 포인터 검증은 이번 도구 검사로 완료 처리하지 않는다.

현재 상태는 [NEXT_WORK_PLAN](../../NEXT_WORK_PLAN.md), [Phase 0](../../Docs/MapleTactics-M1-Phase0.md), [Phase 1](../../Docs/MapleTactics-M1-Phase1.md), [Roadmap](../../Docs/MapleTactics-Roadmap.md)에 반영했다.
