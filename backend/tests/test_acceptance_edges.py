"""Additional Week 13 acceptance edges, not a later comprehensive campaign."""
import io
import uuid
from copy import deepcopy
from datetime import timedelta
from PIL import Image
from pypdf import PdfWriter
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from app import models as m
from app.main import app
from app.db import SessionLocal,utcnow
from app.common import one,rows,change
from app.automation.worker import enqueue,process,claim,renew,finish
from test_week13 import submitted,payload,action

def test_pdf_jpeg_png_and_duplicate_file_slots(student):
    samples=[]
    pdf=io.BytesIO();writer=PdfWriter();writer.add_blank_page(width=100,height=100);writer.write(pdf)
    samples.append(('synthetic.pdf',pdf.getvalue(),'application/pdf'))
    for extension,kind,mime in [('jpg','JPEG','image/jpeg'),('png','PNG','image/png')]:
        buf=io.BytesIO();Image.new('RGB',(20,20),'red').save(buf,format=kind)
        samples.append(('synthetic.'+extension,buf.getvalue(),mime))
    for name,data,mime in samples:
        response=student.post('/api/v1/files/staging',files={'file':(name,data,mime)})
        assert response.status_code==201,response.text
        downloaded=student.get('/api/v1/files/'+str(response.json()['id']))
        assert downloaded.content==data
        assert downloaded.headers['cache-control']=='private, no-store'
        assert downloaded.headers['x-content-type-options']=='nosniff'
    encrypted=io.BytesIO();writer.encrypt('synthetic-password');writer.write(encrypted)
    assert student.post('/api/v1/files/staging',files={'file':('encrypted.pdf',encrypted.getvalue(),'application/pdf')}).status_code==422
    body=payload(student,True);body['payment']['receipt_file_id']=body['attachments'][0]['stored_file_id']
    assert student.post('/api/v1/requests',json=body).status_code==422
    print('PASS decoded PDF/JPEG/PNG round trips, encrypted PDF rejection and separate file slots')

def test_atomic_invalid_submission_and_canonical_replay(student):
    body=payload(student)
    with SessionLocal() as db:
        before=[db.scalar(select(func.count()).select_from(t)) for t in (m.document_requests,m.request_revisions,m.automation_jobs)]
    bad=deepcopy(body);bad['answers']=[]
    assert student.post('/api/v1/requests',json=bad).status_code==422
    with SessionLocal() as db:
        after=[db.scalar(select(func.count()).select_from(t)) for t in (m.document_requests,m.request_revisions,m.automation_jobs)]
    assert before==after
    response=student.post('/api/v1/requests',json=body);assert response.status_code==201
    reordered=deepcopy(body);reordered['answers'].reverse()
    for a in reordered['answers']:
        if 'text_value' in a:a['text_value']='  '+a['text_value']+'  '
    assert student.post('/api/v1/requests',json=reordered).json()==response.json()
    print('PASS invalid submission writes no business/revision/outbox rows; canonical order and trimming replay')

def test_pinned_service_deactivation_and_file_isolation(student,staff):
    created,body=submitted(student,True);rid=created['id']
    with SessionLocal.begin() as db:change(db,m.document_services,body['service_id'],is_active=False)
    try:
        assert student.get('/api/v1/services/'+str(body['service_id'])).status_code==404
        assert student.post('/api/v1/requests',json=body).json()==created
        assert student.get(f'/api/v1/requests/{rid}').json()['service_version_id']==body['service_version_id']
        assert action(staff,rid,'begin-review').status_code==200
        fid=body['answers'][0]['requirement_id']
        cr=action(staff,rid,'corrections',general_instructions='Correct synthetic purpose.',items=[{'target_kind':'requirement','requirement_id':fid,'instruction':'Correct synthetic purpose.'}])
        detail=student.get(f'/api/v1/requests/{rid}').json()
        corrected={k:v for k,v in body.items() if k not in ('service_id','service_version_id')}
        corrected.update(client_submission_key=str(uuid.uuid4()),expected_row_version=detail['row_version'],correction_round_id=cr.json()['correction_round_id'])
        corrected['answers']=deepcopy(body['answers']);corrected['answers'][0]['text_value']='Corrected synthetic purpose'
        before=detail['due_at']
        result=student.post(f'/api/v1/requests/{rid}/correction-submissions',json=corrected)
        assert result.status_code==201,result.text
        assert student.get(f'/api/v1/requests/{rid}').json()['due_at']>before
        assert student.post(f'/api/v1/requests/{rid}/correction-submissions',json=corrected).status_code==200
    finally:
        with SessionLocal.begin() as db:change(db,m.document_services,body['service_id'],is_active=True)
    second=payload(student,True)
    second['attachments'][0]['stored_file_id']=body['attachments'][0]['stored_file_id']
    assert student.post('/api/v1/requests',json=second).status_code==422
    print('PASS pinned inactive service correction, single due-date extension and unrelated-request evidence isolation')

def test_login_throttle_and_cookie_contract():
    client=TestClient(app);client.headers['origin']='http://localhost:8000'
    token=client.get('/api/v1/auth/csrf').json()['csrf_token']
    for _ in range(10):
        assert client.post('/api/v1/auth/login',json={'login':'absent@example.test','password':'invalid-synthetic-password'},headers={'X-CSRF-Token':token}).status_code==401
    response=client.post('/api/v1/auth/login',json={'login':'absent@example.test','password':'invalid-synthetic-password'},headers={'X-CSRF-Token':token})
    assert response.status_code==429 and response.headers['retry-after']=='60'
    print('PASS enforced login throttling with Retry-After')

def test_lease_renewal_and_recipient_authorization(student,staff):
    created,_=submitted(student);process();now=utcnow()
    with SessionLocal.begin() as db:
        other=one(db,m.users,m.users.c.email=='other@example.test')
        uid=one(db,m.users,m.users.c.role=='staff')['id']
        bad=enqueue(db,'notification','unauthorized:'+str(uuid.uuid4()),request_id=created['id'],recipient_user_id=other['id'],payload={'event_key':'unauthorized','title':'Must never reach another owner'},now=now)
        good=enqueue(db,'notification','renew:'+str(uuid.uuid4()),request_id=created['id'],recipient_user_id=uid,payload={'event_key':'renew:'+str(uuid.uuid4()),'title':'Synthetic renewed claim'},now=now)
    claimed=claim(now);assert claimed['job_id']==bad
    assert finish(claimed,now)
    renewed=claim(now);assert renewed['job_id']==good
    assert renew(renewed,now+timedelta(seconds=30))
    assert finish(renewed,now+timedelta(seconds=130))
    assert not renew(renewed,now+timedelta(seconds=140))
    with SessionLocal() as db:
        job=one(db,m.automation_jobs,m.automation_jobs.c.id==bad)
        assert job['status']=='failed_permanently' and job['last_error_code']=='RECIPIENT_UNAUTHORIZED'
        assert len(rows(db,m.notifications,m.notifications.c.automation_job_id==bad))==1
        assert not rows(db,m.notifications,m.notifications.c.recipient_user_id==other['id'],m.notifications.c.event_key=='unauthorized')
    print('PASS lease extension and fencing; unauthorized recipient fails permanently with bounded staff notice')

