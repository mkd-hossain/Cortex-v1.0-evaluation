"""Read-only progress diagnostics; do not print signed download URLs."""
from pathlib import Path
import time

home = Path.home()
for directory in (home / '.cache/uv', home / '.cache/huggingface/hub/models--mkd-hossain--Keural-Cortex-8B-v1.0'):
    files = []
    for path in directory.rglob('*'):
        if path.is_file() and not path.is_symlink():
            st = path.stat()
            if st.st_size > 100_000_000:
                files.append((st.st_mtime, st.st_size, str(path.relative_to(directory))))
    for modified, size, path in sorted(files, reverse=True)[:8]:
        print(directory.name, f'{size / 1e6:.0f} MB', f'{time.time()-modified:.0f}s since update', path)
