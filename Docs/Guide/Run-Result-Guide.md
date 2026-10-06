# Run 종료 결과 · 최근 10판 · 최고 기록

최근 종료 결과 한 건 저장에 이어 **최근 10판 + 최고 기록 별도 보관**을 구현했다. 2026-10-03에 v3 시작 조건과 리전 진행 기록, 2026-10-06에 별도 공개 완주 랭킹을 추가했다. 개인 기록의 저장 키·최고 정책은 유지한다. 공개 동의/설정/조회는 [월드 랭킹 가이드](Run-World-Ranking-Guide.md), 후속 범위는 [작업계획](Run-Ranking-Workplan.md)을 따른다. 시즌 운영·랭킹 보상·리플레이는 미구현이다.

## 진행 상태

- ✅ 공개 랭킹의 Maker 격리 저장·대상 RPC·공개 빌드 및 UI 버튼 이벤트 경로 확인. 기존 개인 15개 + 공개 13개 로컬 mock 회귀 통과. 공개 데이터는 다른 사용자의 UserDataStorage를 읽지 않는 별도 사본이다.
- 🟡 실제 전체 런의 v3 전투 집계·출시/실제 다중 인스턴스/모바일/물리 포인터 회귀. Maker 단일 저장 및 합성 화면 fixture 검증과 구분한다.

- 🟡 v3 시작 조건·리전 집계·개인 기록 지역 탭·가독성 개선: 로컬 Lua 회귀 15개 통과, UIBuilder/lint 오류 0·경고 4개(대형 모달의 기본 예약영역 겹침, 좌우 두 열의 페이지 버튼/오른쪽 탭을 한 줄로 오인한 spacing/centering 안내). **Maker 등록/build/Play 및 실제 렌더는 미검증**이다. 아래 2026-10-01 검증은 기존 v1/v2 기능에 대한 과거 결과다.

- ✅ 최근 10판 개별 저장·작은 인덱스·최고 기록 유지·기존 키 이관 — Maker 저장/조회·삭제·이관 검증 통과
- ✅ 본인 기록 목록/상세 조회·보류 FIFO 일괄 저장·초과 기록 정리 — Maker 및 Play 재시작 검증 통과

- ✅ 결과 규격·서버 종료 경계 — Maker 메서드 경계 테스트 통과
- ✅ UserDataStorage 저장·재조회·중복 방지 — Maker 저장 및 Play 재시작 테스트 통과
- ✅ Maker 회귀: 포기/패배/완주 상태·초기화·본인 조회·오래된 결과·손상 규격·실패 보류/복구
- ✅ SchemaVersion 2: 종료 시 유물·공통 증강·보유 스킬/스킬별 증강을 복사. 강화·초기화·빈 목록·v1 호환·본인 조회 검증
- ✅ RunHistoryUI: UIBuilder 오류 0, Maker build 오류 0, PC 렌더·본인 저장 기록·버튼 이벤트·회귀 검증 통과
- ✅ 로비 기록 NPC: 실제 이동/E키 진입·Escape 닫기·입력 잠금·본인 기록 조회 검증. 포인터는 TouchEvent 연결 시험이며 실제 클릭/모바일 터치는 별도 확인
- 🟡 실제 포인터/모바일 터치의 수동 조작 검증. Maker 마우스 모의 입력은 기본 UI 버튼에 제한이 있어 버튼 연결은 `ButtonClickEvent`로 시험했다
- 🟡 컴포넌트 등록 경고 점검 및 실제 로비→최종 노드 전체 플레이·발행 환경 검증

### 기록 UI 가독성 개선

기록 상세는 긴 통계 문장 대신 전투 클리어·소비 턴·피격·플레이 시간 4개 카드를 사용하고, 제목/본문을 크게 읽히도록 하며 선택한 기록과 탭을 명확히 강조한다. 지역 진행에는 완료/미완료 배지를 표시한다. 날짜 행에서는 개발용 밸런스 버전 문자열만 숨기며, 결과 데이터에는 계속 보존한다. 기존 결과 규격, 저장 키·저장/조회 방식과 기록 데이터는 변경하지 않는다.

2026-10-06 Maker 연결 복구 후 현재 창의 PC 렌더와 공개 DTO의 지역/스킬 탭·선택/전환 버튼 이벤트 경로를 확인했다. v3 실제 전체 전투 집계와 실제 포인터/모바일 조작은 별도 검증 대상이다. 이전 2026-10-03 기록의 'Maker 대기'는 당시 검증 범위를 뜻하며 현재 공개 UI 점검 결과와 구분한다.

## 소유권과 저장

- `PlayerRunCombatStatsComponent`: 기존 통계 원본. 턴 번호/큐 길이를 다시 세지 않는다.
- `PlayerRunRegionHistoryComponent`: 플레이어별 리전 방문 순서·완료 여부·클리어 횟수·통계 차이를 메모리에서 집계한다. 매 턴 저장소에 쓰지 않는다.
- `RunRegionHistoryContractLogic`: 제한된 방문 배열의 검증·값 복사·저장 배열 정규화만 담당하는 순수 계약이다.
- `PlayerRunResultComponent`: 한 판의 시작 시각·영구 RunId·테스트 제외 사유·확정 JSON·보류 FIFO·본인 조회 캐시. 새 Run 시작이 보류 결과를 지우지 않는다.
- `RunResultServiceLogic`: RunManager 시작/종료 경계에서 결과 생성. 보상/스테이지 진행은 소유하지 않는다.
- `RunBuildSnapshotLogic`: 기존 Inventory/Augment의 종료 시 소유 상태를 읽는 어댑터와 빌드 DTO 검증. 소유권·효과·저장소를 변경하지 않는다.
- `RunResultContractLogic`: SchemaVersion 3 생성 및 v1/v2/v3 읽기·JSON 인코딩, 최대 4,000 UTF-8 bytes.
- `RunHistoryContractLogic`: 보관 개수, 인덱스 검증·인코딩, UI용 요약 규격. `RetentionLimit=10`이며 1~50까지 설정 가능.
- `RunBestRecordPolicyLogic`: 최고 기록 후보/비교 규칙만 담당한다. 저장·전투·보상은 소유하지 않는다.
- `RunResultRepositoryLogic`: ProfileCode(없으면 UserId)의 UserDataStorage 결과 전용 키를 읽고 쓴다. `UnionProfile`이나 쿠폰 영수증을 수정하지 않는다.
- `RunHistoryPresenterLogic`: 본인 보존 기록의 ID에 해당하는 현재 카탈로그 표시 정보를 서버에서 대상 클라이언트에 전달한다. 동일 캐시의 반복 전송도 10초 제한을 적용한다.
- `RunHistoryUIComponent`: 클라이언트 화면의 선택·탭·페이지·대기 상태만 관리한다. 저장과 보상 정책을 소유하지 않는다.

