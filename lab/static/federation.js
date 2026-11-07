"use strict";
const $=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let csrf='', state=null, lastDownload=null, busy=false, settingsLoaded=false, job=null;

async function api(path, body, method='POST') {
  const response=await fetch(path, {method:body===undefined?'GET':method, headers:{'Content-Type':'application/json','X-Lab-CSRF':csrf}, body:body===undefined?undefined:JSON.stringify(body)});
  let data;
  try { data=await response.json(); }
  catch { throw Error('Chưa nhận được phản hồi hợp lệ. Kiểm tra kết nối và thử lại.'); }
  if(!response.ok) {
    const detail=data.detail;
    throw Error(DemoLanguage.reason(detail?.reason, 'Chưa thể hoàn tất yêu cầu. Kiểm tra trạng thái dịch vụ và thử lại.'));
  }
  return data;
}

function message(text,error=false){$('message').textContent=text;$('message').className=error?'error':'';$('message').hidden=false}
function options(id,items,preferred){const el=$(id),old=el.value;const html=items.map(i=>`<option value="${esc(i.value)}">${esc(i.text)}</option>`).join('');if(el.innerHTML!==html){el.innerHTML=html;if(items.some(i=>i.value===old))el.value=old;else if(preferred&&items.some(i=>i.value===preferred))el.value=preferred}}
const stamp=t=>t?new Date(typeof t==='number'?t*1000:t).toLocaleTimeString('vi-VN'):'—';
const resource=()=>state?.resource || {};
const person=id=>DemoLanguage.person(resource().principals?.find(user=>user.id===id||user.username===id)||{username:id});
const sourceAccount=id=>state?.partner.identities.find(account=>account.id===id||account.username===id);

function userOption(user) {
  const name=DemoLanguage.person(user), role=DemoLanguage.role(user.role);
  return {value:user.username, text:[name,name===role||name.startsWith(role+' ')?'':role,DemoLanguage.department(user.department)].filter(Boolean).join(' · ')};
}

function deviceName(device, devices) {
  const name=`Thiết bị của ${person(device.principal_id)}`;
  const group=devices.filter(item=>item.principal_id===device.principal_id);
  return group.length>1?`${name} số ${group.indexOf(device)+1}`:name;
}

function deviceStatus(device) {
  if(device.revoked) return 'Đã thu hồi';
  if(!device.compliant) return 'Chưa đạt yêu cầu an toàn';
  return device.risk==='HIGH'?'Rủi ro cao':'Đang dùng được';
}

function sourceFacts() {
  if(!state) return;
  const account=state.partner.identities.find(x=>x.id===$('source-user').value);
  $('source-facts').textContent=account?`${person(account.username)} · ${account.active?'Đang hoạt động':'Đã khóa'} · Cập nhật lúc ${stamp(account.changed_at)}`:'Chưa chọn tài khoản.';
  const devices=state.partner.devices.filter(device=>device.principal_id===account?.id);
  options('source-device',devices.map(device=>({value:device.id,text:`${deviceName(device,devices)} · ${deviceStatus(device)}`})));
}

function renderSessions(broker) {
  const expanded=new Set([...$('sessions').querySelectorAll('details[open]')].map(item=>item.dataset.detail));
  $('sessions').innerHTML=broker.sessions.slice(0,24).map(session=>{
    const active=!session.revoked&&session.expires_at>broker.now;
    const status=session.revoked?'Đã thu hồi':active?'Đang dùng được':'Hết hạn';
    const reopened=session.reason==='SOURCE_ACCOUNT_DISABLED'&&sourceAccount(session.username)?.active===true;
    const description=session.revoked?(reopened?'Phiên đã bị thu hồi trong lần khóa trước.':DemoLanguage.reason(session.reason, 'Đăng nhập lại để tiếp tục.')):`Hết hạn lúc ${stamp(session.expires_at)}`;
    return `<tr><td>${esc(person(session.username))}<br><small>${esc(DemoLanguage.organization(session.organization))}</small></td>
      <td><b>${esc(DemoLanguage.mode(session.mode))}</b><details data-detail="${esc(session.id)}"${expanded.has(session.id)?' open':''}><summary>Mã phiên</summary><code>${esc(session.id)}</code></details></td>
      <td><span class="status ${session.revoked?'bad':active?'ok':'idle'}">${status}</span><br><small>${esc(description)}</small></td>
      <td>${esc(stamp(session.source?.observed_at))}</td><td>${!session.revoked?`<button class="small secondary" data-revoke="${esc(session.id)}">Thu hồi phiên</button>`:''}</td></tr>`;
  }).join('')||'<tr><td colspan="5">Chưa có phiên. Đăng nhập để tạo phiên đầu tiên.</td></tr>';
}

