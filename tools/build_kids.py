#!/usr/bin/env python3
"""Build the Greekquent Kids vault from the student vault.
Usage: build_kids.py <student vault folder> <output folder>
Run it again any week: it rebuilds the kids copy from the current student vault, so nothing is written twice.
Keeps: the kid lessons, the Kids Core word notes (tools/kids-core.json, trimmed for kids), the Γιαγιά game and the plugin.
Leaves out: adult lessons, Fluent in a Year, handouts and other grown-up pages. Links to pages that are left out become plain text."""
import sys, os, re, shutil, json
src, out = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(out): shutil.rmtree(out)
os.makedirs(out)
# 1. Obsidian settings and the plugin (never the window layout)
shutil.copytree(os.path.join(src, '.obsidian'), os.path.join(out, '.obsidian'),
                ignore=lambda d, n: [x for x in n if re.match(r'workspace(-mobile)?\.json$', x) or x == 'data.json'])
for x in ('greekquent-teacher.json', 'greekquent-release.json'):
    p = os.path.join(out, '.obsidian', x)
    if os.path.exists(p): os.remove(p)
# 2. Schedule: kid lesson N runs the same week as class lesson N (from Fluent in a Year)
sched = []
fy = os.path.join(src, 'Fluent in a Year')
for f in sorted(os.listdir(fy)):
    t = open(os.path.join(fy, f), encoding='utf-8').read()
    w, l = re.search(r'^fiay_week:\s*(\d+)', t, re.M), re.search(r'^lesson:\s*(\d+)', t, re.M)
    if w and l: sched.append([int(w.group(1)), int(l.group(1))])
json.dump({'edition': 'kids', 'schedule': sorted(sched)}, open(os.path.join(out, '.obsidian', 'greekquent-kids.json'), 'w'), indent=1)
# 3. Kid lessons
os.makedirs(os.path.join(out, 'Scripts', 'Kid'))
kids = sorted(f for f in os.listdir(os.path.join(src, 'Scripts', 'Kid')) if f.endswith('.md'))
for f in kids: shutil.copy(os.path.join(src, 'Scripts', 'Kid', f), os.path.join(out, 'Scripts', 'Kid', f))
# 4. Word notes, trimmed
def section(t, name):
    m = re.search(r'\n## ' + re.escape(name) + r'\n.*?(?=\n## |\n---\n|\Z)', t, re.S)
    return m
core = json.load(open(os.path.join(here, 'kids-core.json'), encoding='utf-8'))
keep = {w for v in core['categories'].values() for w in v}
extras = core['extras']
os.makedirs(os.path.join(out, 'Words'))
for f in os.listdir(os.path.join(src, 'Words')):
    if f[:-3] not in keep: continue
    t = open(os.path.join(src, 'Words', f), encoding='utf-8').read()
    t = re.sub(r' · rank \*\*#\d+\*\* of 1,500', '', t)
    t = t.replace('Build with words from the 1,500:', 'Build with your words:')
    # "Often appears with": keep only lines whose word is in the kids vault
    t = re.sub(r'^- \[\[([^\]|#]+)[^\n]* — [^\n]*\n', lambda m: m.group(0) if m.group(1) in keep or m.group(1) in extras else '', t, flags=re.M)
    t = re.sub(r'\n## Often appears with\n(?=\n|$)', '\n', t)
    t = re.sub(r' · first in \[\[[^\]]+\]\]', '', t)
    t = re.sub(r'\n- …and \d+ more in the lesson scripts[^\n]*', '', t)
    m = section(t, 'Together in the story')
    if m: t = t[:m.start()] + t[m.end():]
    m = section(t, 'Appears in scripts')
    kl = []
    if m:
        kline = re.search(r'^- Kid lessons: (.+)$', m.group(0), re.M)
        if kline:
            kl = [int(x) for x in re.findall(r'\[\[K(\d+) ', kline.group(1))]
            new = '\n## In the kid lessons\n\n' + ' · '.join(re.findall(r'\[\[[^\]]+\]\]', kline.group(1))) + '\n'
        else: new = ''
        t = t[:m.start()] + new + t[m.end():]
    if kl: t = re.sub(r'^(---\n)', r'\1kid_lessons: [' + ', '.join(map(str, sorted(set(kl)))) + ']\n', t, count=1)
    open(os.path.join(out, 'Words', f), 'w', encoding='utf-8').write(t)
