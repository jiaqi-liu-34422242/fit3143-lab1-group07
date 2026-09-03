from pathlib import Path
import math
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Flowable, Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
    TableStyle,
)
from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing, Line, PolyLine, Rect, String

ROOT = Path('/Users/liujiaqi/Documents/FIT3143/lab01/group07/applied1')
FIG = ROOT / 'figures'
OUT = ROOT / 'FIT3143_Applied1_Report.pdf'
FIG.mkdir(exist_ok=True)

BLUE = '#2563EB'
INK = '#111827'
MUTED = '#5B6470'
LIGHT = '#E0F2FE'
RULE = '#CBD5E1'
BPS = 1_000_000_000

def service_us(byte_count):
    return byte_count * 8 / BPS * 1e6

def line_chart(title, x_labels, series, y_label):
    """Create a lightweight ReportLab chart and export a matching SVG."""
    w, h = 16.2 * cm, 8.45 * cm
    d = Drawing(w, h)
    left, bottom, right, top = 1.65 * cm, 1.15 * cm, w - .35 * cm, h - .9 * cm
    values = [v for _, vals, _ in series for v in vals]
    ymin, ymax = 0, max(values) * 1.12 if max(values) else 1
    d.add(Rect(0, 0, w, h, fillColor=colors.white, strokeColor=colors.HexColor(RULE)))
    d.add(String(w/2, h-.42*cm, title, textAnchor='middle', fontName='Helvetica-Bold', fontSize=9.5, fillColor=colors.HexColor(INK)))
    d.add(Line(left, bottom, left, top, strokeColor=colors.HexColor(INK), strokeWidth=.8))
    d.add(Line(left, bottom, right, bottom, strokeColor=colors.HexColor(INK), strokeWidth=.8))
    for i in range(5):
        y = bottom + (top-bottom)*i/4
        value = ymin + (ymax-ymin)*i/4
        d.add(Line(left, y, right, y, strokeColor=colors.HexColor('#E5E7EB'), strokeWidth=.5))
        d.add(String(left-.12*cm, y-2, f'{value:.2f}', textAnchor='end', fontName='Helvetica', fontSize=6.5, fillColor=colors.HexColor(MUTED)))
    for i, lab in enumerate(x_labels):
        x = left + (right-left)*i/(len(x_labels)-1)
        d.add(String(x, bottom-.25*cm, str(lab), textAnchor='middle', fontName='Helvetica', fontSize=6.5, fillColor=colors.HexColor(MUTED)))
    d.add(String(.28*cm, (top+bottom)/2, y_label, fontName='Helvetica', fontSize=6.5, fillColor=colors.HexColor(MUTED), angle=90))
    legend_y = top-.15*cm
    for idx, (label, vals, colour) in enumerate(series):
        pts=[]
        for i,v in enumerate(vals):
            x=left+(right-left)*i/(len(vals)-1); y=bottom+(top-bottom)*(v-ymin)/(ymax-ymin)
            pts.extend([x,y])
        d.add(PolyLine(pts, strokeColor=colors.HexColor(colour), strokeWidth=1.8))
        for i in range(0,len(pts),2):
            d.add(Rect(pts[i]-1.6,pts[i+1]-1.6,3.2,3.2,fillColor=colors.HexColor(colour),strokeColor=colors.HexColor(colour)))
        ly=legend_y-idx*.32*cm
        d.add(Line(right-5.7*cm,ly,right-5.35*cm,ly,strokeColor=colors.HexColor(colour),strokeWidth=1.8))
        d.add(String(right-5.25*cm,ly-2,label,fontName='Helvetica',fontSize=6.2,fillColor=colors.HexColor(INK)))
    return d

