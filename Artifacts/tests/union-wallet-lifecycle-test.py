"""Execute the cached wallet RPC and reject calls from departed requesters."""
from pathlib import Path
import os
import re
import sys

if os.environ.get("LUPA_PATH"):
    sys.path.insert(0, os.environ["LUPA_PATH"])
from lupa.lua54 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
path = Path(os.environ.get("WALLET_SOURCE", ROOT / "RootDesk/MyDesk/00_Core/UnionCoinPurchaseServiceLogic.mlua"))
source = path.read_text(encoding="utf-8-sig")
match = re.search(r"^    method void RequestWallet\(integer requestId\)\n(.*?)^    end$", source, re.M | re.S)
assert match, "wallet RPC not found"
lua = LuaRuntime(unpack_returned_tuples=True)
lua.globals().request_wallet = lua.eval("function(self, requestId)\n" + match.group(1) + "\nend")
lua.execute(r'''
function isvalid(value) return value~=nil and value.Valid~=false end
function log(_) end
function fixture()
 senderUserId='owner'
 connected={owner={Valid=true}}
 sent={}
 local profile={UnionPoints=245,MagnetPetPurchaseId='',MagnetPetGiftId='gift'}
 _UserService={GetUserEntityByUserId=function(_,id) return connected[id] end}
 _UnionProfileRepositoryLogic={StorageUserKeyByUserId={owner='key',other='other-key'},
  ProfilesByStorageUserKey={key=profile,['other-key']={UnionPoints=999}},
  LoadStateByStorageUserKey={key='LOADED'},StoredRecordExistsByStorageUserKey={key=true}}
 _PremiumBenefitsLogic={SalesEnabled=true,MagnetPetProductId='pet'}
 _UnionCoinShopLogic={ReceiveWallet=function(_,...)
  local args={...}
  assert(isvalid(connected[args[8]]),'cannot send wallet to disconnected user')
  table.insert(sent,args)
 end}
 return {SalesEnabled=true,Coin2000ProductId='small',Coin4000ProductId='large'},profile
end
local service,profile=fixture()
request_wallet(service,71)
local reply=sent[1]
assert(#sent==1 and reply[1]==71 and reply[2] and reply[3]==245 and reply[4]=='small' and reply[5]=='large' and reply[6]=='pet' and reply[7] and reply[8]=='owner')
''')
print("PASS loaded connected owner receives the cached wallet and sale flags")
lua.execute(r'''
for _,departed in ipairs({false,{Valid=false}}) do
 local s=fixture(); connected.owner=departed or nil
 _UnionProfileRepositoryLogic=setmetatable({}, {__index=function() error('departed request accessed profile cache') end})
 request_wallet(s,72)
 assert(#sent==0)
end
''')
print("PASS nil and destroyed requesters cannot read cache or send a reply")
lua.execute(r'''
local s=fixture(); _UnionProfileRepositoryLogic.LoadStateByStorageUserKey.key='LOADING'
request_wallet(s,73)
local r=sent[1]
assert(#sent==1 and r[1]==73 and not r[2] and r[3]==0 and r[4]=='' and r[5]=='' and r[6]=='' and not r[7] and r[8]=='owner')
''')
print("PASS an unready connected owner receives the existing loading response")
lua.execute(r'''
local s=fixture(); _UnionProfileRepositoryLogic.StoredRecordExistsByStorageUserKey.key=false
request_wallet(s,74)
local r=sent[1]
assert(r[2] and r[3]==245 and r[4]=='' and r[5]=='' and r[6]=='' and r[7])
''')
print("PASS an unsaved profile retains its wallet and cannot enable sales")
lua.execute(r'''
local s=fixture(); s.Coin4000ProductId=s.Coin2000ProductId; _PremiumBenefitsLogic.MagnetPetProductId=s.Coin2000ProductId
request_wallet(s,75)
local r=sent[1]
assert(r[2] and r[3]==245 and r[4]=='' and r[5]=='' and r[6]=='')
''')
print("PASS ambiguous product IDs remain unavailable")
lua.execute(r'''
local s=fixture(); s.SalesEnabled=false; _PremiumBenefitsLogic.SalesEnabled=false
request_wallet(s,76)
local r=sent[1]
assert(r[3]==245 and r[4]=='' and r[5]=='' and r[6]=='')
''')
print("PASS closed sales preserve the cached amount and ownership flag")
lua.execute(r'''
local s=fixture(); connected.other={Valid=true}; senderUserId='other'
_UnionProfileRepositoryLogic.LoadStateByStorageUserKey['other-key']='LOADED'
_UnionProfileRepositoryLogic.StoredRecordExistsByStorageUserKey['other-key']=true
request_wallet(s,77)
local r=sent[1]
assert(r[3]==999 and r[8]=='other' and _UnionProfileRepositoryLogic.ProfilesByStorageUserKey.key.UnionPoints==245)
''')
print("PASS wallet data and recipient are selected only from the server-assigned sender")
print("7 wallet lifecycle regression groups passed")