`RunId`는 기존 Union 보상의 영구 `RewardRunId`다. `RunSequence`는 접속 내 진행 번호이며 저장 식별자로 쓰지 않는다. `RecordId=run:<RunId>`는 사용자 저장소 안에서 유일하다.

### 저장 키와 보존 순서

| 키 | 내용 |
|---|---|
| `RunResultLatestV1` | 이전 한 건 저장 키. 읽기/이관 전용이며 원본을 삭제·덮어쓰지 않음 |
| `RunResultHistoryIndexV1` | 최근 RunId 목록, 최고 RunId, 비교 규칙 버전, 정리 대기 목록 등. 최대 4,000 bytes |
| `RunResultRecordV1:<RunId>` | 해당 판의 확정 결과+빌드. 각 값 최대 4,000 bytes |

1. 정상 완주/패배/포기 결과를 영구 RunId 내림차순으로 정렬하고 최근 10건을 유지한다. Maker/테스트 기록도 **최근 목록에는** 포함한다.
2. 최고 기록은 별도 `BestRunId`로 참조한다. 최근 10건에서 밀려나도 해당 판의 **전체 빌드 포함 원본**은 유지한다. 최근 목록에 최고 기록도 있으면 같은 원본을 공유하므로 중복 저장하지 않는다.
3. 원본들을 BatchSet으로 저장하고 성공을 확인한 후 작은 인덱스만 CAS(UpdateAndWait)로 변경한다. 동일 ID/동일 JSON 재시도는 기록 수나 원본을 늘리지 않고, 다른 JSON은 충돌로 거절한다.
4. 인덱스 커밋 **후에만** 오래된 원본을 BatchDelete한다. 최근/최고 기록은 삭제 대상에 넣을 수 없다. 정리 실패는 `PendingDeleteRunIds`에 남겨 다음 저장/중복 재시도 때 처리한다. 정리가 밀려도 이미 저장한 결과·전투·보상을 재실행하지 않는다.
5. `PrunedThroughRunId` 이하의 오래된 재시도는 정리한 기록을 되살리거나 최신 기록을 바꾸지 않는다. 그보다 최신인 지연 결과는 최근 목록 안에 삽입할 수 있지만 최신 결과는 항상 가장 큰 RunId다.

정상 정리 후 최근 10건과 그 밖의 최고 기록 최대 1건을 보관한다. 이전 키 원본은 호환용으로 추가 유지하며, 정리 실패/인덱스 커밋 전 장애로 미참조 원본이 남을 수 있다. 따라서 장애 상황까지 물리 저장 키가 항상 11개라고 보장하지 않는다.

`RetentionLimit`을 바꾸면 **다음 새 결과 저장 때** 적용된다. 낮추면 초과 기록을 정리하고, 늘려도 이미 삭제한 기록을 복구하지 않는다. 파일 기본값이나 Maker Logic 프로퍼티를 수정하며, 클라이언트가 임의 변경하는 RPC는 없다.

기존 인덱스는 CAS로 보호하지만 최초 키/원본 생성은 Set 방식이므로 **최초 저장의 다중 인스턴스 동시 접속 경쟁은 별도 출시 검증 대상**이다. 계정별 분산 잠금과 인덱스 커밋 전 남은 원본의 전역 청소는 이번 범위에서 보장하지 않는다.

### 최고 기록 비교 규칙

`PolicyVersion=completed_progress_turns_hits_time_v1`. `RankEligible=true`인 `COMPLETED`만 후보로 사용한다. Maker/Prototype/시작 미관측/미완주 기록은 최고 기록을 바꾸지 않는다.

1. `CompletedStageNumber`가 높은 기록
2. 같으면 `ConsumedTurns`가 적은 기록
3. 같으면 `HitsTaken`이 적은 기록
4. 같으면 `ElapsedSeconds`가 짧은 기록
5. 완전히 같으면 기존 최고 기록 유지

이것은 **현재 개인 최고 기록 규칙**이지 공개 랭킹의 확정된 점수 공식이 아니다. StageNumber 최댓값을 사용하는 기존 통계 의미도 그대로 유지한다. 향후 경로/직업/난이도/시즌별 랭킹을 도입할 때는 비교 집단과 밸런스 버전을 먼저 고정해야 한다. 정책 버전을 바꾸면 이전 인덱스를 조용히 새 규칙으로 읽지 않고 `RUN_BEST_POLICY_UNSUPPORTED`로 거절하므로 명시적 마이그레이션이 필요하다.

## 종료 연결

- `InitializeNewRunOwnedState`: 정상 시작 메타데이터 캡처.
- `EnsureRunState`: 시작 관측 없이 기존 Run에 붙으면 `RUN_START_UNOBSERVED`로 제외.
- `RecordBattleResult`: 단일 Stage 승리가 아니라 Run이 `Completed`/`Failed`가 된 경우만 확정.
- `CompleteCurrentContent`: 마지막 상점/휴식 등 비전투 노드 완료도 저장.
- `AbandonRun`: 통계를 지우기 전에 `ABANDONED` 확정.
- `ResetFailedRun`: 아직 결과가 없다면 초기화 전에 `DEFEATED` 확정. 기존 확정 결과는 변경하지 않음.
- `MarkRunCompleted`: PrototypeTestMode를 지우기 전에 테스트 제외를 고정.
- `BattleGatewayLogic`의 초기화 및 `MarkStarted` 성공 후: 리전 방문을 관측하고 실제 첫 전투의 난이도를 한 번만 고정.
- `RunManagerLogic.RecordBattleResult`의 진행 상태 커밋 후: 같은 전투 키로 한 번만 리전 클리어를 반영.

