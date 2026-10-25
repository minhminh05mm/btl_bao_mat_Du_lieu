"""Build a human-readable index from observed evidence, never invented values."""
from pathlib import Path
from collections import Counter
import csv,json,math,re

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'results'
latest=json.loads((OUT/'latest.json').read_text())
run_id=latest['run_id']
suite=json.loads((OUT/run_id/'results.json').read_text())
summary=suite['summary']
counts=Counter(row['group'] for row in suite['results'])
integration=sum(value for group,value in counts.items() if not group.startswith('unit-'))
opa_count=next((row.get('actual',{}).get('tests',0) for row in suite['results'] if row['id']=='OPA-native'),0)
unit_match=re.search(r'(\d+) passed',(OUT/run_id/'identity-tests.txt').read_text())
unit_count=int(unit_match.group(1)) if unit_match else 0
benchmark_dir=sorted(OUT.glob('benchmark-*/results.json'))[-1].parent
benchmark=json.loads((benchmark_dir/'results.json').read_text())['summary']
samples=list(csv.DictReader((benchmark_dir/'latency-samples.csv').open(encoding='utf-8-sig')))

lines=['# Kết quả kiểm chứng thực tế','',
       'Các số dưới đây được đọc từ kết quả chạy thật. Chúng chỉ có giá trị trong tập dữ liệu và cấu hình nguyên mẫu đã ghi nhận.','',
       '## Kiểm chứng chức năng và an toàn','',
       f"Lượt `{run_id}`: {summary['passed']}/{summary['total']} mục tổng hợp đạt, {summary['failed']} mục lỗi; thời gian {summary['duration_seconds']} giây.",'',
       f"Trong đó có {integration} mục tích hợp ({counts.get('oracle',0)} oracle và {integration-counts.get('oracle',0)} mục thuộc các nhóm khác) và {summary['total']-integration} mục tổng hợp kết quả kiểm thử đơn vị. Các mục tổng hợp đại diện cho {opa_count} kiểm thử Rego và {unit_count} kiểm thử Python; không tính mỗi mục tổng hợp như một kiểm thử JWT duy nhất.",'',
       f"Cho phép sai: {summary['false_allow']}/{summary['expected_deny_count']} ca cần từ chối; từ chối sai: {summary['false_deny']}/{summary['expected_allow_count']} ca cần cho phép. Các kiểm tra phi quyết định truy cập được đánh giá bằng tiêu chí riêng.",'',
       '| Nhóm | Số mục |','| --- | ---: |']
for group,count in sorted(counts.items()):lines.append(f'| {group} | {count} |')
lines += ['',f'- [Báo cáo HTML]({run_id}/report.html)',f'- [Dữ liệu JSON]({run_id}/results.json)',
          f'- [Dữ liệu CSV]({run_id}/results.csv)',f'- [{opa_count} kiểm thử OPA]({run_id}/opa-tests.txt)',
          f'- [{unit_count} kiểm thử Python]({run_id}/identity-tests.txt)','',
          '## Đối chứng B0/B1','',
          'Cùng 40 ca có kỳ vọng bảo vệ B1, gồm 20 cho phép và 20 từ chối. B0 là cấu hình tham chiếu yếu có chủ ý, không đại diện hệ thống Google hoặc Microsoft. Các ca fail của B0 được giữ nguyên làm bằng chứng khác biệt.','',
          '| Cấu hình | Cho phép sai / cần từ chối | Từ chối sai / cần cho phép | Lỗi vận hành |',
          '| --- | ---: | ---: | ---: |']
for mode,item in benchmark['decision_metrics'].items():
    lines.append(f"| {mode} | {item['false_allow']}/{item['expected_deny']} | {item['false_deny']}/{item['expected_allow']} | {item['operational_errors']} |")
