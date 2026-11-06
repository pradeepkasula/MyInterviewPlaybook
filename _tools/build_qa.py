"""Build Q&A topic pages and track hubs from Markdown sources.

Usage (from the repo root):  python -I _tools/build_qa.py

Sources: _src/<track>/<topic>.md      (underscore dirs are not published by Pages)
Output : <track>/index.html           (hub)
         <track>/<topic>/index.html   (topic page)

Source format
  ---
  track: spring            # folder
  slug: core               # folder name of the topic
  title: Spring Core
  mono: IoC                # short text for the hub card
  prefix: C                # question id prefix
  order: 1
  summary: One line for the hub card.
  ---
  ## Beginner | Intermediate | Experienced | Scenarios and design
  ### Q: Question text {theory|coding|scenario|design}
  answer in Markdown: paragraphs, - bullets, 1. lists, | tables |, ``` code ```,
  ```mermaid diagrams```, **bold**, *italic*, `code`, [text](url)
"""
import glob
import html
import os
import re
import sys

ROOT = os.getcwd()
TRACKS = {
    'spring': dict(name='Spring', blurb='Spring Framework interview questions from beginner to experienced: theory, coding and scenario questions with architecture diagrams.', grad='g-spring'),
    'springboot': dict(name='Spring Boot', blurb='Spring Boot interview questions from beginner to experienced: theory, coding and scenario questions with architecture diagrams.', grad='g-boot'),
}
SECTION_IDS = {'Beginner': 'beginner', 'Intermediate': 'intermediate', 'Experienced': 'experienced', 'Scenarios and design': 'scenarios'}
TYPE_LABEL = {'theory': 'Theory', 'coding': 'Coding', 'scenario': 'Scenario', 'design': 'Design'}
esc = html.escape


# ---------------------------------------------------------------- markdown
def inline(text):
    spans = []

    def keep(m):
        spans.append('<code>' + esc(m.group(1), quote=False) + '</code>')
        return '\x00%d\x00' % (len(spans) - 1)

    text = re.sub(r'`([^`]+)`', keep, text)
    text = esc(text, quote=False)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<em>\1</em>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', r'<a href="\2">\1</a>', text)
    return re.sub(r'\x00(\d+)\x00', lambda m: spans[int(m.group(1))], text)


def md(src):
    lines = src.strip('\n').split('\n')
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith('```'):
            lang = ln.strip()[3:].strip()
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1
            code = esc('\n'.join(buf), quote=False)
            if lang == 'mermaid':
                out.append('<pre class="mermaid">' + code + '</pre>')
            else:
                cls = ' class="language-%s"' % lang if lang else ''
                out.append('<pre><code%s>%s</code></pre>' % (cls, code))
        elif re.match(r'\s*[-*] ', ln):
            items = []
            while i < len(lines) and re.match(r'\s*[-*] ', lines[i]):
                items.append('<li>' + inline(re.sub(r'^\s*[-*] ', '', lines[i])) + '</li>')
                i += 1
            out.append('<ul>' + ''.join(items) + '</ul>')
        elif re.match(r'\s*\d+\. ', ln):
            items = []
            while i < len(lines) and re.match(r'\s*\d+\. ', lines[i]):
                items.append('<li>' + inline(re.sub(r'^\s*\d+\. ', '', lines[i])) + '</li>')
                i += 1
            out.append('<ol>' + ''.join(items) + '</ol>')
        elif ln.strip().startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            head, body = rows[0], [r for r in rows[2:]] if len(rows) > 1 and set(''.join(rows[1])) <= set('-: ') else rows[1:]
            t = '<div class="table-wrap"><table><thead><tr>' + ''.join('<th>%s</th>' % inline(c) for c in head) + '</tr></thead><tbody>'
            t += ''.join('<tr>' + ''.join('<td>%s</td>' % inline(c) for c in r) + '</tr>' for r in body)
            out.append(t + '</tbody></table></div>')
        elif not ln.strip():
            i += 1
        else:
            buf = []
            while i < len(lines) and lines[i].strip() and not re.match(r'\s*([-*] |\d+\. |\||```)', lines[i]):
                buf.append(lines[i].strip())
                i += 1
            out.append('<p>' + inline(' '.join(buf)) + '</p>')
    return '\n'.join(out)


# ---------------------------------------------------------------- parsing
def parse(path):
    raw = open(path, encoding='utf-8').read()
    m = re.match(r'---\n(.*?)\n---\n(.*)', raw, flags=re.S)
    meta = dict(re.findall(r'^(\w+):\s*(.*?)\s*$', m.group(1), flags=re.M))
    sections, cur, q = [], None, None
    for ln in m.group(2).split('\n'):
        if ln.startswith('## '):
            cur = dict(name=ln[3:].strip(), qs=[])
            sections.append(cur)
            q = None
        elif ln.startswith('### Q:'):
            mm = re.match(r'### Q:\s*(.*?)\s*\{(\w+)\}\s*$', ln)
            assert mm, 'bad question line: ' + ln
            assert mm.group(2) in TYPE_LABEL, ln
            q = dict(text=mm.group(1), type=mm.group(2), body=[])
            cur['qs'].append(q)
        elif q is not None:
            q['body'].append(ln)
    meta['sections'] = sections
    meta['n'] = sum(len(s['qs']) for s in sections)
    return meta


