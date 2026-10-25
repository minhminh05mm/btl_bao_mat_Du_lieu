"use strict";

const guided = {catalog:[], selected:"owner", job:null, history:[], ready:false};
const reasonText = {
  ALLOW:"Các điều kiện của thao tác đã được đáp ứng.",
  OWNER_OR_LABEL:"Tài khoản không đáp ứng quyền theo chủ sở hữu hoặc mức nhạy cảm của tài liệu.",
  DEPARTMENT:"Tài liệu thuộc phòng ban khác với phạm vi được cấp quyền.",
  ROLE:"Vai trò này không có quyền thực hiện hành động đã chọn.",
  INACTIVE:"Tài khoản đang bị khóa. Mở Nhân viên để kích hoạt lại hoặc chọn tài khoản khác.",
  DEVICE_MISMATCH:"Chứng thư thiết bị không khớp tài khoản đang gửi yêu cầu.",
  DEVICE_REVOKED:"Thiết bị đã bị thu hồi.", NONCOMPLIANT:"Thiết bị không đạt điều kiện tuân thủ.",
  RISK_HIGH:"Thiết bị đang có tín hiệu rủi ro cao.",
  MISSING_OR_STALE:"Thông tin thiết bị thiếu, quá cũ hoặc có thời điểm không hợp lệ.",
  RESTRICTED_GRANT:"Tải tài liệu hạn chế cần phê duyệt còn hạn, đúng người, tài liệu, phiên bản và hành động.",
  RETENTION_ACTIVE:"Tài liệu chưa hết thời hạn lưu giữ nên chưa được xóa.",
  RETENTION_EXPIRED:"Tài liệu đã hết thời hạn được đọc trong nghiệp vụ.",
  LEGAL_HOLD:"Tài liệu đang được giữ để bảo toàn nên chưa được xóa.",
  NOT_FOUND:"Không tìm thấy tài liệu/đối tượng, hoặc tài liệu đã bị đánh dấu xóa.",
  INVALID_TOKEN:"Không xác thực được thông tin đăng nhập của yêu cầu.",
  PDP_UNAVAILABLE:"Dịch vụ đánh giá chính sách không sẵn sàng; dữ liệu chưa được cấp.",
  KMS_UNAVAILABLE:"Dịch vụ mật mã không sẵn sàng nên không thể cấp bản rõ.",
  AUDIT_UNAVAILABLE:"Không ghi được nhật ký bắt buộc nên thao tác chưa được cho phép hoàn tất.",
  REGISTRY_UNAVAILABLE:"Không lấy được quyền và thuộc tính hiện tại để quyết định.",
  PDP_INVALID:"Phản hồi đánh giá chính sách không hợp lệ nên hệ thống dừng thao tác.",
  INTEGRITY_FAILURE:"Kiểm tra bản mã hoặc nội dung thất bại; dữ liệu chưa được cấp.",
  TRANSPORT_ERROR:"Chưa gửi/nhận được yêu cầu. Kiểm tra dịch vụ, kết nối và chứng thư.",
  TRANSPORT_BLOCKED:"Yêu cầu bị lỗi kết nối hoặc TLS; cần đọc bằng chứng kỹ thuật.",
};

function explainResponse(r) {
  let title=r.ok?"Yêu cầu được chấp nhận":"Yêu cầu chưa được chấp nhận";
  if(!r.ok)title=Number(r.status)===403?"Yêu cầu bị chặn theo chính sách":Number(r.status)===404?"Không tìm thấy đối tượng yêu cầu":Number(r.status)===401?"Yêu cầu chưa xác thực hợp lệ":"Chưa thể hoàn tất yêu cầu";
  let explanation=friendlyFailure(r);
  const path=r.request?.path||"";
  if(r.ok && path.includes("/download")) {
    title="Được tải nội dung tài liệu";
    explanation=`Tài liệu đã sẵn sàng. Chọn Lưu nội dung để tải về máy.`;
  } else if(r.ok && path.startsWith("/audit")) {
    title="Đã đọc nhật ký thành công";
    explanation=`Có ${r.payload?.items?.length||0} sự kiện truy cập.`;
  } else if(r.ok && path.startsWith("/alerts")) {
    title="Đã đọc cảnh báo thành công";
    const n=r.payload?.items?.length||0;
    explanation=n?`Có ${n} cảnh báo trong kết quả.`:"Hiện chưa có cảnh báo.";
  } else if(r.ok && path==="/documents" && r.request?.method==="GET") {
    title="Đã đọc danh sách theo quyền";
    explanation=`Có ${r.payload?.items?.length||0} tài liệu trong kết quả đã lọc. `;
  } else if(r.ok && r.request?.method==="DELETE" && path.startsWith("/documents/")) {
    title="Đã xóa tài liệu";
    explanation="Tài liệu không còn được cung cấp cho các yêu cầu truy cập.";
  } else if(r.ok && path==="/me") {
    title=`Danh tính đang dùng: ${r.payload?.username||r.payload?.id||r.request?.username||""}`;
    explanation="";
  }
  if(r.ok && r.request?.method==="POST" && path==="/documents"){title="Đã thêm tài liệu";explanation=`${r.payload?.title||"Tài liệu"} đã được lưu vào kho.`;}
  return {title,explanation};
}

