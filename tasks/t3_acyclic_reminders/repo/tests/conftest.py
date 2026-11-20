import os
from pathlib import Path

import pytest

from devtools.cluster import Cluster
from devtools.fake_external import FakeExternal

os.environ["NO_PROXY"] = "127.0.0.1,localhost"
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def make_fake():
    fakes = []

    def factory():
        fakes.append(FakeExternal())
        return fakes[-1]

    yield factory
    for fake in fakes:
        fake.stop()


@pytest.fixture
def make_cluster():
    clusters = []

    def factory(externals=None):
        clusters.append(Cluster(ROOT, externals).start())
        return clusters[-1]

    yield factory
    for cluster in clusters:
        cluster.stop()
