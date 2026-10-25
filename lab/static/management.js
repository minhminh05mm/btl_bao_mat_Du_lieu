"use strict";
const management={document:null,employee:null,documentDirty:false,employeeDirty:false};
const roleNames={staff:"Nhân viên",manager:"Trưởng phòng",auditor:"Kiểm toán",security_admin:"Quản trị an toàn"};
const departmentNames={A:"Kinh doanh",B:"Vận hành",OPS:"An toàn thông tin"};
const labelHelp={internal:"Nội bộ: nhân viên và trưởng phòng cùng phòng được đọc.",confidential:"Mật: chủ sở hữu và trưởng phòng cùng phòng được đọc.",restricted:"Hạn chế: trưởng phòng cùng phòng cần quyền còn hạn để tải và sửa; thêm mới cần quản trị an toàn phê duyệt."};
const roleHelp={staff:"Đọc tài liệu Nội bộ cùng phòng; đọc tài liệu Mật do mình sở hữu. Được thêm tài liệu Nội bộ hoặc Mật.",manager:"Đọc tài liệu Nội bộ và Mật cùng phòng. Tải và sửa tài liệu Hạn chế khi được cấp quyền còn hạn. Thêm tài liệu Hạn chế cần quản trị an toàn phê duyệt; người tạo nhận quyền tải và sửa có thời hạn.",auditor:"Đọc nhật ký kiểm toán và cảnh báo. Không được đọc nội dung hoặc thêm tài liệu nghiệp vụ.",security_admin:"Quản lý trạng thái quyền, thiết bị, nhãn và phê duyệt. Đọc cảnh báo và nhật ký vận hành. Không được thêm hoặc đọc nội dung tài liệu nghiệp vụ."};

function friendlyFailure(r){
  const reasons={INVALID_INPUT:"Thông tin tài liệu chưa hợp lệ. Kiểm tra tên, định dạng tệp và nhãn.",INVALID_SIZE:"Tệp phải có nội dung và không vượt quá 1 MiB.",INACTIVE:"Tài khoản đang bị khóa. Mở Nhân viên để kích hoạt lại hoặc chọn tài khoản khác.",ROLE:"Vai trò hiện tại không được thực hiện thao tác này. Chọn tài khoản có quyền phù hợp.",UNKNOWN_SUBJECT:"Không tìm thấy tài khoản trong hệ thống. Chọn lại tài khoản tại Nhân viên.",TRANSPORT_ERROR:"Không kết nối được dịch vụ. Kiểm tra trạng thái hệ thống rồi thử lại.",SERVICE_UNAVAILABLE:"Dịch vụ chưa sẵn sàng. Thử lại sau khi kiểm tra trạng thái hệ thống.",LEDGER_UNAVAILABLE:"Chưa hoàn tất ghi nhận thay đổi. Làm mới danh sách để kiểm tra trước khi gửi lại.",ALLOW:"Thao tác đã hoàn tất."};
  return reasons[r.reason]||(typeof reasonText!=="undefined"&&reasonText[r.reason])||(r.status===413?"Tệp quá lớn. Chọn tệp không vượt quá 1 MiB.":"Không thể hoàn tất yêu cầu. Kiểm tra thông tin và thử lại.");
}

function clearFormErrors(form){
  form.querySelectorAll('.field-error,.form-errors').forEach(e=>e.remove());
  form.querySelectorAll('[aria-invalid="true"]').forEach(e=>{e.removeAttribute('aria-invalid');e.removeAttribute('aria-describedby');});
}

function showFormErrors(form,message,fields={}){
  clearFormErrors(form);
  const summary=document.createElement('div');summary.className='form-errors';summary.setAttribute('role','alert');summary.textContent=message;form.prepend(summary);
  let first=null;
  Object.entries(fields).forEach(([name,text])=>{
    const field=form.querySelector(`[data-field="${CSS.escape(name)}"]`);
    if(!field)return;
    const error=document.createElement('p');error.className='field-error';error.id=`${form.id}-${name}-error`;error.textContent=text;
    field.setAttribute('aria-invalid','true');field.setAttribute('aria-describedby',error.id);
    (field.closest('label')||field.parentElement).append(error);first=first||field;
  });
  if(first)first.focus();else summary.scrollIntoView({block:'nearest',behavior:'smooth'});
}