function renderHumanResponse(r) {
  const target=document.querySelector("#human-response");
  if(!target)return;
  const summary=explainResponse(r);
  target.className=`human-response ${r.ok?"accepted":"blocked"}`;
  target.innerHTML=`<h3>${escapeHTML(summary.title)}</h3><p>${escapeHTML(summary.explanation)}</p>`;
}

async function initGuided() {
  const response=await api("/lab/lessons");
  guided.catalog=response.items||[];
  renderLessonMenu();renderSelectedLesson();
}

function renderLessonMenu() {
  $("#lesson-list").innerHTML=guided.catalog.map((item,i)=>`<button class="lesson-choice ${guided.selected===item.id?"selected":""}" data-lesson="${escapeHTML(item.id)}"><span class="lesson-index">${i+1}</span><span><small>${escapeHTML(item.category)}</small><strong>${escapeHTML(item.title)}</strong></span></button>`).join("");
  $$('[data-lesson]').forEach(button=>button.addEventListener("click",()=>{
    if(state.busy){toast("Đợi bài đang chạy hoàn thành trước khi chọn bài khác.");return;}
    guided.selected=button.dataset.lesson;renderLessonMenu();renderSelectedLesson();
  }));
  guidedBusy(state.busy);
}

function renderSelectedLesson() {
  const lesson=guided.catalog.find(x=>x.id===guided.selected);
  if(!lesson)return;
  $("#lesson-title").textContent=lesson.title;
  $("#lesson-question").textContent=lesson.question;
  $("#lesson-expected").textContent=lesson.expected;
  $("#lesson-changes").textContent=lesson.changes;
  $("#lesson-core").textContent=lesson.core;
  $("#lesson-compare-control").classList.toggle("hidden",!lesson.compare);
  $("#lesson-compare").checked=false;
  $("#lesson-run").textContent="Chạy bài thử và xem từng bước";
  if(guided.job?.result?.lesson?.id!==lesson.id && guided.job?.lesson_id!==lesson.id) {
    guided.job=guided.history.find(x=>x.result?.lesson?.id===lesson.id)||null;
  }
  if(guided.job?.result?.lesson?.id===lesson.id || guided.job?.lesson_id===lesson.id)renderGuidedJob(guided.job);
  else {
    $("#lesson-status").textContent="Chưa chạy bài này. Đọc điều kiện và kết quả mong đợi trước khi bắt đầu.";
    $("#lesson-steps").innerHTML="";
    $("#lesson-export").classList.add("hidden");
    $("#lesson-status").className="lesson-status";
  }
}

function beginGuidedJob(job) {
  job.lesson_id=guided.selected;guided.job=job;
  navigate("guide");renderGuidedJob(job);
}

