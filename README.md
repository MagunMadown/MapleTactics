# MapleTactics

메이플스토리 월드에서 제작하는 1차원 턴제 전술 로그라이크 프로젝트입니다.

핵심 전투는 논리 셀 이동, 방향 전환, 공격 타일 큐 등록, 큐 순차 실행, 적 Intent 예고로 구성합니다. MSW 구현은 서버 권위 `BattleSessionComponent`, 데이터 기반 Pattern/Effect, UserDataSet 중심으로 진행합니다.

## 개발 문서

- [M1 GDD](Docs/MapleTactics-M1-GDD.md)
- [아키텍처 구현 가능성 검토](Docs/MapleTactics-M1-Architecture-Review.md)
- [실제 구현 계획](Docs/MapleTactics-M1-Implementation-Plan.md)
- [데이터 사전](Docs/MapleTactics-M1-Data-Dictionary.md)
- [AI 개발 프롬프트북](Docs/MapleTactics-M1-AI-Prompts.md)

## 현재 상태

- CoreVersion: `26.5.0.0`
- 실제 전투 구현: 시작 전
- 현재 `map01`: MapleTile(0)
- 현재 `map01`: Static Map (`InstanceMap=false`)
- M1 권장 맵 타입: SideViewRectTile(2)
- M1 전투 격리: 플레이어당 Instance Map 하나

맵 타입 전환은 `.map` 파일을 직접 편집하지 않고 Maker Hierarchy에서 수행해야 합니다. 전환 후 AI가 Refresh하고 `TileMapMode`를 다시 확인한 다음 Phase 0 기술 검증을 시작합니다.

## 핵심 개발 규칙

- 일반 Lua `require`/메타테이블 클래스 프레임워크를 만들지 않습니다.
- 사용자 Manager를 엔진 `Service`처럼 확장하지 않습니다.
- 전투 상태는 맵 범위 `BattleSessionComponent`가 단독 소유합니다.
- 플레이어별 런 상태는 `PlayerRunStateComponent`가 소유합니다.
- 일반 적은 데이터 기반 Pattern Runner를 사용하고, 복잡한 보스만 필요 시 BT를 사용합니다.
- `.codeblock`, `.directory`, `Environment`, `Global`은 수정하지 않습니다.
- `.model`, `.map`, `.ui`는 전용 Builder를 사용합니다.
