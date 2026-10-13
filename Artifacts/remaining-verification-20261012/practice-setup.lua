local p=_UserService.UserEntities.Values[1]
assert(isvalid(p) and p.CurrentMap.Name=='lobby')
local profile=_UnionProfileRepositoryLogic:GetUnionProfile(p)
assert(profile.Success)
_UnionProfileRepositoryLogic.StorageKey='RemainingOSVerify20261012_Profile'
_UnionProfileRepositoryLogic.RawByStorageUserKey[profile.StorageUserKey]=''
_UnionProfileRepositoryLogic.StoredRecordExistsByStorageUserKey[profile.StorageUserKey]=false
_RunResultRepositoryLogic.StorageKey='RemainingOSVerify20261012_Latest'
_RunResultRepositoryLogic.HistoryIndexKey='RemainingOSVerify20261012_History'
_RunResultRepositoryLogic.RecordKeyPrefix='RemainingOSVerify20261012_Record:'
local m=_EntityService:GetEntityByPath('/maps/skill_test')
local s=m:GetComponent('script.BattleSessionComponent')
assert(s~=nil and s.SkillTestMode and s.AutoStartPrototypeBattle)
_RunManagerLogic._T.RemainingOSSession=s
_TeleportService:TeleportToMapPosition(p,Vector3(0,0,0),'skill_test')
log('[RemainingVerify] PRACTICE_TRANSFER_DISPATCHED')