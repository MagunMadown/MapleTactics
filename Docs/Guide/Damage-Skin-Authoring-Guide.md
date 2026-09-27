# 데미지스킨 설정 가이드

## 적용 범위

몬스터와 플레이어가 실제로 피해를 받으면 MSW 기본 `DamageSkinService`로 숫자를 한 번 표시한다. 기존 피격 이펙트·모션·HP 처리·큐·턴·사망 처리는 변경하지 않는다.

- 일반/스킬 공격, 밀치기 충돌: `BattleSessionComponent.ApplyDamage`의 성공 결과.
- 독/화상: `BattleSessionComponent.ApplyStatusDamage`의 성공 결과.
- 표시값: 방어/유물 계산 후 **실제 감소한 HP** (`AppliedAmount`). HP가 2 남았는데 5 피해를 주면 2를 표시한다.
- 막힌 공격(피해 0), 이미 죽은 대상, 실패한 공격은 표시하지 않는다.
- 연타는 기존 로직이 피해를 적용하는 매 타격마다 표시한다. 숫자를 늘리기 위한 가짜 타격이나 별도 턴 대기는 없다.
- 네이티브 데미지스킨은 정수 표시다. 현재 정수 전투값은 그대로 표시하며, 향후 소수 피해 도입 시 표시값은 반올림(최소 1)되므로 별도 정책 검토가 필요하다.

## 수정할 파일

`RootDesk/MyDesk/03_Data/DamageSkinDefinitions.csv`가 원본이다. 같은 위치의 `.userdataset`은 Maker 등록용이며 `serveronly=false`로 유지한다. 클라이언트 표시와 서버 선택 검증이 같은 표를 읽는다.

| 필드 | 의미 / 허용값 |
|---|---|
| SchemaVersion | 현재 `1` |
| SkinId | 변경하지 않는 고유 ID. 소문자로 시작하고 소문자·숫자·밑줄만 사용 |
| DisplayName | 목록에 보여줄 이름 |
| ResourceRuid | MSW **데미지스킨 리소스**의 32자리 RUID. 일반 숫자 이미지/이펙트 RUID가 아님 |
| TweenType | `Default`, `Volcano`, `Blade`, `DefaultMini`, `VolcanoMini`, `BladeMini` |
| OffsetX / OffsetY | 대상 원점 기준 위치 보정, 월드 단위(`1 = 100px`), -10~10 |
| Scale | 가로/세로 배율, 0.1~5 |
| PlayRate | 재생 속도, 0.1~5 |
| Alpha | 불투명도, 0.1~1 |

기본 행 `maple_default`(공격 피해), `maple_taken`(플레이어 피격)은 유지한다. 다른 기본 외형을 원하면 이 행의 리소스/표시 설정을 바꾸면 된다. 새 스킨은 새 ID로 행을 추가한다. 수정 후 Maker **Stop → Refresh → Play**로 다시 읽는다.

Repository는 중복 ID, 스키마 버전, 필수값, RUID 형식, 열거값, 숫자 범위, 기본 행 존재를 검증한다. 리소스의 실제 존재/로드 가능 여부는 네이티브 `PreloadAsync` 결과 로그로 확인한다. 표가 잘못되면 숫자 표시는 건너뛰지만 전투 피해 계산은 유지한다.

## 팀원용 API

```lua
-- UI에서 사용할 목록. Success 확인 후 Skins를 사용한다.
local options = _DamageSkinDefinitionRepositoryLogic:GetSkinOptions()
-- options = { Success, Reason, Skins = { { SkinId, DisplayName }, ... } }

-- 서버 내부에서만 호출: 장비/상점 담당 코드가 소유 여부를 검증한 뒤 적용한다.
local presentation = player:GetComponent("script.BattleUnitPresentationComponent")
local result = presentation:SetDamageSkin("maple_default", false) -- 내가 주는 피해
local result2 = presentation:SetDamageSkin("maple_taken", true) -- 내가 받는 피해
-- result = { Success, Reason, SkinId (성공 시) }
```

몬스터에게 주는 피해는 공격자의 `OutgoingDamageSkinId`, 플레이어가 받는 피해는 피격자의 `IncomingDamageSkinId`를 사용한다. 독처럼 공격자가 제거된 뒤 들어오는 피해는 기본 스킨을 사용한다. 알 수 없는 선택 ID는 표시 시 기본 행으로 대체하며, `SetDamageSkin`은 잘못된 ID를 거절한다.

큰 몬스터 등 특정 대상만 위치 조절이 필요하면 기존 `BattleUnitPresentationComponent.DamageNumberOffset`을 조절한다. 최종 위치는 CSV 오프셋 + 대상 보정 + 기존 `GroundVisualOffsetY`다. 킬 판정 전에 호출하되 클라이언트에서 `IsDead`로 숫자를 막지 않아 마지막 타격도 표시 대상으로 포함한다.

이번 기능은 **표시/목록/서버 선택 API**까지다. 선택 UI, 해금/구매, 계정 저장, 커스텀 숫자 이미지 제작, 치명타 판정은 포함하지 않는다. 플레이어 컴포넌트가 유지되는 맵 이동 동안 선택값도 유지되지만 재접속 영구 저장은 없다. 향후 저장 기능에서는 안정적인 `SkinId`만 저장하고 RUID는 표에서 해석한다.

## 검증 현황 및 수동 테스트

Maker MCP 연결 후 Refresh/Play를 확인했다. 빌드 오류 0건, `[DamageSkinData] loaded count=2`, 기본 스킨 2개의 `preloaded` 로그가 확인됐다. 전투 로그에서 몬스터와 플레이어의 `PlayDamageNumber` 호출도 각각 확인됐다. **실제 숫자 위치와 사망 직전 표시의 화면 검증은 아직 남았다.** 정적 검증 명령은 `node Artifacts/tests/damage-skin-contract-test.cjs`다.

화면에서 확인할 항목:

1. 몬스터/플레이어 각 1회 피격 시 실제 피해 숫자가 위로 떠오르는지 확인.
2. 방어 0피해는 숫자 없음, 연타는 타격별 1회, 독/화상도 1회 표시 확인.
3. 몬스터 마지막 타격과 보스/큰 몬스터의 위치 확인. 사망/웨이브 전환 시 숫자가 잘리는지는 반드시 화면에서 확인.
4. 다른 CSV 행으로 선택 후 스킨 변경, 맵 이동 후 유지, 잘못된 ID 거절 확인.
