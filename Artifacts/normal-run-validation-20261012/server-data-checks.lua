local healthy = _ContentValidatorLogic:ValidateAllContent()
assert(healthy.Success, healthy.Reason)
log("[NormalVerify] CONTENT_ALL_PASS ".._HttpService:JSONEncode({ErrorCount=healthy.ErrorCount,StageCount=healthy.CheckedStageCount,RouteCount=healthy.CheckedStageMapRouteCount}))
local proxy = {GetRowCount=function() return 2 end, GetCell=function(_, row, column)
    if column == "StageId" then return "henesys_stage_01" end
    return ""
end}
local audit={Errors={},CheckedStageMapRouteCount=0}
_ContentIntegrityValidatorLogic:ValidateStageMapRoutes(proxy,audit)
assert(#audit.Errors==1 and audit.Errors[1].DataSetName=="StageMapRoutes" and audit.Errors[1].RowIndex==2
    and audit.Errors[1].DetailReason=="DUPLICATE_STAGE_MAP_ROUTE", "duplicate location rejected incorrectly")
log("[NormalVerify] DATA_DUPLICATE ".._HttpService:JSONEncode(audit.Errors[1]))
local effectTable={GetCell=function(_,row,column)
    if column=="Value" then return "not-a-number" end
    return "1"
end}
local reason=_ContentValidatorLogic:ValidateUtilityRawNumbers(effectTable,1,true)
assert(reason=="INVALID_UTILITY_NUMBER:Value", reason)
local detail={Success=true,Errors={}}
_ContentValidatorLogic:AddUtilityError(detail,"UtilitySkillEffectSteps",1,"validation-only",reason)
log("[NormalVerify] DATA_RAW_NUMBER ".._HttpService:JSONEncode({DataSetName="UtilitySkillEffectSteps",RowIndex=1,Column="Value",Value="not-a-number",ActualError=detail.Errors[1]}))
assert(_ContentValidatorLogic:ValidateAllContent().Success, "audit mutated live data")
log("[NormalVerify] DATA_CHECK_DONE")