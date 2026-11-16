#!/usr/bin/env python3
"""Build the Greekquent Kids vault from the student vault.
Usage: build_kids.py <student vault folder> <output folder>
Run it again any week: it rebuilds the kids copy from the current student vault, so nothing is written twice.
Keeps: the kid lessons, every word note (trimmed for kids), the Γιαγιά game and the plugin.
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
os.makedirs(os.path.join(out, 'Words'))
for f in os.listdir(os.path.join(src, 'Words')):
    t = open(os.path.join(src, 'Words', f), encoding='utf-8').read()
    t = re.sub(r' · first in \[\[[^\]]+\]\]', '', t)
    t = re.sub(r'\n- …and \d+ more in the lesson scripts below', '', t)
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
print(f'kids vault: {len(kids)} lessons, {len(os.listdir(os.path.join(out, "Words")))} words, {dead} links made plain')
