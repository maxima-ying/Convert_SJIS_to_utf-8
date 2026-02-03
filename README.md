# detect_shiftjis

Scan a directory for `.java` files and detect if files are Shift_JIS encoded.

Requirements
- Python 3.8+
- Optional: `chardet` for better detection (install with `pip install chardet`).

Usage

```bash
python detect_shiftjis.py path/to/project
python detect_shiftjis.py  --convert  --backup-dir path/to/backup path/to/project >convert01.log
```

Output
- Columns: `File`, `Encoding`, `Conf` (confidence from chardet when available).