function notice(id,message){const el=$(id);el.textContent=message;el.classList.remove('hidden');}
function selectedRecord(kind,id){return toArray(state.data[kind]).find(x=>x.id===id);}
function datetimeValue(value){const d=new Date(Number(value)*1000);return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);}
function withoutExtension(title){return title.replace(/\.(txt|csv|pdf)$/i,'');}
function safeTitle(title,filename){const ext=filename.match(/\.(txt|csv|pdf)$/i)?.[0]||'';return title.toLowerCase().endsWith(ext.toLowerCase())?title:title+ext;}
async function fileContent(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(new Error('Không đọc được tệp. Chọn lại tệp rồi thử lại.'));reader.readAsDataURL(file);});}

function renderManagement(){
  const ownerOptions=toArray(state.data.principals).filter(x=>['staff','manager'].includes(x.role)).map(x=>({value:x.id,label:userLabel(x.id)}));
  setOptions($('#new-document-owner'),ownerOptions);
  setOptions($('#document-edit-actor'),toArray(state.data.principals).map(x=>({value:x.id,label:userLabel(x.id)})));
  if(state.auth){$('#new-document-owner').value=state.auth.username;$('#document-edit-actor').value=state.auth.username;}
  $('#new-document-owner').disabled=Boolean(state.auth);$('#document-edit-actor').disabled=Boolean(state.auth);
  const approvers=[{value:'',label:'Chọn quản trị an toàn'},...toArray(state.data.principals).filter(x=>x.role==='security_admin'&&x.active).map(x=>({value:x.id,label:userLabel(x.id)}))];
  ['new-document-approver','document-edit-approver','document-grant-approver'].forEach(id=>setOptions($('#'+id),approvers));
  const term=$('#document-search').value.trim().toLowerCase();
  const docs=toArray(state.data.documents).filter(x=>!x.deleted&&`${x.title} ${x.id} ${x.owner_id}`.toLowerCase().includes(term)).sort((a,b)=>Number(b.created_at)-Number(a.created_at));
  $('#document-count').textContent=`(${docs.length})`;
  $('#managed-documents').innerHTML=docs.length?docs.map(x=>`<tr><td><strong>${escapeHTML(x.title)}</strong><small>${escapeHTML(x.id)}</small></td><td>${escapeHTML(selectedRecord('principals',x.owner_id)?.display_name||x.owner_id)}<small>${escapeHTML(departmentNames[x.department]||x.department)}</small></td><td><span class="label-badge ${escapeHTML(x.label)}">${escapeHTML(labels[x.label]||x.label)}</span></td><td><button class="button small" data-edit-doc="${escapeHTML(x.id)}">Chỉnh sửa</button></td></tr>`).join(''):'<tr><td colspan="4" class="empty-cell">Chưa có tài liệu phù hợp.</td></tr>';
  $$('[data-edit-doc]').forEach(b=>b.addEventListener('click',()=>openDocumentEditor(b.dataset.editDoc)));
  const query=$('#employee-search').value.trim().toLowerCase();
  const employees=toArray(state.data.principals).filter(x=>`${x.display_name} ${x.username}`.toLowerCase().includes(query));
  $('#managed-employees').innerHTML=employees.length?employees.map(x=>`<tr><td><strong>${escapeHTML(x.display_name||x.username)}</strong><small>${escapeHTML(x.username)}</small></td><td>${escapeHTML(roleNames[x.role]||x.role)}<small>${escapeHTML(departmentNames[x.department]||x.department)}</small></td><td><span class="account-status ${x.active?'active':'locked'}">${x.active?'Hoạt động':'Đã khóa'}</span></td><td><button class="button small" data-edit-employee="${escapeHTML(x.id)}">Chỉnh sửa</button></td></tr>`).join(''):'<tr><td colspan="4" class="empty-cell">Chưa có nhân viên phù hợp.</td></tr>';
  $$('[data-edit-employee]').forEach(b=>b.addEventListener('click',()=>openEmployeeEditor(b.dataset.editEmployee)));
  if(management.document&&!management.documentDirty)fillDocumentEditor();
  if(management.employee&&!management.employeeDirty)fillEmployeeEditor();
  syncDocumentApproval();renderDocumentGrants();updateDocumentAccess();managementBusy(state.busy);
}

