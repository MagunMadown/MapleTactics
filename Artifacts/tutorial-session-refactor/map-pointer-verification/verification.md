# 맵별 이동 검증 기록

검증일: 2026-10-11~12 · CoreVersion: 26.10.0.0 · 기준: codex/battle-session-responsibility-split / 2cec83a

**로비와 전투 20개 맵의 기본 이동·착지 검사는 통과했다. 이동 체감의 완전한 통일은 아직 판정하지 않는다.** 실제 PC 포인터는 OS 도구의 `noWindowsAvailable`로 실행하지 못했고, 사용자가 직접 검증을 나중으로 미뤄 이번 범위에서 제외했다. 게임 코드와 맵 설정은 수정하지 않았다.

## 확인한 동작

- 전투 20개 맵에서 실제 Maker `keyboard_input`으로 좌우 일반 이동을 실행했다. 승인된 이동 48회, 서버 착지 검사 48회가 목적 위치와 일치했고 모두 `corrected=false`였다.
- 로비 첫 라운드는 단발 6회와 같은 프레임 A/D 입력으로 총 8회 도착했다. 착지 검사는 7회이며 한 요청은 다음 이동이 시작돼 교체됐다. 추가 경계 라운드는 이동 10회, 착지 검사 9회, 경계 거절 1회였다.
- 연습 전투에서 `CELL_OCCUPIED`·`OUT_OF_BOUNDS`, 로비에서 `BOUNDARY` 거절과 시각적 밀림 후 복원을 확인했다. 거절 후 루트는 원래 셀에 남았다.
- 연습 전투에서 기존 mage 유틸리티를 할당한 뒤 S로 teleport를 실행했다. 이어 A/D 일반 이동이 정상 도착했고 착지 보정은 없었다.
- A/D 같은 프레임 입력에서 로비는 다음 이동을 예약해 재생했다. 전투는 왼쪽 1회 이동했다. D/A 700ms 유지 입력도 한 번의 KeyDown 이동만 실행했다. 0.1초 간격의 반복 반전 시험은 아니다.
- 사원 보스에서 이동 경과 약 0.039초에 로비 전환을 요청했다. 클라이언트 이동은 `MAP_CHANGED`로 정리됐고, 전환 후 이전 세션의 이동과 착지 검사 모두 false였다.
- 등록된 추종 요소 1개의 로컬 오프셋은 샘플에서 아바타 오프셋과 일치했다. 마지막 로비 위치는 서버 착지 로그와 일치했고, pending=false, blocked=false, Camera.Damping=(2.5,3.9)로 복원됐다.
- Maker 빌드 오류는 0건이다. 정상 경로의 제품 런타임 오류는 확인되지 않았다. 검증 스크립트 오류 2건은 아래에 따로 기록했다. Maker는 edit 모드로 종료했다.

## 발견한 차이 MOVE-VERIFY-01

홉 애니메이션 재생 배율이 로비 1.0, 전투 3.0이다. 실제 `MoveHopAnimation` 로그에서도 Fall의 rate=1.0/3.0을 확인했다. 공통 프로필은 [PlayerGridMovementLogic.mlua](../../../RootDesk/MyDesk/00_Core/Movement/PlayerGridMovementLogic.mlua)의 27행, 전투 기본값은 [BattleSessionComponent.mlua](../../../RootDesk/MyDesk/01_Combat/Components/Shared/BattleSessionComponent.mlua)의 215행에 있다.

이동 시간 설정 0.24초, 홉 높이 설정 0.3, LINEAR 보간과 지연 착지 정책은 공통이다. 애니메이션 배율 차이는 수정하지 않았으며 BS-05/07의 통일 검증을 완료로 올리지 않는다.

## 맵별 기본 이동 결과

모든 대상은 MapBuilder로 확인한 MapleTile(0)이다. 아래는 좌우 일반 이동·착지의 결과이며, 각 맵의 모든 경계/점유/빠른 입력 조합과 화면 체감을 통과했다는 의미가 아니다.

| 맵 | 승인 이동 | 착지 검사 | 보정 |
|---|---:|---:|---:|
| ellinia_battle | 5 | 5 | 0 |
| henesys_battle | 2 | 2 | 0 |
| henesys_boss | 2 | 2 | 0 |
| ellinia_boss | 2 | 2 | 0 |
| kerning_city_battle | 2 | 2 | 0 |
| kerning_city_battle2 | 2 | 2 | 0 |
| kerning_city_boss | 2 | 2 | 0 |
| perion_01_battle | 2 | 2 | 0 |
| perion_02_battle | 2 | 2 | 0 |
| perion_03_battle | 2 | 2 | 0 |
| perion_boss | 2 | 2 | 0 |
| nautilus_battle | 2 | 2 | 0 |
| nautilus_interior_01 | 2 | 2 | 0 |
| nautilus_interior_02 | 2 | 2 | 0 |
| nautilus_boss | 2 | 2 | 0 |
| sleepywood_ant_tunnel | 2 | 2 | 0 |
| sleepywood_food_cart_boss | 2 | 2 | 0 |
| sleepywood_temple_battle | 2 | 2 | 0 |
| sleepywood_temple_boss | 2 | 2 | 0 |
| skill_test | 7 | 7 | 0 |

