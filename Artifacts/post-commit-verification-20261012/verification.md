# 커밋 이후 검증 결과

2026-10-12 · CoreVersion 26.10.0.0 · 기준 커밋 4d02a54d856b982db0e002d09d23c054d7afc692

튜토리얼·세션 분리·공통 이동·상점 경로 응답 수정의 최종 커밋을 다시 검증했다. 기존 회귀 20개 모음, 밸런스 스키마 74개 검사와 vocabulary 검사를 통과했고, Maker 자동 진입·이동·스킬 실행·점유 거절·로비 복귀를 확인했다. 종료 직후 새로 발견한 지갑 RPC 오류는 요청 사용자 확인을 추가하고 별도로 재검증했다. 검증 당시 추가 수정과 이 기록은 미커밋 상태였다. 지갑 수정·회귀·종료 근거는 2026-10-13에 `23ed81b`로 커밋했다.

## 오프라인 확인

- [회귀 20개 모음](regression-results.json) 전부 종료 코드 0. 전투·이동·HUD 16개 모음의 296그룹과 튜토리얼·상점 4개 모음이다.
- node --test tools/balance-schema.test.cjs: 74/74. node tools/check-balance-vocab.cjs: 누락 값 0. [실행 출력](initial-build-and-offline.json).
- [세션 계약](source-contract-check.json): 정리 전·후 공개 메서드 288개, 반환형·인자·ExecSpace 차이 0. 새 책임 로직 14개의 .mlua/.codeblock 쌍이 존재하고 메타데이터 JSON을 읽을 수 있다.
- 지갑 수정 후 [회귀 7그룹](wallet-regression-results.json) 및 기존 union-free-job-token-test.py 10그룹 통과. 원본 메서드는 퇴장 사용자 검사에서 실패했고 수정 후 통과했다.
- git diff 2cec83a..HEAD --check 및 수정 후 git diff --check 통과. 직접 호출 가능한 mLua LSP 진단 도구는 없어 새 LSP 실행을 주장하지 않는다.

## Maker 대표 경로

Maker stop → clear_logs → refresh → build 로그 → play → context 확인 → 실제 keyboard_input/execute_script → normal 로그 → stop 순서로 확인했다. keyboard_input은 Maker 입력 경로이며 물리 PC 포인터 검증을 대신하지 않는다.

| 시나리오 | 확인 결과 |
|---|---|
| 로비 D/A | 두 번의 한 칸 이동 후 원위치 복귀. 각각 0.24초, 착지 corrected=false, 서버/클라이언트 이동 상태 해제 |
| 맵 자동 연습 진입 | AutoStartPrototypeBattle=true의 OnMapEnter 경로. 콘텐츠 감사 6지역/28스테이지/158스킬 등 정상, entry initialized success=true |
| 전투 D/A 및 W | 셀 2→3→2, Left 방향 전환. 착지 두 번 corrected=false |
| 1번 슬롯 장전·Space 실행 | 현재 슬롯 divine_swing 장전, 큐 완료, 실제 적 HP 30→28, DamageSkin 1회, 모션 게이트 해제, PlayerTurn/빈 큐 복귀 |
| 점유 셀 A | CELL_OCCUPIED 거절. 셀 2와 턴 6 유지, 클라이언트 예측·거절 표시 정리 |
| 공통 이동 설정 | 로비/전투 GetDuration 0.24/0.24, 전투 홉 재생 1배, 완료 후 client pending=false |
| 로비 복귀 RPC | 클라이언트 RunAbandonLogic.RequestAbandonRun → 세션 포기·결과 담당 로직 → 로비. 런 Idle, 이전 전투 이동·착지 검사 없음 |
| 복귀 후 D/A | 로비 입력 재개, 0.24초, 서버/클라이언트 최종 위치 일치, pending/blocked=false |
| 상·하단 경로 응답 | 각 5사례: 요청 없음·이전 경로·이전 화면 거절 응답 무시, 현재 요청 거절은 같은 경로 재시도 가능, 중복 응답 무시. 실제 UI 컴포넌트 메서드 호출 검사 |
| 새 Play | 기본 저장 키 4개 복원, 데이터 override=0, RunSequence=0, lobby 확인 |

