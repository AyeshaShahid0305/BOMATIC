from app.engines.e1.step4_legal_trap_flagger import detect_legal_traps
from app.engines.e1.extractors import extract_text
from pathlib import Path

fixtures = Path('storage/e1_test_fixtures')
texts = {}
for f in ['Technical_Bid_Requirements.pdf', 'NDA_Confidentiality_Agreement.docx']:
    result = extract_text(fixtures / f)
    texts[f] = result['text']

flags = detect_legal_traps(texts)

print(f'Found {len(flags)} risk flags:')
for flag in flags:
    deadline = f' | deadline: {flag.deadline}' if flag.deadline else ''
    print(f'  [{flag.severity.upper()}] {flag.flag}{deadline}')