function renderTimeline(partner, broker) {
  const traceNames={login:'Tạo phiên',introspection:'Kiểm tra phiên',event:'Nhận thông báo',revocation:'Thu hồi phiên',source_refresh:'Kiểm tra lại trạng thái',reconciliation:'Kiểm tra lại định kỳ',startup:'Khởi động dịch vụ'};
  const changes=partner.changes.map(change=>{
    const device=partner.devices.find(item=>item.id===change.target);
    const patch=change.patch||{};
    const name=device?deviceName(device,partner.devices):person(change.target);
    let description='Đã cập nhật thông tin.';
    if(typeof patch.active==='boolean') description=patch.active?'Đã mở khóa tài khoản.':'Đã khóa tài khoản.';
    else if(patch.revoked===true) description='Đã thu hồi thiết bị.';
    else if(patch.compliant===false) description='Thiết bị chưa đạt yêu cầu an toàn.';
    else if(patch.risk==='HIGH') description='Đã đánh dấu thiết bị có rủi ro cao.';
    else if(patch.revoked===false) description='Đã khôi phục thiết bị.';
    return {at:change.created_at, kind:'Thay đổi tài khoản hoặc thiết bị', description:`${name} · ${description}`, details:change};
  });
  const traces=broker.trace.map(event=>({at:event.created_at,kind:traceNames[event.kind]||'Hoạt động hệ thống',description:DemoLanguage.reason(event.reason,'Đã ghi nhận hoạt động.'),details:event}));
  const expanded=new Set([...$('timeline').querySelectorAll('details[open]')].map(item=>item.dataset.detail));
  $('timeline').innerHTML=[...changes,...traces].sort((a,b)=>b.at-a.at).slice(0,65).map(event=>{
    const key=`${event.at}-${event.kind}-${event.details.id??''}`;
    return `<div class="event"><time>${stamp(event.at)} · ${esc(event.kind)}</time><div>${esc(event.description)}</div><details data-detail="${esc(key)}"${expanded.has(key)?' open':''}><summary>Chi tiết kỹ thuật</summary><pre>${esc(JSON.stringify(event.details,null,2))}</pre></details></div>`;
  }).join('')||'<p class="hint">Chưa có thay đổi hoặc lượt kiểm tra.</p>';
}

function render() {
  const p=state.partner,b=state.coordinator,r=state.resource;
  options('user',r.principals.map(userOption),'p_alice');
  options('actor',r.principals.map(userOption),'p_admin');
  options('device',[{value:'',text:'Thiết bị đã đăng ký của tài khoản đang chọn'},...r.devices.map(device=>({value:device.id,text:deviceName(device,r.devices)})),{value:'none',text:'Không gửi thông tin xác minh thiết bị'}]);
  options('document',r.documents.filter(doc=>!doc.deleted).map(doc=>({value:doc.id,text:`${DemoLanguage.documentName(doc)} · ${DemoLanguage.label(doc.label)}`})),'A-I01');
  options('source-user',p.identities.map(account=>({value:account.id,text:`${person(account.username)} · ${account.active?'Đang hoạt động':'Đã khóa'}`})),'p_alice');
  sourceFacts();
  $('source-status').textContent=p.faults.source_unavailable?'Đang giả lập mất kết nối':`${p.identities.length} tài khoản · ${p.events.filter(event=>event.status==='pending').length} thông báo đang chờ gửi`;
  $('broker-status').textContent=`${b.sessions.filter(session=>!session.revoked&&session.expires_at>b.now).length} phiên đang dùng được`;
  renderSessions(b);
  renderTimeline(p,b);
  if(!settingsLoaded) {
    $('drop-events').checked=!!p.faults.drop_events;
    $('pause-events').checked=!!p.faults.pause_events;
    $('outage').checked=!!p.faults.source_unavailable;
    $('no-poll').checked=!!b.config.disable_poll;
    $('cache-seconds').value=b.config.cache_seconds;
    $('poll-seconds').value=b.config.poll_seconds;
    settingsLoaded=true;
  }
}

