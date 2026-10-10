"""Include task snapshots in wheels and source distributions."""
import shutil
from pathlib import Path
from setuptools.command.build_py import build_py


class BuildWithTasks(build_py):
    def run(self):
        super().run()
        target = Path(self.build_lib) / "agentbench/builtin_tasks"
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(Path(__file__).resolve().parents[1] / "tasks", target,
                        dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
