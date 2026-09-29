"""Build or serve the local leaflet annotator: python -m tools.leaf_point_annotator."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import webbrowser


def build(output: Path) -> Path:
    source = Path(__file__).with_suffix('.html')
    output.mkdir(parents=True, exist_ok=True)
    destination = output / source.name
    if destination.exists() and destination.read_bytes() != source.read_bytes():
        backup = output / 'backups'
        backup.mkdir(exist_ok=True)
        from datetime import datetime
        shutil.copy2(destination, backup / f'annotator_{datetime.now():%Y%m%d_%H%M%S_%f}.html')
    shutil.copyfile(source, destination)
    return destination


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serve', action='store_true', help='Serve locally until Ctrl+C (fixed origin preserves browser annotations).')
    parser.add_argument('--open', action='store_true', help='Open the program in the default browser.')
    parser.add_argument('--port', type=int, default=8817)
    args = parser.parse_args()
    target = build(root / 'build/leaf_point_annotator')
    if not args.serve:
        print(target)
        if args.open:
            webbrowser.open(target.as_uri())
        return
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(SimpleHTTPRequestHandler, directory=str(target.parent)))
    url = f'http://127.0.0.1:{args.port}/{target.name}'
    print(url, flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
