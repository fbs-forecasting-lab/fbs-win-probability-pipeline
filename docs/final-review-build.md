# Build and inspect the final documentation review

This is a local documentation-only renderer. It imports no pipeline code, fits no
model and calls no API. The current four-page REVIEW DRAFT has a two-page core
and required tutorial/license/docstring appendices; it is not the final submission.

Sources:

- [PDF review text](final-documentation-review.md)
- [Longer unfinished working source](final-documentation-draft.md)
- [Renderer](../bin/build_review_pdf.py), [review dependencies](review-requirements.txt)
- [Actual inline omissions and compatibility plan](inline-docstring-review.md)
- [Monitoring review packet](monitoring-review-packet.md)
- [Monitoring HTML candidate](monitoring-review.html) and [publication proposal](monitoring-publication-review.md)

Use an isolated tooling environment rather than modifying the working application
environment. ReportLab 4.4.9 was already available in the bundled tooling runtime
for PM-10; no installation or application dependency change was made.

```bash
python3.14 -m venv /tmp/fbs-review-tools
/tmp/fbs-review-tools/bin/python -m pip install -r docs/review-requirements.txt
/tmp/fbs-review-tools/bin/python -B bin/build_review_pdf.py \
  --output "$PWD/data/processed/review-new/final-documentation-review.pdf"
```

Use a fresh output filename/directory. The renderer refuses existing output,
symlink paths and outputs outside `data/processed`. `:::license` inserts the
complete current LICENSE; `:::docstring` reads actual source text with AST,
without importing/executing a producer. Explicit `:::pagebreak` keeps the compact
core and appendices in order. Application tests are not required for prose/layout
changes; the renderer output and its refusal/links/content should be checked.

Render each page at readable resolution with an available PDF renderer and open
**every page**. Check headings, body text, code wrapping, tables, clipping, footer
and REVIEW DRAFT labels. Inspect PDF link annotations and source-relative targets;
relative links resolve to the reviewed feature-branch repository sources. Confirm
all 22 class names, exact full-license text and actual docstring excerpts survive
text extraction. A successful renderer exit alone is not visual QA.

For the HTML candidate, use a fresh unauthenticated local browser session. Check
1280-pixel desktop and 375-pixel narrow layouts, fixed report date, 53 pending
labels, unavailable rolling metrics and every approval safeguard. Check no
horizontal overflow, script/form/external asset requests or private identifiers.
The PM-08 original HTML is preserved; no pipeline renderer or report changed.

PM-10 preview/evidence directory: `data/processed/pm10-review-20261121/` (ignored).
The final preview filename and hashes are recorded in its review manifest; earlier
rendering iterations are preserved. No PDF, screenshots, private report/receipt,
settings response or runtime/package artifact is committed. No source is copied
to a publication branch and no hosting setting is changed.
