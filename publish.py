#!/usr/bin/env python3
"""Grads4Grads owner's offline publisher. Run locally; never deploy Python or API keys."""
from __future__ import annotations
import argparse, base64, datetime as dt, hashlib, html, io, json, os, re, shutil, sys
from pathlib import Path
from urllib.parse import urlparse
from source_questions import extract_pdf_mcqs, extract_pdf_qa

ROOT=Path(__file__).resolve().parent
CONTENT=ROOT/'content'
SITE=ROOT/'site'
DATA=SITE/'data'
FILES=CONTENT/'files'
RESOURCES=SITE/'resources'
for folder in [CONTENT,SITE,DATA,FILES,RESOURCES]:folder.mkdir(parents=True,exist_ok=True)

def read_json(path,default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def write_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def slug(s):return re.sub(r'[^a-z0-9]+','',s.lower())[:32]
def now():return dt.date.today().isoformat()
def identifier(prefix,text):return f'{prefix}-{hashlib.sha256(text.encode()).hexdigest()[:12]}'
def code_ok(code):
    code=code.strip().upper().replace(' ','')
    if not any(slug(s['code'])==slug(code) for s in read_json(CONTENT/'subjects.json',[])):
        raise SystemExit(f'Unknown subject: {code}. Available: PEA101..PEA106')
    return next(s['code'] for s in read_json(CONTENT/'subjects.json',[]) if slug(s['code'])==slug(code))

def notify(title,message,subject=None):
    dest=CONTENT/'announcements.json'
    entries=read_json(dest,[])
    ident=identifier('n',title+message+str(dt.datetime.now().timestamp()))
    entries.append({'id':ident,'title':title,'message':message,'date':now(),'subject':subject})
    write_json(dest,entries)
    return ident

def add_file(args):
    code=code_ok(args.subject);p=Path(args.file).expanduser().resolve()
    if not p.is_file():raise SystemExit(f'File not found: {p}')
    if p.suffix.lower() not in {'.pdf','.docx','.txt','.md'}:raise SystemExit('Supported: .pdf, .docx, .txt, .md')
    if p.stat().st_size>30_000_000:raise SystemExit('File exceeds 30 MB limit')
    digest=hashlib.sha256(p.read_bytes()).hexdigest()[:12]
    name=f'{slug(code)}-{digest}{p.suffix.lower()}'
    dest=FILES/name
    if dest!=p:shutil.copy2(p,dest)
    links=read_json(CONTENT/'links.json',[])
    ident='file-'+digest
    if any(x.get('id')==ident for x in links):print('File already published; no changes made.');return
    links.append({'id':ident,'subject':code,'type': 'pdf' if p.suffix.lower()=='.pdf' else 'file','file':name,'title':args.title or p.stem,'added':now(),'sample':False})
    write_json(CONTENT/'links.json',links)
    notify(f'New {code} resource',f'{args.title or p.stem} is now available to study.',code)
    print(f'Added file {name} to {code}. Run `python publish.py publish` to update the student website.')

def add_link(args):
    code=code_ok(args.subject)
    u=urlparse(args.url)
    if u.scheme not in {'http','https'} or not u.netloc:raise SystemExit('Link must be an http(s) URL')
    records=read_json(CONTENT/'links.json',[])
    ident=identifier('link',code+args.url)
    if any(r['id']==ident for r in records):print('Link already published.');return
    records.append({'id':ident,'subject':code,'type':'link','title':args.title,'url':args.url,'added':now(),'sample':False})
    write_json(CONTENT/'links.json',records)
    notify(f'New {code} link',f'{args.title} was added to study resources.',code)
    print('Link added. Reminder: online Google Docs links are NOT extracted for quizzes. Export as PDF/DOCX and add-file to generate questions.')

def add_qa(args):
    code=code_ok(args.subject)
    qas=read_json(CONTENT/'qa.json',{})
    qas.setdefault(code,[]).append({'question':args.question,'answer':args.answer})
    write_json(CONTENT/'qa.json',qas)
    notify(f'New {code} Q&A',f'A question and answer was added: {args.question[:65]}',code)
    print('Q&A added. Run `python publish.py publish`.')

def extract_text(path:Path):
    if path.suffix.lower()=='.pdf':
        try:import fitz
        except ImportError:raise SystemExit('PDF extraction needs pymupdf: pip install -r requirements.txt')
        with fitz.open(path) as doc:return '\n'.join(page.get_text(sort=True) for page in doc)
    if path.suffix.lower()=='.docx':
        try:from docx import Document
        except ImportError:raise SystemExit('DOCX extraction needs python-docx: pip install -r requirements.txt')
        d=Document(str(path));parts=[p.text for p in d.paragraphs]
        for table in d.tables:
            for row in table.rows:parts.append(' | '.join(c.text for c in row.cells))
        return '\n'.join(parts)
    return path.read_text(encoding='utf-8-sig',errors='replace')

def extract_facts(content):
    """Conservative offline fact extraction for term: definition and clear term-is-definition sentences."""
    items=[]
    content=re.sub(r'\r\n?', '\n', content)
    for raw in content.splitlines():
        line=re.sub(r'\s+',' ',raw.strip()).strip(' -*\t')
        if not line or line.startswith(('>','#')):continue
        m=re.match(r'^([A-Za-z][A-Za-z0-9 /()+,\-]{2,65})\s*[:–]\s*(.{18,450})$',line)
        if not m:m=re.match(r'^([A-Z][A-Za-z0-9 /()\-]{2,55})\s+(?:is|are|refers to|means)\s+(.{18,450})$',line)
        if not m:continue
        term=m.group(1).strip(' .:-');definition=m.group(2).strip()
        if term.lower().startswith(('figure','table','page','example','note','chapter','unit','sample')):continue
        if definition[-1] not in '.!?':definition+='.'
        if not any(f[0].casefold()==term.casefold() for f in items):items.append((term,definition))
    return items[:150]

def questions_from_facts(facts,source,source_id):
    if len(facts)<4:return []
    q=[]
    for i,(term,definition) in enumerate(facts):
        peer=[d for j,(_,d) in enumerate(facts) if j!=i and d!=definition]
        if len(peer)<3:continue
        # Reproducible distractors so published questions are stable; student display randomizes each attempt.
        digest=hashlib.sha256((source_id+term).encode()).digest()
        start=int.from_bytes(digest[:3],'big')%len(peer)
        distractors=[peer[(start+k)%len(peer)] for k in range(3)]
        options=[definition]+distractors
        q.append({'id':identifier('q',source_id+term),'prompt':f'Which description best matches “{term}”?','options':options,'correct':0,'explanation':f'{term}: {definition}','source':source})
    return q

def ai_questions(source_text,source_title,subject,model):
    """Optional better questions from owner-side AI. No model or API key is ever shipped to students."""
    try:from openai import OpenAI
    except ImportError:raise RuntimeError('Install the openai Python package for --ai.')
    if not os.getenv('OPENAI_API_KEY'):raise RuntimeError('OPENAI_API_KEY is missing (needed only on your own computer).')
    instructions=('Create 8-16 useful multiple-choice questions from SOURCE TEXT ONLY for '+subject+'. '
                  'Return strictly JSON object {"questions":[{"prompt":"...","options":["...","...","...","..."],"correct":0,"explanation":"...","evidence":"exact short supporting excerpt"}]}. '
                  'correct is index 0..3. Every correct answer and explanation MUST be supported by the provided notes; '
                  'do not invent facts, do not ask about things absent from source. Provide plausible but wrong alternatives. '
                  'No markdown. Avoid duplicate prompts. The evidence must be copied verbatim from the source notes.')
    client=OpenAI()
    response=client.chat.completions.create(model=model,messages=[{'role':'system','content':instructions},{'role':'user','content':f'Source title: {source_title}\nSOURCE TEXT:\n{source_text[:22000]}'}],response_format={'type':'json_object'})
    payload=json.loads(response.choices[0].message.content)
    accepted=[]
    for item in payload.get('questions',[]):
        opts=item.get('options',[]);correct=item.get('correct',-1);evidence=item.get('evidence','')
        if not isinstance(opts,list) or len(opts)!=4 or len(set(opts))!=4 or not isinstance(correct,int) or correct not in range(4):continue
        if not evidence or evidence.strip() not in source_text:continue
        if not item.get('prompt') or not item.get('explanation'):continue
        accepted.append({'id':identifier('ai',source_title+item['prompt']),'prompt':item['prompt'],'options':opts,'correct':correct,'explanation':item['explanation'],'source':f'{source_title} · {evidence[:115]}'})
    return accepted

def markdown_to_html(text,title):
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>body{font:17px/1.8 system-ui,sans-serif;max-width:760px;margin:6vh auto;padding:0 25px;color:#314d6e;background:#f6fbff}article{background:white;border:1px solid #deebf8;border-radius:19px;padding:32px;white-space:pre-wrap}h1{color:#286aa3}</style></head><body><h1>'+html.escape(title)+'</h1><article>'+html.escape(text)+'</article></body></html>'

def original_pdf_page_previews(path, resource_key):
    """Publish lightweight external page images, keeping Subjects HTML small."""
    try:
        import fitz
        from PIL import Image
    except ImportError as exc:
        raise SystemExit('PDF page previews need pymupdf and Pillow: pip install -r requirements.txt') from exc
    folder=SITE/'pages'/Path(resource_key).stem
    folder.mkdir(parents=True, exist_ok=True)
    pages=[]
    with fitz.open(path) as doc:
        for index, pg in enumerate(doc):
            pix=pg.get_pixmap(matrix=fitz.Matrix(1.05,1.05),alpha=False)
            image=Image.open(io.BytesIO(pix.tobytes('png')))
            filename=f'{index+1:03d}.webp'
            image.save(folder/filename,format='WEBP',quality=64,method=4)
            pages.append({'image':'pages/'+Path(resource_key).stem+'/'+filename,
                          'text':pg.get_text(sort=True)[:220]})
    return pages

def publish(args):
    subjects=read_json(CONTENT/'subjects.json',[])
    links=read_json(CONTENT/'links.json',[])
    qa=read_json(CONTENT/'qa.json',{})
    announcements=read_json(CONTENT/'announcements.json',[])
    count=0
    preview_assets={}
    for s in subjects:
        code=s['code'];s['resources']=[];s['qa']=list(qa.get(code,[]));s['questions']=[]
        seen=set()
        for rec in links:
            if rec['subject']!=code:continue
            title=rec['title']
            if rec['type']=='link':
                s['resources'].append({'type':'link','title':title,'url':rec['url'],'added':rec['added'],'sample':rec.get('sample',False)})
                continue
            file=FILES/rec['file']
            if not file.is_file():print(f'WARNING: Missing {file}, skipping',file=sys.stderr);continue
            ext=file.suffix.lower()
            if ext=='.pdf':
                shutil.copy2(file,RESOURCES/file.name)
                preview_assets['resources/'+file.name]=original_pdf_page_previews(file,'resources/'+file.name)
                resource={'type':'pdf','path':'resources/'+file.name,'title':title,'added':rec['added'],'sample':rec.get('sample',False)}
                if rec.get('original_url'):resource['original_url']=rec['original_url']
            else:
                resource_name=file.stem+'.html'
                (RESOURCES/resource_name).write_text(markdown_to_html(extract_text(file),title),encoding='utf-8')
                resource={'type':'notes','path':'resources/'+resource_name,'title':title,'added':rec['added'],'sample':rec.get('sample',False)}
            s['resources'].append(resource)
            text=extract_text(file)
            if len(text.strip())<80:
                print(f'WARNING: {title} has little extractable text; quizzes need a text-based PDF or DOCX.',file=sys.stderr)
                continue
            src=title+(' (DEMO ONLY)' if rec.get('sample') else '')
            # When a faculty PDF already contains a labelled MCQ section, use its
            # actual question, choices and answer key, not invented alternatives.
            if ext=='.pdf':
                existing_qa={item['question'].casefold().strip() for item in s['qa']}
                for item in extract_pdf_qa(file,src):
                    if item['question'].casefold().strip() not in existing_qa:
                        s['qa'].append(item);existing_qa.add(item['question'].casefold().strip())
                explanations={}
                if rec.get('explanation_map'):
                    explanation_path=CONTENT / Path(rec['explanation_map']).name
                    explanations=read_json(explanation_path,{})
                auto=extract_pdf_mcqs(file,src,rec['id'],explanations)
            else:
                auto=[]
            if not auto:
                auto=questions_from_facts(extract_facts(text),src,rec['id'])
            if args.ai:
                try:
                    ai=ai_questions(text,src,code,args.model)
                    if ai:auto=ai
                    else:print(f'WARNING: AI returned no source-verifiable questions for {src}; falling back to definition questions.',file=sys.stderr)
                except Exception as exc:print(f'WARNING: AI unavailable for {src}: {exc}. Offline fallback used.',file=sys.stderr)
            for question in auto:
                if ext=='.pdf' and question.get('source_page'):
                    question['source_pdf']='resources/'+file.name
                if question['id'] not in seen:
                    s['questions'].append(question);seen.add(question['id'])
        curated=read_json(CONTENT/'curated_questions.json',{}).get(code)
        if curated is not None:
            s['questions']=curated
        count+=len(s['questions'])
        if not s['questions'] and s['resources']:
            print(f'NOTICE: {code} has resources but no generated questions yet. Use clear TERM: definition lines or --ai.',file=sys.stderr)
    payload={'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'subjects':subjects,'announcements':announcements}
    write_json(DATA/'published.json',payload)
    # Also embed a safe snapshot for opening subjects.html without a local server.
    html_file=SITE/'subjects.html'
    markup=html_file.read_text(encoding='utf-8')
    markup=re.sub(r'<script id="lectura-embedded" type="application/json">.*?</script>', '', markup,flags=re.DOTALL)
    markup=re.sub(r'<script id="lectura-pages" type="application/json">.*?</script>', '', markup,flags=re.DOTALL)
    embedded=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    previews=json.dumps(preview_assets,ensure_ascii=False,separators=(',',':')).replace('<',chr(92)+'u003c')
    markup=markup.replace('<script id="lectura-app">', f'<script id="lectura-embedded" type="application/json">{embedded}</script><script id="lectura-pages" type="application/json">{previews}</script><script id="lectura-app">')
    html_file.write_text(markup,encoding='utf-8')
    print(f'Published {len(subjects)} subjects, {sum(len(s["resources"]) for s in subjects)} resources, {count} source-grounded MCQs, {len(announcements)} notifications. Open site via preview server.')

def cli():
    p=argparse.ArgumentParser(description='Grads4Grads static website publisher (owner only)')
    sp=p.add_subparsers(dest='cmd',required=True)
    f=sp.add_parser('add-file',help='Publish PDF/DOCX/TXT/MD (automatically announce and generate quizzes)');f.add_argument('--subject',required=True);f.add_argument('--file',required=True);f.add_argument('--title');f.set_defaults(fn=add_file)
    l=sp.add_parser('add-link',help='Publish a Google Docs link or other reference');l.add_argument('--subject',required=True);l.add_argument('--title',required=True);l.add_argument('--url',required=True);l.set_defaults(fn=add_link)
    q=sp.add_parser('add-qa',help='Publish a question and answer');q.add_argument('--subject',required=True);q.add_argument('--question',required=True);q.add_argument('--answer',required=True);q.set_defaults(fn=add_qa)
    n=sp.add_parser('announce',help='Publish an update notification');n.add_argument('--title',required=True);n.add_argument('--message',required=True);n.add_argument('--subject');n.set_defaults(fn=lambda a: print('Added announcement',notify(a.title,a.message,code_ok(a.subject) if a.subject else None)))
    pub=sp.add_parser('publish',help='Build static student site from all content');pub.add_argument('--ai',action='store_true',help='Optional richer AI questions with OPENAI_API_KEY on owner laptop only');pub.add_argument('--model',default='gpt-4.1-mini',help='Model name for optional AI generation');pub.set_defaults(fn=publish)
    args=p.parse_args();args.fn(args)
if __name__=='__main__':cli()
