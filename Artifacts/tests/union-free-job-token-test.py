"""Offline free job-token regressions using the current mLua method bodies.

Run with Python and lupa installed, or set LUPA_PATH to a local installation.
Shop/profile methods and validation run in Lua 5.4. Engine identity, DataStorage,
HTTP JSON, skill-tree, rank/stat/upgrade definition services are fixture mocks.
This does not replace Maker build/play or real DataStorage concurrency checks.
"""

import csv
import json
import os
from pathlib import Path
import re
import sys

if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua54 import LuaRuntime, lua_type


ROOT = Path(__file__).resolve().parents[2]
lua = LuaRuntime(unpack_returned_tuples=True)


def load_methods(path, names):
    """Compile exact method bodies; fail if source formatting/names change."""
    source = (ROOT / path).read_text(encoding="utf-8-sig")
    result = lua.table()
    found = set()
    pattern = r"^([ \t]+)method\s+\w+\s+(\w+)\((.*?)\)\n(.*?)^\1end\s*$"
    for match in re.finditer(pattern, source, re.MULTILINE | re.DOTALL):
        _, name, params, body = match.groups()
        if name not in names:
            continue
        args = ",".join(p.strip().split()[-1] for p in params.split(",") if p.strip())
        result[name] = lua.execute(
            "return function(self" + ("," + args if args else "") + ")\n" + body + "\nend"
        )
        found.add(name)
    assert set(names) == found, (path, "missing methods", set(names) - found)
    return result


def json_value(value):
    if lua_type(value) == "table":
        return {str(key): json_value(item) for key, item in value.items()}
    return value


lua.globals().encode_json = lambda value: json.dumps(
    json_value(value), sort_keys=True, separators=(",", ":"), allow_nan=False
)
lua.globals().decode_json = lambda raw: lua.table_from(json.loads(raw), recursive=True)
lua.globals().shop = load_methods(
    "RootDesk/MyDesk/00_Core/UnionShopServiceLogic.mlua",
    {
        "DefaultState", "CopyState", "ValidateState", "IsUnlockableJob", "IsJobUnlocked",
        "OwnsSkin", "GetProduct", "IsFreeJobTokenProduct", "IsProductSoldOut", "EvaluateAction",
    },
)
lua.globals().repo = load_methods(
    "RootDesk/MyDesk/00_Core/UnionProfileRepositoryLogic.mlua",
    {
        "CreateDefaultProfile", "BuildZeroLevelMap", "NormalizeProfile", "ValidateProfileData",
        "CloneProfile", "BuildJsonSafeProfile", "TryCommitUnionShopAction", "PersistProfileCandidate",
        "TryAcquireMutationLock", "ReleaseMutationLock", "GetCachedSnapshot", "EvictProfile",
        "CreateDefaultJobUnionProgress", "IsKnownUnionJobId", "NormalizeJobUnionProgress",
        "ValidateJobUnionProgress", "NormalizeAllocatedUnionStats", "ValidateAllocatedUnionStats",
        "ValidateAllocatedUnionStatConsistency", "NormalizePurchasedLevelsStrict",
        "CountLegacyBlockEntries", "CopyLevelMap", "CopyRewardReceiptMap", "CountTableEntries",
        "NormalizeRewardReceiptMap", "PruneCommittedRewardKeys", "ReadNonNegativeInteger",
        "IsNonNegativeInteger", "ClampNonNegativeInteger", "ValidateCouponReceiptCodes",
        "NormalizePaidPurchaseReceipts", "CopyPaidPurchaseReceipts",
    },
)

# Use the actual catalog's token prices/flags; catalog validation has its own suite.
products = {}
with (ROOT / "RootDesk/MyDesk/03_Data/UnionShopProducts.csv").open(encoding="utf-8-sig", newline="") as source:
    for row in csv.DictReader(source):
        if row["ProductId"] not in {"job_unlock_free", "job_unlock"}:
            continue
        products[row["ProductId"]] = {
            "Success": True, "Id": row["ProductId"], "Kind": row["Kind"], "Ref": row["RefId"],
            "Price": int(row["Price"]), "Enabled": row["Enabled"] == "true",
            "Retired": row["Retired"] == "true", "Removed": row["Removed"] == "true",
        }