종료 사유는 `COMPLETED`, `DEFEATED`, `ABANDONED`다. Maker Play는 `MAKER_TEST`로 제외하고 테스트 진입은 `PROTOTYPE_TEST`로 제외한다. 같은 Run의 제외 사유는 되돌리지 않는다. 일반 종료 결과의 `RankEligible`는 향후 랭킹 후보 표시일 뿐, 현재 순위 등록은 하지 않는다.

## SchemaVersion 3: 시작 조건과 리전 진행

v2의 기존 필드와 `Build`는 그대로 유지하고 다음 세 필드만 추가한다. 저장 키와 인덱스 버전, 기존 개인 최고 기록 비교 정책은 바꾸지 않는다.

| 필드 | 내용 | 해석 |
|---|---|---|
| `Conditions` | `Captured`, `ObservedStart`, `DifficultyId`, `BalanceVersion`, `SeasonId`, `RankingRuleVersion`, `AccountProgressionMode` | 서버 시작 메타데이터. 난이도는 NEW_RUN 초기화 뒤 실제 첫 전투 커밋에서 한 번 확정 |
| `ClearedBattleCount` | 실제 승리 커밋 수 | 최대 스테이지 번호가 아니다. v1/v2 조회에서는 값이 없으므로 0으로 표시하지 않음 |
| `RegionHistory` | `Captured`, `Complete`, `Visits[]` | 순서 있는 지역 단위 진행 기록. 개별 StageId 목록이나 상점/보상 방문 로그는 저장하지 않음 |

`Visits[]` 각 항목: `RegionId`, `Completed`, `ClearedBattles`, `ConsumedTurns`, `HitsTaken`.

- `Captured`: 해당 버전에서 리전 기록 기능이 실행됐는지. 이전 v1/v2는 false로 조회한다.
- `Complete`: 관측 누락 없이 집계했는지. **게임 완주 여부가 아니다.** 정상적으로 관측한 패배/중단 기록도 true일 수 있다.
- `Completed`: 해당 방문 리전의 마지막 전투를 클리어했는지. 마지막 진행 지역은 미완료로 남을 수 있다.
- `RegionId`는 StageDefinitions 값을 그대로 참조한다. 명칭은 RegionDefinitions의 `DisplayName`을 사용하고, 정의 삭제 시 ID로 표시한다. 이름을 ID 문자열에서 추출하지 않는다.
- 같은 리전 안의 여러 전투는 하나로 합친다. 다른 리전에서 실제 전투를 시작한 경우만 다음 방문을 추가한다. 나중에 이전 리전으로 돌아오면 새로운 방문 항목이 된다. 최대 16회 방문이며 넘기면 관측 불완전으로 제외한다.
- 다음 노드의 비전투 구간을 따라 첫 전투 경계들을 확인한다. 같은 리전 전투가 하나라도 남으면 리전 종료로 간주하지 않는다. 현재 슬리피우드 6-4는 미완료, 6-8은 마지막 전투다.
- 리전 턴/피격 수는 기존 전투 통계의 차이로 계산한다. 패배한 전투·중도 포기의 마지막 통계도 포함한다. 저장은 런 종료 때 기존 결과와 함께 한 번 확정한다.
- `BalanceVersion` 기본값 `unversioned`, `SeasonId=all_time`, `RankingRuleVersion=completion_turns_hits_v1`, `AccountProgressionMode=ACCOUNT_APPLIED`. 운영 밸런스 버전은 공개 랭킹 도입 전에 명시적으로 지정해야 한다. 이 메타데이터 추가가 계정 성장이나 개인 최고 비교 정책을 바꾸지는 않는다.
- v1/v2의 원본 JSON은 유지한다. 읽기 DTO의 새 필드는 `Captured=false`로 제공하며, 과거의 경로/조건을 현재 데이터로 추측하지 않는다.

### 이번 변경 검증과 Maker 확인 순서

2026-10-03 로컬 Lua 런타임에서 실제 mLua 메서드를 추출해 14개 회귀 검사를 통과했다. 엔진·저장소·RPC는 mock이며 Maker 검증의 대체가 아니다. 실제 NodeDefinitions/StageDefinitions 그래프로 중간 보스/최종 보스와 지역 분기를 검사했다. 시작/종료 서비스 연결, 중복 확정, 저장 실패 보류, 새 런 초기화 이후 확정 JSON 유지, 이전/신규/빈 기록 화면 렌더 메서드도 검사했다. 2리전/빌드 포함 예시 결과는 1,184 UTF-8 bytes, 4,001-byte 입력은 거절했다. UIBuilder 구조 오류는 0이다.

1. Maker 편집 모드에서 Refresh해 신규 `RunRegionHistoryContractLogic`과 `PlayerRunRegionHistoryComponent`를 등록한다. `.codeblock`은 Maker가 생성하게 둔다.
2. build 로그를 확인하고 Play한다. 같은 리전에서 2개 전투를 완료해 방문 항목은 하나, 클리어 횟수는 2인지 확인한다.
3. 다음 리전 전투에 실제 진입한 뒤 패배하거나 포기하고 로비 기록 NPC에서 **지역 진행**을 확인한다. 선택만 하거나 실패한 이동은 방문에 추가되면 안 된다.
4. 일반/어려움 시작 조건, 중복 결과 호출, 새 런 초기화, 슬리피우드 중간/마지막 보스와 기존 v1/v2 기록의 미수집 표시를 회귀 확인한다.
5. 새 UI의 실제 포인터·탭·페이지·Escape 및 Play 재시작 후 저장값을 확인한다. 현재 세션에는 Maker 실행 도구가 없어 이 단계는 대기 중이다.

## 기존 SchemaVersion 2: 보유 빌드