function openDocumentEditor(id){management.document=id;management.documentDirty=false;clearFormErrors($('#document-editor'));fillDocumentEditor();if(innerWidth<=1020)$('#document-editor').scrollIntoView({block:'start',behavior:'smooth'});}
function fillDocumentEditor(){
  const row=selectedRecord('documents',management.document);if(!row)return;
  $('#document-editor-empty').classList.add('hidden');$('#document-editor').classList.remove('hidden');
  $('#document-editor-meta').textContent=`${row.id} · ${row.owner_id} · ${departmentNames[row.department]||row.department}`;
  $('#document-edit-title').value=withoutExtension(row.title);$('#document-edit-label').value=row.label;
  $('#document-edit-retention').value=datetimeValue(row.retention_until);$('#document-edit-hold').checked=Boolean(row.legal_hold);
  $('#document-edit-label-help').textContent=labelHelp[row.label];syncDocumentApproval();renderDocumentGrants();updateDocumentAccess();
}
function openEmployeeEditor(id){management.employee=id;management.employeeDirty=false;clearFormErrors($('#employee-editor'));fillEmployeeEditor();if(innerWidth<=1020)$('#employee-editor').scrollIntoView({block:'start',behavior:'smooth'});}
function fillEmployeeEditor(){
  const row=selectedRecord('principals',management.employee);if(!row)return;
  $('#employee-editor-empty').classList.add('hidden');$('#employee-editor').classList.remove('hidden');
  $('#employee-editor-meta').textContent=`Tài khoản: ${row.username}`;
  $('#employee-edit-name').value=row.display_name||row.username;$('#employee-edit-role').value=row.role;
  $('#employee-edit-department').value=row.department;$('#employee-edit-active').checked=Boolean(row.active);syncRole('employee-edit',false);
}

function syncRole(prefix,changed=true){
  const role=$(`#${prefix}-role`).value,select=$(`#${prefix}-department`);
  if(['auditor','security_admin'].includes(role)){select.value='OPS';select.disabled=true;}
  else {select.disabled=false;if(changed&&select.value==='OPS')select.value='A';}
  $(`#${prefix}-permissions`).textContent=roleHelp[role]||'';
}

function managementBusy(busy){
  $$('[id^="open-new-"],#new-document-form button[type="submit"],#new-employee-form button[type="submit"],#employee-editor button[type="submit"],#document-editor button[type="submit"]').forEach(x=>x.disabled=busy);
}

async function prepareRequestUpload(config){
  const form=$('#request-form'),file=$('#upload-file').files[0],errors={};
  if(!file)errors.file='Chọn tệp cần thêm.';
  else if(!/\.(txt|csv|pdf)$/i.test(file.name))errors.file='Chọn tệp TXT, CSV hoặc PDF.';
  else if(file.size===0||file.size>1024*1024)errors.file='Tệp phải có nội dung và tối đa 1 MiB.';
  const title=$('#upload-title').value.trim()||file?.name||'';
  if(title.length>196||/[\\/\r\n\x00]/.test(title))errors.title='Tên tối đa 196 ký tự, không chứa dấu / hoặc \\.';
  if(Object.keys(errors).length){showFormErrors(form,'Kiểm tra lại thông tin tài liệu.',errors);return false;}
  config.json.title=safeTitle(title,file.name);config.json.content_b64=await fileContent(file);return true;
}

