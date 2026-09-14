# 공통 전투 Stage 테스트 가이드

## 목적

전투 Stage마다 테스트 전용 맵이나 진입 코드를 만들지 않고, 모든 전투 맵이 같은 Maker 직접
실행 경로를 사용한다. 운영 중에는 `BattleEntryStateComponent.EntryState=PREPARED` 진입이 항상
우선하므로 테스트 자동 시작이 정상 런의 StageId를 덮어쓰지 않는다.

이제는 전투 맵을 일일이 열지 않아도 `battle_test_hub`에서 Stage, 직업, Seed를 선택해
동일한 운영 진입 경로로 전투를 시작할 수 있다. 빠른 단일 맵 확인이 필요할 때는 아래의
기존 Maker 직접 실행 경로도 계속 사용할 수 있다.

## 권장: 테스트 전용 시작맵

1. Maker에서 `battle_test_hub` 맵을 연다.
2. Play를 시작한다.
3. 좌우 버튼으로 Stage와 직업을 고르고, 필요하면 Seed를 조정한다.
4. `선택한 전투 시작`을 누른다.

Stage 목록은 `StageDefinitions.csv`와 `StageMapRoutes.csv`, 직업 목록은
`JobDefinitions.csv`에서 자동으로 읽는다. 새 Stage를 두 표에 정상 등록하면 테스트 UI에도
자동으로 나타나므로 맵별 테스트 버튼이나 하드코딩을 추가하지 않는다.

테스트 허브 요청은 서버에서 요청자, 현재 맵, Stage·Map Route, 직업, 프로필 준비 상태를
다시 검증한다. 진입에 성공하면 운영 `BattleGateway`의 `NEW_RUN` 경로를 그대로 사용하면서
해당 Run만 Prototype Test Mode로 표시한다. 따라서 허브에서 시작한 전투에서도 F8 강제
클리어를 사용할 수 있지만 정상 로비 Run에서는 사용할 수 없다.

## 빠른 확인: 전투 맵 직접 실행

`BattleSessionComponent.AutoStartPrototypeBattle=true`인 전투 맵을 Maker에서 직접 Play하면
`StageMapRouteRepositoryLogic.GetDefaultStageForMap(MapId)`가 `StageMapRoutes.csv`를 조회한다.

- 연결 Stage가 하나면 해당 Stage를 시작한다.
- 같은 물리 맵을 여러 Stage가 공유하면 `StageDefinitions.StageIndex`가 가장 낮은 Stage를 시작한다.
- MapId에 연결된 Stage가 없으면 잘못된 다른 지역 Stage를 시작하지 않고 오류를 기록한다.
- 운영 Gateway가 준비한 진입 정보가 있으면 이 자동 선택은 실행되지 않는다.

따라서 새 전투 맵은 `StageMapRoutes.csv`에 정상 등록하고 맵 루트의
`AutoStartPrototypeBattle=true`만 설정하면 같은 테스트 진입 기능을 재사용할 수 있다.

## 공용 맵의 특정 Stage 테스트

같은 맵을 공유하는 두 번째 이후 Stage는 맵 루트 `BattleSessionComponent`의
`PrototypeTestStageOverride`에 정확한 StageId를 잠시 입력한다.

예시:

```text
MapId: sleepywood_ant_tunnel
PrototypeTestStageOverride: region_06_stage_02
```

Override Stage가 다른 MapId로 라우팅되면 `PROTOTYPE_STAGE_MAP_MISMATCH`로 진입을 거절한다.
테스트가 끝나면 빈 문자열로 복원해야 다음 직접 Play가 기본 Stage를 선택한다.

## 공통 테스트 설정과 키

| 항목 | 기본값/동작 |
|---|---|
| `PrototypeTestJobId` | `warrior` |
| `PrototypeTestRunSeed` | 맵 설정값, 같은 값이면 웨이브 재현 가능 |
| `PrototypeTestEntryRequestId` | 맵 설정값 |
| `F8` | Prototype Test Mode에서만 현재 Stage 강제 클리어 |
| `Space` | 방향 전환으로 한 턴 소비, 적 Queue/예고 테스트에 사용 |
| `H` | 테스트 인벤토리에 물약이 있을 때 소모품 사용 요청 |

F8 요청은 sender와 `PrototypeTestMode`를 모두 검사하므로 정상 런에서는 동작하지 않는다.

## 검증 로그

테스트 허브에서는 다음 순서를 확인한다.

```text
[BattleTestHub] catalog refreshed ...
[BattleTestHub] start accepted ...
[BattleGateway] prototype test entry activated ...
[BattleWave] spawned ...
```

전투 맵 직접 실행에서는 다음 순서를 확인한다.

```text
[StageMapRoute] default stage resolved ...
[BattleSession] ... prototype auto start ...
[BattlePrototypeEntry] waiting ...          # 프로필 로드 중이면 표시
[BattleWave] spawned ...
[BattlePrototypeEntry] started ...
```

마지막으로 Build Error 0, Runtime Error 0, `[ContentIntegrity] valid`를 확인한다.
