"""Root env discovery and explicit environment precedence, without secret output."""
import os,sys,tempfile,subprocess
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'critic'))
import config
assert config.ENV_PATH==ROOT/'.env'
with tempfile.TemporaryDirectory() as directory:
    env=Path(directory)/'.env';env.write_text('AGRISLEUTH_CONFIG_TEST=file-value\nAGRISLEUTH_OVERRIDE_TEST=file-value\n')
    with patch.object(config,'ENV_PATH',env),patch.dict(os.environ,{'AGRISLEUTH_OVERRIDE_TEST':'process-value'},clear=True):
        config.load_environment()
        assert os.environ['AGRISLEUTH_CONFIG_TEST']=='file-value'
        assert os.environ['AGRISLEUTH_OVERRIDE_TEST']=='process-value'
print('PASS single root env discovery and process-variable precedence')
code="import sys;sys.path.insert(0,sys.argv[1]);import config;assert config.ENV_PATH.is_file();print('PASS env discovery from a different working directory')"
subprocess.run([sys.executable,'-c',code,str(ROOT/'critic')],cwd='/tmp',check=True)
assert not (ROOT/'critic/.env').exists() and not (ROOT/'data/.env.postgres').exists()
print('PASS legacy env files are absent')
