"""The toy repo generator lives in the package (agentbench.toy); this keeps `from toyrepo import ...` working in the tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agentbench.toy import *  # noqa: E402,F401,F403
from agentbench.toy import _git, make_toy  # noqa: E402,F401

if __name__ == "__main__":
    print(make_toy(sys.argv[1]))
