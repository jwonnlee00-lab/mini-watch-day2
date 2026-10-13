"""Flask test-client checks inside the general image, isolated test DB only."""
import os
import runpy
import sys
from unittest.mock import patch

sys.path.insert(0, '/app')
os.environ.update(DB_HOST='general-db', DB_PORT='5432', DB_NAME='general_test',
                  DB_USER='test_user', DB_PASSWORD=os.environ['TEST_DB_PASSWORD'],
                  DB_SSLMODE='disable', SECRET_KEY='test-only-key-with-at-least-32-characters',
                  MONITOR_URL='http://monitor-api:5102/api/events', ENABLE_SENTRY_TEST='true')
from db import connect_db
from observability import configure_errors, remove_request_secrets
from auth_helpers import configure_session
from flask import Flask

with connect_db() as conn:
    user_id = conn.execute("SELECT id FROM users WHERE username='day2-student'").fetchone()['id']

with patch('requests.post'):
    old_app = runpy.run_path('/support/general-app.py')['app']
    old_client = old_app.test_client()
    with old_client.session_transaction() as session:
        session['user_id'] = user_id
    response = old_client.get('/api/sentry-test')
    assert response.status_code == 500
    print('PASS downloaded starter reproduces ZeroDivisionError / HTTP 500')
    from app import app
    client = app.test_client()
    assert client.get('/api/sentry-test').status_code == 401
    with client.session_transaction() as session:
        session['user_id'] = user_id
    response = client.get('/api/sentry-test')
    assert response.status_code == 200 and response.json['status'] == 'ok'
    print('PASS fixed endpoint returns HTTP 200 JSON with authenticated session')
    os.environ['ENABLE_SENTRY_TEST'] = 'false'
    assert client.get('/api/sentry-test').status_code == 404
    print('PASS disabled Sentry test returns 404 even when logged in')

for secure in ['true', 'false']:
    os.environ['SESSION_COOKIE_SECURE'] = secure
    cookie_app = Flask('cookie-check')
    configure_session(cookie_app, 'test_cookie')
    assert cookie_app.config['SESSION_COOKIE_SECURE'] == (secure == 'true')
print('PASS HTTPS and local HTTP Secure cookie configuration')

with patch('sentry_sdk.init') as init, patch('sentry_sdk.set_tag') as tag:
    os.environ.update(SENTRY_DSN='https://public@example.invalid/1',
                      SENTRY_ENVIRONMENT='test-environment', APP_VERSION='test-release')
    configure_errors('mini-general')
    options = init.call_args.kwargs
    assert options['environment'] == 'test-environment' and options['release'] == 'test-release'
    assert options['send_default_pii'] is False
    assert options['include_local_variables'] is False and options['enable_logs'] is False
    assert options['max_request_body_size'] == 'never'
    tag.assert_called_once_with('service', 'mini-general')
    event = {'request': {'data': 'password', 'cookies': 'session', 'headers': 'token',
                         'query_string': 'secret', 'url': 'https://example.invalid/path'},
             'user': {'id': 1}}
    redacted = options['before_send'](event, {})
    assert 'user' not in redacted and set(redacted['request']) == {'url'}
print('PASS Sentry environment/release/service and sensitive request data exclusion (mock SDK)')

import create_user
with connect_db() as conn:
    before = conn.execute("SELECT password_hash FROM users WHERE username='day2-student'").fetchone()
with patch('builtins.input', return_value='day2-student'), patch.object(create_user, 'getpass',
                                                                      return_value='different-test-password'):
    create_user.main()
with connect_db() as conn:
    after = conn.execute("SELECT password_hash FROM users WHERE username='day2-student'").fetchone()
assert before == after
print('PASS create_user does not overwrite existing password hash')
