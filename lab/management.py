"""Local workspace administration; business requests retain JWT/mTLS/PDP checks."""
from __future__ import annotations

import base64
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from . import operations as ops
from .client import LabClient

PROFILES = ops.RT / 'shared/employee-profiles.json'
ROLES = {'staff', 'manager', 'auditor', 'security_admin'}
LABELS = {'internal', 'confidential', 'restricted'}


class InputError(Exception):
    def __init__(self, message, fields=None, status=422, **extra):
        self.status = status
        self.detail = {'message': message, 'fields': fields or {}, **extra}
        super().__init__(message)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.management-tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.chmod(0o644 if path.parent.name=='pki-public' else 0o600)
    os.replace(temporary, path)


def profiles():
    return read_json(PROFILES)


def known_users():
    return {r['username'] for r in ops.rows('principals')}


def ensure_snapshot_attributes(kc):
    """Declare only the two existing snapshot claims, editable by IdP admins."""
    response=kc.get('/admin/realms/bmdl/users/profile');response.raise_for_status()
    profile=response.json();attributes=profile.setdefault('attributes',[]);changed=False
    for name,options in [('b0_role',sorted(ROLES)),('b0_department',['A','B','OPS'])]:
        existing=next((a for a in attributes if a['name']==name),None)
        required={'name':name,'displayName':name,'permissions':{'view':['admin'],'edit':['admin']},
                  'validations':{'options':{'options':options}},'multivalued':False}
        if existing is None:attributes.append(required);changed=True
        elif any(existing.get(k)!=v for k,v in required.items()):existing.update(required);changed=True
    if changed:kc.put('/admin/realms/bmdl/users/profile',json=profile).raise_for_status()


def validate_employee(body, creating=False):
    if not isinstance(body,dict):raise InputError('Thông tin tài khoản phải là một đối tượng dữ liệu.')
    errors = {}
    username = str(body.get('username', '')).strip().lower()
    name = str(body.get('display_name', '')).strip()
    role, department, active = body.get('role'), body.get('department'), body.get('active', True)
    if creating and (not re.fullmatch(r'[a-z][a-z0-9_]{2,31}', username) or username in {'server', 'none', 'rogue', 'bad', 'lab_root'}):
        errors['username'] = 'Dùng 3–32 ký tự thường, số hoặc dấu gạch dưới; bắt đầu bằng chữ.'
    if not name or len(name) > 80 or any(ord(c) < 32 for c in name):
        errors['display_name'] = 'Nhập họ tên từ 1 đến 80 ký tự.'
    if not isinstance(role,str) or role not in ROLES:
        errors['role'] = 'Chọn một vai trò trong danh sách.'
    if not isinstance(department,str) or department not in {'A', 'B', 'OPS'}:
        errors['department'] = 'Chọn một phòng ban trong danh sách.'
    elif isinstance(role,str) and role in {'auditor', 'security_admin'} and department != 'OPS':
        errors['department'] = 'Kiểm toán và quản trị an toàn thuộc bộ phận An toàn thông tin.'
    elif isinstance(role,str) and role in {'staff', 'manager'} and department not in {'A', 'B'}:
        errors['department'] = 'Nhân viên và trưởng phòng thuộc Kinh doanh hoặc Vận hành.'
    if type(active) is not bool:
        errors['active'] = 'Chọn trạng thái hoạt động của tài khoản.'
    password = body.get('password', '')
    if creating and (not isinstance(password, str) or not 8 <= len(password) <= 128):
        errors['password'] = 'Nhập mật khẩu từ 8 đến 128 ký tự.'
    if errors:
        raise InputError('Kiểm tra lại các trường được đánh dấu.', errors)
    return username, name, role, department, active, password