def make_charts():
    nodes=[64,128,256,512,1024,2048,4096]; status=service_us(40)
    node_proxy=[status/(1-(n/4*100*status/1e6)) for n in nodes]
    c1=line_chart('Delay model versus charging nodes (S = 4, f = 100 rounds/s)',nodes,[('QUERY raw',[service_us(16)]*len(nodes),'#64748B'),('REPLY raw',[service_us(32)]*len(nodes),'#0F766E'),('STATUS raw',[status]*len(nodes),'#7C3AED'),('STATUS queue proxy',node_proxy,BLUE)],'microseconds')
    bases=[1,2,4,8,16,32,64]
    base_proxy=[status/(1-(4096/s*50*status/1e6)) for s in bases]
    coord=[2*.5*math.log2(s)+service_us(24)+service_us(16) for s in bases]
    c2=line_chart('Delay model versus base stations (N = 4096, f = 50 rounds/s)',bases,[('QUERY raw',[service_us(16)]*len(bases),'#64748B'),('STATUS queue proxy',base_proxy,BLUE),('Bcast + MINLOC proxy',coord,'#0F766E')],'microseconds')
    freq=[1,50,100,200,300,400,500,600,700]
    fproxy=[status/(1-(4096/4*f*status/1e6)) for f in freq]
    c3=line_chart('Base-ingress queue proxy versus update frequency (N = 4096, S = 4)',freq,[('STATUS delay proxy',fproxy,BLUE)],'microseconds')
    for drawing,name in ((c1,'delay_vs_nodes.svg'),(c2,'delay_vs_bases.svg'),(c3,'delay_vs_frequency.svg')):
        renderSVG.drawToFile(drawing,str(FIG/name))
    return c1,c2,c3

class ArchitectureDiagram(Flowable):
    def __init__(self, width=17.5*cm, height=5.0*cm):
        super().__init__()
        self.width, self.height = width, height
    def draw(self):
        c = self.canv
        c.setStrokeColor(colors.HexColor(RULE)); c.setFillColor(colors.HexColor('#F8FAFC'))
        c.roundRect(0, 5, 6.0*cm, self.height-10, 7, fill=1, stroke=1)
        c.setFillColor(colors.HexColor(LIGHT)); c.roundRect(11.5*cm, 5, 6.0*cm, self.height-10, 7, fill=1, stroke=1)
        c.setFillColor(colors.HexColor(INK)); c.setFont('Helvetica-Bold', 11)
        c.drawString(0.45*cm, self.height-0.75*cm, 'Local sensing plane')
        c.drawString(11.95*cm, self.height-0.75*cm, 'Regional control plane')
        c.setFont('Helvetica', 8.5)
        c.drawString(0.45*cm, self.height-1.25*cm, 'ChargingNode contains ports[P]')
        c.drawString(11.95*cm, self.height-1.25*cm, 'BaseStation owns a region')
        # local node arrows and nodes
        c.setStrokeColor(colors.HexColor(BLUE)); c.setLineWidth(1.7)
        for y in (1.7*cm, 3.0*cm):
            c.line(1.65*cm, y, 3.2*cm, y)
        c.line(1.65*cm, 1.7*cm, 1.65*cm, 3.0*cm)
        c.line(3.2*cm, 1.7*cm, 3.2*cm, 3.0*cm)
        c.setFillColor(colors.white)
        for x, y in ((1.45*cm,1.5*cm),(3.0*cm,1.5*cm),(1.45*cm,2.8*cm),(3.0*cm,2.8*cm)):
            c.circle(x,y,0.20*cm,fill=1,stroke=1)
        c.setFillColor(colors.HexColor(BLUE)); c.line(6.1*cm,2.35*cm,11.35*cm,2.35*cm)
        c.setFillColor(colors.HexColor(INK)); c.setFont('Helvetica-Bold', 8.5)
        c.drawCentredString(8.7*cm,2.55*cm,'STATUS_REPORT / ALERT')
        c.setFillColor(colors.white); c.roundRect(13.0*cm,1.65*cm,2.5*cm,1.4*cm,5,fill=1,stroke=1)
        c.setFillColor(colors.HexColor(INK)); c.setFont('Helvetica-Bold',9)
        c.drawCentredString(14.25*cm,2.48*cm,'BaseStation')
        c.setFont('Helvetica',8); c.drawCentredString(14.25*cm,2.15*cm,'cache + log + search')