assert set(products) == {"job_unlock_free", "job_unlock"}
assert products["job_unlock_free"]["Price"] == 0 and products["job_unlock"]["Price"] == 2000
lua.globals().products = lua.table_from(products, recursive=True)

lua.execute(r'''
log = function(...) end
log_error = log
_UnionShopServiceLogic = shop
_UnionShopProductRepositoryLogic = {
    GetDefinition = function(self, id) return products[id] or {Success=false} end,
    GetCatalog = function(self) return {Success=true, Products=products} end,
}
_HttpService = {
    JSONEncode = function(self, value) return encode_json(value) end,
    JSONDecode = function(self, raw) return decode_json(raw) end,
}
local function deepCopy(source)
    if type(source) ~= "table" then return source end
    local result = {}
    for key, value in pairs(source) do result[key] = deepCopy(value) end
    return result
end
_SkillTreeServiceLogic = {
    DefaultState = function(self) return {Revision=0} end,
    ValidateState = function(self, state) return type(state)=="table" end,
    CopyState = function(self, state) return deepCopy(state) end,
}
_UnionUpgradeDefinitionRepositoryLogic = {
    GetAllDefinitions = function(self)
        return {Success=true, Definitions={{UpgradeId="legacy_attack", MaxLevel=10}}}
    end,
}
_UnionStatDefinitionRepositoryLogic = {
    GetStat = function(self, id)
        return {Success=id=="attack", IsImplemented=true, MaxLevel=10, RequiredUnionRank="rank1"}
    end,
    GetLevel = function(self, id, level) return {Success=id=="attack", RequiredUnionRank="rank1"} end,
}
_UnionRankDefinitionRepositoryLogic = {
    GetRankForLifetimePoints = function(self, points) return {Success=true, SortOrder=1} end,
    GetDefinition = function(self, id) return {Success=id=="rank1", SortOrder=1} end,
}
repo.CurrentSchemaVersion = 5
repo.RewardReceiptRetention = 64
repo.StorageKey = "UnionProfile"
repo.JsonEmptyMapMarker = "__EMPTY_MAP__"
local KEY = "test-account"

function canonical(profile)
    return _HttpService:JSONEncode(repo:BuildJsonSafeProfile(profile))
end
function durable()
    local result = repo:NormalizeProfile(_HttpService:JSONDecode(storage.Raw))
    assert(result.Success, result.DetailReason or result.Reason)
    return result.Profile
end
function cached()
    return repo.ProfilesByStorageUserKey[KEY]
end
function seed(profile, raw)
    repo.ProfilesByStorageUserKey[KEY] = repo:CloneProfile(profile)
    repo.RawByStorageUserKey[KEY] = raw or canonical(profile)
    repo.StoredRecordExistsByStorageUserKey[KEY] = true
    repo.LoadStateByStorageUserKey[KEY] = "LOADED"
    storage.Raw = repo.RawByStorageUserKey[KEY]
end
function fixture(balance)
    repo.ProfilesByStorageUserKey = {}
    repo.RawByStorageUserKey = {}
    repo.StoredRecordExistsByStorageUserKey = {}
    repo.LoadStateByStorageUserKey = {}
    repo.MutationLocksByStorageUserKey = {}
    repo.StorageUserKeyByUserId = {}
    player = {Id="test-player"}
    storage = {Calls=0, Writes=0, Raw=nil, FailNext=0}
    function storage:SetAndWait(key, raw)
        assert(key==repo.StorageKey)
        self.Calls = self.Calls + 1
        if self.FailNext ~= 0 then
            local code = self.FailNext; self.FailNext=0; return code
        end
        self.Raw = raw; self.Writes = self.Writes + 1
        return 0
    end
    function storage:UpdateAndWait(key, expectedRaw, newRaw)
        assert(key==repo.StorageKey)
        self.Calls = self.Calls + 1
        if self.BeforeUpdate ~= nil then
            local callback = self.BeforeUpdate; self.BeforeUpdate=nil; callback()
        end
        if self.FailNext ~= 0 then
            local code = self.FailNext; self.FailNext=0; return code, self.Raw
        end
        if expectedRaw ~= self.Raw then return 2000000, self.Raw end
        self.Raw = newRaw; self.Writes = self.Writes + 1
        return 0, newRaw
    end
    _DataStorageService = {GetUserDataStorage=function(self, key) assert(key==KEY); return storage end}
    -- Identity/load transport is mocked; candidate cloning, commit, validation and writer are real.
    function repo:GetUnionProfile(user)
        assert(user==player)
        if self.LoadStateByStorageUserKey[KEY] ~= "LOADED" then
            return {Success=false, Reason="PROFILE_NOT_LOADED"}
        end
        return {Success=true, StorageUserKey=KEY}
    end
    local result = repo:CreateDefaultProfile()
    assert(result.Success, result.Reason)
    local profile = result.Profile
    profile.UnionPoints = balance or 0
    seed(profile)
    return profile
end
function commit(action, product, revision)
    return repo:TryCommitUnionShopAction(player, action, product, revision, 0)
end
function expectFailure(result, reason)
    assert(result.Success==false and result.Reason==reason, tostring(result.Reason))
end
function expectClaim(profile, tokens, revision, balance)
    assert(profile.UnionShop.FreeJobTokenClaimed==true)
    assert(profile.UnionShop.JobTokens==tokens and profile.UnionShop.Revision==revision)
    assert(profile.UnionPoints==balance)
end
function unlockedLock()
    assert(repo.MutationLocksByStorageUserKey[KEY]==nil)
end
''')

