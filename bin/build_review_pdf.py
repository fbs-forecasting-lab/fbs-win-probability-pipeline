"""Render the documentation review source offline; never run pipeline workloads.

Requires reportlab (see docs/review-requirements.txt). Output must be a new PDF
inside an ignored data/processed directory. Existing evidence is never replaced.
"""
import argparse
import ast
import html
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import simpleSplit
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak,
                               PageTemplate, Paragraph, Preformatted, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/fbs-forecasting-lab/fbs-win-probability-pipeline/blob/feature/final-readiness/'


def inline(text):
    """Escape source text and preserve explicit links/emphasis/inline variables."""
    text = html.escape(text)
    def link(match):
        label, url = match.groups()
        if not re.match(r'^(https://|mailto:)', url):
            url = REPO + 'docs/' + url
        return '<a href="'+url+'" color="#154c79">'+label+'</a>'
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    return re.sub(r'`([^`]+)`', r'<font name="Courier" size="8.2">\1</font>', text)


def docstring(path, name):
    """Read an actual first docstring paragraph without importing project code."""
    tree = ast.parse((ROOT/path).read_text())
    node = next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name)
    text = ast.get_docstring(node)
    if not text:
        raise ValueError('Selected inline docstring is absent.')
    return text.split('\n\n')[0].replace('\n', ' ')


def build(source, output):
    """Build a fresh linked review PDF from the small supported Markdown subset."""
    output = Path(output).absolute()
    if '..' in output.parts or output.suffix.lower() != '.pdf' or not output.is_relative_to(ROOT/'data/processed'):
        raise ValueError('Use a new PDF beneath ignored data/processed.')
    if any(p.is_symlink() for p in (output, *output.parents)) or output.exists():
        raise ValueError('Output exists or contains a symbolic link; nothing overwritten.')
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyReview', fontName='Helvetica', fontSize=10,
                             leading=13, spaceAfter=6, textColor=colors.HexColor('#1c2730')))
    styles.add(ParagraphStyle(name='TableReview', parent=styles['BodyReview'], fontSize=8.4, leading=10.8, spaceAfter=0))
    styles.add(ParagraphStyle(name='SmallReview', parent=styles['BodyReview'], fontSize=9, leading=11.5))
    styles['Heading1'].fontName='Helvetica-Bold';styles['Heading1'].fontSize=17;styles['Heading1'].leading=20;styles['Heading1'].spaceAfter=10
    styles['Heading2'].fontName='Helvetica-Bold';styles['Heading2'].fontSize=12;styles['Heading2'].leading=15;styles['Heading2'].spaceBefore=5;styles['Heading2'].spaceAfter=6
    styles['Heading3'].fontSize=10;styles['Heading3'].leading=13;styles['Heading3'].spaceAfter=4
    width=522
    story=[]
    lines=Path(source).read_text().splitlines();i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line==':::pagebreak':story.append(PageBreak());i+=1;continue
        if line==':::license':
            for paragraph in (ROOT/'LICENSE').read_text().strip().split('\n\n'):
                story.append(Paragraph(inline(paragraph.replace('\n',' ')),styles['SmallReview']))
            i+=1;continue
        if line.startswith(':::docstring '):
            path,name=line.split()[1:]
            story.append(Paragraph('<b>'+html.escape(name)+'</b>: '+html.escape(docstring(path,name)),styles['SmallReview']))
            i+=1;continue
        if line.startswith('```'):
            code=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                for part in simpleSplit(lines[i], 'Courier', 8.3, width-14):code.append(part)
                i+=1
            story.append(Preformatted('\n'.join(code),ParagraphStyle('CodeReview',fontName='Courier',fontSize=8.3,leading=11,backColor=colors.HexColor('#f1f4f6'),borderPadding=7,spaceAfter=9)))
            i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                row=[x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',x) for x in row):rows.append(row)
                i+=1
            n=len(rows[0]);widths=([145,377] if n==2 else [width/n]*n)
            cells=[[Paragraph(inline(x),styles['TableReview']) for x in row] for row in rows]
            table=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9eff4')),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#557087')),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#cbd4dc')),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
            story.extend([table,Spacer(1,6)]);continue
        if line.startswith('#'):
            mark,text=line.split(' ',1);story.append(Paragraph(inline(text),styles['Heading'+str(min(len(mark),3))]));i+=1;continue
        paragraph=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```',':::')):
            paragraph.append(lines[i].strip());i+=1
        story.append(Paragraph(inline(' '.join(paragraph)),styles['BodyReview']))
    def page(canvas, doc):
        canvas.saveState();canvas.setFont('Helvetica-Bold',8);canvas.setFillColor(colors.HexColor('#557087'))
        canvas.drawString(45,766,'FBS FORECASTING LAB  |  SUBMISSION CANDIDATE  |  NOVEMBER 22, 2026')
        canvas.setFont('Helvetica',8);canvas.drawString(45,27,'Saved retrospective demonstration. Operational forecast approval withheld.')
        canvas.drawRightString(567,27,str(doc.page));canvas.restoreState()
    with output.open('xb') as handle:
        doc=BaseDocTemplate(handle,pagesize=(612,792),leftMargin=45,rightMargin=45,topMargin=44,bottomMargin=42,
                            title='FBS Win Probability Pipeline - SUBMISSION CANDIDATE',author='Hampton Abbott',creator='FBS Forecasting Lab')
        doc.addPageTemplates(PageTemplate(id='review',frames=Frame(45,42,width,706,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0),onPage=page))
        doc.build(story)
    return output


def main():
    """Render only documentation; source and application environments stay untouched."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'docs/final-documentation-review.md')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(build(args.source,args.output))


if __name__=='__main__':
    main()