function showRequestUploadError(response){
  const reason=response.reason,fields={};
  if(['ROLE','INACTIVE','UNKNOWN_SUBJECT'].includes(reason))fields.request_user=friendlyFailure(response);
  else if(reason==='INVALID_SIZE')fields.file=friendlyFailure(response);
  else if(reason==='INVALID_INPUT')fields.title=friendlyFailure(response);
  showFormErrors($('#request-form'),friendlyFailure(response),fields);
}

function tryDocument(){
  const row=selectedRecord('documents',management.document);if(!row)return;
  const actor=$('#document-edit-actor').value||row.owner_id;navigate('playground');$('#identity-source').value=state.auth?'interactive':'operator';$('#request-user').value=state.auth?.username||actor;
  $('#request-action').value='download';$('#request-document').value=row.id;$('#request-mode').value='B1';$('#request-device').value='';renderAuth();updateRequestForm();
}
function tryEmployee(){
  if(!management.employee)return;navigate('playground');$('#identity-source').value='operator';$('#request-user').value=management.employee;
  $('#request-action').value='list';$('#request-mode').value='B1';$('#request-device').value='';renderAuth();updateRequestForm();
}

async function submitManagement(form,button,work){
  if(state.busy){showFormErrors(form,'Đợi tác vụ đang chạy hoàn thành.');return;}
  clearFormErrors(form);button.disabled=true;
  try{await work();}catch(error){showFormErrors(form,error.message,error.fields||{});}
  finally{button.disabled=false;if(state.busy)managementBusy(true);}
}