CASES = {
    "new profile: no auto gift; free claim once; consuming token keeps sold-out state": r'''
        local profile = fixture()
        assert(profile.UnionPoints==0 and profile.LifetimeUnionPoints==0)
        assert(profile.UnionShop.JobTokens==0 and profile.UnionShop.FreeJobTokenClaimed==false)
        local result = shop:EvaluateAction(profile, "BUY", "job_unlock_free", 0, 0)
        assert(result.Success and result.Changed and result.Reason=="FREE_TOKEN_CLAIMED")
        expectClaim(profile, 1, 1, 0)
        local before = canonical(profile)
        expectFailure(shop:EvaluateAction(profile, "BUY", "job_unlock_free", 1, 0), "PRODUCT_SOLD_OUT")
        expectFailure(shop:EvaluateAction(profile, "BUY", "job_unlock_free", 0, 0), "SHOP_CHANGED")
        assert(canonical(profile)==before)
        result = shop:EvaluateAction(profile, "UNLOCK_JOB", "mage", 1, 0)
        assert(result.Success and result.Reason=="JOB_UNLOCKED")
        expectClaim(profile, 0, 2, 0)
        assert(shop:IsJobUnlocked(profile.UnionShop, "mage"))
        expectFailure(shop:EvaluateAction(profile, "BUY", "job_unlock_free", 2, 0), "PRODUCT_SOLD_OUT")
    ''',
    "paid token still costs 2000, can repeat, and rejects insufficient coins": r'''
        local profile = fixture(4000)
        assert(shop:EvaluateAction(profile, "BUY", "job_unlock_free", 0, 0).Success)
        for revision=1,2 do
            local result = shop:EvaluateAction(profile, "BUY", "job_unlock", revision, 0)
            assert(result.Success and result.Reason=="PURCHASED")
        end
        expectClaim(profile, 3, 3, 0)
        assert(not shop:IsProductSoldOut(profile.UnionShop, products.job_unlock))
        local before = canonical(profile)
        expectFailure(shop:EvaluateAction(profile, "BUY", "job_unlock", 3, 0), "INSUFFICIENT_UNION_COINS")
        assert(canonical(profile)==before)
    ''',
    "free product recognition requires all four immutable fields": r'''
        assert(shop:IsFreeJobTokenProduct(products.job_unlock_free))
        assert(not shop:IsFreeJobTokenProduct(products.job_unlock))
        for field, value in pairs({Id="other", Kind="SUPPLY", Ref="other", Price=1}) do
            local product = {}
            for key, item in pairs(products.job_unlock_free) do product[key]=item end
            product[field] = value
            assert(not shop:IsFreeJobTokenProduct(product), field)
        end
    ''',
    "real JSON/copy/normalization reconnect retains claim and owned jobs without aliases": r'''
        local profile = fixture(1234)
        assert(shop:EvaluateAction(profile, "BUY", "job_unlock_free", 0, 0).Success)
        assert(shop:EvaluateAction(profile, "UNLOCK_JOB", "archer", 1, 0).Success)
        profile.PaidPurchaseReceipts.receipt = {ProductId="cash-coins", Amount=2000}
        local normalized = repo:NormalizeProfile(_HttpService:JSONDecode(canonical(profile)))
        assert(normalized.Success and not normalized.WasMigrated and not normalized.NeedsPersistence)
        expectClaim(normalized.Profile, 0, 2, 1234)
        assert(normalized.Profile.UnionShop.UnlockedJobs=="warrior|archer")
        local copy = repo:CloneProfile(normalized.Profile)
        copy.UnionShop.JobTokens=99
        copy.PaidPurchaseReceipts.receipt.Amount=4000
        assert(normalized.Profile.UnionShop.JobTokens==0)
        assert(normalized.Profile.PaidPurchaseReceipts.receipt.Amount==2000)
        assert(profile.CommittedRewardKeys[repo.JsonEmptyMapMarker]==nil)
        expectFailure(shop:EvaluateAction(normalized.Profile, "BUY", "job_unlock_free", 2, 0), "PRODUCT_SOLD_OUT")
    ''',
    "schema 5 missing flag defaults false and preserves balances/jobs, with durable rewrite requested": r'''
        local profile = fixture(4321)
        profile.LifetimeUnionPoints=9876
        profile.UnionShop.FreeJobTokenClaimed=nil
        profile.UnionShop.JobTokens=2
        profile.UnionShop.UnlockedJobs="warrior|mage|thief"
        profile.UnionShop.Revision=7
        profile.JobUnionProgress.mage=37
        profile.AllocatedUnionStats.attack=2
        profile.PurchasedLevels.legacy_attack=2
        local copied = shop:CopyState(profile.UnionShop)
        assert(copied.FreeJobTokenClaimed==false and copied.JobTokens==2)
        local normalized = repo:NormalizeProfile(profile)
        assert(normalized.Success and normalized.WasSanitized and normalized.NeedsPersistence)
        assert(not normalized.WasMigrated and normalized.TotalLegacyRefund==0)
        local restored = normalized.Profile
        assert(restored.UnionPoints==4321 and restored.LifetimeUnionPoints==9876)
        assert(restored.UnionShop.FreeJobTokenClaimed==false and restored.UnionShop.JobTokens==2)
        assert(restored.UnionShop.UnlockedJobs=="warrior|mage|thief" and restored.UnionShop.Revision==7)
        assert(restored.JobUnionProgress.mage==37 and restored.AllocatedUnionStats.attack==2)
        assert(restored.PurchasedLevels.legacy_attack==2)
        assert(shop:EvaluateAction(restored, "BUY", "job_unlock_free", 7, 0).Success)
        expectClaim(restored, 3, 8, 4321)
    ''',
    "corrupt claim flag rejects normalization and purchase without mutation": r'''
        for _, invalid in ipairs({"true", 0, 1, {}}) do
            local profile = fixture()
            profile.UnionShop.FreeJobTokenClaimed=invalid
            assert(not shop:ValidateState(profile.UnionShop))
            local normalized = repo:NormalizeProfile(profile)
            expectFailure(normalized, "PROFILE_VALIDATION_FAILED")
            assert(normalized.DetailReason=="INVALID_UNION_SHOP")
            local before = canonical(profile)
            expectFailure(shop:EvaluateAction(profile, "BUY", "job_unlock_free", 0, 0), "INVALID_SHOP_SAVE")
            assert(canonical(profile)==before and storage.Calls==0)
        end
    ''',
    "repository commits flag/token atomically; duplicate requests never write again": r'''
        fixture()
        local result = commit("BUY", "job_unlock_free", 0)
        assert(result.Success and result.Reason=="FREE_TOKEN_CLAIMED")
        expectClaim(cached(), 1, 1, 0)
        expectClaim(durable(), 1, 1, 0)
        assert(storage.Calls==1 and storage.Writes==1)
        expectFailure(commit("BUY", "job_unlock_free", 1), "PRODUCT_SOLD_OUT")
        expectFailure(commit("BUY", "job_unlock_free", 0), "SHOP_CHANGED")
        assert(storage.Calls==1 and storage.Writes==1)
        assert(commit("UNLOCK_JOB", "pirate", 1).Success)
        expectClaim(durable(), 0, 2, 0)
        expectFailure(commit("BUY", "job_unlock_free", 2), "PRODUCT_SOLD_OUT")
        assert(storage.Calls==2 and storage.Writes==2)
        unlockedLock()
    ''',
    "save failure preserves unclaimed cache/raw; retry can claim exactly once": r'''
        fixture()
        local original = cached()
        local originalRaw = storage.Raw
        storage.FailNext=1000001
        expectFailure(commit("BUY", "job_unlock_free", 0), "PROFILE_SAVE_FAILED")
        assert(cached()==original and canonical(cached())==originalRaw)
        assert(cached().UnionShop.FreeJobTokenClaimed==false and cached().UnionShop.JobTokens==0)
        assert(storage.Raw==originalRaw and repo.RawByStorageUserKey["test-account"]==originalRaw)
        assert(repo.LoadStateByStorageUserKey["test-account"]=="LOADED")
        assert(storage.Calls==1 and storage.Writes==0)
        unlockedLock()
        assert(commit("BUY", "job_unlock_free", 0).Success)
        expectClaim(cached(), 1, 1, 0)
        expectClaim(durable(), 1, 1, 0)
        expectFailure(commit("BUY", "job_unlock_free", 1), "PRODUCT_SOLD_OUT")
        assert(storage.Calls==2 and storage.Writes==1)
        unlockedLock()
    ''',
    "CAS conflict evicts stale candidate; reconnect honors another writer's claim": r'''
        fixture()
        local otherWriter = repo:CloneProfile(cached())
        assert(shop:EvaluateAction(otherWriter, "BUY", "job_unlock_free", 0, 0).Success)
        local otherRaw = canonical(otherWriter)
        storage.Raw = otherRaw
        expectFailure(commit("BUY", "job_unlock_free", 0), "PROFILE_WRITE_CONFLICT")
        assert(cached()==nil and repo.RawByStorageUserKey["test-account"]==nil)
        assert(repo.LoadStateByStorageUserKey["test-account"]==nil)
        assert(repo.StoredRecordExistsByStorageUserKey["test-account"]==nil)
        assert(storage.Raw==otherRaw and storage.Writes==0)
        expectClaim(durable(), 1, 1, 0)
        unlockedLock()
        seed(durable(), otherRaw)
        expectFailure(commit("BUY", "job_unlock_free", 1), "PRODUCT_SOLD_OUT")
        assert(storage.Calls==1 and storage.Writes==0)
    ''',
    "overlapping duplicate while writer yields is blocked by actual mutation lock": r'''
        fixture()
        local overlap
        storage.BeforeUpdate = function()
            overlap = commit("BUY", "job_unlock_free", 0)
            assert(cached().UnionShop.FreeJobTokenClaimed==false and cached().UnionShop.JobTokens==0)
        end
        assert(commit("BUY", "job_unlock_free", 0).Success)
        expectFailure(overlap, "PROFILE_MUTATION_IN_PROGRESS")
        assert(storage.Calls==1 and storage.Writes==1)
        expectClaim(cached(), 1, 1, 0)
        expectClaim(durable(), 1, 1, 0)
        unlockedLock()
    ''',
}

for name, code in CASES.items():
    lua.execute(code)
    print("PASS", name)

print(f"PASS {len(CASES)} actual-Lua regression groups")
print("Offline only: Maker build/play, UI/RPC and real DataStorage concurrency NOT RUN.")