# Kid words that are not in the 1,500 (rank after 1,500 so they sort last)
for i, (w, x) in enumerate(extras.items()):
    ex = x['example']
    t = (f'---\nrank: {1501 + i}\nenglish: "{x["english"]}"\npronunciation: "{x["pronunciation"]}"\ntags: [greek-kids, kids-extra, {x["pos"]}]\n---\n'
         f'# {w}\n\n**{x["english"]}** · say it: {x["pronunciation"]} · a kids word\n\n> {ex[0]}\n\n{ex[1]}\n\n## Do the move\n\n{x["move"]}\n')
    open(os.path.join(out, 'Words', w + '.md'), 'w', encoding='utf-8').write(t)
# 5. Kids pages (kept in tools/kids-pages next to this script)
pages = os.path.join(here, 'kids-pages')
for f in os.listdir(pages): shutil.copy(os.path.join(pages, f), os.path.join(out, f))
lessons = ['# All lessons', '', 'One game a week. Back to [[Today]].', '']
for f in kids:
    b = f[:-3]; n = int(b[1:3]); title = re.sub(r'^K\d+\s*', '', b).replace('-student', '')
    lessons.append(f'{n}. [[{b}|{title}]]')
open(os.path.join(out, 'Lessons.md'), 'w', encoding='utf-8').write('\n'.join(lessons) + '\n')
# 6. Links to pages that are not in the kids vault become plain text
names = set()
for d, _, fs in os.walk(out):
    for f in fs:
        if f.endswith('.md'): names.add(f[:-3])
dead = 0
def fix(m):
    global dead
    tgt, alias = m.group(1).split('#')[0].strip(), m.group(2)
    if tgt in names or not tgt: return m.group(0)
    dead += 1
    return alias if alias else m.group(1)
for d, _, fs in os.walk(out):
    if '/.obsidian' in d: continue
    for f in fs:
        if not f.endswith('.md'): continue
        p = os.path.join(d, f); t = open(p, encoding='utf-8').read()
        u = re.sub(r'(?<!!)\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', fix, t)
        if u != t: open(p, 'w', encoding='utf-8').write(u)
# 7. Γιαγιά plays only the Kids Core words (plus the kid extras)
gp = os.path.join(out, '.obsidian', 'plugins', 'greekquent-student-layout', 'apps', 'giagia.html')
g = open(gp, encoding='utf-8').read()
m = re.search(r'window\.GQ_WORDS=(\[.*?\]\]);', g)
gw = [x for x in json.loads(m.group(1)) if re.sub(r'^(ο|η|το|οι|τα) ', '', x[0].split(',')[0].strip()) in keep or x[0] in keep]
gw += [[w, x['english'], 1501 + i, 1, x['gpos']] for i, (w, x) in enumerate(extras.items())]
g = g[:m.start(1)] + json.dumps(gw, ensure_ascii=False, separators=(',', ':')) + g[m.end(1):]
old = "opt('top100', 'Top 100 words'); opt('top300', 'Top 300 words'); opt('top1500', 'All 1,500 words');"
assert old in g
g = g.replace(old, f"opt('top9999', 'All my words ({sum(1 for x in gw if x[2] > 12)})');")
open(gp, 'w', encoding='utf-8').write(g)
print(f'kids vault: {len(kids)} lessons, {len(os.listdir(os.path.join(out, "Words")))} words, {dead} links made plain, Γιαγιά has {len(gw)} words')