맵별 증거는 `<map>-logs.json`, 집계와 fixture·미검증 범위는 [results.json](results.json)에 있다. [로비 경계 기록](lobby-boundary-logs.json), [전환·관찰 코드 기록](transition-and-harness-logs.json)을 함께 본다.

## 측정의 의미와 한계

관찰 스크립트가 루트 위치, 아바타 로컬 오프셋, 등록 추종 요소와 CameraComponent.Damping을 샘플링했다. 카메라의 실제 렌더 위치와 화면상의 HP/이름표 떨림을 측정한 것은 아니다. 프로필의 0.24초는 설정값이다. 목표 X를 처음 관찰한 경과는 전투에서 0.240~0.344초였고, 이는 샘플 간격을 포함한다. 정확한 도착 시각이나 GPU FPS로 해석하지 않는다.

루트 X는 기록의 소수점 5자리 정밀도에서 확인된 LINEAR 보간과 일치했다. `firstSampledRootTargetElapsedRange`와 서버 완료·확인 조건을 기다리는 `firstSampledArrivedFlagElapsedRange`를 구분했다. 관찰이 두 번째 입력보다 먼저 끝난 일부 맵은 양쪽 착지 로그로 도착을 확인했고, 두 번째 궤적의 샘플은 부족하다.

## 테스트 상태·오류의 분리

처음 Maker에서 엘리니아 맵을 직접 시작한 뒤 초기화 실행 스크립트를 중간에 교체했다. 논리 셀과 물리 위치가 맞지 않고 입력 잠금이 남아 이 상태의 이동 결과는 폐기했다. [폐기한 fixture 기록](ellinia-interrupted-fixture-logs.json)은 통과 근거로 사용하지 않는다. 새 플레이에서 기존 준비된 진입·Gateway·Teleport·맵 진입 완료 경로를 사용해 재검증했다.

새 플레이에서 관찰용 MakerScript 오류가 2건 있었다. 저장 키 격리 시 ResolveUserIdentity에 Entity 대신 UserId를 전달한 오류와, 이동 감시에서 존재하지 않는 StartTime을 계산한 오류다. 각각 실제 Entity와 선언된 Elapsed로 고쳐 같은 검증을 다시 실행했다. 두 오류는 게임 코드 오류로 분류하지 않으며 원본 로그를 보존했다. 연습 전투 유틸리티 첫 지정은 잘못된 스킬 ID로 거절됐고, 실제 데이터의 teleport/mage를 지정해 재검증했다.

첫 직접 진입 시 Maker 기본 프로필의 런 카운터가 1회 증가했다. 이후 UnionProfile 저장 키를 MapMoveVerify20261011B / MapMoveVerify20261012C로 격리했다. 기존 완료 기록을 초기화하거나 삭제하지 않았다. 지역별 입력 검사는 CONTINUE_RUN이고 각 진입 전 테스트용 RunCurrentHp만 RunMaxHp로 복구했다. PrototypeTestEntry를 사용했고 셀·점유·턴·RPC 검증은 유지했다. Runtime RequireValidContentAtStartup=false는 전수 콘텐츠 검사 반복만 생략하며 개별 단계 검증은 유지했다. runtime override는 stop으로 종료했다.

## 남은 검증

- 사람의 화면 체감: 이동 속도·홉 모션·카메라·이름표/HP 표시 떨림.
- 0.1초 빠른 반전과 착지 직후의 정밀 입력, 각 맵의 경계·점유·연속 입력 모든 조합.
- 로비 1배/전투 3배 홉 애니메이션 정책을 맞춘 뒤 재검증.
- 실제 PC 포인터 슬롯 드래그·큐 취소/재정렬·결과 클릭: 사용자 요청으로 유예.
- 허용 오차를 넘는 위치 오차의 의도적 주입은 이번 라운드에서 하지 않았다. 기존 오프라인 회귀와 이번 무보정 성공 로그를 구분한다.

모바일·다중 계정·발행/서비스 실패 검증은 이번 요청 범위에서 제외했다. TUT-04/05, BS-04/05/07의 기존 🟡 상태와 GDD/Phase 상태는 유지한다.
