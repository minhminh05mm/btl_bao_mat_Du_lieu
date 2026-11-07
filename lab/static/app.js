"use strict";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pretty = (value) => JSON.stringify(value, null, 2);
const state = { csrf:"", auth:null, data:{}, catalog:null, view:"guide", rows:[], job:null, response:null, busy:false, polling:false, details:[] };
const users = [];
const labels = {internal:"Nội bộ",confidential:"Mật",restricted:"Hạn chế"};
const pageTitles = {documents:"Tài liệu",employees:"Nhân viên",guide:"Bắt đầu có hướng dẫn",overview:"Tổng quan",playground:"Tự thử yêu cầu",tests:"Kiểm chứng",operations:"Điều khiển lab",audit:"Nhật ký & cảnh báo"};

async function api(path, options={}) {
  const headers = {"Content-Type":"application/json", ...(options.headers || {})};
  if (options.method && options.method !== "GET") headers["X-Lab-CSRF"] = state.csrf;
  const response = await fetch(path, {...options, headers});
  let body;
  try { body = await response.json(); } catch { body = {error:`Máy chủ trả HTTP ${response.status}, không có JSON hợp lệ.`}; }
  if (!response.ok) {
    const detail = body.error || body.detail || `HTTP ${response.status}`;
    const error=new Error(typeof detail === "object" ? (detail.message||pretty(detail)) : detail);
    if(typeof detail === "object"){error.fields=detail.fields||{};error.partial=detail.partial;error.document_id=detail.document_id;}
    error.status=response.status;throw error;
  }
  return body;
}

function toast(message, error=false) {
  const element = document.createElement("div");
  element.className = `toast${error ? " error" : ""}`;
  element.textContent = message;
  $("#toasts").append(element);
  setTimeout(() => element.remove(), error ? 10000 : 5000);
}

async function action(button, callback) {
  if (button.disabled) return;
  const original = button.innerHTML;
  button.disabled = true;
  try { await callback(); } catch(error) { toast(error.message, true); }
  finally { button.innerHTML = original; button.disabled = false; if(state.busy)setBusy(true); }
}

function navigate(view) {
  if (!pageTitles[view]) return;
  state.view = view;
  if(["operations","overview"].includes(view))$("#advanced-navigation").open=true;
  $$(".view").forEach(el => el.classList.toggle("active", el.id === `view-${view}`));
  $$(".nav-item").forEach(el => el.classList.toggle("active", el.dataset.view === view));
  $("#breadcrumb-current").textContent = pageTitles[view];
  history.replaceState(null,"",`#${view}`);
  window.scrollTo({top:0, behavior:"smooth"});
}

function toArray(value) {
  if (Array.isArray(value)) return value;
  if (value && Array.isArray(value.items)) return value.items;
  if (value && typeof value === "object") return Object.entries(value).map(([id,item]) => typeof item === "object" && item !== null ? {id,...item} : {id,value:item});
  return [];
}

function timeLabel(value) {
  if (!value) return "—";
  const date = typeof value === "number" ? new Date(value * 1000) : new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("vi-VN", {hour12:false});
}

function principalById(id) {
  return toArray(state.data.principals).find(row => row.id === id || row.username === id);
}

function personById(id) {
  return id?DemoLanguage.person(principalById(id)||{username:id}):"Hệ thống";
}

function userLabel(user) {
  const principal=principalById(user);
  const name=personById(user), role=principal?DemoLanguage.role(principal.role):"";
  return [name,name===role||name.startsWith(role+" ")?"":role,DemoLanguage.department(principal?.department),principal?.active===false?"Đã ngừng quyền truy cập kho":""].filter(Boolean).join(" · ");
}

function setOptions(select, options, selected) {
  const current = selected ?? select.value;
  select.innerHTML = options.map(item => `<option value="${escapeHTML(item.value)}">${escapeHTML(item.label)}</option>`).join("");
  if (options.some(item => String(item.value) === String(current))) select.value = current;
}

function servicesArray() {
  return toArray(state.data.services).map(item => {
    const name = item.service || item.name || item.id || "dịch vụ";
    const raw = item.health || item.status || item.state || item.value || "unknown";
    const text = typeof raw === "object" ? pretty(raw) : String(raw);
    const up = item.running === true || item.healthy === true || /^(running|healthy|ok|up)$/i.test(text) || /running.*healthy/i.test(text);
    return {name,text,up};
  });
}

