
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAV = '[English](README.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Français](README.fr.md)'
SECTION = re.compile(r'^<!-- section: ([a-z-]+) -->\n', re.M)
SHARED = re.compile(r'<!-- shared: ([a-z-]+) -->\n(.*?)\n<!-- /shared -->', re.S)


def sections(text):
    parts = SECTION.split(text.replace(NAV + '\n\n', ''))
    if parts[0].strip() or len(set(parts[1::2])) != len(parts[1::2]):
        raise ValueError('README requires unique named sections.')
    return dict(zip(parts[1::2], (body.strip() for body in parts[2::2])))


def template(body):
    return SHARED.sub(lambda match: '{{' + match[1] + '}}', body)


def source_hash(body):
    return hashlib.sha256(template(body).encode('utf-8')).hexdigest()


def main():
    source = sections((ROOT / 'README.md').read_text(encoding='utf-8'))
    outputs = {}
    for language in ('es', 'pt', 'de', 'fr'):
        translations = json.loads((ROOT / f'translations/readme.{language}.json').read_text(encoding='utf-8'))
        if set(translations) != set(source):
            raise ValueError(f'Incomplete section mapping: {language}')
        rendered = []
        for name, body in source.items():
            entry = translations[name]
            translated = entry['text']
            if entry['source_sha256'] != source_hash(body):
                raise ValueError(f'Stale translation: {language}/{name}')
            tokens = lambda text: Counter(re.findall(r'\d+(?:[.,]\d+)?', text.replace(',', '.')))
            links = lambda text: Counter(re.findall(r'\]\(([^)]+)\)', text))
            shared = {match[1]: match[0] for match in SHARED.finditer(body)}
            placeholders = Counter(re.findall(r'\{\{([a-z-]+)\}\}', translated))
            if placeholders != Counter(shared.keys()):
                raise ValueError(f'Shared blocks changed: {language}/{name}')
            if tokens(translated) != tokens(template(body)) or links(translated) != links(template(body)):
                raise ValueError(f'Numerical content or links changed: {language}/{name}')
            for key, block in shared.items():
                translated = translated.replace('{{' + key + '}}', block)
            rendered.append(f'<!-- section: {name} -->\n{translated}')
        rendered.insert(1, NAV)
        outputs[ROOT / f'README.{language}.md'] = '\n\n'.join(rendered) + '\n'
    for path, content in outputs.items():
        path.write_text(content, encoding='utf-8')
    print('Updated four translations from README.md.')


if __name__ == '__main__':
    main()