async function refresh(){state=await api('/lab/federation/state');render()}
function selection(){return {username:$('user').value,device:$('device').value||$('user').value,mode:$('mode').value}}
function showItems(result, action) {
  const target=$('request-items');
  const rows=result.payload?.items;
  let entries=[];
  if(result.ok && Array.isArray(rows)) {
    if(action==='list') entries=rows.map(doc=>[DemoLanguage.documentName(doc),DemoLanguage.label(doc.label)]);
    if(action==='audit') entries=rows.map(event=>[DemoLanguage.action(event.action),`${person(event.principal_id)} · ${stamp(event.created_at)} · ${DemoLanguage.reason(event.reason,'Đã ghi nhận thao tác.')}`]);
    if(action==='alerts') entries=rows.map(event=>['Cảnh báo truy cập',`${person(event.principal_id)} · ${stamp(event.created_at)}`]);
  }
  if(result.ok && action==='metadata' && result.payload?.title) {
    const doc=result.payload;
    entries=[[DemoLanguage.documentName(doc),[DemoLanguage.label(doc.label),DemoLanguage.department(doc.department),person(doc.owner_id)].filter(Boolean).join(' · ')]];
  }
  target.hidden=!entries.length;
  target.innerHTML=entries.length?`<ul>${entries.slice(0,8).map(([title,detail])=>`<li><strong>${esc(title)}</strong><small>${esc(detail)}</small></li>`).join('')}</ul>${entries.length>8?'<p class="hint">Mở chi tiết kỹ thuật để xem toàn bộ kết quả.</p>':''}`:'';
}

