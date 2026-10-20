# Test fixtures

Unit tests generate their PDFs on the fly with PyMuPDF (`tests/conftest.py`: `make_pdf`,
`make_image_only_pdf`), so no binary files need to be committed for them.

For manual acceptance testing (project.md §13, criterion 2) place real sample files here, e.g.:

- `resume_a.pdf`, `resume_b.pdf`, `resume_c.pdf` — text-based resumes, different layouts
- `scanned.pdf` — image-only PDF
- `protected.pdf` — password-protected PDF
- `fake.pdf` — a non-PDF file renamed to `.pdf`
- `large.pdf` — larger than 1 MB
- `three_pages.pdf` — 3 pages
