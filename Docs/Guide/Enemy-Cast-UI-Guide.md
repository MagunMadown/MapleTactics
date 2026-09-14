# 적 스킬 아이콘과 캐스팅 표시

`EnemySkillDefinitions.csv`의 `HudIconRuid`가 적 큐 아이콘을 지정한다.
패턴은 `EnemyPatternSteps`의 `TileId`로 스킬을 참조하며, 패턴별 아이콘 필드는 없다.
같은 행동에 다른 아이콘이 필요하면 별도 SkillId로 정의한다.

`EnemyIntentHudComponent`는 큐의 `QueuedIconRuids`를 표시한다. 값이 없을 때만 기존 기본 아이콘을 사용한다.
킹크랑 집게와 버블 캐논은 각각 기존 근접/원거리 리소스로 구분한다. 최종 디자인 리소스는 CSV에서 교체한다.

캐스팅 표시는 EnemyIntents의 `CastState`, `InterruptHitsRequired`, `InterruptHitsReceived`를 읽는다.
CASTING에는 남은 중단 적중 횟수, INTERRUPTED에는 중단 문구를 표시한다.
CASTING 동안 TargetCells가 제공되면 바닥 전조도 유지한다.

지속 충전 파티클과 시각 배치 검증은 후속 작업이다. 이번 변경은 기존 HUD의 상태 표시와 아이콘 구분이며 전투 패턴 순서를 변경하지 않는다.