function show(result, action) {
  const login=action==='login';
  const reason=result.reason||(result.ok?'ALLOW':'UNKNOWN');
  const locked=reason==='SOURCE_ACCOUNT_DISABLED';
  const reopened=locked&&!login&&sourceAccount($('user').value)?.active===true;
  const unavailable=['SOURCE_UNAVAILABLE','COORDINATOR_UNAVAILABLE','SOURCE_CONTEXT_EXPIRED'].includes(reason);
  const titles={login:'Đã tạo phiên truy cập',download:'Được tải tài liệu',metadata:'Đã xem thông tin tài liệu',list:'Đã xem danh sách tài liệu',audit:'Đã đọc nhật ký',alerts:'Đã đọc cảnh báo'};
  $('decision').textContent=result.ok?(titles[action]||'Yêu cầu đã hoàn tất'):reopened?'Phiên cũ đã bị thu hồi':locked?'Tài khoản đã bị khóa':unavailable||result.status>=500?'Chưa thể hoàn tất yêu cầu':'Yêu cầu bị từ chối';
  $('decision').className='decision '+(result.ok?'allow':'deny');
  let explanation=DemoLanguage.reason(reason);
  if(locked&&!login) explanation='Phiên truy cập đã bị thu hồi. Đăng nhập lại sau khi tài khoản được mở khóa.';
  if(reopened) explanation='Tài khoản đã được mở khóa. Đăng nhập lại để tạo phiên mới.';
  if(result.ok && result.content_b64) explanation='Bấm Lưu tài liệu về máy để mở nội dung.';
  const count=result.payload?.items?.length;
  if(result.ok && action==='list' && Number.isInteger(count)) explanation=`Có ${count} tài liệu tài khoản này được phép xem trong danh sách.`;
  if(result.ok && action==='audit' && Number.isInteger(count)) explanation=`Có ${count} mục nhật ký trong kết quả.`;
  if(result.ok && action==='alerts' && Number.isInteger(count)) explanation=count?`Có ${count} cảnh báo trong kết quả.`:'Hiện chưa có cảnh báo.';
  $('explanation').textContent=explanation;
  const details={...result};
  if(details.content_b64) details.content_b64='[Nội dung có thể lưu bằng nút Lưu tài liệu về máy]';
  $('response').textContent=JSON.stringify(details,null,2);
  showItems(result,action);

  let stop=99;
  if(!result.ok) {
    if(/TRANSPORT|GATEWAY/.test(reason)) stop=0;
    else if(/DEVICE_MISMATCH|INVALID_TOKEN|IDENTITY/.test(reason)) stop=1;
    else if(/SOURCE|SESSION|COORDINATOR/.test(reason)) stop=2;
    else if(/KMS|INTEGRITY/.test(reason)) stop=4;
    else if(/AUDIT|LEDGER/.test(reason)) stop=5;
    else stop=login?2:3;
  }
  const steps=['Xác minh thiết bị tại cổng','Kiểm tra tài khoản và thiết bị','Kiểm tra phiên và trạng thái tài khoản','Kiểm tra quyền và mức bảo vệ tài liệu','Giải mã nội dung để tải','Ghi nhật ký và kiểm tra trước khi trả kết quả'];
  const skipDecrypt=!login&&action!=='download';
  $('workflow').innerHTML=steps.slice(0,login?3:steps.length).map((step,i)=>{
    const skipped=skipDecrypt&&i===4&&i<stop;
    return `<div class="step ${i===stop?'stop':i<stop&&!skipped?'pass':''}">${i+1}. ${esc(step)}${i===stop?' · Dừng ở đây':skipped?' · Không cần cho thao tác này':''}</div>`;
  }).join('');
  if(login && result.ok) $('selected-session').textContent=`Đã tạo phiên cho ${person($('user').value)} với cách ${DemoLanguage.mode($('mode').value).toLocaleLowerCase('vi')}.`;
  lastDownload=result.content_b64?{data:result.content_b64,name:resource().documents?.find(doc=>doc.id===$('document').value)?.title||'tai_lieu.txt',type:result.content_type}:null;
  $('download').hidden=!lastDownload;
}

async function guarded(button,fn){if(busy)return;busy=true;button.disabled=true;try{await fn()}catch(e){message(e.message,true)}finally{busy=false;button.disabled=false}}
function bind(id,fn){$(id).addEventListener('click',()=>guarded($(id),fn))}
bind('refresh',async()=>{await refresh();await results()});bind('login',async()=>{show(await api('/lab/federation/login',selection()),'login');await refresh()});
bind('send',async()=>{
  const action=$('action').value, doc=encodeURIComponent($('document').value);
  const path={list:'/documents',metadata:`/documents/${doc}/metadata`,download:`/documents/${doc}/download`,audit:'/audit',alerts:'/alerts'}[action];
  show(await api('/lab/federation/request',{...selection(),method:'GET',path}),action);
  await refresh();
});
bind('custom-send',async()=>{
  let body;
  try { body=JSON.parse($('custom-json').value); }
  catch { throw Error('Dữ liệu JSON chưa hợp lệ. Sửa dữ liệu rồi gửi lại.'); }
  const path=$('custom-path').value, method=$('custom-method').value;
  show(await api('/lab/federation/request',{...selection(),method,path,json:body}),path.endsWith('/download')?'download':'custom');
  await refresh();
});

