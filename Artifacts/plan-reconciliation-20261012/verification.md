# 계획 문서 정합성 대조

2026-10-12 · 범위: NEXT_WORK_PLAN 6절의 1번 문서 정리. 게임 소스·데이터·모델·UI·맵·설정은 수정하지 않았으며 새 Play/입력 시험은 하지 않았다.

## 확인한 현재 구현

- MapBuilder로 map 디렉터리의 모든 26개 파일을 읽었다. 모두 MapleTile(0), IsInstanceMap=false. BattleSessionComponent가 있는 맵은 20개(연습 포함). [정적 스냅샷](map-snapshot.json)에 파일별 값을 보존했다.
- SectorConfig의 sector01.maxUserNo=1. 현재 Static Map·1명 운영을 반영했으며 플레이어당 Instance Room/Map을 구현 완료로 기록하지 않았다.
- Environment/config의 CoreVersion은 사용자 승인 26.10.0.0이다. 각 자산의 메타데이터 버전을 이번 작업에서 변경하지 않았다.
- RegionDefinitions 6개와 StageMapRoutes 28개 경로·NodeDefinitions의 상점 전후 연결을 직접 읽었다. 실제 RegionId/MapId를 문서에 반영했고 region_XX_*를 새 파일 생성 지시로 쓰지 않도록 했다.
- WorldMapFutureRegionButtonComponent는 TargetNodeId가 있을 때 서버 다음 노드 선택을 요청하고 빈 값일 때만 미래 지역 안내를 표시한다. UI authoring 바인딩·정상 런 해금/전송·상점 이후 흐름은 이번에 실행하지 않았다.
- 일반 이동의 서버 셀/턴 검증 + 소유 클라이언트 공통 루트 재생, 0.24초/LINEAR/홉 1배/공통 착지 검사를 이전 검증 기록·현재 소스에 맞춰 반영했다.

## 문서 변경

- GDD·Phase 0·Phase 1에 msw-planning 재개 흐름과 build-management 전체 읽기 안내를 추가했다.
- Phase 0의 미착수와 map01/SideViewRectTile 전환 권고를 현재 구현·근거 대기 상태로 정리했다.
- Phase 1에 현재 23개 항목 상태표를 만들었다. 초기 Slice 수치·키·미구현 설명과 날짜별 이력은 현재 작업 지시와 구분한다. 기본 키·실제 맵·5/7/9칸 Stage 기준·기본 큐 3/슬롯 6을 명시했다.
- GDD §9에 Phase 0 6개와 Phase 1 23개를 한 번씩 미러했다. 기존 Phase 2~6 독립 계획은 전체 상태를 임의로 올리지 않고 일부 선행 구현과 구분했다.
- Phase 1 Slice 10은 기존 Maker DAMAGE/PUSH·실제 제어 API와 최신 제어/큐 회귀에 근거해 ✅로 갱신했다. 이전 ✅ 항목은 범위를 넓히지 않았다.
- Roadmap에 M1 active와 기존 후속 작업의 현재 준비/검증 대기를 반영했다. 이미 있는 지역 파일·데이터를 미생성으로 표시하거나 모든 지역 버튼이 안내만 한다고 단정하던 기록을 바로잡았다.
- NEXT_WORK_PLAN의 문서 정리만 ✅로 갱신했다. 튜토리얼·세션 통합과 상점·기록/랭킹·지역 진행·포인터/실기기 검증은 기존 대기 범위다.

## 완료와 대기를 나눈 근거

| ID | 상태 | 작업 | 확인된 범위·남은 확인 |
|---|---|---|---|
| P0-01 | 🟡 | 맵/Body·격리 계약 | 맵·Static Map·최대 인원 확인; 모델별 Body 대조 근거 보강 대기 |
| P0-02 | ✅ | 논리 셀 이동 | 20개 맵 41/41 이동·착지와 로비/전투 공통 경로 검증 |
| P0-03 | 🟡 | 서버 Command 왕복 | 정상 RPC는 Maker 통과, 잘못된 소유권·중복·오래된 요청은 오프라인 통과; Maker에서 잘못된 요청 거절 검증 대기 |
| P0-04 | ✅ | 큐 재타깃 | 기존 Maker Push 이후 Miss와 실제 제어 API, 최신 제어/큐 회귀 통과 |
| P0-05 | 🟡 | UserDataSet 로드·검증 | 정상/누락·중복 참조 이력 있음; 현재 Dataset/Row/Column/Value 오류 로그 통합 대조 대기 |
| P0-06 | 🟡 | 통합 검증 | 관련 build/runtime·회귀는 통과; P0-01/03/05와 실제 UI 포인터 검증 대기 |

Phase 0에서 ✅인 것은 논리 이동과 큐 재타깃 2개다. 모델별 Body 대조, Maker의 잘못된 RPC 거절, 현재 데이터 오류 위치 로그 및 포인터 포함 통합 판정은 새 완료 근거가 없어 🟡로 남겼다. 이는 현재 기능을 미구현/실패로 판정하거나 Phase 1 진행을 되돌리는 의미가 아니다.

근거 파일:

- [튜토리얼·세션](../tutorial-session-refactor/verification.md): 실제 제어 API·튜토리얼 완주/저장·큐·오프라인 요청 검증, 관찰 오류와 제품 실행 분리.
- [이동](../tutorial-session-refactor/movement-feel-verification/verification.md): 20개 맵 41/41, 경계·점유·정밀 이벤트·맵 전환. startup gate 완화와 물리/렌더 미검증 범위를 유지.
- [보조 정리](../tutorial-session-refactor/auxiliary-logic-cleanup/verification.md): 공개 계약 288개, 회귀 18개 모음·새 7개, 로비/전투 이동·스킬 실행.
- Phase 1의 날짜별 Maker/실제 Dataset 기록: 오래된 수치와 당시 완료 범위를 현재 설정과 구분해 보존.

Phase 0/1은 all-✅가 아니므로 Phase 문서를 삭제하거나 GDD를 Archive로 옮기지 않았다. M1은 🔨 active를 유지하며 새 마일스톤·범위·출시 완료를 만들지 않았다. As-built 완료 정리도 실행하지 않았다.

## 문서 검증

GDD/Phase 29개 ID·상태 일치와 중복 없음, 상세 상태 대조, 현재 MapId 28개 라우팅의 파일 존재, 상대 링크 52개, Phase 1 날짜별 이력 보존, 구현 파일 1,366개의 해시·파일 집합 유지 및 git diff --check(종료 0)를 확인했다. Phase 0은 2/6, Phase 1은 9/23 항목이 ✅다. Maker는 이미 edit 상태였고 Refresh 성공·build 로그 0건을 확인했다. 결과는 [checks.json](checks.json)에 저장했다. 새 Play/입력 검증은 수행하지 않았으며 PC 포인터·실기기·화면 체감·상점 정상 런의 기존 대기를 유지한다.
