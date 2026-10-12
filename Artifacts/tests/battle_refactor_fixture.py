"""Load actual stateless battle owners for deterministic mLua regression fixtures."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OWNERS = (
    "Resolvers/BattleUiStateLogic",
    "Resolvers/BattleMovementLogic",
    "Skills/SkillExecutionLogic",
    "Skills/SkillTargetResolverLogic",
    "Resolvers/EnemyPlanningLogic",
    "Skills/EffectExecutors/EnemySpecialEffectExecutorLogic",
    "Skills/BattleQueueLogic",
    "Skills/BattleQuickbarLogic",
)


def wire_logic_owners(runtime):
    for relative in OWNERS:
        path = ROOT / "RootDesk/MyDesk/01_Combat" / (relative + ".mlua")
        source = path.read_text(encoding="utf-8-sig").expandtabs(4)
        owner = runtime.table()
        for name, parameters, body in re.findall(
            r"^    method \w+ (\w+)\(([^\n]*)\)\n(.*?)^    end$", source, re.M | re.S
        ):
            args = [p.strip().split()[-1] for p in parameters.split(",") if p.strip()]
            owner[name] = runtime.eval(
                "function(self" + ("," + ",".join(args) if args else "") + ")\n" + body + "\nend"
            )
        assert list(owner.keys()), path
        runtime.globals()["_" + path.stem] = owner
