# CSV만으로 콘텐츠 추가하기 — 검증 예제

이 예제의 목적은 새 `.mlua` 분기를 만들지 않고 기존 규칙을 조합해 스킬과 적을 추가하는 것이다.
Stage 1 기본 출현 목록에는 섞지 않고 `csv_authoring_test` Pool에서 독립적으로 검증한다.

## 게임에서 추가된 내용

| 콘텐츠 | 체감 동작 |
|---|---|
| 장거리 찌르기 | 앞이 비어 있어도 2칸 안의 첫 적 공격 |
| 갈라치기 | 앞 1칸과 3칸의 적을 동시에 공격 |
| 후퇴형 주황버섯 | 자기 턴에 플레이어 반대쪽 빈칸으로 후퇴 |
| 예고형 주황버섯 | 공격을 2턴 예고한 뒤 실행 단계로 전환 |

## 추가한 Skill 행

```csv
1,csv_long_jab,장거리 찌르기,attack|csv_example,FIRST_ENEMY_FORWARD,2,,1,,0,basic_slash,csv_long_jab_effects,,0.40,false
1,csv_split_sweep,갈라치기,attack|csv_example|area,RANGE_OFFSETS,3,1|3,1,,0,heavy_slash,csv_split_sweep_effects,,0.60,false
```

```csv
1,csv_long_jab_effects,1,DAMAGE,PRIMARY_TARGET,2,,,
1,csv_split_sweep_effects,1,DAMAGE,ALL_SKILL_TARGETS,1,,,
```

기존 Target Resolver, Damage Executor와 Motion Profile만 재사용한다. Session에 SkillId 조건문을
추가하지 않는다.

## 추가한 Enemy 행

```csv
csv_retreat_mushroom,후퇴형 주황버섯,5,1,prototype_retreat,TRACK_PLAYER,FACE_PLAYER,false
csv_telegraph_mushroom,예고형 주황버섯,7,2,prototype_telegraph,FIXED_FACING,FACE_PLAYER,false
```

```csv
csv_authoring_test,csv_retreat_mushroom,battledummyenemy,1,1,1
csv_authoring_test,csv_telegraph_mushroom,battledummyenemy,1,1,1
```

새 적 Model이나 AI 스크립트를 만들지 않고 기존 `battledummyenemy` Model과 Pattern Definition을
조합했다. 외형이 다른 실제 콘텐츠를 제작할 때는 별도 Model/RUID를 준비하되 데이터 계약은 같다.

## 제작자가 지킬 순서

1. 기존 TargetType·EffectType·Pattern으로 표현 가능한지 확인한다.
2. Skill 또는 Enemy Definition 행을 추가한다.
3. 참조하는 Effect Step 또는 Spawn Pool 행을 추가한다.
4. `_ContentValidatorLogic:ValidateAllContent()`를 실행한다.
5. 실제 스폰, 대상 Cell, 피해와 Pattern 전이를 Maker에서 확인한다.

## 2026-08-02 Maker 검증 결과

- 전체 무결성 검사: Skill 9, Effect Step 9 포함, 오류 0건
- `csv_long_jab`: Cell `3|4` 검색 후 Cell 4의 첫 적에게 피해 2
- `csv_split_sweep`: Cell `3|5`의 두 적에게 각각 피해 1
- `csv_retreat_mushroom`: Cell `1 → 0`
- `csv_telegraph_mushroom`: `TELEGRAPH_TILE` 남은 횟수 `2 → 1`, 이후 Step 2 전환
- 위 기능을 위해 추가한 `.mlua` 분기 없음
