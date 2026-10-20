import contextlib
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import os
import shutil
import subprocess
from unittest.mock import patch

from scripts.dev_bootstrap import inventory, prepare, reusable, set_state, readiness


class DeveloperOnboardingTests(unittest.TestCase):
    def test_missing_storage_secret_never_replaces_existing_installation(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'.env.example').write_text('ALLEXPORT_CALENDAR_LIVE_ENABLED=false\n')
            with self.assertRaises(SystemExit):
                prepare(root, True, True, 'test')
            self.assertFalse((root/'.local').exists())
            self.assertFalse((root/'.env').exists())

    def test_missing_runtime_volume_refuses_to_strand_existing_encrypted_data(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'.local').mkdir()
            password = root/'.local/db-password'
            password.write_text('existing-private-database-secret')
            state = root/'.local/dev/test/state.json'
            state.parent.mkdir(parents=True)
            state.write_text(json.dumps({'initialized': True}))
            with self.assertRaises(SystemExit):
                prepare(root, True, False, 'test')
            self.assertEqual(password.read_text(), 'existing-private-database-secret')
            self.assertFalse((root/'.env').exists())

    def test_prepare_preserves_existing_credentials_without_printing_values(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'.env.example').write_text('ALLEXPORT_CALENDAR_LIVE_ENABLED=false\n')
            output = StringIO()
            with contextlib.redirect_stdout(output):
                prepare(root, False, False, 'test')
            password = (root/'.local/db-password').read_bytes()
            (root/'.env').write_text('PRIVATE_TEST_KEY=keep-me-private\n')
            key = root/'.local/encryption-key';key.write_bytes(b'original-key')
            with contextlib.redirect_stdout(output):
                prepare(root, True, True, 'test')
            self.assertEqual((root/'.local/db-password').read_bytes(), password)
            self.assertEqual(key.read_bytes(), b'original-key')
            self.assertEqual((root/'.env').read_text(), 'PRIVATE_TEST_KEY=keep-me-private\n')
            self.assertNotIn(password.decode(), output.getvalue())
            self.assertNotIn('keep-me-private', output.getvalue())

    def test_reuse_requires_matching_mode_source_and_environment(self):
        with TemporaryDirectory() as temp:
            root = Path(temp);(root/'source.txt').write_text('source')
            (root/'.env').write_text('TEST_VALUE=first\n')
            set_state(root, 'test', 'demo', True)
            self.assertTrue(reusable(root, 'test', 'demo'))
            self.assertFalse(reusable(root, 'test', 'normal'))
            (root/'.env').write_text('TEST_VALUE=changed\n')
            self.assertFalse(reusable(root, 'test', 'demo'))
            set_state(root, 'test', 'demo', False)
            self.assertFalse(reusable(root, 'test', 'demo'))

    def test_foreign_checkout_and_mode_change_are_refused(self):
        row={'Config':{'Labels':{'com.docker.compose.project.working_dir':'/other','com.docker.compose.service':'api'},'Env':['APP_MODE=normal','PRIVATE_KEY=not-for-output']},'State':{'Running':True}}
        for expected,mode in [('/checkout','normal'),('/other','demo')]:
            with self.subTest(root=expected,mode=mode), self.assertRaises(SystemExit) as error:
                inventory([row],expected,mode)
            self.assertNotIn('not-for-output',str(error.exception))

    def test_stopped_matching_checkout_can_be_started_in_an_explicit_new_mode(self):
        row={'Config':{'Labels':{'com.docker.compose.project.working_dir':'/checkout','com.docker.compose.service':'api'},'Env':['APP_MODE=normal']},'State':{'Running':False}}
        self.assertEqual(inventory([row],'/checkout','demo'),('normal',0,1))

    def test_database_only_recovery_does_not_block_an_explicit_mode_switch(self):
        rows=[{'Config':{'Labels':{'com.docker.compose.project.working_dir':'/checkout','com.docker.compose.service':service},'Env':['APP_MODE=demo']},'State':{'Running':service=='postgres'}} for service in ['api','worker','postgres']]
        self.assertEqual(inventory(rows,'/checkout','normal'),('demo',1,3))

    def test_doctor_readiness_does_not_create_authentication_sessions(self):
        requested=[]
        class Response(StringIO):
            status=200
        def reply(url,**kwargs):
            requested.append(url)
            if url.endswith('/health'):return Response(json.dumps({'status':'ready','mode':'demo'}))
            if url.endswith('/auth/demo-identities'):return Response(json.dumps({'result':{'users':[{'id':'synthetic'}]}}))
            return Response('html')
        with patch('scripts.dev_bootstrap.urlopen',side_effect=reply), contextlib.redirect_stdout(StringIO()):
            readiness('demo',0)
        self.assertEqual(len(requested),3)
        self.assertFalse(any('session' in value or 'login' in value for value in requested))

    def test_stale_worker_cannot_be_reported_ready(self):
        with patch('scripts.dev_bootstrap.urlopen',side_effect=OSError('unavailable')):
            with self.assertRaises(SystemExit) as error:
                readiness('demo',0)
        self.assertIn('API/database/worker',str(error.exception))


@unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'POSIX launcher adapter runs on Linux')
class LauncherPreflightTests(unittest.TestCase):
    def test_unavailable_prerequisites_never_prepare_configuration(self):
        launcher=Path(__file__).resolve().parents[1]/'dev'
        for failure,message in [('missing','Docker CLI is missing'),('daemon','daemon unavailable'),('compose','Compose plugin missing'),('features','lacks --wait-timeout'),('config','configuration is incompatible')]:
            with self.subTest(failure=failure), TemporaryDirectory(prefix='onboarding path with spaces ') as temp:
                root=Path(temp);(root/'bin').mkdir();(root/'docker').mkdir()
                shutil.copyfile(launcher,root/'dev')
                (root/'docker/api.Dockerfile').write_text('FROM pinned-helper\n')
                os.symlink(shutil.which('dirname'),root/'bin/dirname')
                if failure != 'missing':
                    adapter=root/'bin/docker'
                    adapter.write_text('''#!/bin/bash
case "$1 $2" in
 'info --format') [[ "$FAILURE" != daemon ]];;
 'compose version') [[ "$FAILURE" != compose ]];;
 'compose up') [[ "$FAILURE" == features ]] || echo --wait-timeout;;
 'ps -aq'|'ps --filter') exit 0;;
 'compose -p') exit 1;;
 *) echo "Unexpected mutation" >&2; exit 99;;
esac
''')
                    adapter.chmod(0o700)
                result=subprocess.run([shutil.which('bash'),str(root/'dev'),'up'],env={**os.environ,'PATH':str(root/'bin'),'FAILURE':failure},capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0)
                self.assertIn(message,result.stderr)
                self.assertFalse((root/'.local').exists())
                self.assertFalse((root/'.env').exists())

    def test_migration_seed_and_worker_readiness_failures_never_print_success(self):
        launcher=Path(__file__).resolve().parents[1]/'dev'
        for failure,stage in [('migration','services'),('seed','seed'),('worker','readiness'),('prepare-only',None)]:
            with self.subTest(failure=failure), TemporaryDirectory(prefix='onboarding stage ') as temp:
                root=Path(temp);(root/'bin').mkdir();(root/'docker').mkdir()
                shutil.copyfile(launcher,root/'dev')
                (root/'docker/api.Dockerfile').write_text('FROM pinned-helper\n')
                for tool in ['dirname','id','mkdir']:
                    os.symlink(shutil.which(tool),root/'bin'/tool)
                adapter=root/'bin/docker'
                adapter.write_text('''#!/bin/bash
case "$1 $2" in
 'info --format'|'compose version') exit 0;;
 'compose up') echo --wait-timeout; exit 0;;
 'ps -aq'|'ps --filter') exit 0;;
 'volume inspect') exit 1;;
esac
case " $* " in
 *' prepare '*) mkdir -p .local/dev/allexport;;
 *' build '*) echo unexpected-build > build-called;;
 *' reusable '*) exit 1;;
 *' ready '*) [[ "$FAILURE" != worker ]];;
 *' up -d --force-recreate '*) [[ "$FAILURE" != migration || "$*" == *postgres* ]];;
 *' run --rm -T seed '*) [[ "$FAILURE" != seed ]];;
 *) exit 0;;
esac
''')
                adapter.chmod(0o700)
                arguments=[shutil.which('bash'),str(root/'dev'),'up']
                if failure == 'prepare-only':
                    arguments.append('--prepare-only')
                result=subprocess.run(arguments,env={**os.environ,'PATH':str(root/'bin'),'FAILURE':failure,'COMPOSE_PROJECT_NAME':'allexport'},capture_output=True,text=True)
                if failure == 'prepare-only':
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertTrue((root/'.local/dev/allexport').is_dir())
                    self.assertFalse((root/'build-called').exists())
                    self.assertNotIn('Ready:',result.stdout)
                    continue
                self.assertNotEqual(result.returncode,0)
                self.assertIn('Stage '+stage+' failed',result.stderr)
                self.assertNotIn('Ready:',result.stdout)
                self.assertTrue((root/'.local/dev/allexport'/f'{stage}.log').is_file())


if __name__=='__main__':unittest.main()