function wireManagement(){
  $('#upload-file').dataset.field='file';$('#upload-title').dataset.field='title';$('#request-user').dataset.field='request_user';
  $('#document-search').addEventListener('input',renderManagement);$('#employee-search').addEventListener('input',renderManagement);
  $('#document-editor').addEventListener('input',()=>management.documentDirty=true);$('#document-editor').addEventListener('change',()=>management.documentDirty=true);
  $('#employee-editor').addEventListener('input',()=>management.employeeDirty=true);$('#employee-editor').addEventListener('change',()=>management.employeeDirty=true);
  ['new-employee','employee-edit'].forEach(prefix=>$(`#${prefix}-role`).addEventListener('change',()=>syncRole(prefix)));
  ['new-document','document-edit'].forEach(prefix=>$(`#${prefix}-label`).addEventListener('change',()=>{$(`#${prefix}-label-help`).textContent=labelHelp[$(`#${prefix}-label`).value];syncDocumentApproval();updateDocumentAccess();}));
  $('#document-edit-actor').addEventListener('change',updateDocumentAccess);
  $$('[data-close-dialog]').forEach(b=>b.addEventListener('click',()=>document.getElementById(b.dataset.closeDialog).close()));
  $('#open-new-document').addEventListener('click',()=>{clearFormErrors($('#new-document-form'));$('#new-document-label-help').textContent=labelHelp[$('#new-document-label').value];syncDocumentApproval();$('#new-document-dialog').showModal();});
  $('#open-new-employee').addEventListener('click',()=>{clearFormErrors($('#new-employee-form'));syncRole('new-employee',false);$('#new-employee-dialog').showModal();});
  $('#test-managed-document').addEventListener('click',tryDocument);$('#test-managed-employee').addEventListener('click',tryEmployee);
  $('#new-document-form').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;submitManagement(form,form.querySelector('[type="submit"]'),async()=>{
    const file=$('#new-document-file').files[0];
    if(!file){showFormErrors(form,'Chọn tệp cần thêm.',{file:'Chọn tệp TXT, CSV hoặc PDF.'});return;}
    if(!/\.(txt|csv|pdf)$/i.test(file.name)||!file.size||file.size>1024*1024){showFormErrors(form,'Tệp chưa hợp lệ.',{file:'Chọn tệp TXT, CSV hoặc PDF có nội dung, tối đa 1 MiB.'});return;}
    const result=await api('/lab/documents',{method:'POST',body:JSON.stringify({filename:file.name,title:$('#new-document-title').value.trim(),owner_id:$('#new-document-owner').value,label:$('#new-document-label').value,approver_id:$('#new-document-approver').value,ttl_seconds:Number($('#new-document-ttl').value),content_b64:await fileContent(file)})});
    $('#new-document-dialog').close();form.reset();management.document=result.id;management.documentDirty=false;await refreshState(true);if(!state.auth){$('#document-edit-actor').value=result.owner_id;updateDocumentAccess();}notice('#documents-notice',`Đã thêm ${result.title}.`);
  });});
  $('#document-grant-form').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;submitManagement(form,form.querySelector('[type="submit"]'),async()=>{
    const result=await api(`/lab/documents/${encodeURIComponent(management.document)}/grants`,{method:'POST',body:JSON.stringify({principal_id:$('#document-grant-target').value,approver_id:$('#document-grant-approver').value,ttl_seconds:Number($('#document-grant-ttl').value)})});
    await refreshState(true);$('#document-grant-notice').textContent=`Đã cấp quyền đến ${new Date(result.expires_at*1000).toLocaleString('vi-VN')}.`;
  });});
  $('#new-employee-form').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;submitManagement(form,form.querySelector('[type="submit"]'),async()=>{
    const body={username:$('#new-employee-username').value.trim(),display_name:$('#new-employee-name').value.trim(),password:$('#new-employee-password').value,role:$('#new-employee-role').value,department:$('#new-employee-department').value,active:$('#new-employee-active').checked};
    const result=await api('/lab/employees',{method:'POST',body:JSON.stringify(body)});$('#new-employee-dialog').close();form.reset();$('#new-employee-active').checked=true;management.employee=result.id;management.employeeDirty=false;await refreshState(true);notice('#employees-notice',`Đã tạo ${result.display_name}. Tài khoản ${result.username} có thể sử dụng ngay.`);
  });});
  $('#document-editor').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;submitManagement(form,form.querySelector('[type="submit"]'),async()=>{
    const retention=new Date($('#document-edit-retention').value).getTime()/1000;
    if(!Number.isFinite(retention)){showFormErrors(form,'Chọn hạn lưu giữ hợp lệ.',{retention_until:'Chọn ngày và giờ.'});return;}
    await api(`/lab/documents/${encodeURIComponent(management.document)}`,{method:'PUT',body:JSON.stringify({actor_id:$('#document-edit-actor').value,approver_id:$('#document-edit-approver').value,ttl_seconds:Number($('#document-edit-ttl').value),title:$('#document-edit-title').value.trim(),label:$('#document-edit-label').value,retention_until:retention,legal_hold:$('#document-edit-hold').checked})});management.documentDirty=false;await refreshState(true);notice('#documents-notice','Đã cập nhật tài liệu.');
  });});
  $('#employee-editor').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;submitManagement(form,form.querySelector('[type="submit"]'),async()=>{
    await api(`/lab/employees/${encodeURIComponent(management.employee)}`,{method:'PUT',body:JSON.stringify({display_name:$('#employee-edit-name').value.trim(),role:$('#employee-edit-role').value,department:$('#employee-edit-department').value,active:$('#employee-edit-active').checked})});management.employeeDirty=false;await refreshState(true);notice('#employees-notice','Đã lưu quyền truy cập. Thay đổi có hiệu lực với yêu cầu tiếp theo.');
  });});
}