function renderOverview() {
  const principals = toArray(state.data.principals);
  const documents = toArray(state.data.documents);
  const services = servicesArray();
  const alerts = toArray(state.data.alerts);
  $("#stat-documents").textContent = documents.length || (state.data.error ? "—" : "0");
  $("#stat-principals").textContent = principals.length || (state.data.error ? "—" : "0");
  $("#stat-services").textContent = services.length ? `${services.filter(s=>s.up).length}/${services.length}` : "—";
  $("#services-caption").textContent = services.length ? "Đọc từ môi trường triển khai" : "Chưa nhận được trạng thái dịch vụ";
  $("#stat-alerts").textContent = alerts.filter(a => !a.acknowledged && !a.ack && a.status !== "acknowledged").length;
  $("#health-updated").textContent = new Date().toLocaleTimeString("vi-VN", {hour12:false});
  $("#health-list").innerHTML = services.length ? services.map(s => `<div class="health-row"><span class="health-name"><i class="service-dot ${s.up?"up":"down"}"></i>${escapeHTML(s.name)}</span><span class="health-status">${escapeHTML(s.text)}</span></div>`).join("") : '<div class="empty compact">Chưa có dữ liệu dịch vụ.<br>Kiểm tra trạng thái môi trường hoặc làm mới.</div>';
  const disk = state.data.disk;
  $("#disk-info").textContent = disk ? `Lưu trữ · ${typeof disk === "string" ? disk : Object.entries(disk).map(([k,v])=>`${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(" · ")}` : "Không có dữ liệu dung lượng từ môi trường.";
}

function renderAuth() {
  const auth = state.auth;
  $("#auth-user").textContent = auth ? personById(auth.username) : "Chưa đăng nhập";
  $("#auth-caption").textContent = auth ? "Đang dùng tài khoản đã đăng nhập" : "Đăng nhập để sử dụng tài khoản của bạn";
  $("#identity-light").classList.toggle("authenticated", Boolean(auth));
  $("#login-button").classList.toggle("hidden", Boolean(auth));
  $("#logout-button").classList.toggle("hidden", !auth);
  $("#mobile-auth").textContent=auth ? `${personById(auth.username)} · Đăng xuất` : "Đăng nhập";
  if ($("#identity-source").value === "interactive") {
    $("#request-user").disabled = true;
    if (auth) $("#request-user").value = auth.username;
  } else $("#request-user").disabled = false;
}

function renderDocumentOptions() {
  DemoLanguage.modeOptions($("#request-mode"));
  const documents = toArray(state.data.documents);
  users.splice(0,users.length,...toArray(state.data.principals).map(x=>x.username||x.id));
  setOptions($("#request-document"), documents.map(doc => ({value:doc.id || doc.doc_id, label:`${DemoLanguage.documentName(doc)} · ${DemoLanguage.label(doc.label)}${doc.deleted ? " · Đã xóa" : ""}`})));
  setOptions($("#request-user"), users.map(user => ({value:user,label:userLabel(user)})));
  setOptions($("#request-device"),[
    {value:"",label:"Thiết bị đã đăng ký của tài khoản đang chọn"},
    ...users.map(user=>({value:user,label:`Thiết bị của ${personById(user)}`})),
    {value:"rogue",label:"Thiết bị chưa đăng ký"},
    {value:"bad",label:"Thiết bị có thông tin xác minh không đáng tin cậy"},
    {value:"none",label:"Không gửi thông tin xác minh thiết bị"}
  ]);
  renderAuth();
  updateRequestForm();
}

async function refreshState(silent=false) {
  try {
    state.data = await api("/lab/state");
    renderOverview(); renderDocumentOptions(); renderEditOptions(); renderRegistry(); renderSnapshots(); renderAudit(); renderFaults();renderManagement();
    if(state.busy)setBusy(true);
    return true;
  } catch(error) {
    if (!silent) toast(`Không đọc được môi trường: ${error.message}`,true);
    $("#health-list").innerHTML = `<div class="empty compact">${escapeHTML(error.message)}</div>`;
    return false;
  }
}

function requestConfiguration() {
  const act = $("#request-action").value;
  const id = encodeURIComponent($("#request-document").value);
  const config = {username:$("#request-user").value, mode:$("#request-mode").value, device:$("#request-device").value || null,
    identity_source:$("#identity-source").value, method:"GET", path:"/documents"};
  if (act === "metadata") config.path = `/documents/${id}/metadata`;
  if (act === "download") config.path = `/documents/${id}/download`;
  if (act === "delete") {config.method="DELETE";config.path=`/documents/${id}`;}
  if (act === "audit") config.path="/audit";
  if (act === "alerts") config.path="/alerts";
  if (act === "upload") {config.method="POST";config.path="/documents";config.json={title:$("#upload-title").value || $("#upload-file").files[0]?.name || "",label:$("#upload-label").value,content_b64:"(nội dung file được đọc khi gửi)"};}
  if (act === "custom") {config.method=$("#custom-method").value;config.path=$("#custom-path").value;config.json=JSON.parse($("#custom-body").value || "{}");}
  config.headers=JSON.parse($("#request-headers").value || "{}");
  return config;
}

function updateRequestForm() {
  const act = $("#request-action").value;
  $("#document-control").classList.toggle("hidden", !["metadata","download","delete"].includes(act));
  $("#upload-controls").classList.toggle("hidden", act !== "upload");
  $("#custom-request").classList.toggle("hidden", act !== "custom");
  renderDocumentExplanation();
  renderActionExplanation();
  try {$("#request-preview").textContent=pretty(requestConfiguration());} catch(error) {$("#request-preview").textContent=`JSON chưa hợp lệ: ${error.message}`;}
}

function renderClassificationRules() {
  $("#dataset-version").textContent = state.catalog?.dataset_version || "Chưa đọc tập mẫu";
  const rules = state.catalog?.rules || {};
  $("#classification-rules").innerHTML = Object.entries(rules).map(([key, rule]) =>
    `<article class="classification-rule"><h3>${escapeHTML(rule.name)}</h3><p>${escapeHTML(rule.criterion)}</p><p><span>Hậu quả khi tiết lộ:</span> ${escapeHTML(rule.consequence)}</p><p><span>Quyền đọc:</span> ${escapeHTML(rule.access)}</p></article>`).join("");
}

function renderActionExplanation() {
  const element = $("#action-explanation");
  if (!element) return;
  const action = $("#request-action").value;
  const descriptions = {
    audit: {
      title: "Đọc nhật ký kiểm toán",
      purpose: "Xem các sự kiện truy cập và thay đổi trạng thái đã được ghi nhận; không cần chọn một tài liệu cụ thể.",
      access: "Kiểm toán đọc nhật ký kiểm toán. Quản trị an toàn đọc nhật ký phục vụ vận hành. Mục này dành cho hai vai trò đó.",
      result: "Bấm Gửi yêu cầu và xem kết quả để nhận danh sách sự kiện trong phần Kết quả thực tế."
    },
    alerts: {
      title: "Đọc cảnh báo an toàn",
      purpose: "Xem các cảnh báo đã phát sinh. Lab tạo cảnh báo khi cùng chủ thể có ít nhất 5 yêu cầu bị từ chối trong 60 giây.",
      access: "Mục này dành cho vai trò Kiểm toán hoặc Quản trị an toàn.",
      result: "Kết quả sẽ cho biết số cảnh báo. Nếu danh sách trống, trang hiển thị Hiện chưa có cảnh báo."
    },
    custom: {
      title: "Yêu cầu API tùy chỉnh",
      purpose: "Tự chọn phương thức, đường dẫn và JSON body để gửi yêu cầu qua gateway bằng tài khoản và chứng thư đang chọn.",
      access: "Phụ thuộc endpoint đang gọi. Ví dụ GET /me dành cho tài khoản hợp lệ; GET /audit cần vai trò Kiểm toán hoặc Quản trị an toàn. Các thao tác thay đổi dữ liệu vẫn chịu đầy đủ kiểm soát của API.",
      result: "Ví dụ đọc an toàn: Method GET, đường dẫn /me, JSON body {}. Đường dẫn dùng /me hoặc /audit, không thêm tiền tố /api."
    }
  };
  const description = descriptions[action];
  element.classList.toggle("hidden", !description);
  if (!description) { element.textContent = ""; return; }
  const method = action === "custom" ? $("#custom-method").value : "GET";
  const path = action === "custom" ? $("#custom-path").value : `/${action}`;
  element.innerHTML = `<h3>${escapeHTML(description.title)}</h3>
    <p>${escapeHTML(description.purpose)}</p>
    <p><span>Quyền cần có:</span> ${escapeHTML(description.access)}</p>
    <p><span>Yêu cầu:</span> ${escapeHTML(method)} ${escapeHTML(path)}</p>
    <small>${escapeHTML(description.result)} Chọn thiết bị đã đăng ký của tài khoản để gửi yêu cầu thông thường.</small>`;
}

function renderDocumentExplanation() {
  const element = $("#document-explanation");
  const action = $("#request-action").value;
  const id = $("#request-document").value;
  const current = toArray(state.data.documents).find(doc => doc.id === id);
  const baseline = state.catalog?.items?.find(doc => doc.id === id);
  element.classList.toggle("hidden", !current || !["metadata", "download", "delete"].includes(action));
  if (!current) { element.textContent = ""; return; }
  const changed = baseline && current.label !== baseline.baseline_label;
  const reason = baseline?.classification_reason || "Tài liệu do người dùng tải lên; nhãn ban đầu được chọn theo thẩm quyền, máy chủ không tự suy ra từ nội dung.";
  element.innerHTML = `<h3>${escapeHTML(current.title || baseline?.title || id)}</h3>
    <p>${escapeHTML(baseline?.document_type || "Tài liệu tải lên")} · ${escapeHTML(baseline?.department_name || DemoLanguage.department(current.department))} · chủ hồ sơ ${escapeHTML(personById(current.owner_id))}</p>
    <p><span>Nhãn hiện tại:</span> ${escapeHTML(labels[current.label] || current.label)}${current.deleted ? " · đã hủy" : ""}</p>
    <p><span>${baseline ? `Căn cứ nhãn ban đầu ${labels[baseline.baseline_label] || baseline.baseline_label}` : "Căn cứ nhãn"}:</span> ${escapeHTML(reason)}</p>
    ${changed ? '<p class="classification-change">Nhãn đã thay đổi sau khi khởi tạo. Kho kiểm tra theo nhãn hiện tại.</p>' : ""}
    <small>Mô tả dữ liệu mẫu dành cho người vận hành. Nội dung đầy đủ chỉ được trả qua yêu cầu tải xuống được cấp quyền.</small>`;
}

async function sendRequest(event) {
  event.preventDefault();
  await action($("#send-request"), async()=>{
    if ($("#identity-source").value === "interactive" && !state.auth) throw new Error("Bấm Đăng nhập ở thanh bên để dùng tài khoản của bạn.");
    const config = requestConfiguration();
    if (["metadata","download","delete"].includes($("#request-action").value) && !$("#request-document").value) throw new Error("Chưa có tài liệu được chọn.");
    if ($("#request-action").value === "delete" && !(await confirmDialog("Đánh dấu xóa tài liệu trong demo?", "Nếu đủ quyền và hết hạn lưu giữ, kho sẽ đánh dấu tài liệu là đã xóa. Tệp gốc trên máy và bản sao lưu vẫn có thể dùng. Tài liệu đang được giữ để bảo toàn chưa thể xóa."))) return;
    clearFormErrors($("#request-form"));
    if ($("#request-action").value === "upload" && !(await prepareRequestUpload(config))) return;
    $("#send-request").textContent="Đang gửi yêu cầu…";
    state.response = await api("/lab/request",{method:"POST",body:JSON.stringify(config)});
    renderResponse();
    if($("#request-action").value==="upload"&&!state.response.ok)showRequestUploadError(state.response);
    if (["upload","delete"].includes($("#request-action").value)) await refreshState(true);
  });
}

function renderResponse() {
  const r=state.response;
  renderHumanResponse(r);
  $("#response-empty").classList.add("hidden");$("#response-content").classList.remove("hidden");
  $("#response-time").textContent=new Date().toLocaleTimeString("vi-VN",{hour12:false});
  $("#response-status").textContent=r.status ? `HTTP ${r.status}` : "LỖI KẾT NỐI";
  $("#response-status").classList.toggle("error",!r.ok);
  $("#response-reason").textContent=r.reason || (r.ok ? "Yêu cầu hoàn thành" : "Xem phản hồi chi tiết");
  $("#response-latency").textContent=`${r.latency_ms ?? "—"} ms`;
  $("#response-id").textContent=r.request_id || "Không có · kiểm tra lớp kết nối/TLS";
  $("#response-policy").textContent=r.policy_version || "—";
  $("#response-size").textContent=r.size != null ? `${r.size.toLocaleString("vi-VN")} byte` : "—";
  const display={...r}; if(display.content_b64) display.content_b64=`[${r.size} byte nội dung đã được cấp; dùng nút Lưu nội dung]`;
  $("#response-json").textContent=pretty(display);
  $("#download-content").classList.toggle("hidden",!r.content_b64);
  if(innerWidth<=1020)$("#human-response").scrollIntoView({block:"center",behavior:"smooth"});
}

function downloadBlob(name, content, type="application/json") {
  const blob=content instanceof Blob ? content : new Blob([content],{type});
  const url=URL.createObjectURL(blob); const a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}

const faultDefinitions=[
  ["opa","Dừng dịch vụ OPA","Mất điểm quyết định chính sách thực tế"],
  ["openbao","Dừng dịch vụ OpenBao","Mất khả năng giải mã qua KMS"],
  ["audit_write_failure","Lỗi ghi nhật ký","Không thể ghi bằng chứng trước thao tác"],
  ["opa_response_invalid","PDP trả phản hồi không hợp lệ","Kiểm tra validate kết quả quyết định"],
  ["registry_unavailable","Nguồn thuộc tính không sẵn sàng","Thiếu trạng thái quyền hiện tại"],
  ["stale_signals","Tín hiệu thiết bị quá hạn","Ngừng tự làm mới và làm cũ timestamp"],
];

function renderFaults() {
  const services=servicesArray();
  $("#fault-list").innerHTML=faultDefinitions.map(([service,title,subtitle])=>{
    const enabled=service==="stale_signals" ? toArray(state.data.devices).some(device=>device.auto_refresh===false&&Number(device.observed_at)<Date.now()/1000-60) : ["opa","openbao"].includes(service) ? services.some(item=>item.name===service&&!item.up) : Boolean(state.data.faults?.[service]);
    return `<div class="fault-row"><div><strong>${escapeHTML(title)}${enabled?' <span class="fault-on">Đang bật</span>':""}</strong><small>${escapeHTML(subtitle)}</small></div><div class="fault-controls"><button data-fault="${service}" data-enabled="true">Tạo lỗi</button><button data-fault="${service}" data-enabled="false">Khôi phục</button></div></div>`;
  }).join("");
  $$("[data-fault]").forEach(button=>button.addEventListener("click",()=>action(button,async()=>{await startTask("/lab/fault",{service:button.dataset.fault,enabled:button.dataset.enabled==="true"});})));
}

function patchOptions(kind) {
  const now=Math.floor(Date.now()/1000);
  if(kind==="principal")return [["Thu hồi quyền",{active:false}],["Kích hoạt",{active:true}],["Nhân viên A",{role:"staff",department:"A"}],["Trưởng phòng A",{role:"manager",department:"A"}]];
  if(kind==="device")return [["Không tuân thủ",{compliant:false}],["Tuân thủ",{compliant:true}],["Rủi ro cao",{risk:"HIGH"}],["Tín hiệu mới",{risk:"NORMAL",observed_at:now,risk_at:now,auto_refresh:true}],["Tín hiệu cũ",{observed_at:now-120,risk_at:now-120,auto_refresh:false}],["Thu hồi thiết bị",{revoked:true}],["Khôi phục thiết bị",{revoked:false}]];
  if(kind==="document")return [["Nhãn hạn chế",{label:"restricted"}],["Hết thời hạn",{retention_until:now-10}],["Còn thời hạn",{retention_until:now+86400}],["Bật legal hold",{legal_hold:true}],["Bỏ legal hold",{legal_hold:false}]];
  return [["Thu hồi grant",{revoked:true}],["Hết hạn grant",{expires_at:now-10}],["Gia hạn 5 phút",{revoked:false,expires_at:now+300}]];
}

function renderEditOptions() {
  const kind=$("#edit-kind").value;
  const rows=toArray(state.data[`${kind}s`]);
  const options=rows.map(row=>({value:row.id,label:`${row.id}${row.role ? ` · ${row.role}` : ""}${row.label ? ` · ${labels[row.label]||row.label}` : ""}`}));
  if(kind==="grant")options.unshift({value:"__new__",label:"Cấp grant mới qua API secadmin"});
  setOptions($("#edit-id"),options);
  $("#quick-patches").innerHTML=patchOptions(kind).map(([title,patch],i)=>`<button type="button" data-patch="${i}">${escapeHTML(title)}</button>`).join("");
  $$("[data-patch]").forEach(button=>button.addEventListener("click",()=>{$("#edit-patch").value=pretty(patchOptions(kind)[Number(button.dataset.patch)][1]);renderPatchSummary();}));
  updateGrantEditor();
}

function updateGrantEditor(){
  const create=$("#edit-kind").value==="grant"&&$("#edit-id").value==="__new__";
  $("#quick-patches").classList.toggle("hidden",create);
  $("#edit-note").textContent=create?"Chọn người nhận, tài liệu và thời gian ở các ô lựa chọn. Khi bấm Áp dụng trạng thái, yêu cầu phê duyệt được gửi bằng tài khoản secadmin qua API; hệ thống vẫn kiểm tra quyền người phê duyệt.":"Chọn một điều kiện mẫu, đọc thay đổi dự kiến rồi bấm Áp dụng trạng thái. Đây là bước chuẩn bị thí nghiệm; các lần truy cập sau vẫn được kiểm tra theo chính sách. JSON thời gian nâng cao dùng Unix epoch theo UTC.";
  $("#grant-simple-fields").classList.toggle("hidden",!create);
  if(create){try{const current=JSON.parse($("#edit-patch").value);if(!current.principal_id||!current.doc_id)$("#edit-patch").value=pretty({principal_id:"adam",doc_id:"A-R01",ttl_seconds:300});}catch{$("#edit-patch").value=pretty({principal_id:"adam",doc_id:"A-R01",ttl_seconds:300});}}
  if(create){
    const current=JSON.parse($("#edit-patch").value||"{}");
    setOptions($("#grant-user"),toArray(state.data.principals).filter(x=>x.role==="manager").map(x=>({value:x.id,label:userLabel(x.id)})),current.principal_id);
    setOptions($("#grant-document"),toArray(state.data.documents).filter(x=>x.label==="restricted"&&!x.deleted).map(x=>({value:x.id,label:`${x.title||x.id} (${x.id})`})),current.doc_id);
    $("#grant-minutes").value=Math.max(1,Math.round((current.ttl_seconds||300)/60));
    $("#edit-patch").value=pretty({principal_id:$("#grant-user").value,doc_id:$("#grant-document").value,ttl_seconds:Number($("#grant-minutes").value)*60});
  }
  renderPatchSummary();
}

function renderRegistry() {
  const kind=$("#state-table-kind").value;
  const rows=toArray(state.data[kind]);
  const columns={principals:["id","role","department","active","permission_version"],devices:["id","principal_id","compliant","revoked","risk","observed_at","auto_refresh"],documents:["id","owner_id","department","label","version","retention_until","legal_hold","deleted"],grants:["id","principal_id","doc_id","doc_version","expires_at","revoked","approver"]}[kind];
  $("#state-table").innerHTML=`<table><thead><tr>${columns.map(c=>`<th>${escapeHTML(c)}</th>`).join("")}</tr></thead><tbody>${rows.length ? rows.map((row,index)=>`<tr data-state-detail="${index}">${columns.map(c=>`<td>${escapeHTML(["observed_at","risk_at","retention_until","expires_at"].includes(c)?timeLabel(row[c]):row[c] ?? "—")}</td>`).join("")}</tr>`).join(""):`<tr><td colspan="${columns.length}" class="empty-cell">Chưa có dữ liệu ${escapeHTML(kind)}.</td></tr>`}</tbody></table>`;
  $$("[data-state-detail]").forEach(row=>row.addEventListener("click",()=>showDetails(rows[Number(row.dataset.stateDetail)])));
}

function renderSnapshots() {
  const snapshots=toArray(state.data.snapshots);
  setOptions($("#restore-snapshot"),snapshots.length ? snapshots.map(s=>({value:s.snapshot_id||s.id||s.name,label:`${s.snapshot_id||s.id||s.name}${s.created_at ? ` · ${timeLabel(s.created_at)}` : ""}`})) : [{value:"",label:"Chưa có snapshot"}]);
}

function showDetails(value) {$("#detail-json").textContent=pretty(value);$("#detail-dialog").showModal();}

function renderAudit() {
  const term=$("#audit-search").value.trim().toLowerCase();
  const records=toArray(state.data.documents);
  const events=toArray(state.data.audit).map(raw=>({
    raw,
    person:personById(raw.principal_id||raw.username||raw.actor),
    action:DemoLanguage.action(raw.action),
    title:raw.doc_id?DemoLanguage.documentName(records.find(doc=>doc.id===raw.doc_id)):"",
    decision:DemoLanguage.reason(raw.reason,raw.decision==="deny"?"Yêu cầu bị từ chối.":"Đã ghi nhận thao tác."),
  })).filter(event=>`${event.person} ${event.action} ${event.title} ${event.decision} ${JSON.stringify(event.raw)}`.toLowerCase().includes(term)).reverse();
  state.details=events;
  $("#audit-body").innerHTML=events.length ? events.map((event,i)=>`<tr><td>${escapeHTML(timeLabel(event.raw.created_at))}</td><td>${escapeHTML(event.person)}</td><td>${escapeHTML(event.action)}<span class="result-title">${escapeHTML(event.title)}</span></td><td>${escapeHTML(event.decision)}</td><td><button type="button" class="button small" data-audit-detail="${i}">Xem chi tiết</button></td></tr>`).join("") : '<tr><td colspan="5" class="empty-cell">Không có lượt truy cập phù hợp.</td></tr>';
  $$("[data-audit-detail]").forEach(button=>button.addEventListener("click",()=>showDetails(events[Number(button.dataset.auditDetail)].raw)));
  const alerts=toArray(state.data.alerts).slice().reverse();
  $("#alerts-count").textContent=alerts.length;
  $("#alerts-list").innerHTML=alerts.length ? alerts.map((alert,i)=>`<div class="alert-row"><span class="alert-icon">!</span><div><strong>Nhiều yêu cầu bị từ chối</strong><p>${escapeHTML(personById(alert.principal_id))} · ${escapeHTML(timeLabel(alert.created_at))}${alert.acknowledged ? " · Đã xác nhận" : ""}</p><p>${escapeHTML(alert.count)} lần trong ${escapeHTML(alert.window_seconds)} giây.</p><button type="button" class="button small" data-alert-detail="${i}">Xem chi tiết</button></div></div>`).join("") : '<div class="empty compact">Hiện chưa có cảnh báo.</div>';
  $$("[data-alert-detail]").forEach(button=>button.addEventListener("click",()=>showDetails(alerts[Number(button.dataset.alertDetail)])));
}

function normalizeResult(row) {
  const id=row.id||row.case_id||row.test_id||row.name||"—";
  const expected=row.expected??row.expected_status??row.expected_outcome??"—";
  const actual=row.actual??row.actual_status??row.status_code??row.status??"—";
  let passed=row.passed;
  if(typeof passed!=="boolean")passed=typeof row.pass==="boolean" ? row.pass : typeof row.success==="boolean" ? row.success : ["pass","passed","success"].includes(String(row.result||row.verdict).toLowerCase());
  const reason=row.reason||row.actual_reason||row.actual?.reason||row.response?.reason||row.error||"—";
  const latency=row.latency_ms??row.duration_ms??row.response?.latency_ms;
  return {id,expected,actual,passed,reason,latency,title:row.title||row.name||row.description||"",raw:row};
}

function cellValue(value) {
  if(value&&typeof value==="object"){
    const status=value.status??(Array.isArray(value.statuses)?value.statuses.join(" / "):null);
    if(status!=null||typeof value.allow==="boolean")return `${status!=null?`HTTP ${status}`:""}${status!=null&&typeof value.allow==="boolean"?" · ":""}${typeof value.allow==="boolean"?(value.allow?"Cho phép":"Từ chối"):""}`;
    return JSON.stringify(value);
  }
  return String(value ?? "—");
}

function renderResults() {
  const term=$("#result-search").value.toLowerCase(),filter=$("#result-filter").value;
  const rows=state.rows.map(normalizeResult).filter(r=>(filter==="all"||(filter==="passed"&&r.passed)||(filter==="failed"&&!r.passed))&&JSON.stringify(r.raw).toLowerCase().includes(term));
  $("#results-body").innerHTML=rows.length ? rows.map((r,i)=>`<tr data-result-detail="${i}"><td><strong>${escapeHTML(r.id)}</strong><span class="result-title">${escapeHTML(r.title)}</span></td><td>${escapeHTML(cellValue(r.expected))}</td><td>${escapeHTML(cellValue(r.actual))}</td><td>${escapeHTML(cellValue(r.reason))}</td><td>${r.latency!=null ? `${Number(r.latency).toFixed(1)} ms` : "—"}</td><td><span class="${r.passed?"pass-badge":"fail-badge"}">${r.passed?"Đạt":"Không đạt"}</span></td></tr>`).join("") : '<tr><td colspan="6" class="empty-cell">Chưa có kết quả phù hợp. Chạy kiểm thử để thu bằng chứng.</td></tr>';
  $$("[data-result-detail]").forEach(row=>row.addEventListener("click",()=>showDetails(rows[Number(row.dataset.resultDetail)].raw)));
  $("#run-passed").textContent=state.rows.length ? state.rows.map(normalizeResult).filter(r=>r.passed).length : "—";
  $("#run-failed").textContent=state.rows.length ? state.rows.map(normalizeResult).filter(r=>!r.passed).length : "—";
  $("#run-total").textContent=state.rows.length || "—";
}

function setBusy(busy) {
  state.busy=busy;
  guidedBusy(busy);managementBusy(busy);
  ["run-standard","run-custom","reset-lab","backup-lab","restore-lab","send-request","save-cases","restore-cases"].forEach(id=>{$(`#${id}`).disabled=busy;});
  $$("[data-fault]").forEach(el=>el.disabled=busy);
  $("#edit-form button[type=submit]").disabled=busy;
}

