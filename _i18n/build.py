#!/usr/bin/env python3
"""Build the translated home pages, printable PDFs and sitemap.

Usage (from the repo root):
  python3 _i18n/build.py          # pages + sitemap
  python3 _i18n/build.py --pdf    # also the translated PDF templates (needs node + Playwright with Chromium)

English text lives in _i18n/strings/en.json and the layout in _i18n/template.html.
index.html (English) is generated too, so edit the template or en.json, not index.html.
The English PDFs at the repo root are kept as they are and never regenerated.
"""
import html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, '_i18n')
BASE = 'https://willtoforge.com/eisenhower-matrix/'
LANGS = json.load(open(os.path.join(HERE, 'languages.json'), encoding='utf-8'))


def load(code):
    return json.load(open(os.path.join(HERE, 'strings', code + '.json'), encoding='utf-8'))


EN = load('en')


def strings_for(lang):
    s = load(lang['code'])
    missing = [k for k in EN if k not in s]
    extra = [k for k in s if k not in EN]
    if missing or extra:
        sys.exit(f"{lang['code']}.json: missing {missing} extra {extra}")
    return s


def page(lang, s):
    tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    root = '../' if lang['dir'] else ''
    alts = [f'<link rel="alternate" hreflang="{l["hreflang"]}" href="{BASE}{l["dir"]}">' for l in LANGS]
    alts.append(f'<link rel="alternate" hreflang="x-default" href="{BASE}">')
    links = []
    for l in LANGS:
        name = html.escape(load(l['code'])['_name'])
        if l is lang:
            links.append(f'<span lang="{l["hreflang"]}">{name}</span>')
        else:
            href = (root + l['dir']) or './'
            if not l['dir']:
                href = root or './'
            links.append(f'<a href="{href}" hreflang="{l["hreflang"]}" lang="{l["hreflang"]}">{name}</a>')
    vals = {k: v for k, v in s.items() if not k.startswith('_')}
    vals.update({
        'lang': lang['hreflang'],
        'canonical': BASE + lang['dir'],
        'hreflang': '\n'.join(alts),
        'og_locale': lang['og_locale'],
        'root': root,
        'campaign': 'site' if lang['code'] == 'en' else 'site-' + lang['code'],
        'hl': '&hl=' + lang['play_hl'] if lang['play_hl'] else '',
        'blog_hreflang': '' if lang['code'] == 'en' else ' hreflang="en"',
        'blog_note': '' if not s['blog_note'] else f'<p>{s["blog_note"]}</p>\n',
        'pdf_a4': 'eisenhower-matrix-template.pdf',
        'pdf_letter': 'eisenhower-matrix-template-letter.pdf',
        'lang_links': ' '.join(links),
    })
    # Only these keys may contain markup; everything else is escaped.
    markup = {'hreflang', 'lang_links', 'blog_note', 'history_p'}
    attrs = {'title', 'description', 'og_desc', 'icon_alt', 'alt1', 'alt2', 'alt3', 'alt4', 'lang_label', 'canonical', 'og_locale', 'lang'}

    def sub(m):
        k = m.group(1)
        if k not in vals:
            sys.exit(f'template key {k} has no value for {lang["code"]}')
        v = vals[k]
        if k in markup:
            return v
        v = html.escape(v, quote=False)
        return v.replace('"', '&quot;') if k in attrs else v

    out = re.sub(r'\{\{(\w+)\}\}', sub, tpl)
    return out


