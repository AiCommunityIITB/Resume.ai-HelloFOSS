"""Dependency-free snapshot gate. Complements, not replaces, Gitleaks history scans.

Never prints matched values. Run before committing and before publishing.
"""
import ast
import csv
import hashlib
import re
import sys
from pathlib import Path

RULES = {
    'google-key': re.compile(r'\bAIza[A-Za-z0-9_-]{35}\b'),
    'provider-key': re.compile(r'\b(?:csk-|gsk_)[A-Za-z0-9_-]{20,}\b'),
    'github-token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b'),
    'aws-key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'database-uri': re.compile(r'(?:postgres(?:ql)?(?:\+\w+)?|mysql(?:\+\w+)?|mssql(?:\+\w+)?)://[^\s\"\x27:@]+:[^@$\s\"\x27]+@'),
    'compose-password': re.compile(r'POSTGRES_PASSWORD:\s*[\"\x27][^$\"\x27\r\n]+[\"\x27]'),
    'personal-local-path': re.compile('/U' + r'sers/[^/\s\"\x27]+/|C:\\\\U' + r'sers\\\\[^\\\s\"\x27]+'),
    'institutional-email': re.compile(r'\b[A-Za-z0-9._%+-]+@(?:[\w.-]+\.)?iitb\.ac\.in\b', re.I),
}
IDENTIFIERS = {'file', 'filename', 'file_path', 'resume_no', 'resume_id', 'name', 'email', 'roll_number', 'student_id'}
PRIVATE_SUFFIXES = {'.pdf', '.db', '.sqlite', '.sqlite3', '.pem', '.key', '.p12', '.pfx'}
EXCLUDED = {'.git', '__pycache__', 'node_modules', '.next', '.venv'}


def inspect(root):
    root = Path(root)
    findings = []
    files = 0
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root)
        if not p.is_file() or any(part in EXCLUDED for part in rel.parts):
            continue
        files += 1
        label = rel.as_posix()
        if (p.name.startswith('.env') and p.name != '.env.example') or p.suffix.lower() in PRIVATE_SUFFIXES or p.name in {'testv1.png', 'testv2.png', 'Resume-rating.webp'}:
            findings.append((label, 'private-file'))
        try:
            source = p.read_text(encoding='utf-8-sig')
        except UnicodeDecodeError:
            continue
        for rule, pattern in RULES.items():
            if pattern.search(source): findings.append((label, rule))
        if p.suffix == '.py':
            try: ast.parse(source, filename=label)
            except SyntaxError: findings.append((label, 'python-syntax'))
        if p.name == '.env.example':
            for line in source.splitlines():
                if not line.strip() or line.lstrip().startswith('#') or '=' not in line: continue
                key, value = line.split('=', 1)
                sensitive = key.upper().endswith(('_PASSWORD', '_TOKEN', '_SECRET', '_SECRET_KEY', '_DB_URL')) or 'API_KEY' in key.upper() or key.upper() in {'SECRET_KEY', 'DATABASE_URL'}
                if sensitive and value.strip() not in {'', '\"\"', "''"}:
                    findings.append((label, 'nonblank-secret-template'))
        if p.suffix == '.csv':
            rows = list(csv.reader(source.splitlines()))
            if not rows: continue
            if any(c.strip().lower() in IDENTIFIERS for c in rows[0]): findings.append((label, 'identifier-column'))
            if '/whitespace_layout_scorer/' in '/'+label:
                aggregate = rows[0] == ['feature', 'mean', 'optimum']
                try:
                    for row in rows[1:]:
                        for cell in (row[1:] if aggregate else row): float(cell)
                except ValueError: findings.append((label, 'nonnumeric-layout-data'))
    return files, findings


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
    files, findings = inspect(root)
    # Counts only: diagnostic output must never disclose matched secrets or PII.
    print(f'RELEASE_CHECK files={files} findings={len(findings)} status={"FAIL" if findings else "PASS"}')
    return int(bool(findings))


if __name__ == '__main__':
    raise SystemExit(main())
