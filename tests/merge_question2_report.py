"""Replace only Question 2 in the existing combined DOCX, preserving other parts."""
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import posixpath
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
ET.register_namespace('w', W)
ET.register_namespace('r', R)
path = ROOT / 'submission/23F-0590-0669_BSCS-7A_IS-A2.docx'
with ZipFile(path) as archive:
    files = {n: archive.read(n) for n in archive.namelist()}
with ZipFile(ROOT / 'submission/Part_2_Report.docx') as archive:
    source = {n: archive.read(n) for n in archive.namelist()}
doc = ET.fromstring(files['word/document.xml'])
body = doc.find(f'{{{W}}}body')
children = list(body)
text = lambda node: ''.join(t.text or '' for t in node.iter(f'{{{W}}}t'))
start = next(i for i, n in enumerate(children) if text(n) == 'Question 2 CampusHub Web Security Project')
end = next(i for i, n in enumerate(children) if i > start and text(n) == 'Submission Evidence Review')
newbody = ET.fromstring(source['word/document.xml']).find(f'{{{W}}}body')
newnodes = [deepcopy(n) for n in newbody if n.tag != f'{{{W}}}sectPr']
first_title = next(n for n in newnodes if text(n) == 'CampusHub Web Security Project')
first_title.find(f'.//{{{W}}}t').text = 'Question 2 CampusHub Web Security Project'
for i, n in enumerate(n for node in newnodes for n in node.iter() if n.tag.endswith('}docPr')):
    n.set('id', str(1000 + i))

# Import source styles under unique names so the rendered Part 2 layout survives.
styles = ET.fromstring(files['word/styles.xml'])
for node in list(styles):
    if (node.get(f'{{{W}}}styleId') or '').startswith('Q2_'):
        styles.remove(node)
srcstyles = ET.fromstring(source['word/styles.xml'])
stylemap = {n.get(f'{{{W}}}styleId'): 'Q2_' + n.get(f'{{{W}}}styleId') for n in srcstyles.findall(f'{{{W}}}style')}
for node in srcstyles.findall(f'{{{W}}}style'):
    node = deepcopy(node)
    node.set(f'{{{W}}}styleId', stylemap[node.get(f'{{{W}}}styleId')])
    node.attrib.pop(f'{{{W}}}default', None)
    for n in node.iter():
        value = n.get(f'{{{W}}}val')
        if n.tag in [f'{{{W}}}{k}' for k in ('basedOn', 'next', 'link')] and value in stylemap:
            n.set(f'{{{W}}}val', stylemap[value])
    styles.append(node)
for node in newnodes:
    for n in node.iter():
        value = n.get(f'{{{W}}}val')
        if n.tag in [f'{{{W}}}{k}' for k in ('pStyle', 'rStyle', 'tblStyle')] and value in stylemap:
            n.set(f'{{{W}}}val', stylemap[value])

rels = ET.fromstring(files['word/_rels/document.xml.rels'])
for node in list(rels):
    if (node.get('Id') or '').startswith('Q2Rel'):
        rels.remove(node)
srcrels = ET.fromstring(source['word/_rels/document.xml.rels'])
relmap = {}
for i, rel in enumerate(srcrels):
    if not rel.get('Type').endswith(('/image', '/hyperlink')):
        continue
    newrel = deepcopy(rel)
    rid = f'Q2Rel{i}'
    relmap[rel.get('Id')] = rid
    newrel.set('Id', rid)
    if rel.get('TargetMode') != 'External':
        original = posixpath.normpath(posixpath.join('word', rel.get('Target')))
        target = 'media/q2_' + posixpath.basename(original)
        files['word/' + target] = source[original]
        newrel.set('Target', target)
    rels.append(newrel)
for node in newnodes:
    for n in node.iter():
        for attr, value in list(n.attrib.items()):
            if attr.startswith('{' + R + '}') and value in relmap:
                n.set(attr, relmap[value])

for node in children[start:end]:
    body.remove(node)
for offset, node in enumerate(newnodes):
    body.insert(start + offset, node)
pagebreak = ET.fromstring(f'<w:p xmlns:w="{W}"><w:r><w:br w:type="page"/></w:r></w:p>')
body.insert(start + len(newnodes), pagebreak)
updates = {
    'Question 2 includes both modes,': 'Question 2 includes both versions, frontend and backend source, seed data, exact attack payloads, defenses and 41 browser captures dated 11 October 2026. Six HTTP regression test methods and all Chromium checks passed. The reliable external CSRF demonstration uses localhost:8001 and verifies authenticated server-side rejection in safe mode. Updated source and evidence are published on the complete-question2 GitHub branch.',
    'The checklist requires full-screen timestamped screenshots.': 'Part 1 explicitly requires full-screen screenshots with visible system date and time. Part 2 requires matching exploit and safe-version evidence; its browser captures include an application date and time. Part 1 requirements remain separate from this Question 2 update.'
}
for node in body:
    for prefix, replacement in updates.items():
        if text(node).startswith(prefix):
            ts = list(node.iter(f'{{{W}}}t'))
            ts[0].text = replacement
            for t in ts[1:]:
                t.text = ''
def serialize(root, original, extra=b''):
    data = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    declarations = dict(re.findall(rb'xmlns:([\w]+)="([^"]+)"', original + extra))
    present = dict(re.findall(rb'xmlns:([\w]+)="([^"]+)"', data))
    missing = b''.join(b' xmlns:' + prefix + b'="' + uri + b'"' for prefix, uri in declarations.items() if prefix not in present)
    pos = data.index(b'>', data.index(b'?>') + 2)
    return data[:pos] + missing + data[pos:]
files['word/document.xml'] = serialize(doc, files['word/document.xml'], source['word/document.xml'])
files['word/styles.xml'] = serialize(styles, files['word/styles.xml'], source['word/styles.xml'])
files['word/_rels/document.xml.rels'] = ET.tostring(rels, encoding='utf-8', xml_declaration=True)
output = path.with_suffix('.updated.docx')
with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
    for name, data in files.items():
        archive.writestr(name, data)
output.replace(path)
print('Combined Word report updated with 41 fresh Question 2 captures.')
