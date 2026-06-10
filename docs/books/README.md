# Computational chemistry books

This directory contains page-oriented Markdown extracted from the local PDF
references in `Books computational chemistry/`.

The conversion preserves page boundaries so architecture notes can cite a
stable source page. PDF extraction does not reconstruct equations, figures, or
multi-column layouts perfectly; consult the original PDF before making a
scientific claim or selecting a production calculation method.

Regenerate the files with:

```powershell
backend\.venv\Scripts\python.exe scripts\pdf_to_markdown.py `
  "Books computational chemistry" docs\books
```