async function change(kind,patch){const r=await api('/lab/federation/source',{actor:$('actor').value,kind,target:$(kind==='principal'?'source-user':'source-device').value,patch});const reason=r.payload?.detail?.reason;$('source-result').textContent=r.ok?`Bên quản lý tài khoản đã lưu thay đổi lúc ${stamp(r.payload?.source_changed_at)}. ${r.warning?'Thay đổi đã lưu. Hệ thống vẫn đang cập nhật trạng thái đăng nhập.':''}`:DemoLanguage.reason(reason,'Chưa lưu được thay đổi. Kiểm tra quyền của người thực hiện rồi thử lại.');message($('source-result').textContent,!r.ok);await refresh()}
bind('disable',()=>change('principal',{active:false}));bind('enable',()=>change('principal',{active:true}));bind('revoke-device',()=>change('device',{revoked:true}));bind('healthy-device',()=>change('device',{revoked:false,compliant:true,risk:'NORMAL',auto_refresh:true}));bind('risk-device',()=>change('device',{risk:'HIGH'}));bind('noncompliant-device',()=>change('device',{compliant:false}));
async function saveSettings(reset){await api('/lab/federation/settings',{service:'partner',value:reset?{}:{drop_events:$('drop-events').checked,pause_events:$('pause-events').checked,source_unavailable:$('outage').checked}},'PUT');await api('/lab/federation/settings',{service:'coordinator',value:reset?{}:{disable_poll:$('no-poll').checked,cache_seconds:Number($('cache-seconds').value),poll_seconds:Number($('poll-seconds').value)}},'PUT');settingsLoaded=false;await refresh();message('Đã lưu cấu hình thử nghiệm.')}
bind('settings',()=>saveSettings(false));bind('settings-reset',()=>saveSettings(true));$('source-user').addEventListener('change',sourceFacts);$('mode').addEventListener('change',()=>{$('mode-help').textContent=DemoLanguage.modes[$('mode').value].help;$('selected-session').textContent='Đã đổi cách kiểm tra. Nếu đã tạo phiên cho lựa chọn này, có thể gửi lại bằng phiên đó.'});
['user','device'].forEach(id=>$(id).addEventListener('change',()=>{$('selected-session').textContent='Nếu chưa có phiên cho tài khoản và thiết bị này, hãy đăng nhập trước khi gửi.'}));
document.addEventListener('click',e=>{const b=e.target.closest('[data-revoke]');if(b)guarded(b,async()=>{await api('/lab/federation/revoke',{session_id:b.dataset.revoke});await refresh()})});
$('download').addEventListener('click',()=>{if(!lastDownload)return;const binary=atob(lastDownload.data),bytes=Uint8Array.from(binary,c=>c.charCodeAt(0)),url=URL.createObjectURL(new Blob([bytes],{type:lastDownload.type})),a=document.createElement('a');a.href=url;a.download=lastDownload.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
const cases={
  K01:['Tải tài liệu khi mọi điều kiện đều hợp lệ','Cả ba cách kiểm tra đều tải được đúng nội dung.'],
  K02:['Tải tài liệu ngoài phạm vi được cấp','Kho kiểm tra quyền tài liệu trong cả ba cách.'],
  K03:['Khóa tài khoản khi phiên vẫn còn hạn','Kho thu hồi phiên ở hai cách có nhận thông báo. Phiên chỉ kiểm tra khi đăng nhập vẫn dùng được.'],
  K03b:['Mở khóa tài khoản sau khi thu hồi phiên','Phiên cũ vẫn bị từ chối. Người dùng đăng nhập lại để tạo phiên mới.'],
  K04:['Thu hồi thiết bị đã đăng ký','Kho thu hồi đúng phiên gắn với thiết bị đó.'],
  K05:['Thông báo khóa tài khoản bị mất','Cách có tự kiểm tra lại phát hiện tài khoản đã khóa và thu hồi phiên. Cách chỉ chờ thông báo vẫn giữ phiên cũ.'],
  K06:['Bên quản lý tài khoản không phản hồi','Kho dừng yêu cầu khi thông tin đã lưu hết hạn và chưa xác nhận lại được trạng thái.'],
  K07:['Thông báo giả, trùng hoặc đến sai thứ tự','Các thông báo này không khôi phục phiên đã thu hồi.'],
  K08:['Khôi phục cơ sở dữ liệu từ bản sao','Phiên cũ vẫn bị vô hiệu sau khi khôi phục.'],
  S01:['Thử dùng thông tin đăng nhập hoặc thiết bị không khớp','Kho từ chối thông tin không thay thế được phiên hoặc không khớp với phiên.'],
  S02:['Thử quản lý dữ liệu thuộc bên còn lại','Mỗi bên chỉ thực hiện được thao tác trong phạm vi được cấp.'],
  S03:['Thử đọc cơ sở dữ liệu của bên còn lại','Tài khoản dịch vụ bị từ chối khi đọc cơ sở dữ liệu ngoài phạm vi.'],
  S04:['Thử dùng thông tin thiết bị đã quá hạn','Ký lại thông tin không làm thay đổi thời điểm thiết bị được kiểm tra.'],
  S05:['Khóa rồi mở tài khoản giữa hai lần kiểm tra','Kho vẫn phát hiện thay đổi và thu hồi phiên cũ.'],
  S06:['Kiểm tra thông tin có thuộc đúng yêu cầu hay không','Kho xác minh đúng người, đúng bên quản lý, đúng thiết bị và đúng lượt kiểm tra.'],
  S07:['Gặp lỗi khi kiểm tra quyền, ghi nhật ký hoặc giải mã','Kho dừng yêu cầu trước khi trả nội dung.'],
  S08:['Thông tin trạng thái bị sửa trái phép','Kho từ chối tạo phiên khi không xác minh được thông tin.'],
  R01:['Quản lý tài liệu Hạn chế, nhật ký và cảnh báo','Tạo, sửa, tải và đọc nhật ký vẫn hoạt động khi người dùng có quyền.'],
  R02:['Thêm nhân viên kho và đổi quyền đang dùng','Quyền mới có hiệu lực với cả phiên đã tạo.'],
};

async function results() {
  const result=await api('/lab/federation/results');
  const rows=result.cases||[];
  $('test-results').innerHTML=rows.map(test=>{
    const [name,explanation]=Object.hasOwn(cases,test.id)?cases[test.id]:['Tình huống bổ sung','Kết quả khớp điều kiện kiểm tra.'];
    return `<tr><td>${esc(name)}</td><td><span class="status ${test.pass?'ok':'bad'}">${test.pass?'Đạt':'Không đạt'}</span></td><td>${esc(test.pass?explanation:'Kết quả chưa đúng như mong đợi. Mở chi tiết để xem bước gặp lỗi.')}<details><summary>Chi tiết kỹ thuật</summary><pre>${esc(JSON.stringify(test,null,2))}</pre></details></td></tr>`;
  }).join('')||'<tr><td colspan="3">Chưa chạy bộ kiểm tra.</td></tr>';
  $('test-status').textContent=rows.length?`${rows.filter(test=>test.pass).length}/${rows.length} tình huống đạt${result.finished_at?' · '+new Date(result.finished_at*1000).toLocaleString('vi-VN'):''}`:'Chưa có kết quả.';
}

bind('verify',async()=>{const r=await api('/lab/federation/verify',{});job=r.id;$('test-status').textContent='Đang chạy các tình huống kiểm tra.';message('Hệ thống đang kiểm tra và sẽ khôi phục thiết lập khi hoàn tất.')});
async function poll(){try{if(job){const r=await api('/lab/tasks/'+job);$('test-status').textContent='Đang chạy các tình huống kiểm tra.';if(['completed','failed'].includes(r.status)){job=null;settingsLoaded=false;await results();if(r.error)message('Bộ kiểm tra chưa hoàn tất. Kiểm tra trạng thái dịch vụ rồi thử lại.',true);else message("Đã hoàn tất và lưu kết quả kiểm tra.")}}if(!busy&&$('auto-refresh').checked)await refresh()}catch(e){if(!state)message('Chưa kết nối được các dịch vụ. '+e.message,true)}}
async function init(){DemoLanguage.modeOptions($('mode'));$('mode-help').textContent=DemoLanguage.modes[$('mode').value].help;try{const boot=await api('/lab/bootstrap');csrf=boot.csrf;await refresh();await results();setInterval(poll,4000)}catch(e){message(e.message,true)}}init();
