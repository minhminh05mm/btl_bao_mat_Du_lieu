"""Guided experiments for the trusted local console; never a business API."""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path

from . import operations as ops
from .client import LabClient

LESSONS = [
    dict(id="owner", title="Ai được đọc tài liệu của Anna?", category="Quyền đọc", question="Cùng phòng có đủ quyền đọc một tài liệu mật không?", expected="Alice bị chặn; trưởng phòng Adam được đọc.", changes="Chuẩn bị Alice, Adam và tài liệu A-C02 theo điều kiện bài; thử tải cùng tài liệu.", core="Phân quyền theo vai trò, phòng ban, chủ sở hữu và nhãn.", compare=True),
    dict(id="revocation", title="Đăng nhập rồi có giữ quyền mãi không?", category="Quyền hiện tại", question="Nếu Alice bị thu hồi quyền khi token còn hạn thì sao?", expected="Yêu cầu mới dùng cùng token bị chặn sau thu hồi.", changes="Tạm thu hồi active của Alice qua API secadmin rồi khôi phục thuộc tính sau bài.", core="Đánh giá quyền hiện tại ở từng yêu cầu; phân biệt xác thực và cấp quyền.", compare=True),
    dict(id="device", title="Có phê duyệt nhưng thiết bị không phù hợp", category="Thiết bị", question="Grant hợp lệ có bỏ qua rủi ro hoặc chứng thư sai không?", expected="Thiết bị bình thường được đọc; sai chứng thư hoặc rủi ro cao bị chặn.", changes="Tạo grant 5 phút cho Brian tải B-R02; tạm đổi risk của thiết bị mẫu rồi khôi phục. Grant của bài được thu hồi khi kết thúc.", core="Ràng buộc danh tính với chứng thư; kết hợp grant và trạng thái thiết bị giả lập.", compare=True),
    dict(id="encryption", title="Kho lưu bản gì khi người dùng tải tài liệu?", category="Mã hóa", question="Nội dung được lưu dưới dạng bản mã và điều gì xảy ra khi dịch vụ khóa dừng?", expected="Kho không chứa bản rõ của fixture; dừng OpenBao làm yêu cầu tải bị chặn; khôi phục thì tải lại đúng hash.", changes="Kiểm tra kho bằng quyền operator; dừng OpenBao thật trong thời gian ngắn rồi khởi động và unseal lại.", core="Mã hóa qua Transit, giới hạn quyền khóa, kiểm tra hash và mặc định từ chối.", compare=False),
    dict(id="audit", title="Ai ghi nhận các lần truy cập bị chặn?", category="Nhật ký và cảnh báo", question="Năm lần Alice truy cập ngoài quyền có dấu vết và cảnh báo không?", expected="Cả 5 yêu cầu bị chặn, tìm được Request ID trong audit và cảnh báo của Alice.", changes="Gửi 5 yêu cầu thật. Nhật ký và cảnh báo phát sinh được giữ để quan sát; không đặt lại dữ liệu lab.", core="Liên kết phản hồi với audit; cảnh báo theo ngưỡng 5 lần từ chối trong 60 giây.", compare=False),
    dict(id="lifecycle", title="Khi nào được đọc và được xóa tài liệu?", category="Vòng đời dữ liệu", question="Hết hạn đọc và legal hold ảnh hưởng việc xóa như thế nào?", expected="Chưa hết hạn không được xóa; hết hạn bị chặn đọc; legal hold chặn xóa; xóa hợp lệ tạo tombstone.", changes="Tạm đổi thời hạn và legal hold của A-I01; thực hiện xóa logic trong DB demo rồi hoàn tác thuộc tính thử nghiệm. Không xóa file nguồn trên máy.", core="Lưu giữ, bảo toàn tài liệu, xóa logic và dấu vết phục hồi.", compare=False),
    dict(id="recovery", title="Bản sao cũ có làm sống lại quyền đã thu hồi?", category="Sao lưu và phục hồi", question="Phục hồi snapshot trước lúc Alice bị thu hồi quyền có bỏ sót thay đổi mới không?", expected="DB và khóa phục hồi cô lập; hash đúng; quyền thu hồi được đối chiếu. Primary không bị thay thế.", changes="Tạo snapshot thật, tạm thu hồi Alice, dựng DB/KMS tạm để kiểm tra rồi dọn tài nguyên. API tạm dừng khi lấy cặp backup; snapshot và bằng chứng được giữ.", core="Snapshot dữ liệu/khóa nhất quán; đối chiếu ledger; phục hồi cô lập.", compare=False),
]


