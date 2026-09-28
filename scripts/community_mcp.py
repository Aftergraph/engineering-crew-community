#!/usr/bin/env python3
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from aftergraph_crew.community_server import CommunityMCPServer
server=CommunityMCPServer()
for line in sys.stdin:
    try:
        req=json.loads(line)
        print(json.dumps(server.handle(req),sort_keys=True),flush=True)
    except Exception as exc:
        print(json.dumps({'jsonrpc':'2.0','id':None,'error':{'code':-32000,'message':str(exc)}}),flush=True)