기존 필드: `RecordId`, `RunId`, `RunSequence`, `RunSeed`, `RuleVersion`, `StartedAtUtc`, `EndedAtUtc`, `EndReason`, `EndDetail`, `JobId`, `NodeGraphId`, `LastNodeId`, `LastStageId`, `RouteId`, `CompletedStageNumber`, `ConsumedTurns`, `HitsTaken`, `ElapsedSeconds`, `CurrentHp`, `MaxHp`, `RankEligible`, `RankExclusionReason`. v2에 `Build`를 추가했다.

- 시각: 서버 UTC 문자열(`yyyy-MM-dd HH:mm:ss.fff UTC`). MSW JSONDecode가 ISO `T/Z` 문자열을 지원하지 않는 Date 토큰으로 자동 변환하므로 ISO 형식은 사용하지 않는다. 경과 시간: 기존 Run 통계의 초 단위 값이며 상점 체류도 포함한다.
- `CompletedStageNumber`는 현재 진행 코드의 StageNumber 최댓값이다. 실제 통과 노드 수나 지역 번호로 해석하지 않는다.
- `RouteId`는 현재 선택 분기(`UPPER`/`LOWER`)다. 아직 랭킹용 완전 경로 ID를 정의한 것이 아니다.
- 직업과 빌드는 종료 시 서버 소유 상태에서 읽는다. v3의 시즌·난이도·밸런스 버전은 위 `Conditions`에 별도로 기록한다. `RuleVersion`은 게임 집계 규칙 버전이며 저장 스키마 번호와 별개다.
- 손상된 저장값/미지원 스키마/과대 JSON은 실패로 반환하고 기본값으로 덮지 않는다.

### Build: 종료 시 보유 목록

| 조회 DTO | 저장하는 내용 | 의미 |
|---|---|---|
| `Build.Captured` | boolean | v2의 실제 수집 결과는 true. v1 기록은 false로 조회되어, 정보 미수집과 실제 빈 빌드를 구분 |
| `Build.Relics[]` | `RelicId`, `Amount` | 종료 시 보유 유물 ID와 수량 |
| `Build.Augments[]` | `AugmentId`, `Stacks` | 공통/패시브 증강 ID와 중첩 수. 스킬에 붙은 증강은 이 목록에 중복 등록하지 않음 |
| `Build.Skills[]` | `SkillId`, `Amount`, `SkillTier`, `SlotIndex`, `AugmentIds[]` | 보유 스킬 ID·수량·정의상 강화 단계·스킬바 위치·해당 스킬의 증강 ID 목록 |

- `SkillTier`는 CSV 정의의 단계다. `Amount`와 증강 개수를 스킬 단계로 오해하지 않는다. `SlotIndex=0`은 스킬바에 없거나 아직 초기화되지 않은 보유 스킬이다. 슬롯 수를 6으로 하드코딩하지 않는다.
- `AugmentIds`는 적용 순서와 중복을 그대로 보존한다. 예: `skill_power, skill_quick, skill_power`. 스킬 강화로 ID가 교체되면 기존 소유 컴포넌트가 이전한 증강들을 강화된 ID 아래에 기록한다.
- 서버의 동일 RunSequence만 읽고, 초기화 전에 일반 테이블로 복사한 뒤 JSON을 확정한다. 기록을 새 Run의 소유 상태에 다시 연결하거나 재계산하지 않는다.
- 최종 보유 목록이지 획득/판매/소모 이력은 아니다. 이미 판매하거나 소진해 사라진 유물, 교체한 이전 스킬은 목록에 남지 않는다. 유물 사용 잔량·회복 횟수·일시 버프·전투 중 쿨타임도 이번 DTO 범위가 아니다.
- 크기 절약을 위해 이름·아이콘·전체 효과 정의는 저장하지 않는다. 표시 계층은 ID를 카탈로그에 매핑하고, 삭제된 ID는 ID 자체로 표시해야 한다. 저장 당시의 피해/쿨타임/효과 문구까지 고정한 밸런스 스냅샷은 아니다. 결과 UI는 로비 메뉴에서 기록을 열고 선택한 판의 보유 빌드를 조회하는 화면으로 구현한다.
- 단일 목록은 최대 128개까지 검증한다(과대 입력 방어; 게임의 실제 보유 상한을 바꾸는 규칙이 아님). 전체 JSON의 4,000-byte 제한이 우선이며, 초과 시 목록을 몰래 자르지 않고 저장을 거절한다. 콘텐츠 상한이 커지면 별도 빌드 키/크기 규격을 함께 설계해야 한다.

### 저장/조회 호환 규칙

- 인덱스가 없으면 기존 `RunResultLatestV1` 한 건을 최근/최고 DTO로 읽는다. 다음 저장에서 원본 JSON을 개별 키에 그대로 복사하고 새 인덱스에 포함한다. 이관 전 조회만으로 빈 인덱스를 쓰지 않는다. 키 이름의 V1은 키 규격 이름이며, 결과 본문의 `SchemaVersion`(현재 3)과 다르다.
- v1은 읽을 때만 `Build={Captured=false, Relics={}, Augments={}, Skills={}}`를 제공한다. 원본 JSON은 바꾸지 않아 CAS/중복 비교가 유지되고, 과거 빌드를 현재 소유 목록으로 추정하지 않는다. 새 결과 쓰기는 v2만 허용한다.
- MSW `JSONEncode`는 빈 테이블을 직렬화하지 못한다. 저장 JSON에서는 빈 `Relics/Augments/Skills/AugmentIds`를 생략하고, 알려진 v2를 읽을 때 빈 목록으로 복원한다. `false`/문자열 같은 잘못된 목록 값은 빈 목록으로 취급하지 않고 거절한다. UI 조회 DTO에서는 항상 목록 테이블을 받는다.

## UI/다른 팀 연결

기존 최신 한 건 API는 호환 유지한다. 새 UI는 목록과 선택 상세를 분리하면 된다. 아래 함수들은 결과 화면을 직접 생성하지 않는 **데이터 연결 규격**이다.

