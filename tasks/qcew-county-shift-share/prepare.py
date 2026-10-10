"""Prepare pinned BLS inputs and independently derived answers outside the shipped tree."""
import argparse
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path
import tomllib

from build_reference import build


def prepare(destination, cache):
    template = Path(__file__).resolve().parent
    final = Path(destination) / 'qcew-county-shift-share'
    if final.exists():
        raise ValueError('destination exists; choose another directory to preserve it')
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    recipe = tomllib.loads((template / 'data_recipe.toml').read_text())
    for row in recipe['files']:
        archive = cache / row['name']
        if not archive.exists():
            partial = archive.with_suffix('.part')
            subprocess.run(['curl', '-fL', '--retry', '2', row['url'], '-o', str(partial)], check=True)
            partial.rename(archive)
        with archive.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != row['sha256']:
            raise ValueError('BLS source vintage changed; cached inputs preserved, no task created')
    final.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.qcew-prepare-', dir=final.parent) as name:
        task = Path(name) / 'task'
        shutil.copytree(template, task)
        (task / 'repo' / 'data').mkdir(parents=True)
        (task / 'gold').mkdir()
        for row in recipe['files']:
            shutil.copy2(cache / row['name'], task / 'repo' / 'data' / row['name'])
        shutil.copy2(template / 'README-inputs.md', task / 'repo' / 'README.md')
        build(task / 'repo' / 'data', task / 'gold')
        for file in (task / 'gold').glob('*.csv'):
            shutil.copy2(file, task / 'hidden' / file.name)
        task.rename(final)
    return final


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tasks-dir', required=True)
    parser.add_argument('--cache-dir', required=True)
    args = parser.parse_args()
    print(prepare(args.tasks_dir, args.cache_dir))
