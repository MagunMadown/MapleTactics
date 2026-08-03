# MapleTactics 객체지향 규격 감사 — 2026-08-01

## 결론

현재 규격은 MSW의 Entity/Component 구조에 맞는 조합 중심 설계이며 전면 재작성할
수준의 문제는 없다. 일반 Lua식 대규모 상속 대신 상태 소유 Component, 무상태 Logic,
Definition/Repository, Facade/DTO를 사용한 방향은 유지한다.

## 이번에 수정한 불일치

| 발견 | 원칙 | 조치 |
|---|---|---|
| Session이 Unit HP/IsDead/Cell/Facing을 직접 대입 | 캡슐화·단일 책임 | 모든 변경을 `BattleUnitComponent` API로 이동 |
| `PlayerRunStateComponent`가 진행과 인벤토리를 함께 소유 | 단일 책임 | `PlayerRunInventoryComponent` 분리, 외부 Facade는 `RunManagerLogic` 유지 |
| 물약 추가 시 ID 분기가 들어갈 여지 | 개방-폐쇄·의존 역전 | Consumable Definition → Router → 독립 Effect Handler 구조 도입 |
| 사망마다 Trigger 한 종류만 전달 | 조합성 | Trigger Resolver가 ANY/COMBO/BOSS의 순서 집합을 생성하도록 변경 |
| 초기 검토 문서가 현재 규격처럼 읽힘 | 단일 진실 원본 | 역사 문서 표시와 현재 Architecture Standard 링크 추가 |
| `InitialFacingPolicy`가 문서에만 존재 | 데이터-구현 정합성 | 실제 Enemy Dataset, Repository 검증, Spawn 적용 연결 |

## 유지해도 되는 선택

- `|`, `~` 구분 Snapshot은 MSW 동기화 제약을 감싼 내부 직렬화다. 외부 소비자가 직접
  파싱하지 않고 DTO/API만 사용하므로 현재 단계에서는 교체하지 않는다.
- Router의 `EffectType`/`ActionType` 명시적 분기는 원시 규칙의 닫힌 확장점이다.
  특정 Skill/Item/Enemy ID 분기와 다르므로 허용한다.
- `@Logic` Repository/Resolver는 플레이어별 변경 상태를 보유하지 않으므로 현재 수명 선택이 맞다.
- UI는 디버그용 배치와 최종 배치를 호환 대상으로 삼지 않고 DTO/Request 계약만 안정화한다.

## 남은 구조 부채

| 우선순위 | 항목 | 처리 원칙 |
|---|---|---|
| P1 | `BattleSessionComponent`가 여전히 큰 조정자 | 새 기능을 더 넣지 말고 Enemy Intent, Spawn, Action 조정을 검증 가능한 Slice로 이동 |
| P1 | 범용 Modifier 파이프라인 미구현 | 실제 피해/비용/타깃 Modifier 요구가 생길 때 Context와 순서를 먼저 규격화 |
| P1 | 실제 Stage/Node Dataset 일부 미이관 | 호환 fallback을 복제하지 않고 실제 Dataset 페어로 전환 |
| P2 | 문자열 Snapshot 공용 Codec 없음 | 두 번째 소비자가 직접 파서를 요구할 때 Codec 객체로 추출 |
| P2 | 자동 회귀 테스트 없음 | 현재 Maker 검증 스크립트를 Stage/Drop/Consumable 회귀 묶음으로 고정 |

## 신규 개발자가 확인할 규칙

1. 상태를 바꾸려면 먼저 소유 Component와 `Apply/Try/Record/Consume` API를 찾는다.
2. 새 콘텐츠 ID만 다르면 Dataset 행을 추가한다.
3. 새 원시 규칙이면 Router 한 곳과 독립 Handler 하나를 추가한다.
4. Session, RunManager, UI에 특정 콘텐츠 ID 조건문을 추가하지 않는다.
5. UI는 `GetBattleUiState()`와 Request API만 사용한다.
6. 변경 후 Build Warning/Error/Fatal 0과 실제 Server/Client DTO를 함께 검증한다.