function syncDocumentApproval(){
  const row=selectedRecord('documents',management.document);
  $('#new-document-approval').classList.toggle('hidden',$('#new-document-label').value!=='restricted');
  $('#document-edit-approval').classList.toggle('hidden',!row||row.label==='restricted'||$('#document-edit-label').value!=='restricted');
}
function validDocumentGrants(row){
  return toArray(state.data.grants).filter(g=>g.doc_id===row.id&&g.doc_version===row.version&&g.action==='download'&&!g.revoked&&Number(g.expires_at)>Date.now()/1000&&g.approver!==g.principal_id);
}
function updateDocumentAccess(){
  const row=selectedRecord('documents',management.document);if(!row)return;
  const actor=selectedRecord('principals',$('#document-edit-actor').value),box=$('#document-edit-access');
  if(!actor){box.textContent='Chọn người thực hiện để kiểm tra quyền.';return;}
  if(!actor.active){box.textContent='Tài khoản đang bị khóa. Kích hoạt tại Nhân viên.';return;}
  if(row.label!=='restricted'){box.textContent='Lưu thay đổi yêu cầu người thực hiện có quyền tải tài liệu hiện tại. Thiết bị và quyền được kiểm tra lại khi gửi.';return;}
  if(actor.role!=='manager'||actor.department!==row.department){box.textContent='Không có quyền tải và sửa: cần trưởng phòng cùng phòng với tài liệu.';return;}
  const grant=validDocumentGrants(row).find(g=>g.principal_id===actor.id);
  box.textContent=grant?`Quyền tải và sửa đến ${new Date(grant.expires_at*1000).toLocaleString('vi-VN')}. Thiết bị được kiểm tra lại khi gửi.`:'Chưa có quyền tải và sửa còn hạn. Cấp quyền trong phần bên dưới rồi lưu lại.';
}
function renderDocumentGrants(){
  const row=selectedRecord('documents',management.document),panel=$('#document-permissions-panel');
  panel.classList.toggle('hidden',!row||row.label!=='restricted');if(!row||row.label!=='restricted')return;
  const targets=toArray(state.data.principals).filter(p=>p.role==='manager'&&p.department===row.department&&p.active);
  setOptions($('#document-grant-target'),targets.map(p=>({value:p.id,label:userLabel(p.id)})));
  const grants=toArray(state.data.grants).filter(g=>g.doc_id===row.id).sort((a,b)=>Number(b.created_at)-Number(a.created_at));
  $('#document-grants-list').innerHTML=grants.length?`<div class="table-wrap"><table><thead><tr><th>Người nhận</th><th>Hiệu lực</th><th>Trạng thái</th><th></th></tr></thead><tbody>${grants.map(g=>{
    const current=g.doc_version===row.version&&!g.revoked&&Number(g.expires_at)>Date.now()/1000;
    const status=g.revoked?'Đã thu hồi':g.doc_version!==row.version?'Phiên bản cũ':Number(g.expires_at)<=Date.now()/1000?'Hết hạn':'Còn hạn';
    return `<tr><td>${escapeHTML(userLabel(g.principal_id))}<small>Phiên bản ${escapeHTML(g.doc_version)}</small></td><td>${escapeHTML(new Date(g.expires_at*1000).toLocaleString('vi-VN'))}</td><td>${status}</td><td>${current?`<button type="button" class="button small" data-revoke-document-grant="${escapeHTML(g.id)}">Thu hồi</button>`:''}</td></tr>`;
  }).join('')}</tbody></table></div>`:'<p class="field-help">Chưa cấp quyền cho tài liệu này.</p>';
  $$('[data-revoke-document-grant]').forEach(button=>button.addEventListener('click',async()=>{
    const form=$('#document-grant-form');submitManagement(form,button,async()=>{await api(`/lab/documents/${encodeURIComponent(row.id)}/grants/${encodeURIComponent(button.dataset.revokeDocumentGrant)}`,{method:'DELETE',body:JSON.stringify({approver_id:$('#document-grant-approver').value})});await refreshState(true);$('#document-grant-notice').textContent='Đã thu hồi quyền. Yêu cầu tải và sửa tiếp theo sẽ được kiểm tra lại.';});
  }));
}