def catalog():
    return LESSONS


def run(lesson_id, compare=False, progress=None):
    lesson = next((item for item in LESSONS if item['id'] == lesson_id), None)
    if not lesson:
        raise ValueError('Unknown lesson')
    run_id = 'lesson-' + time.strftime('%Y%m%d-%H%M%S', time.gmtime()) + '-' + uuid.uuid4().hex[:6]
    steps, changes, grants, stopped, cleanup_errors = [], {}, [], [], []
    started = time.time()
    client = LabClient()

    def record(title, explanation, *, kind='request', passed=True, expected=None, actual=None):
        step = dict(number=len(steps)+1, title=title, explanation=explanation, kind=kind,
                    passed=bool(passed), expected=expected, actual=ops.safe(actual or {}), at=time.time())
        steps.append(step)
        if progress:
            progress({'type':'lesson_step', 'step':step})
        return step

    def row(kind, identifier):
        table = {'principal':'principals','device':'devices','document':'documents'}[kind]
        item = next((r for r in ops.rows(table) if r['id'] == identifier), None)
        if not item:
            raise ValueError(f'Missing fixture: {identifier}')
        return item

    def patch(kind, identifier, values):
        original = row(kind, identifier)
        saved = changes.setdefault((kind, identifier), {})
        for key in values:
            saved.setdefault(key, original[key])
        return ops.edit_state(kind, identifier, values)

    def user(identifier, role, department):
        patch('principal', identifier, dict(active=True, role=role, department=department))
        now = time.time()
        patch('device', 'dev-'+identifier, dict(compliant=True, revoked=False, risk='NORMAL',
              observed_at=now, risk_at=now, auto_refresh=True))

    def document(identifier, label, owner):
        current = row('document', identifier)
        if current['owner_id'] != owner:
            raise ValueError('Owner differs from the fixture required by this lesson')
        patch('document', identifier, dict(label=label, deleted=False,
              retention_until=time.time()+86400, legal_hold=False))

    def request(title, explanation, who, path, status, reason=None, *, method='GET', mode='B1', device=None, token=None, payload=None):
        response = client.request(who, method, path, mode=mode, device=device, token=token, json=payload)
        try:
            body = response.json()
        except ValueError:
            body = {}
        detail = body.get('detail', {}) if isinstance(body, dict) else {}
        observed_reason = response.headers.get('x-policy-reason') or (detail.get('reason') if isinstance(detail, dict) else None)
        actual = dict(status=response.status_code, reason=observed_reason,
                      request_id=response.headers.get('x-request-id') or (detail.get('request_id') if isinstance(detail, dict) else None),
                      username=who, method=method, path=path, mode=mode, device=device or who,
                      bytes=len(response.content), content_released='/download' in path and response.is_success)
        if actual['content_released']:
            actual['sha256'] = hashlib.sha256(response.content).hexdigest()
        if isinstance(body, dict) and isinstance(body.get('items'), list):
            actual['item_count'] = len(body['items'])
        passed = response.status_code == status and (reason is None or reason == observed_reason)
        record(title, explanation, passed=passed, expected=dict(status=status, reason=reason), actual=actual)
        if method in {'POST','PUT'} and not response.is_success:
            raise RuntimeError('Preparation through business API was rejected')
        return response, body, actual

    def grant():
        response, body, _ = request('Secadmin phê duyệt tải trong 5 phút', 'Đây là bước chuẩn bị bằng API cấp grant; không phải Brian tự cấp quyền.',
            'secadmin', '/admin/grants', 200, 'ALLOW', method='POST', payload=dict(principal_id='brian',doc_id='B-R02',ttl_seconds=300))
        identifier = body.get('id') or body.get('grant', {}).get('id')
        if not identifier:
            raise RuntimeError('Grant response did not contain an ID')
        grants.append(identifier)

    with ops.LOCK:
        try:
            services = ops.state()
            unavailable = [r['name'] for r in services['services'] if r['status'] != 'running']
            if unavailable or any(services.get('faults', {}).values()):
                raise RuntimeError('Khôi phục các dịch vụ/cờ lỗi đang bật trong Điều khiển lab trước khi chạy bài.')
            user('secadmin', 'security_admin', 'OPS')
            if lesson_id in {'owner','audit'}:
                user('alice','staff','A'); user('adam','manager','A')
                document('A-C02','confidential','anna')
            elif lesson_id in {'revocation','encryption','lifecycle','recovery'}:
                user('alice','staff','A'); document('A-I01','internal','alice')
            elif lesson_id == 'device':
                user('brian','manager','B'); document('B-R02','restricted','brian')
            if lesson_id == 'audit':
                user('auditor','auditor','OPS')
            record('Chuẩn bị điều kiện của bài', lesson['changes'], kind='setup', actual={'prepared':True})

            if lesson_id == 'owner':
                request('Alice xin tải tài liệu mật của Anna', 'B1 xét chủ sở hữu: cùng phòng chưa đủ quyền cho nhân viên.', 'alice','/documents/A-C02/download',403,'OWNER_OR_LABEL')
                request('Adam tải cùng tài liệu', 'Trưởng phòng cùng phòng được đọc tài liệu mật.', 'adam','/documents/A-C02/download',200,'ALLOW')
                if compare:
                    request('Đối chứng B0: Alice tải cùng tài liệu', 'B0 cố ý chỉ dùng quyền đọc đơn giản hơn; ca này minh họa tác dụng của điều kiện chủ sở hữu.', 'alice','/documents/A-C02/download',200,'ALLOW',mode='B0')
            elif lesson_id == 'revocation':
                same_token = client.token('alice')
                request('Trước thu hồi: Alice tải nội bộ', 'Token và quyền hiện tại đều hợp lệ.', 'alice','/documents/A-I01/download',200,'ALLOW',token=same_token)
                request('Secadmin thu hồi quyền hiện tại của Alice', 'Thay active qua API quản trị; token của Alice vẫn được giữ nguyên trong bài.', 'secadmin','/admin/principals/alice',200,'ALLOW',method='PUT',payload={'active':False})
                request('Gửi lại bằng chính token cũ', 'B1 đọc active hiện tại và chặn yêu cầu mới; không thu hồi các byte đã tải trước đó.', 'alice','/documents/A-I01/download',403,'INACTIVE',token=same_token)
                if compare:
                    request('Đối chứng B0 với token cũ', 'B0 vẫn dùng quyền chụp lúc đăng nhập trên đường đọc được đối chứng.', 'alice','/documents/A-I01/download',200,'ALLOW',mode='B0',token=same_token)
            elif lesson_id == 'device':
                grant()
                request('Brian có grant và thiết bị bình thường', 'Grant gắn với Brian, B-R02 và phiên bản hiện tại.', 'brian','/documents/B-R02/download',200,'ALLOW')
                request('Giữ tài khoản Brian, dùng chứng thư Bob', 'Chứng thư phải khớp chủ thể; grant không thay thế điều kiện này.', 'brian','/documents/B-R02/download',403,'DEVICE_MISMATCH',device='bob')
                patch('device','dev-brian',{'risk':'HIGH'})
                record('Người vận hành đặt tín hiệu rủi ro HIGH', 'Đây là tín hiệu thiết bị mẫu được giả lập phía máy chủ; không phải quét mã độc trên máy thật.',kind='setup',actual={'risk':'HIGH'})
                request('Đúng chứng thư, có grant, nhưng thiết bị HIGH', 'B1 chặn theo rủi ro hiện tại dù quyền tải còn hạn.', 'brian','/documents/B-R02/download',403,'RISK_HIGH')
                if compare:
                    request('Đối chứng B0 khi thiết bị HIGH', 'B0 bỏ qua điều kiện rủi ro trong phép đối chứng này.', 'brian','/documents/B-R02/download',200,'ALLOW',mode='B0')
            elif lesson_id == 'encryption':
                storage = ops.inspect_storage('A-I01')
                proof = {k:v for k,v in storage.items() if k != 'ciphertext'}
                proof['ciphertext_preview'] = str(storage['ciphertext'])[:90]+'…'
                record('Kiểm tra dữ liệu đang lưu bằng quyền operator', 'Chỉ hiện đoạn bản mã và kết quả kiểm tra; không đưa khóa hoặc bản rõ vào bằng chứng.',kind='inspection',passed=not storage['plaintext_present'] and not storage['key_material_present'] and not storage['app_kms_admin_allowed'],actual=proof)
                _,_,before = request('Tải khi dịch vụ khóa sẵn sàng', 'API giải mã theo quyền; bằng chứng chỉ lưu hash và số byte.', 'alice','/documents/A-I01/download',200,'ALLOW')
                stopped.append('openbao'); ops.stop_service('openbao')
                record('Người vận hành dừng OpenBao thật', 'Container dịch vụ khóa bị dừng trong bài; thao tác này ảnh hưởng khả năng giải mã của lab.',kind='setup',actual={'service':'openbao','running':False})
                request('Thử tải khi không có dịch vụ khóa', 'Không cấp bản rõ khi thành phần mật mã bắt buộc không sẵn sàng.', 'alice','/documents/A-I01/download',503,'KMS_UNAVAILABLE')
                ops.start_service('openbao'); stopped.remove('openbao')
                _,_,after = request('Khôi phục OpenBao và tải lại', 'Dịch vụ đã được khởi động và unseal lại.', 'alice','/documents/A-I01/download',200,'ALLOW')
                record('Đối chiếu hash nội dung trước và sau', 'Kiểm tra các lần tải thành công thu được cùng nội dung, khớp hash đang lưu.',kind='inspection',passed=before.get('sha256') == after.get('sha256') == storage['sha256'],actual={'before_sha256':before.get('sha256'),'after_sha256':after.get('sha256'),'stored_sha256':storage['sha256']})
            elif lesson_id == 'audit':
                ids=[]
                for i in range(5):
                    _,_,actual=request(f'Lần truy cập ngoài quyền {i+1}/5', 'Mỗi lần là một yêu cầu thật và có Request ID riêng.', 'alice','/documents/A-C02/download',403,'OWNER_OR_LABEL')
                    ids.append(actual['request_id'])
                _,body,_=request('Auditor đọc nhật ký', 'Đọc audit không đồng nghĩa được tải nội dung tài liệu.', 'auditor','/audit',200,'ALLOW')
                found={r['request_id'] for r in body.get('items',[])}
                record('Tìm dấu vết của cả 5 yêu cầu', 'Đối chiếu Request ID, không suy từ màu hiển thị.',kind='inspection',passed=all(i and i in found for i in ids),actual={'matched':sum(i in found for i in ids),'expected':5,'request_ids':ids})
                _,body,_=request('Auditor đọc cảnh báo', 'Cảnh báo có thể đã tồn tại trong cửa sổ thời gian; kiểm tra có cảnh báo cho Alice, không xóa lịch sử để tạo số mới.', 'auditor','/alerts',200,'ALLOW')
                matching=[r for r in body.get('items',[]) if r.get('principal_id') == 'alice' and r.get('created_at',0) >= time.time()-60]
                record('Kiểm tra cảnh báo theo ngưỡng', 'Lab tổng hợp từ các yêu cầu bị từ chối, không lấy số cảnh báo giả.',kind='inspection',passed=bool(matching),actual={'matching_alerts':len(matching),'principal_id':'alice'})
            elif lesson_id == 'lifecycle':
                # Capture deletion timestamp separately; document versions remain monotonic.
                original_deleted_at=row('document','A-I01').get('deleted_at')
                request('Chưa hết thời hạn: yêu cầu xóa', 'Bị chặn để giữ tài liệu trong thời hạn quy định của lab.', 'alice','/documents/A-I01',403,'RETENTION_ACTIVE',method='DELETE')
                patch('document','A-I01',{'retention_until':time.time()-10,'legal_hold':True})
                request('Hết thời hạn: thử đọc', 'Thời hạn đọc đã hết, dù Alice vẫn sở hữu tài liệu.', 'alice','/documents/A-I01/download',403,'RETENTION_EXPIRED')
                request('Có legal hold: thử xóa', 'Giữ tài liệu để bảo toàn nên chưa được xóa.', 'alice','/documents/A-I01',403,'LEGAL_HOLD',method='DELETE')
                patch('document','A-I01',{'legal_hold':False})
                request('Bỏ hold và xóa logic trong kho demo', 'API đánh dấu deleted và ghi tombstone; file nguồn, bản mã và backup vẫn được giữ.', 'alice','/documents/A-I01',200,'ALLOW',method='DELETE')
                request('Thử đọc tài liệu đã đánh dấu xóa', 'API không phục vụ lại tài liệu này.', 'alice','/documents/A-I01/metadata',404,'NOT_FOUND')
            elif lesson_id == 'recovery':
                snapshot=ops.backup()
                record('Tạo cặp sao lưu dữ liệu và khóa', 'Snapshot thật được giữ trên ổ E. Các API tạm dừng trong khoảng lấy cặp nhất quán.',kind='backup',passed=bool(snapshot.get('snapshot_id')),actual=snapshot)
                request('Thu hồi Alice sau thời điểm snapshot', 'Sự kiện quản trị mới hơn bản sao phải được đối chiếu khi phục hồi.', 'secadmin','/admin/principals/alice',200,'ALLOW',method='PUT',payload={'active':False})
                restored=ops.restore(snapshot['snapshot_id'])
                passed=all(restored.get(k) is True for k in ['isolated','reconciled','contents_verified','pair_hashes_verified','temporary_resources_removed']) and restored.get('primary_replaced') is False
                record('Phục hồi vào DB/KMS riêng và đối chiếu ledger', 'Đây là kiểm chứng trên môi trường cô lập; không thay thế hệ thống đang phục vụ.',kind='recovery',passed=passed,actual=restored)
                request('Kiểm tra quyền hiện tại trên hệ thống chính', 'Ca này kiểm tra primary vẫn chặn Alice; bằng chứng phục hồi cô lập nằm ở bước trước.', 'alice','/documents/A-I01/download',403,'INACTIVE')
        except Exception as error:
            record('Bài thử chưa hoàn thành', str(error)[:350],kind='error',passed=False,actual={'error_type':type(error).__name__})
        finally:
            for service in stopped:
                try: ops.start_service(service)
                except Exception: cleanup_errors.append('Khởi động lại '+service)
            for identifier in grants:
                try: ops.patch_grant(identifier,{'revoked':True})
                except Exception: cleanup_errors.append('Thu hồi grant của bài')
            for (kind,identifier), values in reversed(list(changes.items())):
                try: ops.edit_state(kind,identifier,values)
                except Exception: cleanup_errors.append('Khôi phục '+identifier)
            if lesson_id == 'lifecycle' and 'original_deleted_at' in locals():
                try:
                    with ops.db() as conn:
                        conn.execute('UPDATE documents SET deleted_at=%s WHERE id=%s',(original_deleted_at,'A-I01'))
                except Exception: cleanup_errors.append('Khôi phục mốc xóa của A-I01')
            record('Khôi phục các thuộc tính đã thay đổi', 'Nhật ký, cảnh báo, snapshot, bằng chứng và bộ đếm phiên bản được giữ. Grant mới của bài được thu hồi. Không đặt lại toàn bộ lab.',kind='cleanup',passed=not cleanup_errors,actual={'restored':not cleanup_errors,'errors':cleanup_errors})
            client.close()

    outcome=dict(run_id=run_id,lesson=lesson,steps=steps,passed=all(s['passed'] for s in steps),
                 compare=bool(compare and lesson['compare']),started_at=started,finished_at=time.time(),
                 cleanup={'restored':not cleanup_errors,'errors':cleanup_errors})
    folder=Path('/project/results')/run_id
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'results.json').write_text(json.dumps(ops.safe(outcome),ensure_ascii=False,indent=2),encoding='utf-8')
    return ops.safe(outcome)
