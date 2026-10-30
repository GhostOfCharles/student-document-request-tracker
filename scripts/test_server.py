"""Serve the already-populated disposable test DB for evidence review; no reset."""
import os,json
from pathlib import Path
from dotenv import dotenv_values
root=Path(__file__).resolve().parents[1]
cfg=dotenv_values(root/'.env')
url=cfg.get('SDRT_TEST_DATABASE_URL','')
from sqlalchemy.engine import make_url
if not url.startswith('mysql+pymysql://') or not make_url(url).database.endswith('_test'):
    raise SystemExit('Only a dedicated _test database may be used.')
os.environ['SDRT_DATABASE_URL']=url
os.environ['SDRT_ENVIRONMENT']='test'
os.environ['SDRT_ALLOWED_ORIGINS']=json.dumps(['http://localhost:8001'])
os.environ['SDRT_PRIVATE_DIR']=str(root/'.private/test-uploads')
import sys
sys.path.insert(0,str(root/'backend'))
import uvicorn
if __name__=='__main__':uvicorn.run('app.main:app',host='127.0.0.1',port=8001,access_log=False)
