# 전투 세션 유틸리티 책임 분리 검증

검증일: 2026-10-11. develop `f85c18d`의 기존 작업을 보존하며 피해·지원 책임 분리 다음 단계부터 진행했다. 이 기록은 유틸리티 분리에 한정하며 전체 세션 분리 완료를 의미하지 않는다.

## 변경

- `Skills/UtilitySkillExecutionLogic.mlua`로 `TryUseUtilitySkill`, `ExecuteUtilityEffect`, `ApplyFairyTurnCollisionStun`의 실제 구현을 이동했다.
- `BattleSessionComponent`의 같은 메서드는 기존 인자·반환값·ServerOnly 경계를 유지하는 로직 호출만 남겼다. 세션 본문은 263줄 감소했다.
- 이동 본문 3개는 self → session 수신자 변경 외에 동일하다. 나머지 285개 세션 메서드도 분리 전과 동일하다.
- 새 Logic은 속성이나 전투별 전역 상태를 보유하지 않는다. 플레이어·턴·요청·완료 타이머·쿨다운 스냅샷은 기존 세션/유닛/런타임 컴포넌트가 계속 소유한다.
- `RequestUtilitySkill`의 RPC 인자와 소유자·현재 맵 검증, 서버의 직업별 스킬 선택을 유지했다. 기존 이동·강제 재배치·피해·표시 경로를 재사용한다.
- `ContentValidatorLogic`의 구현 위치 주석만 갱신했다. CSV·밸런스 값·닫힌 값의 종류는 변경하지 않았다.
- 새 codeblock은 Maker Refresh가 생성했다. AGENTS.md의 책임 분리 규칙은 이미 반영된 상태다.

## 코드·회귀 검증

| 검사 | 결과 |
|---|---|
| 유틸리티 실행 | 새 18개 회귀 그룹 통과. 분리 전 원본으로도 같은 18개 통과 |
| 피해·지원 | 19개 통과 |
| 스킬 실행 | 21개 통과 |
| 일반 이동 | 37개 통과 |
| 모션 완료 게이트 | 33개 통과 |
| UI 상태 | 11개 통과 |
| 적 계획 스냅샷 | 12개 통과 |
| 적 계획 | 14개 통과 |
| 적 턴 실행 | 21개 통과 |
| HUD 맵 생명주기 | 8개 통과 |
| 관련 회귀 합계 | 194개 그룹 통과 |
| 변경된 mLua 3개 LSP | 오류·경고 0. 기존 동적 컴포넌트 접근 Info는 유지 |
| Balance Studio vocabulary | `node tools/check-balance-vocab.cjs` 통과 |
| 공백·충돌 검사 | `git diff --check` 통과 |

유틸리티 회귀는 실제 mLua 본문, 실제 턴 예약 및 쿨다운 메서드를 실행한다. 엔진·타깃 탐색·강제 이동·표시의 외부 경계는 mock이다. 소유자/RPC 거절, 상태이상·쿨다운·행동 잠금, 예약 큐 유지, 효과 실패와 비용 미소비, 화상 사망, 완료 타이머 대체 경로와 오래된 플레이어·맵·진입·턴, 두 세션의 상태 독립성, 좌우 텔레포트, 적 뒤 착지와 앞쪽 대체 착지, HEAVY 던지기 거절, 다중 밀치기·큐 취소·시전자 동반 이동, 충돌 스턴 및 투사체 표시 타이밍을 검사한다.

재현 명령:

```bash
LUPA_PATH=/private/tmp/mapletactics-landing-lupa python3 Artifacts/tests/utility-skill-execution-test.py
ORIGINAL_SESSION=/private/tmp/mapletactics-session-before-utility-extraction.mlua LUPA_PATH=/private/tmp/mapletactics-landing-lupa python3 Artifacts/tests/utility-skill-execution-test.py
```

Lupa와 분리 전 임시 소스는 이 머신의 /private/tmp에 있다. 별도 `new-player-tutorial-test.py`의 기존 fixture가 `NewPlayerTutorialLogic.GetGuideMessage`를 찾지 못하는 실패는 이번 통과 수에 포함하지 않았다. 전체 테스트 모음 통과를 의미하지 않는다.

## Maker 실제 입력 검증