[자동 진입·입력 핵심 원본 근거](native-critical-evidence.json), [전체 메시지·시각·실행 측](native-runtime.jsonl), [경로 검사 스크립트](route-guard-smoke.lua) 및 [첫 라운드 핵심 근거](direct-critical-evidence.json)를 보존했다. 자동 진입·입력 라운드 916개 캡처 로그는 Error/Warning 0이다. 마지막 종료 단계에서 아래 별도 오류를 발견했으므로 종료까지 처음부터 오류가 없었다고 기록하지 않는다.

## 종료 직후 지갑 RPC 수정

새 Play의 기본 키 복원 검사는 통과했으나 종료 직후 UnionCoinPurchaseServiceLogic.RequestWallet에서 LEA-3032 FailedSendToClient 오류가 한 번 발생했다. [수정 전 로그](wallet-shutdown-before-fix.json), [원본 소스](wallet-before.mlua.txt)를 남겼다.

지갑 조회는 저장 호출이 없는 캐시 조회다. UnionCoinShopLogic.OnUpdate의 주기 요청이 사용자가 퇴장한 뒤 서버에 도착해도 RequestWallet은 응답을 보냈다. 이제 서버가 부여한 senderUserId로 UserService.GetUserEntityByUserId를 조회해 유효하지 않은 사용자 요청은 반환한다. 클라이언트 인자·지갑 payload·판매 조건·구매 영수증 처리·저장 경로는 유지한다.

오프라인에서는 nil/파괴된 사용자 응답 금지, 정상 지갑·준비 중 응답·미저장 프로필·판매 종료·중복 상품 ID·수신자 격리를 검사했다. Maker에서는 연결된 사용자의 LastReceivedId 갱신과 잔액 표시를 확인한 뒤 캐시 요청 8개를 보내고 종료하는 라운드를 두 번 실행했다. 각각 [168개](wallet-shutdown-after-fix-round1.json)/[166개](wallet-shutdown-after-fix-round2.json) 로그의 Error/Warning은 0이다. 정확한 퇴장 분기는 오프라인에서 강제 재현했으며, Maker 종료 시점의 모든 경합을 증명하는 검사는 아니다.

## 준비 시도와 최종 보존 범위

도구에서 직접 호출한 추가 콘텐츠 감사와 초기화는 완료 로그가 나오기 전에 중단했다. [미완료 직접 초기화](direct-initialization-attempt.json), [추가 감사 관찰](audit-observer-before-cancellation.json)은 성공 근거에서 제외한다. 이후 정상 맵 자동 진입에서는 초기 감사와 재구성 감사·전투 초기화를 모두 통과했으며 gate를 비활성화하지 않았다.

종료 재검증 2차 라운드의 첫 준비는 Play 전환 중 context unavailable로 입력 실행 전에 중단됐다. 편집 상태를 확인하고 다시 시작한 뒤 실제 context와 SHUTDOWN_ROUND2_SENT 로그를 확인한 라운드만 두 번째 통과로 센다.

연습 런의 저장은 CommitVerify20261012/CommitNativeVerify20261012 접두 키로 격리했다. 기존 기본 키의 기록을 초기화·삭제하지 않았다. 테스트 키 기록은 남겼으며 source의 StorageKey 기본값을 변경하지 않았다.

[보호 소스 비교](protected-source-check.json): RootDesk 소스·메타데이터 448개 중 UnionCoinPurchaseServiceLogic.mlua 한 파일만 추가 수정됐다. ProcessPurchase 본문은 동일하다. 원래 12개 커밋은 그대로이며 새 테스트·검증 기록만 추가했다. 마지막 Maker는 편집 모드이고 빌드 Error/Warning은 0이다.

실제 PC 포인터·사람의 화면 체감·모바일·다중 계정/인스턴스·발행 환경은 미검증이다. 이번에는 모든 전투맵의 정밀 이동, 튜토리얼 전체 완주·드래그, 정상 전술 입력만의 전체 런을 다시 실행하지 않았다. P0-05/06의 Column/Value 오류 진단 보완 등 기존 작업 계획의 대기 항목도 그대로다.