function readableEvidence(step) {
  const a=step.actual||{};
  let lines=[];
  if(step.kind==="inspection" && "plaintext_present" in a) {
    lines=[a.plaintext_present?"Phát hiện bản rõ trong phép kiểm tra kho.":"Không tìm thấy nội dung mẫu ở dạng bản rõ trong bản quét cơ sở dữ liệu.",
      a.key_material_present?"Phát hiện vật liệu khóa trong bản quét.":"Không tìm thấy vật liệu khóa được kiểm tra trong cơ sở dữ liệu.",
      a.app_kms_admin_allowed?"Ứng dụng có thao tác quản trị khóa được chấp nhận.":"Các yêu cầu ứng dụng đọc, xoay và xuất khóa đều bị từ chối."];
    if(a.ciphertext_preview)lines.push("Dữ liệu quan sát được là bản mã; có thể xem một đoạn trong bằng chứng kỹ thuật.");
  } else if(step.kind==="inspection" && "before_sha256" in a) {
    lines=[a.before_sha256 && a.before_sha256===a.after_sha256 && a.before_sha256===a.stored_sha256?"Nội dung tải trước và sau khi khôi phục trùng nhau, khớp dấu kiểm tra SHA-256 đang lưu.":"Dấu kiểm tra nội dung chưa khớp hoặc thiếu kết quả tải."];
  } else if(step.kind==="inspection" && "matched" in a) {
    lines=[`Tìm thấy ${Number(a.matched)} / ${Number(a.expected)} yêu cầu trong nhật ký theo mã nhận diện riêng.`];
  } else if(step.kind==="inspection" && "matching_alerts" in a) {
    lines=[`Tìm thấy ${Number(a.matching_alerts)} cảnh báo của ${a.principal_id} trong cửa sổ 60 giây.`];
  } else if(step.kind==="backup") {
    lines=[`Đã lưu ${Array.isArray(a.files)?a.files.length:0} tệp trong cặp sao lưu dữ liệu và khóa.`,
      a.encrypted===true?"Kho sao lưu được mã hóa.":"Chưa xác nhận mã hóa kho sao lưu.",
      a.repository_verified===true?"Đã kiểm tra kho sao lưu thành công.":"Chưa xác nhận kiểm tra kho sao lưu."];
  } else if(step.kind==="recovery") {
    lines=[`Đã xác minh nội dung của ${Number(a.verified_documents||0)} tài liệu trong môi trường phục hồi.`,
      `Đã áp dụng ${Number(a.reconciliation?.events_applied||0)} sự kiện quản trị sau thời điểm bản sao.`,
      a.primary_replaced===false?"Hệ thống chính được giữ nguyên.":"Chưa xác nhận hệ thống chính được giữ nguyên.",
      a.temporary_resources_removed===true?"Tài nguyên phục hồi tạm đã được dọn.":"Cần kiểm tra tài nguyên phục hồi tạm còn lại."];
  } else if(step.kind==="cleanup") {
    lines=[a.restored===true?"Các thuộc tính bài thử thay đổi đã được khôi phục.":"Một số thuộc tính chưa được khôi phục; xem lỗi bên dưới."];
  }
  return lines.length?`<div class="step-outcome evidence-facts">${lines.map(line=>`<span>${escapeHTML(line)}</span>`).join("")}</div>`:"";
}

function renderGuidedJob(job) {
  guided.job=job;
  if(job.status==="completed" && job.result)guided.history=[job,...guided.history.filter(x=>x.id!==job.id)];
  const result=job.result;
  const lesson=result?.lesson || guided.catalog.find(x=>x.id===job.lesson_id);
  if(lesson && guided.selected!==lesson.id) {
    guided.selected=lesson.id;renderLessonMenu();
    $("#lesson-title").textContent=lesson.title;$("#lesson-question").textContent=lesson.question;
    $("#lesson-expected").textContent=lesson.expected;$("#lesson-changes").textContent=lesson.changes;$("#lesson-core").textContent=lesson.core;
    $("#lesson-compare-control").classList.toggle("hidden",!lesson.compare);
  }
  const steps=result?.steps || (job.events||[]).filter(x=>x.step).map(x=>x.step);
  const pending=["queued","running"].includes(job.status);
  const ok=result?.passed===true && job.status==="completed";
  $("#lesson-status").className=`lesson-status ${pending?"running":ok?"success":"attention"}`;
  $("#lesson-status").textContent=pending?`Đang chạy: đã ghi nhận ${steps.length} bước. Có thể xem kết quả đến đâu hiện đến đó.`:ok?"Bài thử hoàn thành: các kiểm tra khớp kỳ vọng, thuộc tính thử nghiệm đã được khôi phục.":`Bài thử có bước chưa đạt. ${job.error||"Đọc bước được đánh dấu bên dưới; không coi lỗi dịch vụ ngoài dự kiến là kết quả đạt."}`;
  const kindNames={setup:"Chuẩn bị thí nghiệm",request:"Yêu cầu qua gateway",inspection:"Đối chiếu bằng chứng",backup:"Sao lưu thật",recovery:"Phục hồi cô lập",cleanup:"Khôi phục sau bài",error:"Lỗi thực thi"};
  $("#lesson-steps").innerHTML=steps.map(step=>{
    const a=step.actual||{};
    let outcome="";
    if(step.kind==="request") {
      outcome=`<div class="step-outcome"><b>${a.status>=200&&a.status<300?"Được chấp nhận":"Bị chặn / chưa hoàn tất"}</b><span>${escapeHTML(reasonText[a.reason]||a.reason||"Xem bằng chứng chi tiết.")}</span>${a.content_released?'<span>Nội dung tài liệu đã được cấp; bằng chứng lưu hash, không lưu bản rõ.</span>':a.path?.includes('/download')?'<span>Không cấp nội dung tài liệu.</span>':""}</div>`;
    }
    outcome+=readableEvidence(step);
    const expected=step.expected?`<p><strong>Mong đợi:</strong> HTTP ${escapeHTML(step.expected.status)}${step.expected.reason?` · ${escapeHTML(step.expected.reason)}`:""}</p>`:"";
    return `<article class="lesson-step ${step.passed?"step-pass":"step-fail"}"><div class="step-heading"><span class="step-number">${step.number}</span><div><small>${escapeHTML(kindNames[step.kind]||step.kind)}</small><h3>${escapeHTML(step.title)}</h3></div><span class="step-verdict">${step.passed?(step.kind==="setup"||step.kind==="cleanup"?"Đã thực hiện":"Đúng kỳ vọng"):"Chưa đạt"}</span></div><p>${escapeHTML(step.explanation)}</p>${outcome}${expected}<details class="technical"><summary>Xem bằng chứng kỹ thuật${a.request_id?" và Request ID":""}</summary><pre class="code">${escapeHTML(pretty(a))}</pre></details></article>`;
  }).join("");
  $("#lesson-export").classList.toggle("hidden",pending||!result);
}