# ---------------------------------------------------------------- templates
HEAD = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="stylesheet" href="{up}assets/style.css">
<link rel="stylesheet" href="{up}assets/qa.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css" media="(prefers-color-scheme: light)">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css" media="(prefers-color-scheme: dark)">
</head>
'''


def topic_page(meta, topics, tr):
    up = '../../'
    secs = [s for s in meta['sections'] if s['qs']]
    nav = ''.join('<a href="#%s">%s <span class="cnt">%d</span></a>\n' % (SECTION_IDS[s['name']], esc(s['name']), len(s['qs'])) for s in secs)
    others = ''.join('<a href="../%s/"%s>%s</a>\n' % (t['slug'], ' class="here"' if t['slug'] == meta['slug'] else '', esc(t['title'])) for t in topics)
    body, k = [], 0
    for s in secs:
        body.append('<h2 id="%s">%s</h2>' % (SECTION_IDS[s['name']], esc(s['name'])))
        for q in s['qs']:
            k += 1
            qid = '%s%d' % (meta['prefix'], k)
            body.append('<p class="q" id="%s"><strong><span class="qid">%s</span> %s <span class="tag t-%s">%s</span></strong></p>' % (
                qid, qid, inline(q['text']), q['type'], TYPE_LABEL[q['type']]))
            body.append('<blockquote>\n' + md('\n'.join(q['body'])) + '\n</blockquote>')
    counts = ' &middot; '.join('%s %d' % (esc(s['name']), len(s['qs'])) for s in secs)
    return HEAD.format(title='%s Interview Questions | My Interview Playbook' % esc(meta['title']),
                       desc=esc(meta['summary']), up=up) + '''<body>
<button class="menu-btn" id="menuBtn" aria-label="Toggle contents" aria-expanded="false">Contents</button>
<aside class="sidebar" id="sidebar">
  <a class="back" href="../">&larr; {track} track</a>
  <p class="side-title">On this page</p>
  <nav>
<a href="#top-of-page">Overview</a>
{nav}  </nav>
  <p class="side-title" style="margin-top:20px">{track} topics</p>
  <nav class="topics">
{others}  </nav>
  <label class="practice"><input type="checkbox" id="practice"> Practice mode<span>Hide answers. Click a question to reveal its answer.</span></label>
</aside>
<main class="content">
<header class="hero" id="top-of-page"><p class="eyebrow">{track} interview playbook</p><h1 class="doc-title">{title}</h1><p class="subtitle">{summary}</p><p class="intro">{n} questions: {counts}. Each question is tagged <span class="tag t-theory">Theory</span> <span class="tag t-coding">Coding</span> <span class="tag t-scenario">Scenario</span> <span class="tag t-design">Design</span>. Use Practice mode to hide the answers and test yourself.</p></header>
{body}
<footer class="foot">Answers target Spring Framework 6 and Spring Boot 3 (Java 17+). Verify version-specific details against the official reference documentation before an interview.</footer>
</main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<script src="{up}assets/script.js"></script>
<script src="{up}assets/qa.js"></script>
</body>
</html>
'''.format(track=tr['name'], nav=nav, others=others, title=esc(meta['title']), summary=esc(meta['summary']),
           n=meta['n'], counts=counts, body='\n'.join(body), up=up)


def hub_page(slug, tr, topics):
    cards = []
    for t in topics:
        levels = ' &middot; '.join('%d %s' % (len(s['qs']), esc(s['name'].split()[0].lower())) for s in t['sections'] if s['qs'])
        cards.append('''    <li><a class="card" href="{slug}/">
      <div class="thumb {grad}"><span class="mono">{mono}</span></div>
      <div class="body"><span class="badge">{n} questions</span><h3>{title}</h3><p>{summary}</p><p class="lv">{levels}</p></div>
    </a></li>'''.format(slug=t['slug'], grad=tr['grad'], mono=esc(t['mono']), n=t['n'], title=esc(t['title']),
                       summary=esc(t['summary']), levels=levels))
    total = sum(t['n'] for t in topics)
    return '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} Interview Questions | My Interview Playbook</title>
<meta name="description" content="{blurb}">
<link rel="stylesheet" href="../assets/landing.css">
</head>
<body>
<header class="top"><div class="wrap">
  <a class="back light" href="../">&larr; All tracks</a>
  <p class="eyebrow">Interview track</p>
  <h1>{name}</h1>
  <p class="sub">{blurb} {total} questions across {nt} topics.</p>
</div></header>
<main class="wrap">
  <h2 class="section-title">Topics</h2>
  <ul class="grid">
{cards}
  </ul>
</main>
<footer class="foot">Prepared by Pradeep Kasula &middot; <a href="https://pradeepkasula.github.io/">Portfolio</a></footer>
</body>
</html>
'''.format(name=tr['name'], blurb=tr['blurb'], total=total, nt=len(topics), cards='\n\n'.join(cards))


def main():
    for slug, tr in TRACKS.items():
        files = sorted(glob.glob(os.path.join(ROOT, '_src', slug, '*.md')))
        if not files:
            continue
        topics = sorted((parse(f) for f in files), key=lambda t: int(t['order']))
        for t in topics:
            d = os.path.join(ROOT, slug, t['slug'])
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(topic_page(t, topics, tr))
            print('built %s/%s (%d questions)' % (slug, t['slug'], t['n']))
        open(os.path.join(ROOT, slug, 'index.html'), 'w', encoding='utf-8').write(hub_page(slug, tr, topics))
        print('built hub %s' % slug)


if __name__ == '__main__':
    main()