```lua
-- ClientOnly: 화면을 열 때 한 번 요청(저장소 조회)
_RunResultServiceLogic:RequestMyRunHistory()

-- 동기화 후: 목록/최고 기록 읽기(저장소 호출 없음)
local history = _RunResultServiceLogic:GetLocalRunHistorySnapshot()
-- Success, Reason, IsLoaded, IsStale, Entries[], RetentionLimit,
-- HasBest, BestRecord, BestPolicyVersion, CleanupPending,
-- PendingResultCount, PersistenceState, Revision
if history.Success and history.IsLoaded then
    for _, entry in ipairs(history.Entries) do
        -- 최신순 요약: RunId, EndedAtUtc, EndReason, JobId,
        -- CompletedStageNumber, ConsumedTurns, HitsTaken, ElapsedSeconds,
        -- RankEligible, BuildCaptured. 전체 Build는 목록에 넣지 않는다.
    end
end

-- 사용자가 행 또는 최고 기록을 선택할 때: 본인 보존 목록의 RunId만 요청
_RunResultServiceLogic:RequestMyRunResultDetail(selectedRunId)
-- 동기화 후 선택 상세 읽기(전체 Build 포함, 저장소 호출 없음)
local detail = _RunResultServiceLogic:GetLocalRunResultDetailSnapshot()
-- Success, Reason, HasRecord, Record, IsStale, Revision
```

목록 요청과 기존 최신 요청은 같은 10초 제한·서버 캐시를 공유한다. 상세 RPC는 서버에서 0.25초 간격으로 제한하고, 이번 UI의 행 선택은 0.31초 디바운스를 적용한다. 상세는 로드된 본인 최근/최고 캐시에서만 제공한다. 목록을 먼저 로드해야 한다. 다른 계정의 ID나 정리된 RunId를 지정해 원본 저장 키를 임의 조회할 수 없다. 프레임마다 getter를 읽는 것은 저장소를 조회하지 않는다.

동기화는 비동기이므로 요청 직후 이전 선택 결과가 잠깐 남을 수 있다. UI는 현재 선택한 판 ID와 응답의 `Record.RunId`가 같은지 확인하고, 선택이 바뀐 뒤 도착한 늦은 응답은 폐기한다. `Revision`은 동기화된 스냅샷 변화를 감지하는 보조 값이다.

### 기록 화면 연결

- 로비 `Esc` 메뉴의 **플레이 기록** 항목에서 기록 화면을 연다. `GameMenuLogic`이 메뉴 진입점을 연결하고, `RunHistoryUIComponent`는 클라이언트 UI 어댑터로 화면 표시·탭·페이지·선택 상태를 담당한다.
- 추가 진입점은 로비 2층의 `/maps/lobby/Lobby_2F/Facilities/RunHistoryNPC` NPC다. NPC의 `LobbyInteractionComponent.InteractionId`를 `RunHistory`로 지정하고 `LobbyInteractionFocusLogic.TargetPaths`에 이 경로를 등록해 기존 상호작용 라우팅을 재사용한다. NPC를 클릭하거나 가까이에서 현재 상호작용 키(기본 `E`)를 누르면 `/ui/RunHistoryUI/Controller`의 `RunHistoryUIComponent:SetOpen(true)`로 기록 화면을 연다. 기존 `Esc` 메뉴 진입은 그대로 유지하며, 원격 저장이나 기록 DTO는 변경하지 않는다.
- NPC 명패는 **플레이 기록**이며 유니온 상점 오른쪽 게시판 옆에 있다. 기본 로비 시작점에서 오른쪽 5칸 이동 후 `E`로 열 수 있다. 위치는 `map/lobby.map`의 Transform, 명패는 NameTag, 대기 모션은 SpriteRenderer의 `SpriteRUID=eb08d517056849509e291579b3cfaca9`로 조정한다. 상호작용 거리도 NPC의 `LobbyInteractionComponent` 설정으로 조정하며 별도 NPC 저장소/서비스는 추가하지 않는다.
- 최근 기록은 페이지당 5개를 보여 주며 페이지 수는 실제 목록 개수로 계산한다(기본 보관 수 10). 최고 완주 기록은 최근 목록과 별도로 선택할 수 있다.
- 선택한 기록은 **지역 진행 / 스킬 / 증강 / 유물** 네 탭으로 나누고, 각 탭은 페이지당 3개씩 표시한다. 기본 탭은 지역 진행이며 방문 순서·완료 여부·클리어 횟수·턴·피격을 보여 준다. 스킬 상세에는 해당 스킬에 붙은 증강을 저장된 순서와 중복 그대로 보여 준다.
- v1 기록은 빌드가 실제로 비어 있는 것이 아니라 미수집 상태다. `Build.Captured=false`이면 **빌드 정보 미수집**으로 표시한다. `Captured=true`이면서 해당 목록이 비었을 때만 그 종류에 **없음**을 표시한다.
- 저장 대기 중이거나 조회에 실패해도 이전에 로드한 기록은 화면에서 지우지 않는다. 성공/최신 상태가 아닌 경우 stale 또는 저장 대기 상태를 함께 표시한다. 목록은 성공한 저장 세대만 기준으로 하며 새 보류 결과는 `PendingResultCount`/`IsStale` 상태로 구분한다.
- `RunHistoryPresenterLogic`은 ServerOnly 경계에서 해당 계정이 보유한 최근/최고 기록 ID만 대상으로 서버 전용 CSV 카탈로그에서 이름·아이콘·설명을 찾고, 표시용 DTO만 요청한 클라이언트에 전달한다. 전체 CSV나 다른 계정의 ID/기록을 공개하지 않는다.
- 이 화면 연결은 저장 키·결과 JSON 규격·보상 처리·서버 CSV 공개 여부를 바꾸지 않는다. ID 카탈로그 매핑은 표시용일 뿐, 저장 당시 밸런스/효과 설명을 고정하는 스냅샷은 아니다.
- 번역 키가 미등록이거나 정의가 삭제된 경우 이름 대신 ID를 표시한다. 프리미엄 자석펫은 기존 읽기 전용 정의를 사용하며 조회로 구매/지급을 실행하지 않는다.
- v3는 실제 `ClearedBattleCount`를 **전투 클리어 N회**로 표시한다. v1/v2는 `CompletedStageNumber`를 **최대 단계 N (이전 기록)**으로 표시해 실제 클리어 횟수와 구분한다.
- 조회가 8초 안에 완료되지 않으면 조회 지연 문구를 표시한다. 첫 조회가 지연됐다고 빈 기록으로 단정하지 않는다. 늦게 정상 응답이 도착하면 표시를 복구한다.
- 2026-10-01 당시 v1/v2 기록 UI는 UIBuilder 오류 0, 오프라인 배치와 Maker PC 렌더·메서드/버튼 이벤트 검증을 완료했다. 이는 과거 검증 결과이며, 현재 v3 지역 탭·가독성 변경은 Maker에서 미검증이다. 실제 포인터/모바일 터치 조작과 발행 환경도 별도 확인 항목이다.

