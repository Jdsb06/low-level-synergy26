"""Generate the concise review report; optional reportlab dependency only."""
from pathlib import Path
import hashlib
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted

ROOT = Path(__file__).resolve().parents[1]
NAVY = colors.HexColor('#15324c')
TEAL = colors.HexColor('#087e8b')
LIGHT = colors.HexColor('#edf4f7')


def main():
    fonts = Path('/usr/share/fonts/truetype/dejavu')
    pdfmetrics.registerFont(TTFont('Review', str(fonts / 'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('ReviewBold', str(fonts / 'DejaVuSans-Bold.ttf')))
    pdfmetrics.registerFont(TTFont('ReviewMono', str(fonts / 'DejaVuSansMono.ttf')))
    pdfmetrics.registerFontFamily('Review', normal='Review', bold='ReviewBold')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReviewBody', fontName='Review', fontSize=9.4, leading=14,
                              textColor=NAVY, spaceAfter=8))
    styles.add(ParagraphStyle(name='ReviewTitle', fontName='ReviewBold', fontSize=24, leading=29,
                              textColor=NAVY, spaceAfter=12))
    styles.add(ParagraphStyle(name='ReviewHead', fontName='ReviewBold', fontSize=13, leading=18,
                              textColor=TEAL, spaceBefore=11, spaceAfter=7))
    styles.add(ParagraphStyle(name='ReviewSmall', fontName='Review', fontSize=8, leading=11,
                              textColor=NAVY, spaceAfter=6))
    styles.add(ParagraphStyle(name='ReviewCode', fontName='ReviewMono', fontSize=8, leading=12,
                              textColor=NAVY, spaceAfter=10))
    story = []

    def p(text, style='ReviewBody'):
        story.append(Paragraph(text, styles[style]))

    def heading(text):
        p(text, 'ReviewHead')

    def table(rows, widths):
        data = [[Paragraph(escape(str(cell)), styles['ReviewSmall']) for cell in row] for row in rows]
        t = Table(data, colWidths=widths, hAlign='LEFT', repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('VALIGN',(0,0),(-1,-1),'TOP'),
                              ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
                              ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),5),
                              ('LINEBELOW',(0,0),(-1,0),.6,TEAL),
                              ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f7f9fa')])]))
        story.append(t)
        story.append(Spacer(1,8))

    p('libmemctl', 'ReviewTitle')
    p('SYSPROG10 / Systems Programming / Technical report', 'ReviewHead')
    p('<b>Jashandeep Singh</b> - solo participant - IMT2024022<br/>13 November 2026')
    p('A C11 Linux allocator providing the four required my_* functions through private anonymous mappings. '
      'The current source combines reusable small-object regions, eight shards and capped dedicated-mapping '
      'reuse for requests above 64 KiB through 1 MiB. The report covers design, measured trade-offs and executed validation; no official score is claimed.')
    heading('Measured improvement and cost')
    p('Five fresh processes per case on a shared i3-1315U laptop, GCC 15.2.0 and glibc 2.43. '
      'The comparison uses the pinned baseline without large-mapping reuse, with identical traces and flags.  '
      'Small/mixed throughput below uses the longer five-million-call confirmation.')
    table([['Throughput (M API calls/s)','Threads','Old','Current'],
           ['Small',1,'38.277','37.293'],['Small',8,'60.753','59.870'],
           ['Mixed',1,'29.486','30.650'],['Mixed',8,'57.639','51.240'],
           ['Large',1,'0.165','0.235'],['Large',8,'0.0437','0.0740']], [260,55,85,85])
    p('<b>Large at eight threads:</b> throughput median rose 69.6%; malloc p99 fell from 1,784.819 to 1,105.217 microseconds (38.1%). '
      '<b>Costs:</b> eight-thread mixed-throughput median fell 11.1%, and held virtual memory in the full-touch large burst rose 34.7%. '
      'The corresponding resident-memory growth was nearly unchanged. One-thread large p99 rose 8.3%.')
    p('The mixed-throughput min-max ranges overlap, and clock, scheduling, thermal and desktop noise remain. '
      'These observations do not establish a universal speedup. See docs/report.md and results/benchmarks/ for the methodology, counts, seeds and ranges. The paired comparison was captured on 9 November 2026.', 'ReviewSmall')

    story.append(PageBreak())
    p('Design and correctness', 'ReviewTitle')
    heading('Core invariants')
    for text in [
        '<b>Ownership:</b> each region has one immutable shard/class owner; valid objects keep their backing region live. Cross-thread free follows that owner, including after producer exit.',
        '<b>Locking:</b> per-bin locks protect lists, counts and cache slots. No operation holds two allocator locks; realloc allocates/copies before releasing the old object.',
        '<b>Space:</b> 64 small classes cover requests through 64 KiB. Regions start compact, then grow after demand. Large reuse uses 64-KiB bands through 1 MiB; larger requests map directly.',
        '<b>Reclamation:</b> all empty caches share a 2 MiB reservation bound including mapping overhead. Trim removes only unused mappings. Sparse live objects can still pin large partially occupied regions.',
        '<b>API:</b> checked arithmetic, max alignment, explicit calloc zeroing and failure-preserving realloc. The implementation does not forward calls to the standard heap allocator.'
    ]:
        p(text)
    heading('Executed evidence')
    table([['Environment / check','Result and scope'],
           ['Ubuntu 26.04.1, GCC 13.4 / GCC 15.2','Native independent and six official tests; ASan/UBSan controls passed.'],
           ['ASan control subprocesses','59/59: 25 valid and 34 detected invalid accesses, including cached large boundaries.'],
           ['GCC 15 stress / TSan','Two million native mixed operations plus handoffs; ASan/UBSan and TSan soaks passed.'],
           ['NHPC GCC 9.3.1 / glibc 2.17','Current source built on login host; allocated compute job passed independent checks, one million operations and 131,072 handoffs.'],
           ['Linux 3.10 compatibility','Full-touch memory probe passed using a summed smaps RSS fallback; no cluster performance comparison.']], [185,300])
    p('Sanitizers do not prove correctness. LeakSanitizer was disabled for the documented host limitation. '
      'Address reuse can hide stale-pointer access; invalid/double frees are outside the API contract. '
      'Only the authored allocator mappings are covered by the independent reclamation accounting.', 'ReviewSmall')

    story.append(PageBreak())
    p('Evaluate and reproduce', 'ReviewTitle')
    heading('One-command evaluation')
    p('From the repository root, run the isolated evaluator. It verifies source and artifact integrity, '
      'builds fresh objects, checks forbidden allocator references, runs independent correctness tests '
      'and compiles/executes the public-API example. Each run saves exact commands, compiler version, '
      'stdout/stderr, exit codes and the source hash in its own build directory.')
    story.append(Preformatted('python3 scripts/evaluate.py\npython3 scripts/evaluate.py --sanitizers', styles['ReviewCode']))
    p('Only the optional --official-dir argument needs the separately obtained official public tests. '
      'The default check is offline. Linux x86-64, a C11 compiler, Make, binutils, pthreads, coreutils '
      'and Python 3.9+ are required; report/plot/video tooling is optional.')
    heading('Evidence map')
    table([['Artifact','Location'],
           ['Implementation / interface','src/allocator.c; include/libmemctl.h'],
           ['Design / methodology','docs/architecture.md; docs/report.md'],
           ['Throughput, latency and memory','results/benchmarks/'],
           ['Correctness and stress','results/correctness/'],
           ['Executed Linux environments','results/compatibility/'],
           ['Library / test executables','prebuilt/ (source and binary checksums included)'],
           ['Functional demonstration','demo/run_demo.sh; demo/terminal-replay.mp4']], [185,300])
    p('The results index links the selected paired comparisons, longer common-workload confirmation '
      'and current-source 1/2/4/8-thread scaling. Raw records preserve capture-time identifiers and '
      'paths. The supplied baseline has a pinned source hash and is compiled separately for comparisons. '
      'Current reproduction commands are in docs/reproduction.md.', 'ReviewSmall')
    heading('Attribution and sources')
    p('AI assistance was used for implementation, testing, analysis and documentation. Permission is '
      'attributed to the participant\'s report of SPOC phone confirmation, not to a published AI-code clause. '
      'The implementation and independent tests were authored for the permitted event window. '
      'Official kit copies are not redistributed.')
    p('<link href="https://github.com/Jdsb06/low-level-synergy26" color="#087e8b">Source, evaluator and recorded results</link><br/>'
      '<link href="https://github.com/rudra-shroff06/LLH-26/blob/d23ac1d865df4cdacf7ad8e9fff3e1d560761c46/Systems%20Programming/SYSPROG10/PROBLEM.md" color="#087e8b">Official selected statement, pinned d23ac1d</link>')
    p('Allocator SHA-256:', 'ReviewSmall')
    story.append(Preformatted(hashlib.sha256((ROOT/'src/allocator.c').read_bytes()).hexdigest(), styles['ReviewCode']))
    p('The video replays an actual preserved terminal run; it is not a desktop screen capture. '
      'No official normalization targets or hidden-test results are inferred. Benchmark limitations '
      'and the throughput/space costs are retained in the full report.', 'ReviewSmall')

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(TEAL)
        canvas.line(55,44,540,44)
        canvas.setFont('Review',7.5)
        canvas.setFillColor(NAVY)
        canvas.drawString(55,31,'libmemctl | SYSPROG10 | Jashandeep Singh')
        canvas.drawRightString(540,31,str(doc.page))
        canvas.restoreState()

    target=ROOT/'output/pdf/libmemctl-review.pdf'
    target.parent.mkdir(parents=True, exist_ok=True)
    doc=SimpleDocTemplate(str(target),pagesize=A4,rightMargin=55,leftMargin=55,topMargin=52,bottomMargin=60,
                          title='libmemctl - technical report',author='Jashandeep Singh',
                          creator='libmemctl review generator (AI assisted)',invariant=1)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(target)


if __name__=='__main__':
    main()
