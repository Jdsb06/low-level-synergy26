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
    p('SYSPROG10 / Systems Programming / Review candidate', 'ReviewHead')
    p('<b>Jashandeep Singh</b> - solo participant - IMT2024022<br/>9 November 2026')
    p('A C11 Linux allocator providing the four required my_* functions through private anonymous mappings. '
      'The current source combines reusable small-object regions, eight shards and capped dedicated-mapping '
      'reuse for requests above 64 KiB through 1 MiB. This report is a review artifact, not an official score or submission receipt.')
    heading('Measured improvement and cost')
    p('Five fresh processes per case on a shared i3-1315U laptop, GCC 15.2.0 and glibc 2.43. '
      'The comparison uses the exact checkpoint-4 source with identical traces and flags. '
      'Small/mixed throughput below uses the longer five-million-call confirmation.')
    table([['Throughput (M API calls/s)','Threads','Old','Current'],
           ['Small',1,'38.277','37.293'],['Small',8,'60.753','59.870'],
           ['Mixed',1,'29.486','30.650'],['Mixed',8,'57.639','51.240'],
           ['Large',1,'0.165','0.235'],['Large',8,'0.0437','0.0740']], [260,55,85,85])
    p('<b>Large at eight threads:</b> throughput median rose 69.6%; malloc p99 fell from 1,784.819 to 1,105.217 microseconds (38.1%). '
      '<b>Costs:</b> eight-thread mixed-throughput median fell 11.1%, and held virtual memory in the full-touch large burst rose 34.7%. '
      'The corresponding resident-memory growth was nearly unchanged. One-thread large p99 rose 8.3%.')
    p('The mixed-throughput min-max ranges overlap, and clock, scheduling, thermal and desktop noise remain. '
      'These observations do not establish a universal speedup. See CHECKPOINT5.md and its raw JSON/CSV for counts, seeds, ranges and the retained initial trial.', 'ReviewSmall')

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
    p('Reproduce and review', 'ReviewTitle')
    heading('Clean source package')
    p('The review archives contain complete authored source, headers, tests, build instructions, design notes, '
      'benchmark evidence and a terminal test recording. An explicit file allowlist excludes official kits, '
      'credentials, other competitions and intermediate build products. Explicitly included prebuilt Linux binaries '
      'are separately labeled and verified. Each archive includes per-file SHA-256 checksums.')
    story.append(Preformatted('sha256sum -c MANIFEST.sha256\nmake check\nmake sanitize\nmake profiles benchmark\nbash demo/run_demo.sh', styles['ReviewCode']))
    p('Only make public-test requires the separately obtained official participant kit. '
      'Python 3.6+ suffices for the symbol checker; full evidence/package runners use Python 3.9+. '
      'PDF regeneration additionally uses reportlab. No API credit or paid service is required.')
    heading('Delivery review')
    p('The official form was inspected read-only on 9 November. Known values: Systems Programming, '
      'SYSPROG10 and the participant repository below. The YouTube demo field is explicitly optional. '
      'Institute/contact details, final access/deadline and any later organizer updates still need participant review. '
      'No form fields have been filled, no organizer has been contacted and no entry has been submitted.')
    heading('Attribution and sources')
    p('AI assistance was used for implementation, testing, analysis and documents. Permission is attributed '
      'to the participant\'s report of SPOC phone confirmation, not a published AI-code clause. '
      'Registration and solo identity are participant-confirmed; no portal receipt has been inspected.')
    p('<link href="https://github.com/Jdsb06/low-level-synergy26" color="#087e8b">Development repository and checkpoint evidence</link><br/>'
      '<link href="https://github.com/rudra-shroff06/LLH-26/blob/d23ac1d865df4cdacf7ad8e9fff3e1d560761c46/Systems%20Programming/SYSPROG10/PROBLEM.md" color="#087e8b">Official selected statement, pinned d23ac1d</link><br/>'
      '<link href="https://forms.cloud.microsoft/r/WDNMEiRVUG" color="#087e8b">Official submission form (review only)</link>')
    p('Current allocator SHA-256:', 'ReviewSmall')
    story.append(Preformatted(hashlib.sha256((ROOT/'src/allocator.c').read_bytes()).hexdigest(), styles['ReviewCode']))
    p('The terminal video is a rendered replay of an actual preserved terminal run, not an unedited desktop screen capture. '
      'Final upload requires separate explicit approval. Performance normalization targets were not supplied in the reviewed statement; no official points are calculated.', 'ReviewSmall')

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(TEAL)
        canvas.line(55,44,540,44)
        canvas.setFont('Review',7.5)
        canvas.setFillColor(NAVY)
        canvas.drawString(55,31,'Review candidate | Jashandeep Singh | 9 November 2026')
        canvas.drawRightString(540,31,str(doc.page))
        canvas.restoreState()

    target=ROOT/'output/pdf/libmemctl-review.pdf'
    target.parent.mkdir(parents=True, exist_ok=True)
    doc=SimpleDocTemplate(str(target),pagesize=A4,rightMargin=55,leftMargin=55,topMargin=52,bottomMargin=60,
                          title='libmemctl - review candidate',author='Jashandeep Singh',
                          creator='libmemctl review generator (AI assisted)',invariant=1)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(target)


if __name__=='__main__':
    main()
