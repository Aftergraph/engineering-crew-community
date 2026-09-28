from aftergraph_crew.version import RELEASE_VERSION
from aftergraph_crew.community_server import CommunityMCPServer
from aftergraph_crew.dependency_hygiene_v13 import audit_pyproject
from pathlib import Path

def test_release_identity(): assert RELEASE_VERSION == '13.0.0-frontier.1'
def test_mcp_tools():
    r=CommunityMCPServer().handle({'jsonrpc':'2.0','id':1,'method':'tools/list','params':{}})
    assert {x['name'] for x in r['result']['tools']} >= {'community_doctor','uiux_audit','uiux_compile','metrics_aggregate'}
def test_dependency_hygiene(): assert audit_pyproject(Path(__file__).parents[1]/'pyproject.toml', community=True).ok