lines += ['', '## Hiệu năng','',
          '2.400 mẫu đo: 200 yêu cầu mỗi hành động/cấu hình/lần, 3 lần lặp, 20 lượt làm nóng trước mỗi nhóm, đồng thời 1. Thứ tự B0/B1 luân phiên. Mỗi lượt tải đều kiểm tra hash bản rõ. JWT được cache sau đăng nhập; số đo không bao gồm thao tác người dùng nhập mật khẩu.','',
          '| Cấu hình | Hành động | Mẫu | Trung bình (ms) | p50 (ms) | p95 (ms) | Lỗi |',
          '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
for mode in ['B0','B1']:
    for action in ['metadata','download']:
        selected=[row for row in samples if row['mode']==mode and row['action']==action]
        values=sorted(float(row['latency_ms']) for row in selected)
        p=lambda q:values[math.ceil(len(values)*q)-1]
        errors=sum(row['correct_content']!='True' for row in selected)
        lines.append(f'| {mode} | {action} | {len(values)} | {sum(values)/len(values):.3f} | {p(.5):.3f} | {p(.95):.3f} | {errors} |')
lines += ['', 'Các percentile trên được tính trực tiếp từ 600 mẫu mỗi dòng, không lấy trung bình các percentile. Đây là số đo cục bộ; không suy ra B1 luôn nhanh hơn/chậm hơn B0 hoặc khả năng chịu tải thực tế.','',
          f'- [Báo cáo đối chứng]({benchmark_dir.name}/report.html)',
          f'- [2.400 mẫu gốc]({benchmark_dir.name}/latency-samples.csv)',
          f'- [12 nhóm đo]({benchmark_dir.name}/performance-summary.csv)',
          f'- [Môi trường đo]({benchmark_dir.name}/environment.json)','',
          '## Phục hồi và giới hạn bằng chứng','']
restore_case=next((row for row in suite['results'] if row['id']=='T23b'),None)
snapshot=restore_case['evidence']['snapshot_id'] if restore_case else None
proofs=[]
for path in (OUT/'recovery').glob('bmdl-restore-*.json'):
    item=json.loads(path.read_text())
    if item.get('snapshot_id')==snapshot:proofs.append((path,item))
if proofs:
    path,proof=proofs[-1]
    lines += [f"Phục hồi PostgreSQL và OpenBao cô lập: {proof['verified_documents']} tài liệu được giải mã/đối chiếu hash, {proof['available_documents']} tài liệu còn sử dụng và {proof['blocked_documents']} tombstone sau đối chiếu ledger. RTO đo được {proof['rto_seconds']} giây. Tuổi snapshot tại lúc bắt đầu phục hồi là {proof['rpo_seconds']} giây; đây không phải lượng dữ liệu nghiệp vụ bị mất.",'',
              f"- [Bằng chứng phục hồi]({path.relative_to(OUT).as_posix()})"]
lines += ['', 'Phục hồi kiểm chứng không thay thế hệ thống đang hoạt động và không công bố API của bản phục hồi. T23b kiểm tra DB/KMS cô lập; T23c–T23e là các yêu cầu HTTP tới hệ thống chính sau kiểm chứng. Việc promote bản phục hồi thành hệ thống chính chưa được tự động hóa.','',
          'Tín hiệu thiết bị/rủi ro do lab giả lập. Không ngăn được sao chép bản rõ sau khi tải hợp lệ; không chống được quản trị viên chiếm toàn bộ máy chủ. Backup, khóa phục hồi và dữ liệu đều ở cùng ổ E nên không bảo vệ trước sự cố mất ổ vật lý. Bản sao lưu được giữ trong kho cục bộ; lịch tự động loại bản sao sau 7 ngày chưa được triển khai.','',
          '## Giao diện và dữ liệu thử','',
          '- [Ảnh tổng quan](ui/01-overview-desktop.png)',
          '- [Thử cấp quyền](ui/02-playground-allow.png)',
          '- [Thử từ chối](ui/03-playground-deny.png)',
          '- [Sửa trạng thái thu hồi](ui/06-editor-revoked.png)',
          '- [Chạy bộ case tùy chỉnh](ui/07-custom-results.png)',
          '- [Kết quả JSON của case tùy chỉnh đã chạy](ui/custom-run.json)','']
report = ROOT/'docs'/'bang_chung'/f'{run_id}-tu_dong.md'
report.parent.mkdir(parents=True, exist_ok=True)
document = '\n'.join(lines)
document = re.sub(r'\]\((?![A-Za-z][A-Za-z0-9+.-]*:|#)([^)]+)\)',
                  lambda match: '](../../results/' + match.group(1) + ')', document)
document = document.replace('# Kết quả kiểm chứng thực tế',
    '# Kết quả tự sinh theo lượt\n\nBản này lấy suite và benchmark đã lưu; hai lượt có thể thuộc phạm vi khác nhau. '
    'Đọc [chỉ mục kết quả đã phân loại](../ket_qua_kiem_chung.md) trước khi diễn giải. '
    'Bản tự sinh không thay thế chỉ mục đó.', 1)
report.write_text(document, encoding='utf-8')
print(json.dumps({'summary':str(report),'suite':run_id,'benchmark':benchmark_dir.name}))
