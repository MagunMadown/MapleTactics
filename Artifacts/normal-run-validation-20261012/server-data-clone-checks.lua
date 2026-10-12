local bundle=_SkillDefinitionRepositoryLogic:GetSkillBundle("la_mancha_spear")
assert(bundle.Success)
assert(_ContentValidatorLogic:ValidateSkillBundle(bundle).Success)
local dataSetName,row,raw="",-1,""
for _,name in ipairs(_SkillDefinitionRepositoryLogic:GetSkillDataSetNames()) do
 local ds=_DataService:GetTable(name)
 if ds~=nil then for i=1,ds:GetRowCount() do if ds:GetCell(i,"SkillId")=="la_mancha_spear" then dataSetName,row,raw=name,i,ds:GetCell(i,"Range") end end end
end
assert(row>0)
local invalid=_HttpService:JSONDecode(_HttpService:JSONEncode(bundle))
invalid.Definition.Range=0
local rejected=_ContentValidatorLogic:ValidateSkillBundle(invalid)
assert(not rejected.Success and rejected.DetailReason=="INVALID_SKILL_RANGE")
log("[FlowVerify] DATA_RANGE_REJECT dataset="..dataSetName.." row="..row.." column=Range original="..raw.." injected=0 reason="..rejected.DetailReason)
local duplicate=_HttpService:JSONDecode(_HttpService:JSONEncode(bundle))
duplicate.Definition.MatchCount=2
local rejectedDuplicate=_ContentValidatorLogic:ValidateSkillBundle(duplicate)
assert(not rejectedDuplicate.Success and rejectedDuplicate.DetailReason=="DATA_DUPLICATE_SKILL_ID")
assert(_SkillDefinitionRepositoryLogic:GetSkillDefinition("la_mancha_spear").Range==bundle.Definition.Range)
assert(_ContentValidatorLogic:ValidateSkillById("la_mancha_spear").Success)
_SkillDefinitionRepositoryLogic:RecountTestOverrides()
assert(_SkillDefinitionRepositoryLogic.TestOverrideCount==0)
log("[FlowVerify] DATA_CLONE_PASS originalRange="..bundle.Definition.Range.." overrides=0")
local nativeIssue={Errors={}}
_ContentIntegrityValidatorLogic:AddError(nativeIssue,dataSetName,row,"la_mancha_spear",rejected.DetailReason)
assert(nativeIssue.Errors[1].DataSetName==dataSetName and nativeIssue.Errors[1].RowIndex==row)
assert(nativeIssue.Errors[1].Column==nil and nativeIssue.Errors[1].Value==nil)
log("[FlowVerify] DATA_NATIVE_DIAGNOSTIC_GAP fields=DataSetName,RowIndex,ContentId,DetailReason missing=Column,Value serialized=".._ContentIntegrityValidatorLogic:SerializeErrors(nativeIssue.Errors))
log("[FlowVerify] DATA_CLONE_DONE")