function guidedBusy(busy) {
  const blocked=busy||!guided.ready;
  const run=document.querySelector('#lesson-run');if(run)run.disabled=blocked;
  const compare=document.querySelector('#lesson-compare');if(compare)compare.disabled=blocked;
  $$('[data-lesson]').forEach(x=>x.disabled=blocked);
}

function wireGuidedEvents() {
  $("#lesson-run").addEventListener("click",()=>action($("#lesson-run"),async()=>{
    const lesson=guided.catalog.find(x=>x.id===guided.selected);
    if(!lesson)throw new Error("Chưa đọc được bài thử.");
    if(["lifecycle","encryption","recovery"].includes(lesson.id)) {
      const accepted=await confirmDialog("Chạy bài thử trên kho demo?",lesson.changes+" Các thuộc tính bài thay đổi được khôi phục khi kết thúc; nhật ký và bằng chứng được giữ.");
      if(!accepted)return;
    }
    await startTask(`/lab/lessons/${encodeURIComponent(lesson.id)}/run`,{compare:$("#lesson-compare").checked});
  }));
  $("#lesson-export").addEventListener("click",()=>{
    if(guided.job?.result)downloadBlob(`${guided.job.result.run_id}.json`,pretty(guided.job.result));
  });
  ["#grant-user","#grant-document","#grant-minutes"].forEach(id=>$(id).addEventListener("change",()=>{
    $("#edit-patch").value=pretty({principal_id:$("#grant-user").value,doc_id:$("#grant-document").value,ttl_seconds:Number($("#grant-minutes").value)*60});
    renderPatchSummary();
  }));
  $("#edit-patch").addEventListener("input",renderPatchSummary);
}

function renderPatchSummary() {
  const target=document.querySelector('#edit-change-summary');if(!target)return;
  try {
    const patch=JSON.parse($("#edit-patch").value||"{}");
    const names={active:"Tài khoản hoạt động",role:"Vai trò",department:"Phòng ban",compliant:"Thiết bị tuân thủ",revoked:"Đã thu hồi",risk:"Rủi ro",observed_at:"Thời điểm tín hiệu",risk_at:"Thời điểm rủi ro",auto_refresh:"Tự làm mới tín hiệu",label:"Nhãn",retention_until:"Hạn lưu giữ",legal_hold:"Giữ tài liệu khỏi xóa",expires_at:"Hạn phê duyệt",principal_id:"Người được phê duyệt",doc_id:"Tài liệu",ttl_seconds:"Hiệu lực (giây)"};
    target.textContent="Chưa áp dụng. Thay đổi sắp gửi: "+Object.entries(patch).map(([k,v])=>`${names[k]||k}: ${typeof v==="boolean"?(v?"Có":"Không"):["observed_at","risk_at","retention_until","expires_at"].includes(k)?timeLabel(v):v}`).join(" · ")+". Bấm Áp dụng trạng thái để thực hiện.";
  } catch {target.textContent="JSON nâng cao chưa hợp lệ. Sửa dữ liệu trước khi áp dụng.";}
}
