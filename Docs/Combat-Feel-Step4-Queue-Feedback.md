# 전투 조작감 STEP 4 — 스킬 예약 입력 피드백

## 적용 범위

- `BattleQueueHudComponent`의 클라이언트 UI 표현만 변경했다.
- 스킬 버튼을 누르면 해당 아이콘이 즉시 0.10초 Scale Punch로 반응한다.
- 서버 Presenter 상태에서 `QueuedTileIds` 증가가 확인되면 새로 예약된 스킬 아이콘이 0.10초 Pop으로 반응한다.
- Queue 확정 Pop 시 기존 공용 UI 클릭 사운드를 0.35 볼륨으로 재생한다.

## 로직 분리

- Punch/Pop은 `_TimerService` 기반 클라이언트 UI 타이머이며 요청·턴 처리 코드는 기다리지 않는다.
- 첫 HUD 동기화, Queue 실행 전환, Queue 비우기에는 확정 Pop을 재생하지 않는다.
- 연속 피드백이 같은 슬롯에 겹치면 이전 타이머를 정리하고 원본 아이콘 크기에서 다시 시작한다.
- HUD 종료 시 모든 아이콘 타이머를 해제하고 원본 크기를 복원한다.

## 변경하지 않은 규칙

- Skill ID, Damage, Cooldown
- Queue 최대 개수 및 실행 순서
- 스킬 예약과 Execute의 턴 소비 규칙
- 적 행동 및 턴 전환
- `.ui` 구조와 바인딩

## 검증

- 실제 프로젝트 API 인덱스를 연결한 mLua 정적 진단: 오류 0, 경고 0
- `git diff --check`: 통과 필요
- Maker Play Test: 이 환경에는 Play/입력/로그 도구가 없어 사용자 환경에서 아래 항목 확인 필요
  - 스킬 클릭 즉시 아이콘 Punch
  - Queue 확정 직후 아이콘·순서 배지 표시와 Pop
  - 애니메이션 중에도 턴 진행 지연 없음
  - 빠른 연타 시 Queue 중복 등록 및 아이콘 크기 누적 없음