async function startTask(path, payload={}) {
  if(state.busy)throw new Error("Một tác vụ đang chạy; đợi hoàn thành trước khi thay đổi môi trường.");
  const job=await api(path,{method:"POST",body:JSON.stringify(payload)});
  setBusy(true);
  if(job.kind==="lesson"){beginGuidedJob(job);}
  else if(job.kind==="suite"){
    state.job=job;state.rows=[];renderResults();navigate("tests");
    $("#run-title").textContent="Đang thực thi bộ kiểm chứng";
    $("#run-caption").textContent=`Mã tác vụ ${job.id} · mỗi kết quả đến từ một yêu cầu thực tế`;
    $("#run-progress").classList.add("running");
    $("#run-events").classList.remove("hidden");
    $$(".export").forEach(el=>el.disabled=true);
  }else {$("#operation-summary").textContent="Tác vụ vận hành đang thực hiện. Đợi hoàn thành trước khi thay đổi tiếp.";$("#operation-result").textContent=`Đang thực hiện ${job.kind}…\nMã tác vụ ${job.id}`;}
  pollTask(job.id);
  return job;
}

async function pollTask(id) {
  let transientErrors=0;
  for(;;){
    let job;
    try{job=await api(`/lab/tasks/${encodeURIComponent(id)}`);transientErrors=0;}
    catch(error){transientErrors++;if(transientErrors>=10){setBusy(false);toast(`Không thể theo dõi tác vụ: ${error.message}. Tác vụ có thể vẫn đang chạy.`,true);return;}await new Promise(r=>setTimeout(r,1500));continue;}
    const events=job.events||[];
    if(job.kind==="lesson")renderGuidedJob(job);
    if(job.kind==="suite"){
      state.job=job;
      $("#run-events").textContent=events.slice(-12).map(event=>`${new Date((event.time||Date.now()/1000)*1000).toLocaleTimeString("vi-VN",{hour12:false})} · ${event.message||event.id||event.case_id||JSON.stringify(event)}`).join("\n");
      $("#run-events").scrollTop=$("#run-events").scrollHeight;
      const partial=events.filter(event=>event.result&&typeof event.result==="object").map(event=>event.result);
      if(partial.length){state.rows=partial;renderResults();}
    }
    if(["completed","failed"].includes(job.status)){
      setBusy(false);
      if(job.kind==="lesson"){renderGuidedJob(job);}
      else if(job.kind==="suite"){
        const result=job.result||{};state.rows=Array.isArray(result)?result:result.results||result.cases||[];
        renderResults();$("#run-progress").classList.remove("running");$("#run-progress").style.width=job.status==="completed"?"100%":"0";
        $("#run-title").textContent=job.status==="completed"?"Đã hoàn thành kiểm chứng":"Lần chạy dừng do lỗi";
        $("#run-caption").textContent=job.error||`Mã ${job.id} · ${((job.finished_at-job.started_at)||0).toFixed(1)} giây · nhấp một hàng để xem bằng chứng`;
        $$(".export").forEach(el=>el.disabled=false);
      }else {$("#operation-result").textContent=pretty(job.error?{status:job.status,error:job.error}:job.result);$("#operation-summary").textContent=job.error?"Tác vụ chưa hoàn thành: "+job.error:job.kind==="restore"?"Đã kiểm chứng phục hồi trên môi trường cô lập; hệ thống chính không bị thay thế.":job.kind==="backup"?"Đã tạo bản sao dữ liệu và khóa. Có thể chọn bản sao để thử phục hồi cô lập.":job.kind==="reset"?"Đã đưa dữ liệu lab về bộ mẫu ban đầu.":"Đã áp dụng thay đổi môi trường. Có thể gửi yêu cầu để kiểm tra.";}
      toast(job.status==="completed"?`Đã hoàn thành tác vụ ${job.kind}.`:`Tác vụ lỗi: ${job.error}`,job.status!=="completed");
      await refreshState(true);return;
    }
    await new Promise(resolve=>setTimeout(resolve,800));
  }
}