ServerOnly에서는 `_RunResultServiceLogic:GetRunHistory(playerEntity)`로 같은 세대의 최근 ID 목록/기록 맵/최고 기록을 읽는다.

### 기존 최신 한 건 연결

ClientOnly에서 명시적으로 한 번 요청:

```lua
_RunResultServiceLogic:RequestMyLatestRunResult()
```

동기화 후 UI 읽기:

```lua
local result = _RunResultServiceLogic:GetLocalLatestRunResultSnapshot()
-- Success, Reason, HasRecord, Record, PersistenceState, IsStale, Revision
if result.Success and result.HasRecord then
    local build = result.Record.Build
    if build.Captured then
        for _, skill in ipairs(build.Skills) do
            -- SkillId -> 표시 카탈로그, SkillTier -> 강화 단계, AugmentIds -> 적용 증강 목록
        end
    else
        -- 이전 기록: "빌드 정보 미수집" (소유 스킬/유물 없음으로 표시하지 말 것)
    end
end
```

최초 플레이 전 로비에서도 요청할 수 있다. 사용자 ID나 점수를 인자로 받지 않는다. 요청은 10초 간격으로 제한한다. 읽기 함수만 프레임마다 호출해도 저장소를 조회하지 않는다.
조회 대기 중 새 결과가 확정되면, 늦게 돌아온 이전 조회값은 Revision 비교로 버린다.

ServerOnly에서 재조회:

```lua
local result = _RunResultServiceLogic:GetLatestRunResult(playerEntity)
```

`PersistenceState`: `NONE`, `PENDING`, `SAVING`, `SAVED`. `PENDING`은 아직 DB 저장에 성공한 것이 아니다. 보류 결과는 FIFO로 보존하며 새 판이 끝나도 이전 보류 JSON을 교체하지 않는다. 저장/퇴장에서는 그 시점의 보류분을 **하나의 payload BatchSet + 인덱스 커밋**으로 합쳐 처리한다. 대기 중 추가된 결과는 지우지 않고 다음 저장으로 넘긴다.

5/10/20/40/60초 간격으로 최대 5번 자동 재시도하며 크레딧 소진은 60초 간격으로 완화한다. 퇴장 시 보류분을 다시 시도한다. 서버 강제 종료나 계속되는 저장 장애에서 메모리 보류 결과의 영속성은 보장하지 않는다. 전투/보상 처리를 재실행해 재시도하지 않는다. 재조회 실패 시 기존 캐시는 보존하지만 `Success=false`, `IsStale=true`로 반환한다. 최근 목록은 저장 성공 세대만 표시하고 보류분이 있으면 `IsStale=true`/`PendingResultCount`로 표시한다. 최신 한 건은 새 확정 결과를 PENDING 상태로 먼저 보여줄 수 있다.

## 테스트와 다음 작업

2026-10-01, lobby Maker Play, MCP 서버/클라이언트 메서드 호출로 확인:

| 항목 | 확인 결과 |
|---|---|
| 중도 포기 | `ABANDONED`, 2턴·피격 1회·HP 9·직업 warrior 저장. Run 초기화 후 통계는 0이어도 저장 DTO는 유지 |
| 완주 상태 | `MarkRunCompleted`→FinalizeRun에서 `COMPLETED` 저장. PrototypeTestMode가 지워져도 Maker 제외 유지 |
| 패배 | ResetFailedRun 및 실제 RunManager.RecordBattleResult의 Defeat 경계에서 `DEFEATED` 저장 |
| Stage만 승리 | RunState의 Stage 승리 후 Run은 Active, 새 Frozen JSON 없음, 이전 저장 결과 유지 |
| 재실행 | Play 중지/재시작 후 RunId 175 결과 재조회. 새 접속의 RunSequence 1은 새 RunId 176을 사용 |
| 중복/역순/충돌 | 확정 재호출은 같은 JSON 반환. 동일 JSON 중복 쓰기 없음. 오래된 RunId 무시. 같은 ID의 변경 JSON 거절 |
| 규격 | SchemaVersion 99·음수 턴·4,001-byte 입력 거절, 기존 결과 보호 |
| 저장 실패/복구 | 별도 테스트 사용자 저장소의 미지원 스키마로 실패 유도: PENDING 및 결과 유지, 복구 후 SAVED. 테스트 키 삭제 코드 0 |
| 클라이언트 | 본인 요청 후 동기화된 DEFEATED 결과, `Success=true`, `HasRecord=true`, `PersistenceState=SAVED` 확인 |

완주 시험은 최종 상태/서비스 경계 호출 시험이며, 모든 맵을 실제 플레이한 E2E 시험은 아니다. Stage 승리 시험도 영구 보상을 임의 지급하지 않도록 RunState 메서드 경계로 진행했다.

현재 남은 확인:

- Maker에서 PlayerRunResultComponent와 PlayerRunShopStateComponent를 함께 동적으로 부착할 때 `LWA-3048 DuplicateComponent` 경고가 발생했다. 부착 순서를 바꾸면 경고의 두 이름 순서도 바뀐다. 파일의 상속 선언은 각각 `extends Component`, 자동 생성 UUID도 다르며, 기능 시험에서는 각각 조회 가능했다. 정확한 등록 경고 원인은 아직 확정하지 못했다. Maker 재시작 후 재현/등록 구조 점검이 필요하며 출시 준비 완료로 간주하지 않는다.
- 발행 환경의 실제 완주·접속 해제, 두 클라이언트 본인 이외 RPC 거부, 다중 인스턴스 최초 저장 경쟁은 별도 시험 필요.
- 타임아웃/크레딧 소진의 자동 타이머 재시도와 조회/종료 동시성은 구현되어 있지만 이번 Maker에서 해당 네트워크 장애를 강제로 재현하지는 않았다.