Maker MCP의 stop → refresh → 빌드 로그 → play 경로를 사용했다. `skill_test`는 MapleTile(직렬화 값 0)이며 플레이어는 Rigidbody를 사용한다. Alpha1로 예약한 공격 1개를 유지한 상태에서 S 키로 아래 5개 직업 유틸리티를 실행했다. 연습 모드의 기존 직업 변경·위치 변경 메서드로 준비 상태를 만들었으며 실제 스킬 발동은 키 입력을 사용했다.

| 유틸리티 | 확인 |
|---|---|
| 전사 royal_guard | 방어 활성화, 예약 큐 1개 유지, 쿨다운 4, 기존 완료 시점의 턴 복귀와 타이머 정리 |
| 마법사 teleport | 셀 2 → 4, 서버와 클라이언트 최종 X=2.2400000095367 일치 |
| 도적 rapid_evasion | 적 셀 2를 지나 플레이어 셀 0 → 3, Left로 방향 전환 |
| 궁수 fairy_turn | 벽에 막힌 적의 StopActionTurns=1 및 스턴 마커, 투사체·착탄 표시 경로 실행 |
| 해적 somersault_kick | HEAVY 대상은 턴·쿨다운을 소비하지 않고 거절. 저항을 해제한 연습 표적은 셀 1 → 4로 던지기 성공 |

이후 RightArrow 3회로 일반 이동 셀 0 → 1 → 2 → 3에 복귀했고 턴 진행·서버 최종 셀과 위치·이동 및 착지 검사 정리를 확인했다. Space로 남겨 둔 공격을 실행하여 훈련 표적 HP 30 → 28, 큐 1 → 0, PlayerTurn 복귀와 행동·충격 타이머/피해 컨텍스트 정리를 확인했다. 이 긴 시나리오의 마지막 클라이언트 검사 스크립트는 완료 전에 stop되었으므로 최종 성공 근거로 집계하지 않았다.

최종 소스 Refresh 후 별도 실행에서 Alpha1 → S를 다시 입력했고 서버와 클라이언트의 상태를 재확인했다.

```text
[UtilitySeparationVerify] FINAL_SERVER_PASS turn=3 queue=1 cooldown=4 timer=0
[UtilitySeparationVerify] FINAL_CLIENT_PASS turn=3 queue=1 cooldown=4 x=0.0
```

마지막 상태 확인 로그는 Info 2, 오류·경고 0이다. 전체 시나리오 로그와 구분한다. 최종 빌드 로그 1,294개는 Info 1,293, 오류 0, 기존 IsPCPlatform 폐기 예정 경고 1이었다. Maker는 edit 모드로 종료했다.

검사 스크립트 실패 이력도 보존했다. 첫 시나리오에서 네이티브 MapComponent.TileMapMode enum을 숫자 0과 비교한 assertion 1건이 실패했다. MapleTile enum 기준으로 수정해 서버·클라이언트 위치를 재확인했다. 마지막 별도 실행에서는 엔티티의 미존재 _T를 읽은 검사 오류 1건이 발생했다. 컴포넌트 소유 상태 기준으로 수정하고 상태·위치 확인을 재실행해 통과했다. 이 검사 오류들을 숨기기 위해 런타임 구현을 바꾸지는 않았다.

선별된 Maker 원본 로그·전체 로그 개수/심각도·분리 전후 검사 출력: `/private/tmp/mapletactics-utility-separation-verification.json`.

## 다음 재개 지점과 한계

- 다음 분리 대상: 사망·유닛 생명주기와 특수 효과, 큐 실행, 이동·시각 효과 및 진입/재구성 구현. 타이머와 맵/플레이어 상태 소유권 및 RPC 검증은 계속 세션에 유지한다.
- 유틸리티 분리는 검증 완료했지만 세션 전체가 위임만 남은 상태는 아니다. GDD/Phase 체크리스트의 기능 완료 상태는 이번 리팩터링으로 올리지 않았다.
- 이번에는 실멀티플레이, 모바일·모든 전투맵 및 카메라/추종 표시의 실제 시각적 체감을 검증하지 않았다. Maker 입력과 상태 로그 검증을 프레임/GPU 성능 측정으로 간주하지 않는다.