async function loadCases(){const result=await api("/lab/cases");$("#cases-json").value=pretty(result.cases);$("#cases-status").textContent=result.custom?"Bộ tùy chỉnh đã lưu":"Bộ chuẩn từ fixtures/cases.json";}

function confirmDialog(title,message){return new Promise(resolve=>{const dialog=$("#confirm-dialog");$("#confirm-title").textContent=title;$("#confirm-message").textContent=message;const cleanup=(accepted)=>{dialog.close();$("#confirm-ok").onclick=null;$("#confirm-cancel").onclick=null;resolve(accepted);};$("#confirm-ok").onclick=()=>cleanup(true);$("#confirm-cancel").onclick=()=>cleanup(false);dialog.oncancel=()=>cleanup(false);dialog.showModal();});}

function wireEvents(){
  $$("[data-view]").forEach(el=>el.addEventListener("click",()=>navigate(el.dataset.view)));
  $$("[data-go]").forEach(el=>el.addEventListener("click",()=>navigate(el.dataset.go)));
  $("#refresh").addEventListener("click",()=>action($("#refresh"),()=>refreshState()));
  $("#refresh-audit").addEventListener("click",()=>action($("#refresh-audit"),()=>refreshState()));
  $("#logout-button").addEventListener("click",async()=>{try{await api("/auth/logout",{method:"POST"});state.auth=null;renderAuth();toast("Đã đăng xuất.");}catch(error){toast(error.message,true);}});
  $("#mobile-auth").addEventListener("click",async()=>{if(!state.auth){window.location.href="/auth/login";return;}try{await api("/auth/logout",{method:"POST"});state.auth=null;renderAuth();toast("Đã đăng xuất.");}catch(error){toast(error.message,true);}});
  $("#identity-source").addEventListener("change",()=>{renderAuth();updateRequestForm();if($("#identity-source").value==="interactive"&&!state.auth)toast("Dùng nút Đăng nhập ở thanh bên để tiếp tục.");});
  $$("#request-form select, #request-form input, #request-form textarea").forEach(el=>el.addEventListener("change",updateRequestForm));
  $("#request-form").addEventListener("submit",sendRequest);
  $("#copy-response").addEventListener("click",async()=>{try{await navigator.clipboard.writeText($("#response-json").textContent);toast("Đã sao chép bằng chứng phản hồi.");}catch{toast("Trình duyệt không cho phép sao chép tự động.",true);}});
  $("#download-content").addEventListener("click",()=>{const r=state.response;if(!r?.content_b64)return;const bytes=Uint8Array.from(atob(r.content_b64),c=>c.charCodeAt(0));const id=decodeURIComponent(r.request?.path?.match(/\/documents\/([^/]+)\/download/)?.[1]||"document").replace(/[^\w.-]/g,"_");const title=toArray(state.data.documents).find(doc=>doc.id===id)?.title;const name=title ? title.replace(/[\\/:*?"<>|\x00-\x1f]/g,"_") : `${id}.bin`;downloadBlob(name,new Blob([bytes],{type:r.content_type||"application/octet-stream"}));});
  $("#edit-kind").addEventListener("change",()=>{ $("#edit-patch").value=pretty(patchOptions($("#edit-kind").value)[0][1]); renderEditOptions();});
  $("#edit-id").addEventListener("change",updateGrantEditor);
  $("#edit-form").addEventListener("submit",event=>{event.preventDefault();action($("#edit-form button[type=submit]"),async()=>{if(state.busy)throw new Error("Đợi tác vụ đang chạy hoàn thành.");const id=$("#edit-id").value;if(!id)throw new Error("Chưa có đối tượng để chỉnh sửa.");const kind=$("#edit-kind").value;const patch=JSON.parse($("#edit-patch").value);let result;if(kind==="grant"&&id==="__new__"){result=await api("/lab/request",{method:"POST",body:JSON.stringify({username:"secadmin",mode:"B1",method:"POST",path:"/admin/grants",json:patch})});if(!result.ok)throw new Error(`API cấp grant từ chối: HTTP ${result.status} · ${result.reason||result.error||pretty(result.payload)}`);}else result=await api("/lab/edit",{method:"POST",body:JSON.stringify({kind,id,patch})});$("#operation-result").textContent=pretty(result);$("#operation-summary").textContent=`Đã áp dụng thay đổi cho ${id}. Trạng thái hiện tại đã được làm mới; sang Tự thử yêu cầu để kiểm tra tác dụng.`;toast("Đã cập nhật trạng thái vận hành.");await refreshState();});});
  $("#state-table-kind").addEventListener("change",renderRegistry);
  $("#backup-lab").addEventListener("click",()=>action($("#backup-lab"),()=>startTask("/lab/backup")));
  $("#restore-lab").addEventListener("click",()=>action($("#restore-lab"),async()=>{const id=$("#restore-snapshot").value;if(!id)throw new Error("Tạo hoặc chọn một snapshot trước khi phục hồi.");if(await confirmDialog("Kiểm chứng phục hồi trong môi trường cô lập?","Hệ thống dựng PostgreSQL và OpenBao tạm, khôi phục snapshot, kiểm tra nội dung và đối chiếu quyền thu hồi cùng tombstone. Dữ liệu hoạt động không bị thay thế. Tài nguyên tạm được dọn sau kiểm chứng."))await startTask("/lab/restore",{snapshot_id:id});}));
  $("#reset-lab").addEventListener("click",()=>action($("#reset-lab"),async()=>{if(await confirmDialog("Đặt lại dữ liệu lab?","Tài liệu tải lên và lịch sử truy cập sẽ được thay bằng dữ liệu ban đầu. Tài khoản đã thêm được giữ lại."))await startTask("/lab/reset");}));
  $("#run-standard").addEventListener("click",()=>action($("#run-standard"),()=>startTask("/lab/runs",{use_defaults:true})));
  $("#run-custom").addEventListener("click",()=>action($("#run-custom"),()=>startTask("/lab/runs",{cases:JSON.parse($("#cases-json").value)})));
  $("#load-cases").addEventListener("click",()=>action($("#load-cases"),loadCases));
  $("#save-cases").addEventListener("click",()=>action($("#save-cases"),async()=>{await api("/lab/cases",{method:"PUT",body:JSON.stringify({cases:JSON.parse($("#cases-json").value)})});$("#cases-status").textContent="Đã lưu bộ tùy chỉnh";toast("Đã lưu bộ kiểm thử.");}));
  $("#restore-cases").addEventListener("click",()=>action($("#restore-cases"),async()=>{await api("/lab/cases",{method:"DELETE"});await loadCases();toast("Đã nạp lại bộ kiểm thử chuẩn.");}));
  $("#import-cases").addEventListener("change",async(event)=>{try{const file=event.target.files[0];if(!file)return;if(file.size>2_000_000)throw new Error("File tối đa 2 MB.");$("#cases-json").value=pretty(JSON.parse(await file.text()));$("#cases-status").textContent="Đã nhập file; chưa lưu";}catch(error){toast(error.message,true);}});
  $("#export-cases").addEventListener("click",()=>{try{downloadBlob("bmdl-custom-cases.json",pretty(JSON.parse($("#cases-json").value)));}catch(error){toast(error.message,true);}});
  $("#add-case").addEventListener("click",()=>{try{const parsed=JSON.parse($("#cases-json").value||"[]");const rows=Array.isArray(parsed)?parsed:parsed.cases;if(!Array.isArray(rows))throw new Error("JSON cần là array hoặc object có trường cases.");const example=rows.length?JSON.parse(JSON.stringify(rows[0])):{username:"alice",method:"GET",path:"/documents/A-I01/metadata",expected_status:200,mode:"B1"};example.id=`CUSTOM-${Date.now().toString().slice(-6)}`;example.title="Tình huống tự thiết kế";rows.push(example);$("#cases-json").value=pretty(parsed);$("#cases-status").textContent="Đã thêm tình huống; sửa điều kiện và kỳ vọng trước khi chạy";}catch(error){toast(error.message,true);}});
  $("#result-search").addEventListener("input",renderResults);$("#result-filter").addEventListener("change",renderResults);
  $$(".export").forEach(button=>button.addEventListener("click",()=>{if(state.job)window.location.href=`/lab/export/${encodeURIComponent(state.job.id)}/${button.dataset.format}`;}));
  $("#audit-search").addEventListener("input",renderAudit);
  $("#close-details").addEventListener("click",()=>$("#detail-dialog").close());
}

async function boot(){
  wireEvents();wireGuidedEvents();wireManagement();renderFaults();
  setOptions($("#request-user"),users.map(user=>({value:user,label:user})));
  DemoLanguage.modeOptions($("#request-mode"));
  navigate(location.hash.slice(1)||"documents");
  try{const bootstrap=await api("/lab/bootstrap");state.csrf=bootstrap.csrf;state.auth=bootstrap.auth;renderAuth();if(new URLSearchParams(location.search).get("auth")==="success")toast("Đã đăng nhập.");}
  catch(error){toast(`Không khởi tạo được console: ${error.message}`,true);}
  try{state.catalog=await api("/lab/dataset");renderClassificationRules();}
  catch(error){$("#classification-rules").textContent="Chưa đọc được mô tả tập dữ liệu mẫu.";}
  await refreshState();
  try{await initGuided();}catch(error){$("#lesson-status").textContent="Chưa tải được bài thử: "+error.message;}
  try{await loadCases();}catch(error){$("#cases-json").value="[]";$("#cases-status").textContent=error.message;}
  try{const history=await api("/lab/tasks");const running=history.items.find(job=>["running","queued"].includes(job.status));if(running){setBusy(true);if(running.kind==="suite"){state.job=running;navigate("tests");$("#run-progress").classList.add("running");$("#run-events").classList.remove("hidden");}if(running.kind==="lesson"){navigate("guide");renderGuidedJob(running);}pollTask(running.id);}else{guided.history=history.items.filter(job=>job.kind==="lesson"&&job.status==="completed");renderSelectedLesson();const recent=history.items.find(job=>job.kind==="suite"&&job.status==="completed");if(recent){state.job=recent;state.rows=recent.result?.results||[];renderResults();$("#run-title").textContent="Kết quả lần chạy gần nhất";$("#run-caption").textContent=`Mã tác vụ ${recent.id}`;$$(".export").forEach(el=>el.disabled=false);}}}catch(error){console.warn("Không đọc được lịch sử tác vụ",error);}
  guided.ready=true;guidedBusy(state.busy);
  setInterval(()=>{if(!state.busy&&document.visibilityState==="visible")refreshState(true);},20000);
}

boot();
