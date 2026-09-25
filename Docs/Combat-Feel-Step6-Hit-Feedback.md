# 전투 조작감 STEP 6 — 공격 타격 피드백

## 명중 타이밍

- 모든 일반 공격과 스킬 피해는 `BattleSessionComponent.ApplyDamage()`의 단일 HP 변이 경로를 통과한다.
- `BattleUnitComponent.ApplyDamage()`가 성공한 같은 impact 호출에서만 시각 피드백을 한 번 발생시킨다.
- 빗나감, 같은 팀, 사망 유닛, 0 이하 피해에는 피드백을 발생시키지 않는다.

## 적용 효과

- Hit Stop
  - 일반: 기본 0.04초, 0.03~0.05초 범위 제한
  - 강공격: 기본 0.065초, 0.05~0.08초 범위 제한
  - 전역 Time Scale 대신 공격자·피격자의 로컬 Sprite 재생률만 잠깐 0으로 두고 원래 값으로 복원한다.
- Enemy Hit Reaction
  - 0.08초 Squash → Stretch → 원본 Scale 복원
  - Sprite/Avatar visual entity의 Scale만 변경하며 Position, CellIndex, BoardState는 변경하지 않는다.
- Hit Flash
  - 기존 Flash 경로를 재사용하고 기본 지속 시간을 0.065초로 단축했다.
  - Inspector 값도 0.05~0.08초 범위로 제한한다.
- Camera Shake
  - 기존 `BattleCameraAnchor`의 CameraOffset을 약하게 흔든 뒤 정확한 원래 Offset으로 복원한다.
  - 일반 진폭 0.025, 강공격 진폭 0.045, 기본 지속 시간 0.08초다.

## 강공격 시각 등급

- 기존 일반 공격 피해 3, Heavy Slash 피해 6 사이인 5를 기본 임계값으로 사용한다.
- 이 값은 시각 효과 강도만 선택하며 데미지 계산과 스킬 데이터는 변경하지 않는다.

## 변경하지 않은 규칙

- 실제 Damage 및 HP 변이 횟수
- 공격 판정과 Impact Delay
- Knockback 판정과 Grid Position
- Queue, Cooldown, Skill ID, 실행 순서
- 턴 소비 및 적 행동

## 검증

- 변경한 두 mLua 파일 정적 진단: 오류 0, 경고 0
- `git diff --check`: 통과 필요
- 추가된 코드에 Damage, Turn, Queue, Grid Position, 전역 Time Scale 변이 없음
- Maker Play Test: 현재 세션에는 Play/입력/로그 도구가 없어 사용자 환경에서 확인 필요
  - 일반/강공격 Hit Stop 체감 차이
  - 치명타가 아닌 연속 공격에서도 Scale·Color·PlayRate·CameraOffset 정상 복원
  - 한 번 명중 시 HP 한 번 감소 및 턴 한 번 진행
  - 빗나감에는 Hit Feedback 없음