def pdf_html(s, letter):
    e = {k: html.escape(v) for k, v in s.items()}
    size = 'letter landscape' if letter else 'A4 landscape'
    lines = '<div class="ln"></div>' * 7
    return f'''<!doctype html><html lang="{s.get('_lang','en')}"><meta charset="utf-8"><style>
@page{{size:{size};margin:0}}*{{box-sizing:border-box}}
html,body{{margin:0;height:100%}}body{{font-family:Inter,sans-serif;color:#111;padding:9mm 11mm 7mm;display:flex;flex-direction:column;height:100vh}}
.top{{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:1.2px solid #111;padding-bottom:6px}}
.top h1{{margin:0;font-size:22px;font-weight:700}}.top span{{font-size:10px}}
.cols{{display:grid;grid-template-columns:9mm 1fr 1fr;gap:0 3mm;text-transform:uppercase;font-size:9px;font-weight:700;letter-spacing:1.4px;text-align:center;padding:7px 0 5px}}
.grid{{flex:1;display:grid;grid-template-columns:9mm 1fr 1fr;grid-template-rows:1fr 1fr;gap:3mm}}
.side{{writing-mode:vertical-rl;transform:rotate(180deg);text-transform:uppercase;font-size:9px;font-weight:700;letter-spacing:1.4px;text-align:center}}
.box{{border:1.2px solid #111;border-radius:9px;padding:8px 10px;display:flex;flex-direction:column;overflow:hidden}}
.box b{{font-size:15px}}.box small{{font-size:8.5px;margin-top:1px}}.lines{{flex:1;display:flex;flex-direction:column;justify-content:space-evenly;margin-top:4px}}.ln{{border-bottom:.6px solid #aaa}}
.foot{{display:flex;justify-content:space-between;font-size:8px;padding-top:6px;gap:20px}}
</style><body>
<div class="top"><h1>{e['pdf_title']}</h1><span>{e['pdf_date']} ______________________</span></div>
<div class="cols"><div></div><div>{e['pdf_urgent']}</div><div>{e['pdf_not_urgent']}</div></div>
<div class="grid">
<div class="side">{e['pdf_important']}</div>
<div class="box"><b>{e['do']}</b><small>{e['pdf_do']}</small></div>
<div class="box"><b>{e['sc']}</b><small>{e['pdf_sc']}</small></div>
<div class="side">{e['pdf_not_important']}</div>
<div class="box"><b>{e['de']}</b><small>{e['pdf_de']}</small><div class="lines">{lines}</div></div>
<div class="box"><b>{e['ba']}</b><small>{e['pdf_ba']}</small><div class="lines">{lines}</div></div>
</div>
<div class="foot"><span>{e['pdf_quote']}</span><span>{e['pdf_credit']}</span></div>
</body></html>'''


def build_pdfs(targets):
    """Write one HTML page per PDF to a temp folder, then print them with Chromium (node + Playwright)."""
    import subprocess, tempfile
    tmp = tempfile.mkdtemp()
    jobs = []
    for lang, s, outdir in targets:
        s = dict(s, _lang=lang['hreflang'])
        for letter, name in ((False, 'eisenhower-matrix-template.pdf'), (True, 'eisenhower-matrix-template-letter.pdf')):
            src = os.path.join(tmp, f"{lang['code']}-{name}.html")
            open(src, 'w', encoding='utf-8').write(pdf_html(s, letter))
            jobs.append({'src': src, 'out': os.path.join(outdir, name)})
    jobfile = os.path.join(tmp, 'jobs.json')
    json.dump(jobs, open(jobfile, 'w'))
    subprocess.run(['node', os.path.join(HERE, 'pdf.js'), jobfile], check=True)


def sitemap():
    old = open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8').read()
    keep = [u for u in re.findall(r'  <url><loc>[^<]+</loc>.*?</url>', old) if '/blog/' in u]
    alts = ''.join(f'<xhtml:link rel="alternate" hreflang="{l["hreflang"]}" href="{BASE}{l["dir"]}"/>' for l in LANGS)
    alts += f'<xhtml:link rel="alternate" hreflang="x-default" href="{BASE}"/>'
    homes = [f'  <url><loc>{BASE}{l["dir"]}</loc>{alts}</url>' for l in LANGS]
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
           + '\n'.join(homes + keep) + '\n</urlset>\n')
    open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8').write(xml)


def main():
    pdf_targets = []
    for lang in LANGS:
        s = strings_for(lang)
        outdir = os.path.join(ROOT, lang['dir'])
        os.makedirs(outdir, exist_ok=True)
        open(os.path.join(outdir, 'index.html'), 'w', encoding='utf-8').write(page(lang, s))
        if lang['dir']:
            pdf_targets.append((lang, s, outdir))
    sitemap()
    if '--pdf' in sys.argv:
        build_pdfs(pdf_targets)
    print('built', ', '.join(l['code'] for l in LANGS))


if __name__ == '__main__':
    main()