def create_employee(body):
    username, name, role, department, active, password = validate_employee(body, creating=True)
    with ops.LOCK:
        cfg = ops.config()
        if username in known_users() or username in cfg['users']:
            raise InputError('Tên đăng nhập đã được sử dụng.', {'username': 'Chọn tên đăng nhập khác.'}, 409)
        pki = ops.RT / 'pki'
        paths = [pki / f'{username}{suffix}' for suffix in ('.key', '.crt', '.p12')]
        if any(path.exists() for path in paths):
            raise InputError('Tên đăng nhập trùng với thiết bị đã có.', {'username': 'Chọn tên đăng nhập khác.'}, 409)
        old_cfg = read_json(ops.RT / 'secrets/config.json')
        old_registry = read_json(pki / 'registry.json')
        old_public = read_json(ops.RT / 'pki-public/registry.json')
        old_profiles = profiles()
        created_id = None
        written = []
        saved_files = []
        with httpx.Client(base_url='http://keycloak:8080', timeout=15, trust_env=False) as kc:
            try:
                auth = kc.post('/realms/master/protocol/openid-connect/token', data={
                    'grant_type': 'password', 'client_id': 'admin-cli', 'username': 'lab-root',
                    'password': cfg['keycloak_admin_password']})
                auth.raise_for_status()
                kc.headers['Authorization'] = 'Bearer ' + auth.json()['access_token']
                ensure_snapshot_attributes(kc)
                result = kc.post('/admin/realms/bmdl/users', json={
                    'username': username, 'enabled': True, 'emailVerified': True,
                    'firstName': name, 'lastName': 'BMDL', 'email': username + '@bmdl.test',
                    'attributes': {'b0_role': [role], 'b0_department': [department]},
                    'credentials': [{'type': 'password', 'value': password, 'temporary': False}]})
                if result.status_code == 409:
                    raise InputError('Tên đăng nhập đã tồn tại trong hệ thống đăng nhập.', {'username': 'Chọn tên đăng nhập khác.'}, 409)
                if result.status_code==400:
                    description=result.text.lower()
                    if 'person-name' in description:
                        raise InputError('Họ tên chứa ký tự không được chấp nhận.',{'display_name':'Nhập họ tên thông thường; không dùng dấu ngoặc hoặc ký tự đặc biệt.'})
                    if 'password' in description:
                        raise InputError('Mật khẩu chưa đáp ứng yêu cầu đăng nhập.',{'password':'Dùng ít nhất 8 ký tự, gồm chữ và số.'})
                    raise InputError('Thông tin tài khoản chưa hợp lệ.',{'display_name':'Kiểm tra lại họ tên và tên đăng nhập.'})
                result.raise_for_status()
                created_id = result.headers['Location'].rstrip('/').rsplit('/', 1)[1]
                key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
                ca = x509.load_pem_x509_certificate((pki / 'ca.crt').read_bytes())
                ca_key = serialization.load_pem_private_key((ops.RT / 'secrets/ca.key').read_bytes(), password=None)
                now = datetime.now(timezone.utc)
                cert = (x509.CertificateBuilder()
                    .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, username)]))
                    .issuer_name(ca.subject).public_key(key.public_key())
                    .serial_number(x509.random_serial_number())
                    .not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=90))
                    .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                    .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
                    .sign(ca_key, hashes.SHA256()))
                contents = [key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()),
                    cert.public_bytes(serialization.Encoding.PEM),
                    pkcs12.serialize_key_and_certificates(username.encode(), key, cert, [ca], serialization.BestAvailableEncryption(password.encode()))]
                for path, content in zip(paths, contents):
                    path.write_bytes(content); path.chmod(0o600); written.append(path)
                registry = {**old_registry, username: {'serial': format(cert.serial_number, 'X'), 'subject_id': created_id, 'role': role, 'department': department}}
                cfg['users'][username] = password
                new_profiles = {**old_profiles, username: {'display_name': name, 'created_at': time.time(), 'role':role, 'department':department, 'active':active}}
                for path, value, original in [
                    (ops.RT / 'secrets/config.json', cfg, old_cfg), (pki / 'registry.json', registry, old_registry),
                    (ops.RT / 'pki-public/registry.json', registry, old_public), (PROFILES, new_profiles, old_profiles)]:
                    write_json(path, value); saved_files.append((path, original))
                stamp = time.time()
                with ops.db() as conn:
                    conn.execute('INSERT INTO principals(id,username,subject_id,role,department,active,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                        (username, username, created_id, role, department, active, stamp))
                    conn.execute("INSERT INTO devices(id,principal_id,cert_serial,compliant,risk,observed_at,risk_at,updated_at) VALUES (%s,%s,%s,true,'NORMAL',%s,%s,%s)",
                        ('dev-'+username, username, format(cert.serial_number, 'X'), stamp, stamp, stamp))
                    ops._ledger('principal', username, {'active': active, 'role': role, 'department': department, 'permission_version': 1, 'updated_at': stamp})
                    ops._ledger('device', 'dev-'+username, {'compliant': True, 'revoked': False, 'risk': 'NORMAL', 'observed_at': stamp, 'risk_at': stamp, 'auto_refresh': True, 'updated_at': stamp})
                return {'id': username, 'username': username, 'display_name': name, 'role': role, 'department': department, 'active': active, 'device_id': 'dev-'+username}
            except Exception as error:
                cleanup = []
                for path, original in reversed(saved_files):
                    try: write_json(path, original)
                    except Exception: cleanup.append('khôi phục cấu hình')
                for path in written:
                    try: path.unlink(missing_ok=True)
                    except Exception: cleanup.append('dọn chứng thư')
                if created_id:
                    try:
                        removed = kc.delete('/admin/realms/bmdl/users/' + created_id)
                        if removed.status_code not in {204, 404}: cleanup.append('xóa tài khoản tạo chưa hoàn tất')
                    except Exception: cleanup.append('xóa tài khoản tạo chưa hoàn tất')
                if cleanup:
                    raise InputError('Tạo tài khoản chưa hoàn tất. Cần kiểm tra bước ' + ', '.join(cleanup) + '.', status=503) from None
                if isinstance(error, InputError): raise
                raise InputError('Chưa thể tạo tài khoản. Kiểm tra dịch vụ đăng nhập và thử lại.', status=503) from None


def update_employee(identifier, body):
    _, name, role, department, active, _ = validate_employee(body)
    with ops.LOCK:
        previous = next((r for r in ops.rows('principals') if r['id'] == identifier), None)
        if not previous: raise InputError('Không tìm thấy nhân viên.', status=404)
        patch = {'role': role, 'department': department, 'active': active, 'permission_version': previous['permission_version']+1}
        result = ops.edit_state('principal', identifier, patch)
        data = profiles(); data[identifier] = {**data.get(identifier, {}), 'display_name': name, 'role':role, 'department':department, 'active':active}
        write_json(PROFILES, data)
        return {**result, 'display_name': name}


REASONS = {
    'INACTIVE': 'Tài khoản đã bị khóa. Mở Nhân viên và kích hoạt tài khoản này.',
    'ROLE': 'Vai trò này không có quyền thực hiện thao tác. Chọn nhân viên hoặc trưởng phòng phù hợp.',
    'RESTRICTED_ROLE': 'Tài liệu Hạn chế chỉ dành cho trưởng phòng. Chọn trưởng phòng sở hữu tài liệu.',
    'RESTRICTED_APPROVAL': 'Phê duyệt thêm tài liệu Hạn chế chưa hợp lệ hoặc đã hết hạn. Chọn quản trị an toàn và phê duyệt lại.',
    'RESTRICTED_GRANT': 'Chưa có quyền tải và sửa tài liệu Hạn chế còn hạn. Cấp quyền cho đúng người và phiên bản tài liệu ở phần Quyền tải và sửa.',
    'DEPARTMENT': 'Tài khoản không cùng phòng với tài liệu. Chọn trưởng phòng đúng phòng ban.',
    'OWNER_OR_LABEL': 'Tài khoản không có quyền tải và sửa tài liệu này. Kiểm tra vai trò, chủ sở hữu và nhãn.',
    'LABEL_DOWNGRADE': 'Không được hạ mức nhạy cảm của tài liệu tại đây. Giữ nguyên nhãn hoặc chọn nhãn cao hơn.',
    'LIFECYCLE_ADMIN_REQUIRED': 'Quyền tải và sửa không bao gồm thay đổi thời hạn hoặc bảo toàn. Quản trị an toàn quản lý các thuộc tính này.',
    'RETENTION_EXPIRED': 'Tài liệu đã hết hạn lưu giữ. Điều chỉnh thời hạn trong Điều khiển lab trước khi truy cập.',
    'TRANSPORT_BLOCKED': 'Không kết nối được dịch vụ hoặc chứng thư không hợp lệ. Kiểm tra trạng thái hệ thống và thiết bị.',
    'INVALID_INPUT': 'Thông tin chưa hợp lệ. Kiểm tra tên tệp, nhãn và nội dung.',
    'LEDGER_UNAVAILABLE': 'Chưa hoàn tất ghi nhận thay đổi. Làm mới danh sách để kiểm tra trước khi gửi lại.',
    'DEVICE_MISMATCH': 'Thiết bị không khớp tài khoản. Chọn thiết bị của đúng người gửi.',
    'DEVICE_REVOKED': 'Thiết bị đã bị thu hồi. Khôi phục thiết bị trong Điều khiển lab.',
    'NONCOMPLIANT': 'Thiết bị chưa đạt yêu cầu tuân thủ.', 'RISK_HIGH': 'Thiết bị đang có rủi ro cao.',
    'MISSING_OR_STALE': 'Thông tin thiết bị đã quá hạn. Làm mới tín hiệu thiết bị rồi thử lại.',
    'KMS_UNAVAILABLE': 'Dịch vụ mã hóa chưa sẵn sàng. Khôi phục OpenBao rồi thử lại.',
    'PDP_UNAVAILABLE': 'Dịch vụ kiểm tra quyền chưa sẵn sàng. Khôi phục OPA rồi thử lại.',
    'AUDIT_UNAVAILABLE': 'Chưa ghi được nhật ký. Khôi phục chức năng ghi nhật ký rồi thử lại.'}


def checked(response, field='owner_id'):
    if response.is_success: return response.json()
    try: detail = response.json().get('detail', {})
    except ValueError: detail = {}
    reason = response.headers.get('x-policy-reason') or (detail.get('reason') if isinstance(detail, dict) else None)
    message = REASONS.get(reason, 'Yêu cầu chưa hoàn tất. Kiểm tra kết nối và các dịch vụ trước khi thử lại.')
    raise InputError(message, {field: message}, status=response.status_code if response.status_code >= 400 else 503,
        reason=reason, request_id=response.headers.get('x-request-id'))


def selected_principal(identifier, field='actor_id', *, restricted=False):
    principal = next((r for r in ops.rows('principals') if r['id']==identifier), None)
    if not principal:
        raise InputError('Chọn nhân viên hoặc trưởng phòng thực hiện thao tác.', {field:'Tài khoản phải có vai trò nghiệp vụ.'})
    if principal['role'] not in {'staff','manager'}:
        raise InputError('Vai trò này không được thêm hoặc sửa nội dung tài liệu.',{field:'Chọn nhân viên hoặc trưởng phòng có quyền với tài liệu.'},403)
    if not principal['active']:
        raise InputError('Tài khoản đã bị khóa.', {field:'Kích hoạt tài khoản tại Nhân viên hoặc chọn tài khoản khác.'}, 403)
    if restricted and principal['role']!='manager':
        raise InputError('Tài liệu Hạn chế yêu cầu trưởng phòng có quyền tải và sửa.', {field:'Chọn trưởng phòng cùng phòng ban; nhân viên, kiểm toán và quản trị an toàn không được xử lý nội dung Hạn chế.'}, 403)
    return principal


def approval_options(body):
    identifier=body.get('approver_id')
    approver=next((r for r in ops.rows('principals') if r['id']==identifier), None)
    if not approver or not approver['active'] or approver['role']!='security_admin':
        raise InputError('Cần quản trị an toàn phê duyệt.', {'approver_id':'Chọn quản trị an toàn đang hoạt động.'}, 403)
    ttl=body.get('ttl_seconds',900)
    if type(ttl) not in {int,float} or not 60<=ttl<=3600:
        raise InputError('Thời hạn cấp quyền chưa hợp lệ.', {'ttl_seconds':'Chọn thời hạn từ 1 đến 60 phút.'})
    return identifier, ttl


def request_approval(client, body, principal, doc_id=None):
    approver,ttl=approval_options(body)
    return checked(client.request(approver,'POST','/admin/restricted-approvals',json={
        'principal_id':principal,'doc_id':doc_id,'ttl_seconds':ttl}), 'approver_id')


def create_document(body, token=None):
    if not isinstance(body,dict):raise InputError('Thông tin tài liệu phải là một đối tượng dữ liệu.')
    filename, title = str(body.get('filename', '')).strip(), str(body.get('title', '')).strip()
    label, owner = body.get('label'), body.get('owner_id')
    errors = {}
    if Path(filename).suffix.lower() not in {'.txt', '.csv', '.pdf'} or any(c in filename for c in '\\\r\n\x00/'):
        errors['file'] = 'Chọn tệp TXT, CSV hoặc PDF.'
    title = title or filename
    extension=Path(filename).suffix.lower()
    if extension and not title.lower().endswith(extension): title+=extension
    if not title or len(title)>200 or any(ord(c)<32 or c in '\\/' for c in title):
        errors['title'] = 'Nhập tên tối đa 200 ký tự, không chứa dấu / hoặc \\.'
    if not isinstance(label,str) or label not in LABELS: errors['label'] = 'Chọn nhãn Nội bộ, Mật hoặc Hạn chế.'
    principal = next((r for r in ops.rows('principals') if r['id']==owner), None)
    if not principal or principal['role'] not in {'staff', 'manager'}: errors['owner_id'] = 'Chọn nhân viên hoặc trưởng phòng sở hữu tài liệu.'
    elif not principal['active']: errors['owner_id'] = 'Tài khoản đã bị khóa. Kích hoạt tại Nhân viên hoặc chọn người khác.'
    try: data = base64.b64decode(body.get('content_b64', ''), validate=True)
    except (ValueError, TypeError): data = b''
    if not data or len(data)>1024*1024: errors['file'] = 'Chọn tệp có nội dung, tối đa 1 MiB.'
    if errors: raise InputError('Kiểm tra lại thông tin tài liệu.', errors)
    with ops.LOCK:
        selected_principal(owner, 'owner_id', restricted=label=='restricted')
        client = LabClient()
        try:
            payload={'title':title,'label':label,'content_b64':base64.b64encode(data).decode()}
            if label=='restricted':
                approval=request_approval(client,body,owner)
                payload['approval_id']=approval['id']
            result=checked(client.request(owner,'POST','/documents',json=payload,token=token),'owner_id')
            return document_metadata(result['id'])
        finally: client.close()


def document_metadata(identifier):
    item = next((r for r in ops.rows('documents') if r['id']==identifier), None)
    if not item: raise InputError('Không tìm thấy tài liệu.', status=404)
    return ops.safe(item)


def update_document(identifier, body, token=None):
    if not isinstance(body,dict):raise InputError('Thông tin tài liệu phải là một đối tượng dữ liệu.')
    label = body.get('label')
    hold, retention = body.get('legal_hold'), body.get('retention_until')
    title = str(body.get('title', '')).strip()
    errors = {}
    if not isinstance(label,str) or label not in LABELS: errors['label'] = 'Chọn nhãn trong danh sách.'
    if type(hold) is not bool: errors['legal_hold'] = 'Chọn trạng thái bảo toàn tài liệu.'
    if type(retention) not in {int, float} or not 0 <= retention <= 253402300799:
        errors['retention_until'] = 'Chọn thời hạn hợp lệ.'
    if not title or len(title)>200 or any(ord(c)<32 or c in '\\/' for c in title):
        errors['title'] = 'Nhập tên từ 1 đến 200 ký tự, không chứa dấu / hoặc \\.'
    if errors: raise InputError('Kiểm tra lại thông tin tài liệu.', errors)
    with ops.LOCK:
        previous = document_metadata(identifier)
        if previous['deleted']: raise InputError('Tài liệu đã bị xóa. Chọn tài liệu đang hoạt động.', status=409)
        extension=Path(previous['title']).suffix.lower()
        if extension in {'.txt','.csv','.pdf'} and not title.lower().endswith(extension):title+=extension
        if len(title)>200:raise InputError('Tên tài liệu quá dài.',{'title':'Nhập tên ngắn hơn 196 ký tự.'})
        actor=body.get('actor_id')
        selected_principal(actor, restricted='restricted' in {label,previous['label']})
        client=LabClient()
        try:
            payload={'title':title,'label':label,'legal_hold':hold,'retention_until':retention}
            if label=='restricted' and previous['label']!='restricted':
                payload['approval_id']=request_approval(client,body,actor,identifier)['id']
            checked(client.request(actor,'PUT',f'/documents/{identifier}',json=payload,token=token),'actor_id')
            return document_metadata(identifier)
        finally:client.close()


def grant_document(identifier,body):
    if not isinstance(body,dict):raise InputError('Thông tin cấp quyền chưa hợp lệ.')
    with ops.LOCK:
        doc=document_metadata(identifier)
        if doc['deleted'] or doc['label']!='restricted':
            raise InputError('Chọn tài liệu Hạn chế đang hoạt động.',status=409)
        target=selected_principal(body.get('principal_id'),'principal_id',restricted=True)
        if target['department']!=doc['department']:
            raise InputError('Người nhận không cùng phòng với tài liệu.',{'principal_id':'Chọn trưởng phòng cùng phòng ban.'},403)
        approver,ttl=approval_options(body)
        client=LabClient()
        try:return checked(client.request(approver,'POST','/admin/grants',json={
            'principal_id':target['id'],'doc_id':identifier,'ttl_seconds':ttl}),'approver_id')
        finally:client.close()


def revoke_document_grant(identifier,grant_id,body):
    if not isinstance(body,dict):raise InputError('Thông tin thu hồi chưa hợp lệ.')
    with ops.LOCK:
        grant=next((r for r in ops.rows('grants') if r['id']==grant_id and r['doc_id']==identifier),None)
        if not grant:raise InputError('Không tìm thấy quyền đã cấp cho tài liệu.',status=404)
        approver,_=approval_options(body)
        client=LabClient()
        try:return checked(client.request(approver,'DELETE',f'/admin/grants/{grant_id}'),'approver_id')
        finally:client.close()


def restore_employees_after_reset():
    """Keep user-created identities usable when the document fixtures are reset."""
    from app.db import USERS
    fixtures={user for user,_,_ in USERS}
    existing=known_users()
    registry=read_json(ops.RT/'pki/registry.json')
    added=0
    with ops.db() as conn:
        for username,profile in profiles().items():
            if username in fixtures or username in existing or username not in registry:continue
            entry=registry[username];stamp=time.time()
            conn.execute('INSERT INTO principals(id,username,subject_id,role,department,active,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                (username,username,entry['subject_id'],profile.get('role',entry['role']),profile.get('department',entry['department']),profile.get('active',True),stamp))
            conn.execute("INSERT INTO devices(id,principal_id,cert_serial,compliant,risk,observed_at,risk_at,updated_at) VALUES (%s,%s,%s,true,'NORMAL',%s,%s,%s)",
                ('dev-'+username,username,entry['serial'],stamp,stamp,stamp))
            added+=1
    return added