첫 저장 슬라이스 검증: 빌드 오류 0(기존 경고 3), 기능 실행 오류 0, 포기 결과 517 bytes 저장, 초기화 후 서버/클라이언트 `SAVED` 재조회 통과. 위 등록 경고는 남아 있다.

### v2 빌드 목록 확장 회귀

2026-10-01, lobby Maker Play, MCP 메서드 호출로 추가 확인:

| 항목 | 확인 결과 |
|---|---|
| 실제 v1 저장값 | 기존 사용자 저장소의 v1 결과 읽기 성공, `Build.Captured=false`, 원본 JSON 유지 |
| 실제 소유·강화 | 유물 2개 테스트 지급 + 기존 출발 유물로 총 3개, 공통 증강 1개, 스킬 2개. brandish→brave_slash 강화 후 Tier 2 및 증강 3개 순서/중복 유지 |
| 읽기 전용 캡처 | InventoryRevision/AugmentRevision 불변. 다른 RunSequence 캡처 거절 |
| 종료·초기화·저장 | AbandonRun에서 v2 결과 921 bytes 저장. 초기화로 런 목록이 비워져도 저장 빌드와 종료 직전 빌드의 필드별 값 동일 |
| 빈 목록 | 유물/증강/스킬 없는 캡처 DTO 인코딩·재조회 성공. 원본 DTO의 빈 목록은 수정되지 않음 |
| 잘못된 빌드 | 음수 수량·false 목록·중복 유물 ID·미지원 버전 거절. 동일 결과 중복 쓰기는 무시 |
| 용량 | 직업 조건에 맞는 유물 17종 + 스킬 6개에 증강 각 4개를 넣은 합성 DTO 2,103 bytes. 8,158-byte 합성 DTO는 TOO_LARGE로 거절, 실제 저장값 불변 |
| 본인 UI 조회 | `Success=true`, `PersistenceState=SAVED`, `Captured=true`, 유물 3/스킬 2 및 증강 배열 확인 |
| Play 재시작 | 로비에서 본인 조회 API만 호출해 RunId 179의 v2 결과 재조회. 유물 3/공통 증강 1/스킬 2와 강화 단계·슬롯·증강 배열 유지 |

용량 시험은 DTO 시험이며 해당 유물/스킬을 실제 런에 모두 지급하거나 저장하지 않았다. 전체 로비→최종 노드 플레이와 실제 UI 디자인 검증을 대체하지 않는다. 컴포넌트 등록 경고는 이 회귀 중에도 재현되어, 별도 점검 항목으로 유지한다.

v2 최종 검증: 빌드 오류 0(기존 경고 3), 재시작 후 조회 실행 오류 0. Maker는 편집 모드로 복귀했다. 재시작 후 본인 조회만 한 경로에는 상점 컴포넌트를 추가하지 않으므로, 이 경로에서 경고가 없다는 사실을 위 중복 등록 문제의 해결로 해석하지 않는다.

### 최근 10판 확장 회귀

2026-10-01, lobby Maker Play, 별도 테스트 UserDataStorage와 실제 본인 조회 API:

| 항목 | 확인 결과 |
|---|---|
| 빈 사용자 | 조회 성공, 기록 없음. 빈 인덱스를 쓰지 않음 |
| 12판 보존 | 최신 12~3번 10건, 최고 1번 별도 유지. 2번 원본 실제 삭제. 해당 인덱스 170 bytes |
| 최고 교체 | 13번으로 최고 교체 후 목록 밖 이전 최고 1번 삭제. Maker 제외 14번은 최고를 바꾸지 않음 |
| 중복·역순·충돌 | 동일 결과는 재기록하지 않음. 이미 정리한 오래된 ID는 부활하지 않음. 같은 ID의 다른 JSON 거절 |
| v1 이관 | 한 건 v1을 읽고 다음 저장에서 개별 키+인덱스로 이관. 원본 JSON 불변, 과거 빌드는 미수집으로 유지 |
| 손상 보호 | 미지원 인덱스 버전·중복 ID·삭제/보존 겹침 거절. 미지원 인덱스는 덮어쓰지 않고 새 원본도 쓰지 않음 |
| 정리 중단 회복 | 이미 삭제한 ID가 정리 대기 목록에 남은 상태를 재현. 중복 재시도로 목록 정리 |
| 보관 설정 | 3건으로 변경 시 4~2번 유지 + 최고 1번 별도 유지. 테스트 후 기본 10으로 복귀 |
| UI 조회 | 본인 이전 179번 목록/상세 조회. 10행 합성 fixture 요약·최고 기록·유물 3/스킬 2 상세 동기화 확인. 미보존 ID 거절 |
| 12판 일괄 저장 | 12개 JSON을 한 번의 SaveResults로 저장해 최근 10건+목록 밖 최고 기록 유지. 같은 배치 재시도는 쓰기 없음, 충돌이 포함된 배치는 거절 |
| 보류 FIFO | 보류 2판을 한 번에 저장해 두 원본 모두 유지. 보류 수 0, 최신 14번, SAVED 확인 |
| 자동 재시도 | 별도 테스트 사용자의 로컬 저장 잠금으로 PENDING을 유도한 뒤 잠금 해제. 실제 5초 타이머가 저장 성공. 네트워크 장애 시험은 아님 |
| Play 재시작 | 최근 10건·최고 기록·목록 밖 최고 기록의 전체 빌드·이관된 v1의 미수집 표시 유지 |
| 실제 종료 연결 | StartNewRun→ApplyJobSelection→AbandonRun에서 180번 생성. 기존 179번 원본 이관 및 보존, 실제 목록 2건, Maker 기록은 최고 후보에서 제외 |
| 입력 방어 | 빈 배치·빈 JSON·성긴 배열·문자열 키 목록·혼합 목록 거절. 동일 결과 2개 배치는 중복 쓰기 없음. 클라이언트 음수 상세 ID 거절 |
| 최종 재조회 | Play 재시작 후 본인 목록 180/179 및 두 기록의 빌드 상세 조회. 보류 수 0, SAVED, 기존 179번의 유물 3/스킬 2 유지 |
| 테스트 정리 | 격리된 합성 사용자 7개의 테스트 키 38개 삭제 후 비어 있음 재확인. 실제 사용자 179/180번과 기존 이전 키는 보존 |

