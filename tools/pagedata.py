#!/usr/bin/env python3
"""Fill the JSON data block of a reference page in docs/ (a guide, a map, a database).

  python3 tools/pagedata.py docs/guide/index.html DATA.json [--check]

A page keeps its data on one line between
    <script type="application/json" id="page-data">  and  </script>
and renders it with its own script, so the page stays one file with no build step. This replaces
what's between the markers with DATA.json, compacted. --check only reports whether the page is
up to date (exit 1 if not). The kit's guide/starter.html is a page with such a block.

A game's own data tool reads the original's tables and the English names from translation/, then
calls write() - so the page always uses the patch's names:

    import pagedata
    pagedata.write(paths.DOCS / 'guide' / 'index.html', data, check=args.check)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

START, END = '<script type="application/json" id="page-data">', '</script>'


def write(page, data, check=False):
    """Put data (JSON-serialisable) into page's data block; with check, only compare.
    Returns True when the page was already up to date."""
    page = Path(page)
    html = page.read_text(encoding='utf-8')
    a = html.find(START)
    b = html.find(END, a + len(START)) if a >= 0 else -1
    if a < 0 or b < 0:
        sys.exit(f'{paths.show(page)}: no {START}...{END} block')
    # </ inside a script would end it early: escape the slash, as JSON allows
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    new = html[:a + len(START)] + blob + html[b:]
    if new == html:
        return True
    if check:
        sys.exit(f'{paths.show(page)}: data out of date - run the tool that writes it')
    page.write_text(new, encoding='utf-8', newline='\n')
    print(f'{paths.show(page)}: data block updated ({len(blob):,} bytes)')
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], epilog=paths.FOLDER_HELP,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('page', type=Path, help='the page, e.g. docs/guide/index.html')
    ap.add_argument('data', type=Path, help='a JSON file')
    ap.add_argument('--check', action='store_true', help='only check that the page is up to date')
    args = ap.parse_args(paths.configure(sys.argv[1:] if argv is None else argv))
    if write(args.page, json.loads(args.data.read_text(encoding='utf-8')), args.check) and args.check:
        print(f'{paths.show(args.page)}: up to date')


if __name__ == '__main__':
    main()
