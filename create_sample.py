"""Creates explicitly labelled DEMO files. Not faculty content."""
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
import hashlib,json,shutil
root=Path(__file__).resolve().parent
notes=root/'content/notes'
files=root/'content/files';files.mkdir(exist_ok=True)
text=(notes/'PEA101_demo.md').read_text()
pdf=files/'pea101-demo-notes.pdf'
doc=SimpleDocTemplate(str(pdf),pagesize=(595,842),topMargin=48,bottomMargin=45,leftMargin=52,rightMargin=52)
st=getSampleStyleSheet()
st.add(ParagraphStyle(name='DemoTitle',parent=st['Title'],fontSize=19,leading=25,textColor=colors.HexColor('#2a5379'),spaceAfter=16,alignment=TA_LEFT))
st.add(ParagraphStyle(name='DemoBody',parent=st['Normal'],fontSize=10.5,leading=17,textColor=colors.HexColor('#344963'),spaceAfter=8))
from xml.sax.saxutils import escape
story=[Paragraph('GRADS4GRADS · SAMPLE NOTES — DEMO ONLY',st['DemoTitle']),Paragraph('Illustrative content for testing the PDF viewer and auto-generated quiz. NOT provided by faculty.',st['DemoBody']),Spacer(1,16)]
for line in text.splitlines():
    if not line.strip() or line.lstrip().startswith(('#','>')):continue
    story.append(Paragraph(escape(line),st['DemoBody']))
doc.build(story)
shutil.copy2(notes/'PEA105_demo.md',files/'pea105-demo-notes.md')
recs=[{'id':'demo-pea101','subject':'PEA 101','type':'pdf','file':pdf.name,'title':'SAMPLE — Problem Solving Notes (PDF)','added':'2026-10-23','sample':True},
      {'id':'demo-pea105','subject':'PEA 105','type':'file','file':'pea105-demo-notes.md','title':'SAMPLE — Data Structures Notes','added':'2026-10-23','sample':True}]
(root/'content/links.json').write_text(json.dumps(recs,indent=2))
print('Created sample PDF',pdf.stat().st_size)
