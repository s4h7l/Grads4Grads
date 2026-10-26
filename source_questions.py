"""Extract explicitly supplied study Q&A and MCQs from a faculty PDF.

This is a conservative *structured* extractor. If source formatting doesn't match
an unambiguous numbered question and 4 choices plus a lettered answer key, it
skips the item rather than inventing answers. A human should review output.
"""
from __future__ import annotations
import re, hashlib, bisect

def clean(s):
    return re.sub(r'\s+', ' ', s.replace('\uf0b7', '•')).strip()

def _source_pages(pdf):
    try: import fitz
    except ImportError: return []
    with fitz.open(pdf) as doc:
        return [p.get_text(sort=True) for p in doc]

def extract_pdf_mcqs(path, source_title, source_id, explanation_map=None):
    pages=_source_pages(path)
    if not pages: return []
    # Only parse a section explicitly titled multiple-choice questions, so
    # other numbered examples/assignments cannot accidentally become MCQs.
    text='\n'.join(pages)
    start=re.search(r'Part\s+B\s*[–-]\s*\d+\s+Multiple.Choice\s+Questions', text, flags=re.I)
    if not start: return []
    end=re.search(r'Part\s+C\s*[–-]',text[start.end():], flags=re.I)
    region=text[start.end(): start.end()+end.start()] if end else text[start.end():]
    base=start.end()
    matches=list(re.finditer(r'(?m)^\s*(\d{1,3})\.\s+',region))
    out=[]; seen=set()
    page_ends=[]; total=0
    for p in pages:
        total+=len(p)+1;page_ends.append(total)
    for k,m in enumerate(matches):
        number=int(m.group(1));next_start=matches[k+1].start() if k+1<len(matches) else len(region)
        chunk=region[m.end():next_start]
        answer=re.search(r'\bAnswer\s*:\s*([A-D])\b',chunk,re.I)
        if not answer: continue
        before=chunk[:answer.start()]
        options=list(re.finditer(r'(?<!\w)([A-D])\.\s+',before))
        if len(options)!=4 or [x.group(1) for x in options]!=list('ABCD'):continue
        prompt=clean(before[:options[0].start()]);opts=[]
        for i,op in enumerate(options):
            following=options[i+1].start() if i+1<len(options) else len(before)
            opts.append(clean(before[op.end():following]))
        if not prompt or any(len(x)<2 for x in opts) or len(set(opts))!=4:continue
        correct=ord(answer.group(1).upper())-65
        key=prompt.casefold()
        if key in seen:continue
        seen.add(key)
        page=bisect.bisect_right(page_ends,base+m.start())+1
        explanation=(explanation_map or {}).get(str(number))
        if not explanation:
            explanation=f'The notes identify “{opts[correct]}” as the correct response to this question.'
        out.append({'id':'doc-'+hashlib.sha256((source_id+str(number)+prompt).encode()).hexdigest()[:12],
                    'prompt':prompt, 'options':opts, 'correct':correct,
                    'explanation':explanation,
                    'source':f'{source_title} · PDF p. {page} · Q{number}',
                    'source_page':page, 'source_number':number})
    return out

def extract_pdf_qa(path,source_title):
    pages=_source_pages(path)
    if not pages:return []
    text='\n'.join(pages)
    start=re.search(r'Part\s+A\s*[–-]\s*\d+\s+Questions\s+and\s+Answers',text,re.I)
    if not start:return []
    end=re.search(r'Part\s+B\s*[–-]',text[start.end():],re.I)
    region=text[start.end():start.end()+end.start()] if end else text[start.end():]
    header=re.compile(r'(?m)^\s*(\d{1,3})\.\s+(.{8,180}?)\n\s*Answer\s*:',re.I)
    headers=list(header.finditer(region));qas=[]
    for i,match in enumerate(headers):
        until=headers[i+1].start() if i+1<len(headers) else len(region)
        part=region[match.end():until]
        part=re.sub(r'(?m)^\s*Topic\s+\d+\s*:[^\n]*', '', part)
        part=re.sub(r'(?m)^\s*\d{1,3}\s*$', '', part)
        answer=clean(part)
        question=clean(match.group(2))
        if not answer or not question:continue
        qas.append({'question':question,'answer':answer,'source':source_title,'source_number':int(match.group(1))})
    return qas