합성 fixture는 실제 사용자 보상/인벤토리를 변경하지 않는다. 실제 종료 연결 시험은 기존 RunManager의 정상 직업 시작/포기 경계로 진행했고, 기존 영구 기록을 임의로 삭제하지 않았다. 테스트용으로 분리한 키만 정리했다.

최종 검증: 빌드 오류 0(기존 경고 3), 마지막 재시작·입력 검증·본인 목록/상세 조회 실행 오류 0. Maker는 편집 모드로 복귀했다. 실제 Run 시작 시험에서는 위 컴포넌트 등록 경고가 재현되었으므로, 최종 조회 경로에서 경고가 없다고 해결된 것으로 간주하지 않는다.

### 기록 UI 회귀

2026-10-01, lobby Maker Play와 MCP 클라이언트 DTO/버튼 이벤트 검사:

| 항목 | 확인 결과 |
|---|---|
| 등록·진입 | 새 UI/스크립트 등록, Esc 메뉴의 플레이 기록 버튼 이벤트로 열기, 메뉴 닫기·입력 차단 연결 |
| 실제 본인 기록 | Play 재시작 후 기존 180/179번 2판 조회, 선택한 판의 종료 통계와 전체 빌드 표시 |
| 스킬·증강·유물 | 스킬 2개·스킬 증강 3개 순서/중복, 유물 3개, 공통 증강 1개. 이름·아이콘·자석펫 표시와 번역 누락 ID fallback |
| 상세 페이지 | 5개 스킬/증강 행을 3행/페이지로 표시, 다음/이전 버튼 이벤트와 세 탭 연결 검증 |
| 최근/최고 | UI 전용 10행 fixture의 2페이지와 목록 밖 최고 기록 선택. 실제 사용자 저장 키에 합성 기록을 쓰지 않음 |
| 빈 기록·이전 버전 | 빈 목록, 실제 빈 빌드, v1 미수집 문구가 서로 구분됨 |
| 조회 실패·지연 | UI fixture에서 기존 행 유지와 지연 안내 확인. 실제 네트워크 장애 재현 시험은 아님 |
| 응답 순서 | 179번 선택 중 180번 상세 응답 폐기, 빠른 재선택은 최종 ID 또는 같은 ID의 캐시만 사용 |
| 반복 요청·닫기 | 연속 새로고침 2회가 표시 카탈로그 1회만 갱신. 실제 Escape 입력으로 기록만 닫고 메뉴가 재열리지 않음 |

최종 build 오류 0(기존 경고 3), 마지막 UI 회귀 실행 오류 0. Maker는 편집 모드로 복귀했다. 테스트 fixture는 클라이언트 UI 상태를 복구했으며 저장 규격·실제 사용자 기록·보상 상태를 변경하지 않았다. 버튼 연결은 Maker의 기본 UI 마우스 모의 입력 제한 때문에 `SendEvent(ButtonClickEvent())`로 검사했다. PC 렌더는 확인했으나 실제 포인터/모바일 터치 hit 영역의 수동 검증은 완료했다고 주장하지 않는다.

### 기록 NPC 회귀

2026-10-01, lobby Maker Play 재시작 후 MCP 입력/클라이언트 검사:

| 항목 | 확인 결과 |
|---|---|
| 배치·등록 | 기존 엔티티 67개에 NPC 1개만 추가. 타일 298개·Foothold 39개·MapleTile(0) 유지, Rigidbody 및 실제 사서 위즈 대기 모션 등록 |
| 실제 키 입력 | 시작점에서 `D` 5회 → `RunHistoryNPC` focus/inRange → `E`로 기록 창 열림. 상호작용 대상 7개, 기존 포털 우선순위 유지 |
| 본인 기록 | NPC 진입 후 실제 보존 목록 2건 로드, 180번 선택. 저장/보상 상태를 새로 생성하거나 변경하지 않음 |
| 입력·닫기 | 창이 열린 동안 `D`를 눌러도 위치 불변. `Escape`로 닫힌 뒤 입력 잠금 해제, 플레이 기록 안내 복구 |
| 모달 중복 방지 | Esc 메뉴가 열린 동안 NPC TouchEvent로 기록 창을 추가로 열지 않음 |
| 터치 이벤트 연결 | `SendEvent(TouchEvent(...))`로 공통 NPC handler → 기존 기록 UI 열기 확인. AutoFit 영역 `(0.4, 0.7)` 및 발판 높이 `y=-6.769` 확인 |

빌드 오류 0(기존 경고 3), NPC 회귀 실행 오류 0, 편집 모드로 복귀했다. Maker `mouse_input`의 화면 클릭은 이 검사에서 NPC의 TouchEvent를 발생시키지 않아 실제 포인터 hit 영역 통과로 기록하지 않는다. 클릭/모바일 터치는 수동 확인 대상이며 E키는 실제 입력 경로로 검증했다. NPC 전용 디버그 로그는 소스에 추가하지 않고 Maker 검사 스크립트로 증거를 수집했다.

다음 범위: 실제 전체 런·포인터/모바일 UI·복수 실제 계정/인스턴스 검증, 공개 랭킹 시즌 운영 및 과거 공개 payload 정리. 공개 SortableDataStorage 랭킹 기본 구현은 [월드 랭킹 가이드](Run-World-Ranking-Guide.md) 참조. 네트워크 장애와 실제 다중 인스턴스 경쟁은 별도 출시 회귀가 필요하다. 개인 최근 보관 개수 기본값은 50판이 아니라 **10판**이다.