class SequenceDiagram(Flowable):
    def __init__(self, width=17.5*cm, height=7.2*cm):
        super().__init__(); self.width, self.height = width, height
    def draw(self):
        c=self.canv; xs=[1.4*cm,5.6*cm,9.8*cm,14.0*cm]; labels=['Node','Neighbours','Assigned base','Other bases']
        c.setStrokeColor(colors.HexColor(RULE)); c.setLineWidth(.6); c.setDash(3,3)
        for x,label in zip(xs,labels):
            c.line(x,.35*cm,x,self.height-.55*cm)
            c.setDash(); c.setFillColor(colors.HexColor(INK)); c.setFont('Helvetica-Bold',8.5); c.drawCentredString(x,self.height-.35*cm,label); c.setDash(3,3)
        c.setDash(); c.setStrokeColor(colors.HexColor(BLUE)); c.setLineWidth(1.2)
        events=[(6.1*cm,0,2,'STATUS_REPORT'),(5.1*cm,0,1,'QUERY / REPLY'),(3.8*cm,0,2,'ALERT'),(2.7*cm,2,3,'Bcast(alert)'),(1.65*cm,2,3,'Allreduce(MINLOC)'),(.75*cm,2,0,'REDIRECT')]
        for y,a,b,label in events:
            x1,x2=xs[a],xs[b]; c.line(x1,y,x2,y)
            sign=1 if x2>=x1 else -1; c.line(x2,y,x2-sign*.18*cm,y+.10*cm); c.line(x2,y,x2-sign*.18*cm,y-.10*cm)
            c.setFillColor(colors.HexColor(INK)); c.setFont('Helvetica',8); c.drawCentredString((x1+x2)/2,y+.12*cm,label)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='RptTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=23, leading=28, textColor=colors.HexColor(INK), spaceAfter=10))
