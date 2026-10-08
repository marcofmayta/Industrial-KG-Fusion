
from datetime import datetime, timezone
from pathlib import Path
import zipfile

from src.data import sha256, write_json


def snapshot_results(root):
    root = Path(root)
    directory = root/'results'
    files = sorted(p for p in directory.rglob('*') if p.is_file())
    if not files:
        return None
    identifier = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = root/'archive/runs'/identifier
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {p.relative_to(root).as_posix(): sha256(p) for p in files}
    with zipfile.ZipFile(destination/'results.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root).as_posix())
    write_json(destination/'manifest.json', {'sha256': manifest, 'purpose': 'Previous values retained before pipeline execution'})
    return destination, manifest


def record_changes(root, snapshot, reason):
    if snapshot is None:
        return []
    root = Path(root)
    destination, before = snapshot
    changes = []
    for relative, old in before.items():
        path = root/relative
        new = sha256(path) if path.exists() else None
        if old != new:
            changes.append({'artifact': relative, 'old_sha256': old, 'new_sha256': new,
                'old_values': (destination/'results.zip').relative_to(root).as_posix()+' :: '+relative,
                'new_values': relative if new else 'absent'})
    write_json(destination/'changes.json', {'reason': reason, 'changes': changes,
        'responsible_code_sha256': {p.relative_to(root).as_posix(): sha256(p) for directory in ['src', 'tools', 'notebooks'] for p in sorted((root/directory).glob('*')) if p.suffix in ['.py', '.ipynb']}})
    ledger = root/'docs/RESULT_CHANGELOG.md'
    if not ledger.exists():
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text('# Result changelog\n\nOriginal values are preserved before re-execution. Changes are never evidence of improvement by themselves.\n', encoding='utf-8')
    text = '\n## '+destination.name+'\n\nReason: '+reason+'\n\n'
    text+='Previous values and manifest: `'+destination.relative_to(root).as_posix()+'`. This local archive is excluded from Git.\n\n'
    if changes:
        text+='| Artifact | Old value source | New value source | Explanation |\n| --- | --- | --- | --- |\n'
        for change in changes:
            text+='| '+change['artifact']+' | '+change['old_values']+' | '+change['new_values']+' | Recomputed by recorded source versions; changed bytes require interpretation, not automatic acceptance |\n'
    else:
        text+='No previous result artifact changed.\n'
    with ledger.open('a', encoding='utf-8') as stream:
        stream.write(text)
    return changes
