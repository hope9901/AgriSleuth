"""Actual local model adapter -> Critic -> FastAPI boundary with fixture HTTP."""
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'critic'))
from local_model import LocalStructuredModel
from runtime_errors import RuntimeReportedError, RuntimeUnreachableError
from schemas import CriticReview
from main import app, build_review_graph

OriginalClient = httpx.AsyncClient
request = dict(crop='rice', observations='Fixture', candidates=[dict(id='rice_001',name='Fixture',claim='Tentative',evidence_ids=['e1'])], evidence=[dict(id='e1',text='Fixture',source='Fixture',location='Fixture')])
payload = {'error':{'message':'Server says invalid key','type':'authentication_error','code':'auth_rate_limited'}, 'meterless':{'fix':['Enter a valid key'], 'chat_carrier':True}}
calls = []

def provider(request):
    calls.append(request)
    return httpx.Response(429, json=payload)

def adapter(**kwargs):
    return OriginalClient(transport=httpx.MockTransport(provider), **kwargs)

with TestClient(app) as client:
    app.state.review_graph = build_review_graph(LocalStructuredModel('http://fixture/v1','fixture','fixture',CriticReview))
    with patch('local_model.httpx.AsyncClient', adapter):
        response = client.post('/api/reviews',json=request)
    assert response.status_code == 429, response.text
    assert len(calls) == 1
    assert response.json()['error'] == dict(message='Server says invalid key\nEnter a valid key',type='authentication_error',code='auth_rate_limited')
    assert response.json()['meterless'] == payload['meterless']
print('PASS actual HTTP adapter, Critic and API preserve typed refusal status/reason/fix/carrier without retry')

def offline(request):
    raise httpx.ConnectError('offline',request=request)

with TestClient(app) as client:
    app.state.review_graph = build_review_graph(LocalStructuredModel('http://fixture/v1','fixture','fixture',CriticReview))
    with patch('local_model.httpx.AsyncClient',lambda **kwargs: OriginalClient(transport=httpx.MockTransport(offline),**kwargs)):
        response=client.post('/api/reviews',json=request)
    assert response.status_code == 503, response.text
    assert "isn't reachable at http://fixture/v1" in response.json()['error']['message']
    assert response.json()['actions'] == ['Start the runtime','Run Auto Detect']
print('PASS network failure survives model/Critic/API boundaries and offers both runtime actions')