styles.add(ParagraphStyle(name='RptSub', parent=styles['Normal'], fontName='Helvetica', fontSize=10.5, leading=14, textColor=colors.HexColor(MUTED), spaceAfter=8))
styles.add(ParagraphStyle(name='RptH1', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=colors.HexColor(INK), spaceBefore=13, spaceAfter=7))
styles.add(ParagraphStyle(name='RptH2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor(BLUE), spaceBefore=9, spaceAfter=5))
styles.add(ParagraphStyle(name='RptBody', parent=styles['BodyText'], fontName='Helvetica', fontSize=9.3, leading=13.2, textColor=colors.HexColor('#1F2937'), spaceAfter=6))
styles.add(ParagraphStyle(name='RptSmall', parent=styles['BodyText'], fontName='Helvetica', fontSize=7.7, leading=9.7, textColor=colors.HexColor('#1F2937')))
styles.add(ParagraphStyle(name='RptHead', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=7.7, leading=9.7, textColor=colors.white))
styles.add(ParagraphStyle(name='RptQuote', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=10, leading=14, textColor=colors.HexColor(INK), leftIndent=8, rightIndent=8, spaceAfter=8))

def p(txt, st='RptBody'):
    return Paragraph(txt, styles[st])

def styled_table(rows, widths, highlight=None):
    data = [[p(cell, 'RptHead' if r == 0 else 'RptSmall') for cell in row] for r,row in enumerate(rows)]
    t=Table(data,colWidths=widths,repeatRows=1)
    cmds=[('BACKGROUND',(0,0),(-1,0),colors.HexColor(INK)),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.35,colors.HexColor(RULE)),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F8FAFC')])]
    if highlight is not None: cmds.append(('BACKGROUND',(0,highlight),(-1,highlight),colors.HexColor(LIGHT)))
    t.setStyle(TableStyle(cmds)); return t

def footer(canvas, doc):
    canvas.saveState(); canvas.setStrokeColor(colors.HexColor(RULE)); canvas.line(1.8*cm,1.35*cm,19.2*cm,1.35*cm)
    canvas.setFillColor(colors.HexColor(MUTED)); canvas.setFont('Helvetica',7.5); canvas.drawString(1.8*cm,.88*cm,'FIT3143 Applied #1 - EVCNS Design Report | Group 07'); canvas.drawRightString(19.2*cm,.88*cm,f'Page {doc.page}'); canvas.restoreState()

def build_report():
    c1,c2,c3=make_charts()
    story=[]
    story += [p('Distributed EV Charging Navigation System','RptTitle'),p('FIT3143 Applied #1 - Network topology, MPI architecture, and communication analysis','RptSub'),p('<b>Team:</b> Group 07 &nbsp;&nbsp; <b>Students:</b> [replace with names, IDs, and Monash emails]','RptSub'),Spacer(1,.35*cm)]
    story += [p('<b>Executive decision.</b> We model three different communication scopes: a non-periodic 2-D logical mesh for local charging-node sensing, a region-sharded star forest for direct node-to-base reporting, and a small base-station control overlay for global redirection. The mesh is a logical regular-area baseline, not a claim that physical EV stations form a grid.','RptQuote'),PageBreak()]

    story += [p('1. Task 1 - Network topology','RptH1'),p('The 3 x 3 drawing in the specification is illustrative. Physical station placement is external to this assessment; the design task is to choose logical communication relationships. Immediate adjacency is logical: it neither guarantees the geographically closest station nor asserts a dedicated physical cable. The simulator must distinguish physical deployment, logical topology, and MPI process placement.','RptBody')]
    top_rows=[['Topology','Degree','Diameter','Cost','EVCNS fit'],['Linear array','1-2','N-1','N-1','Poor 2-D locality; O(N) remote path.'],['Ring','2','floor(N/2)','N','Only two neighbours; artificial wrap-around.'],['Star','1 / N-1','2','N','Good reporting hub, not local sensing.'],['Binary tree','1-3','O(log N)','N-1','Parent-child is not geographic locality.'],['2-D mesh','2-4','O(sqrt(N))','O(N)','Selected local logical baseline.'],['2-D torus','4','O(sqrt(N))','O(N)','False boundary neighbours.'],['3-D mesh / cube','3-6','O(N^(1/3))','O(N)','Unnatural third locality dimension.'],['Hypercube','log2(N)','log2(N)','N log2(N)/2','Non-geographic edges; growing degree.'],['Fully connected','N-1','1','N(N-1)/2','Not scalable for large N.']]
    story += [styled_table(top_rows,[2.4*cm,1.35*cm,1.85*cm,2.05*cm,10.2*cm],highlight=5),Spacer(1,.25*cm)]
    story += [p('The selected hybrid topology applies each topology only where it fits: mesh for local sensing, regional stars for reporting, and a small inter-base control overlay for global coordination. For an R x C mesh, E = R(C - 1) + C(R - 1) = 2N - R - C, so the local link cost grows linearly. A strongly irregular deployment is an explicit future extension using a configured adjacency graph.','RptBody'),PageBreak()]

    story += [p('2. Task 2 - MPI simulation architecture','RptH1'),p('Each ChargingNode contains its own ChargingPort objects. A port is local shared-memory state rather than a separate MPI rank. A BaseStation owns a region, maintains a cache and event log, and coordinates redirects.','RptBody'),ArchitectureDiagram(),Spacer(1,.18*cm)]
    msg_rows=[['Message / operation','Direction','Trigger','Purpose'],['STATUS_REPORT','node -> assigned base','Every round','Refresh cache and log.'],['QUERY','heavy node -> local neighbours','utilisation > threshold','Request local utilisation.'],['NEIGHBOUR_REPLY','neighbour -> querying node','On QUERY','Return availability and utilisation.'],['ALERT','node -> assigned base','node and all valid neighbours heavy','Report local saturation.'],['Bcast + Allreduce(MINLOC)','bases','Every alert','Select globally nearest available candidate.'],['REDIRECT','owner base -> alerting node','Candidate selected','Return target or no availability.']]
    story += [styled_table(msg_rows,[3.3*cm,3.2*cm,4.15*cm,7.2*cm]),Spacer(1,.18*cm)]
    story += [p('Ranks 0 ... S-1 represent base stations and ranks S ... S+N-1 represent charging nodes. node_comm contains charging nodes; cart_comm is its non-periodic Cartesian topology; base_comm contains bases. MPI provides inter-process communication. OpenMP is used only when a sufficiently large ports[P] scan benefits from local shared-memory parallelism; MPI calls remain master-thread only under MPI_THREAD_FUNNELED.','RptBody'),PageBreak()]

    story += [p('3. Task 2 - communication sequence','RptH1'),p('Every node reports status each round. Neighbour queries occur only when the local utilisation is above the user-configured threshold. Missing or stale neighbour data never proves all neighbours are busy; it produces an incomplete assessment and withholds the all-neighbours alert.','RptBody'),SequenceDiagram(),Spacer(1,.2*cm),p('For every alert, every base supplies its regional nearest candidate. This is required because an available candidate in the source region is not necessarily globally closest. Allreduce(MINLOC) therefore remains in the correctness path.','RptBody'),PageBreak()]

    story += [p('4. Task 3 - communication analysis','RptH1'),p('The cluster is modelled with 1 Gbps links. For a payload L bytes and a fabric hop count H_fabric that is constant with respect to N, the serialisation component is T_tx = 8 L H_fabric / B. In the figures, H_fabric = 1 is an equivalent-link assumption. Real MPI wall-clock time additionally includes startup, switching, contention, and queueing.','RptBody')]
    size_rows=[['Message','Payload assumption','Scaling result'],['QUERY','16 B','One transfer O(1); total local traffic O(N).'],['NEIGHBOUR_REPLY','32 B','One transfer O(1); total local traffic O(N).'],['STATUS_REPORT','40 B','One transfer O(1); per-base ingress O(N/S).'],['ALERT','24 B','O(A) traffic per round, where 0 <= A <= N.'],['REDIRECT','32 B','O(A) traffic per round.'],['Bcast + MINLOC','24 B + 16 B','O(log S) critical path per alert.']]
    story += [styled_table(size_rows,[3.6*cm,3.2*cm,11.05*cm]),Spacer(1,.2*cm)]
    story += [p('For a mesh with E = 2N - R - C, the worst-case local message count is 2E QUERYs plus 2E replies: 4E = O(N). If A alerts occur in one round, tree-based collective coordination has critical path O(A log S). In the worst case A = N, this is O(N log S). More bases reduce regional ingress from approximately N to N/S but increase collective depth logarithmically; the outcome is diminishing returns. When S = 1, coordination is a singleton operation and the only base cache is global.','RptBody')]
    for chart, caption in [(c1,'Figure 1. Raw serialisation is constant per direct message; the blue curve is a stated base-ingress queue proxy.'),(c2,'Figure 2. More bases reduce report ingress pressure, while collective coordination depth grows.'),(c3,'Figure 3. Higher update frequency increases offered base load and queueing near capacity.')]:
        story += [chart,p(caption,'RptSmall'),Spacer(1,.15*cm)]
    story += [PageBreak()]

    story += [p('5. Limitations, future work, and references','RptH1'),p('This report makes a logical regular-area mesh assumption and uses analytical payload/queueing models. It does not replace measurements on the target cluster. A production system would add irregular configured adjacency graphs, stale-data expiry, failure detection, authentication, and durable storage.','RptBody'),p('Presentation conclusion','RptH2'),p('We use a non-periodic 2-D logical mesh for bounded local sensing, regional stars for node reporting, and a small control overlay for globally correct redirection. This hybrid architecture models each communication scope with a topology appropriate to its scale and purpose.','RptQuote'),p('References','RptH2')]
    for r in ['FIT3143 Applied #1 - Distributed Wireless Sensor Network assessment specification.','FIT3143 Applied #1 marking rubric.','FIT3143 Topic 5 - network topology and MPI material.','Teaching-team Ed clarification: 3 x 3 is illustrative; immediate adjacency is required; physical EV nodes are not constructed by students; choose a topology or hybrid topology for a real-life situation.']:
        story += [p('• '+r,'RptBody')]
    story += [p('<b>Before submission:</b> replace student placeholders and attach the required AI declaration and complete prompt records.','RptBody')]
    doc=SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=1.8*cm,rightMargin=1.8*cm,topMargin=1.65*cm,bottomMargin=1.7*cm,title='FIT3143 Applied #1 EVCNS Design Report')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)

if __name__ == '__main__':
    build_report()
    print(OUT)
