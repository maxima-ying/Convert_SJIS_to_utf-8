#!/usr/bin/env python3
"""Detect Shift_JIS encoding for .java files under a directory.

Usage:
    python detect_shiftjis.py [--convert] PATH

Prints a table with file path and whether it's Shift_JIS.
If `--convert` is given, Shift_JIS files are backed up (original bytes saved to `file.java.jis`) and
the original file is overwritten with UTF-8 decoded content.
"""
from __future__ import annotations

import sys
import io
import os
import argparse
from typing import Iterable, Tuple, Optional

try:
    import chardet
except Exception:
    chardet = None


def iter_java_files(root: str) -> Iterable[str]:
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith('.java'):
                yield os.path.join(dirpath, fn)


def detect_shift_jis_bytes(data: bytes) -> bool:
    # Quick heuristic: try decoding with shift_jis
    try:
        data.decode('shift_jis')
        return True
    except Exception:
        return False


def detect_with_chardet(data: bytes) -> Tuple[str, float]:
    if chardet is None:
        return ('unknown', 0.0)
    r = chardet.detect(data)
    return (r.get('encoding') or 'unknown', float(r.get('confidence') or 0.0))


def analyze_file(path: str) -> Tuple[str, str, float]:
    # Returns: (path, result, confidence)
    try:
        with open(path, 'rb') as f:
            data = f.read()
    except Exception as e:
        return (path, f'error: {e}', 0.0)

    if chardet is not None:
        enc, conf = detect_with_chardet(data)
        if enc and enc.lower().replace('-', '') in ('shiftjis', 'shift_jis', 'sjis', 'cp932'):
            return (path, 'Shift_JIS', conf)
        # if chardet suggests something else but low confidence, try heuristic
        if conf < 0.6:
            if detect_shift_jis_bytes(data):
                return (path, 'Shift_JIS(heuristic)', conf)
        return (path, enc or 'unknown', conf)

    # fallback: pure heuristic
    is_sjis = detect_shift_jis_bytes(data)
    return (path, 'Shift_JIS' if is_sjis else 'not Shift_JIS', 1.0 if is_sjis else 0.0)


def backup_and_convert_to_utf8(path: str, root: str | None = None, backup_root: str | None = None, src_encoding: str = 'shift_jis') -> Tuple[bool, str]:
    """Create a backup file with '.jis' appended and convert original to UTF-8.

    If `backup_root` is provided and `root` is given, the backup will be written to
    os.path.join(backup_root, relative/path/to/file.java) + '.jis', preserving relative path.

    Returns (success, message).
    """
    try:
        with open(path, 'rb') as f:
            data = f.read()
    except Exception as e:
        return False, f'read error: {e}'

    # Determine backup path
    if backup_root and root:
        try:
            rel = os.path.relpath(path, root)
        except Exception:
            rel = os.path.basename(path)
        backup_full = os.path.join(backup_root, rel) + '.jis'
        backup_dir = os.path.dirname(backup_full)
        try:
            os.makedirs(backup_dir, exist_ok=True)
        except Exception as e:
            return False, f'backup dir create error: {e}'
    else:
        backup_full = path + '.jis'

    try:
        # write original bytes as backup
        with open(backup_full, 'wb') as bf:
            bf.write(data)
    except Exception as e:
        return False, f'backup error: {e}'

    # decode using provided encoding. Some bytes like 0x87 are lead-bytes in Shift_JIS
    # and will raise on lone occurrences; try a few encodings and fall back to
    # replacement to avoid exceptions while preserving best-effort text.
    text: Optional[str] = None
    tried = []
    for enc in (src_encoding, 'cp932', 'shift_jis'):
        if enc in tried:
            continue
        tried.append(enc)
        try:
            text = data.decode(enc)
            break
        except Exception:
            try:
                # use replacement for undecodable bytes (avoid exception for lone lead bytes)
                text = data.decode(enc, errors='replace')
                break
            except Exception:
                text = None

    if text is None:
        return False, 'decode error: unable to decode data with shift_jis/cp932'

    try:
        # overwrite original file with UTF-8 bytes (no newline translation)
        out_bytes = text.encode('utf-8')
        with open(path, 'wb') as out:
            out.write(out_bytes)
    except Exception as e:
        return False, f'write error: {e}'

    return True, f'backed up to {backup_full} and converted to UTF-8'


def main(argv: Optional[list[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description='Detect Shift_JIS in .java files and optionally convert to UTF-8')
    parser.add_argument('path', help='Root path to scan')
    parser.add_argument('--convert', action='store_true', help='Backup .jis and convert Shift_JIS files to UTF-8')
    parser.add_argument('--backup-dir', help='Directory where .jis backups will be stored (preserves relative paths)')
    args = parser.parse_args(argv)

    root = args.path
    do_convert = args.convert
    backup_dir = getattr(args, 'backup_dir', None)

    if not os.path.exists(root):
        print('Path not found:', root)
        return 3

    files = list(iter_java_files(root))
    if not files:
        print('No .java files found under', root)
        return 0

    # header
    print(f"{'File':<80} {'Encoding':<20} {'Conf':>6} {'Action':<40}")
    print('-' * 150)

    for fp in files:
        path, result, conf = analyze_file(fp)
        #print("------------------------")
        # print("path:", path)
        # print("result:", result)
        
        # if 'MacRoman' in result:
        #     print(f"{path:<80} {result:<20} {conf:6.2f}")
        print(f"{path:<80} {result:<20} {conf:6.2f}")
        
        action = ''
        if do_convert and ('Shift_JIS' in result or 'MacRoman' in result or 'Windows-1252' in result):
            ok, msg = backup_and_convert_to_utf8(path, root=root if backup_dir else None, backup_root=backup_dir, src_encoding='shift_jis')
            action = msg if ok else f'ERROR: {msg}'
            print(f"{path:<80} {result:<20} {conf:6.2f} {action:<40}")

    return 0


if __name__ == '__main__':
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    raise SystemExit(main())
