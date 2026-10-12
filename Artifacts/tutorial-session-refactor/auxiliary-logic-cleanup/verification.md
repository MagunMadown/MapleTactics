# 배틀 세션 보조 로직 정리 검증

2026-10-12 · CoreVersion 26.10.0.0(사용자 승인 기준)

확인한 보조 함수 6개의 구현을 기존 책임 파일로 옮겼다. 새 mLua 파일 없이 세션의 공개 진입점은 유지했다. 이 하위 작업은 구현·회귀·Maker 검증을 통과했으며, BS-04/05/07 전체의 포인터·실기기·화면 검증 대기 상태는 유지한다.

| 세션 함수 | 구현 소유자 |
|---|---|
| IsTeamTurn | BattleActionLogic.IsTeamTurn |
| GetFacingDirection | BattleMovementLogic.GetFacingDirection |
| GetTileActionType | BattleQueueLogic.GetTileActionType |
| GetSkillSpeedMultiplier | BattleCombatPresentationLogic.GetSkillSpeedMultiplier |
| FlushDamageNumberBatch | BattleCombatPresentationLogic.FlushDamageNumberBatch |
| GetPlayerHopDuration | PlayerGridMovementLogic.GetHopDuration |

세션은 2,745 → 2,732줄이다. 공개 메서드 288개의 반환형·인자·ExecSpace를 유지했고, 세션의 다른 본문·프로퍼티·이벤트/RPC 검증은 그대로다. 책임 로직의 기존 메서드도 변경하지 않았다. 공통 이동 GetDuration만 기존 홉 보정식을 GetHopDuration 호출로 바꾸어 같은 계산의 중복을 없앴다. 이동 프로필, 실제 이동·착지·카메라 정책과 스킬 속도 값은 변경하지 않았다.

본문 6개는 주석·공백, self→session 및 홉 함수의 프로퍼티→인자 치환을 제외하고 동일하다. [공개 계약](source-contracts.json), [본문 비교](moved-body-equivalence.json)에 근거를 저장했다. 피해 목록은 표시 전에 비우고 기존 목록·대상 조회 순서·0.08초 간격을 그대로 전달하므로 재진입과 재호출이 같은 묶음을 다시 표시하지 않는다.

## 오프라인 검증

- 기존 전투·튜토리얼 회귀 18개 모음 모두 종료 코드 0. 명령과 출력은 [회귀 결과](regression-results.json)에 있다.
- battle-session-boundary-test.py는 기존 16개와 새 보조 검사 7개, 총 23개를 통과했다. 모든 팀/단계 조합, 방향의 기존 대체값, 검증 성공 여부에 따른 타일 행동, 속도 하한/상한 미설정, 공통 홉 범위와 시각적 홉 활성/비활성, 빈 피해 목록, 재진입·세션 간 묶음 격리를 검사한다.
- 새 검사를 정리 전 세션 원본으로도 실행해 23개 통과를 확인했다. 이는 기존 세션 함수 계약과의 비교이며 엔진 실행을 대신하지 않는다.
- grid-movement-latency-test.py의 공통 이동 로더에 GetHopDuration을 포함했다. 기존 37개 이동 검사와 실제 로비/전투 기본값 프로필 비교를 통과했다.
- node tools/check-balance-vocab.cjs 및 git diff --check 통과. 닫힌 데이터 값의 추가·변경은 없다.
- 이 환경에 직접 호출 가능한 mLua LSP 진단 도구는 없었다. Maker Refresh·빌드 로그·실제 함수/입력 실행으로 등록과 실행을 확인했다.

## Maker 검증

실제 호출 순서는 stop → 편집 모드 확인 → refresh → build 로그 → play → context 확인 → 격리 저장·진입 → 입력/로그 → stop이다. 연습 맵과 로비는 MapBuilder로 MapleTile(0)을 확인했다. 새 .codeblock을 직접 작성하지 않았으며 여섯 변경 스크립트의 메타데이터 쌍을 확인했다.

| 시나리오 | 결과 |
|---|---|
| 실제 연습 세션의 보조 함수 호출 | phase=true, facing=true, speedFloor=0.1, hopFloor=0.12, 기본 홉=0.24, 기존 속도=2.0, brandish 행동=EXECUTE_SKILL |
| 4,7,2 피해 숫자 묶음 두 번 호출 | 원본 값 유지·묶음 소비, DamageSkin hits=3 interval=0.08 로그 1회. HP를 변경하지 않은 표시 계약 검사 |
| native D/A 전투 이동 | 셀 2→3→2, 착지 검사 2/2, corrected=false |
| native W/1/Space | Right→Left, brandish 장전·실행·큐 완료 성공, 실제 피해 HP 30→28과 native DamageSkin 1회 확인 |
| 클라이언트 공통 계산 | 로비/전투 이동 시간 0.24/0.24, 홉 하한 0.12, 방향 1, 완료 후 pending=false |
| 기존 스폰 복귀 후 native A/D 로비 이동 | 두 이동 모두 0.24초, 착지 검사 2/2, corrected=false |
| 최종 상태 | 서버/클라이언트 모두 lobby와 같은 최종 위치, client pending=false·blocked=false, 이전 전투 oldMove=false·oldLanding=false |

원본 실행 로그와 판정은 [최종 Maker 기록](maker-final-logs.json), [판정 요약](results.json)을 따른다. 최종 빌드·런타임 Error는 0이고 Maker는 편집 모드로 돌려놓았다. 첫 Refresh의 기존 IsPCPlatform 폐기 예정 경고는 새 오류와 구분한다.

검증 준비에서 등록되지 않은 skill_test_stage를 잘못 사용해 STAGE_MAP_ROUTE_NOT_FOUND로 거절됐고, 초기화 완료 전에 다음 관찰 스크립트를 실행해 준비가 중단됐다. [처음 준비 로그](initial-fixture-logs.json)를 보존했다. 재시도는 맵의 실제 SkillTestStageId와 기존 StartPrototypeBattleFromMap을 사용하고 INITIALIZED success=true 로그 후 다음 단계를 실행했다. Maker 정지 전환 중 Refresh unavailable도 편집 모드 확인 후 재시도했다. 이 준비 오류들을 성공 근거로 사용하지 않는다.

저장은 런타임 전용 UnionProfile:AuxiliaryLogicVerify20261012G/H 키로 격리했다. G는 중단된 준비, H는 최종 검증에 사용했고 기존 기본 키의 완료 기록을 초기화·삭제하지 않았다. 캐시 프로필을 유지하되 해당 테스트 키의 raw/existence 캐시만 분리했다. 테스트 기록은 남겨 두었으며 source의 StorageKey 기본값은 변경하지 않았다. 연습 맵은 런타임에서 startup content gate를 완화한 기존 prototype fixture이므로 일반 콘텐츠/해금/정상 런 전체 검증으로 확대하지 않는다.

## 미검증 범위

이번에는 로비와 연습 전투의 대표 경로를 확인했다. 모든 맵·직업·점유 조합을 재실행하지 않았고, 실제 PC 포인터·물리 정밀 입력·사람의 렌더 체감·모바일·다중 계정·발행 환경과 실제 저장/전송 장애 주입은 기존 대기 항목으로 남는다. GPU FPS나 화면 떨림 없음의 근거로 사용하지 않는다.
