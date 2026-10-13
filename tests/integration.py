"""Run only against tests/compose.yaml; never uses production DB configuration."""
import os
import time
from pathlib import Path

import psycopg
import requests
from werkzeug.security import generate_password_hash

GENERAL = 'http://general-api:5101'
MONITOR = 'http://monitor-api:5102'
NEXT = 'http://monitor-web:3100'
PASSWORD = os.environ['TEST_ACCOUNT_PASSWORD']
DB_PASSWORD = os.environ['TEST_DB_PASSWORD']
TOKEN = os.environ['EVENT_TOKEN']
passed = 0


def check(condition, label):
    global passed
    assert condition, label
    passed += 1
    print(f'PASS {label}', flush=True)


def db(host, name):
    return psycopg.connect(host=host, dbname=name, user='test_user',
                           password=DB_PASSWORD, sslmode='disable')


for base, path in [(MONITOR, '/health'), (GENERAL, '/health'), (NEXT, '/')]:
    response = None
    for attempt in range(30):
        try:
            response = requests.get(base + path, timeout=3)
            if response.status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(1)
    check(response is not None and response.status_code == 200, f'{base}{path} HTTP 200')

for host, name, username in [('general-db', 'general_test', 'day2-student'),
                             ('monitor-db', 'monitor_test', 'day2-operator')]:
    with db(host, name) as conn:
        conn.execute('INSERT INTO users(username,password_hash) VALUES(%s,%s) '
                     'ON CONFLICT(username) DO NOTHING',
                     (username, generate_password_hash(PASSWORD)))

general = requests.Session()
monitor = requests.Session()
state = general.get(GENERAL + '/api/auth/me').json()
response = general.post(GENERAL + '/api/auth/login',
                        headers={'X-CSRF-Token': state['csrf_token']},
                        json={'username': 'day2-student', 'password': PASSWORD + '-wrong'})
check(response.status_code == 401, 'general login failure 401')
response = general.post(GENERAL + '/api/auth/login',
                        headers={'X-CSRF-Token': state['csrf_token']},
                        json={'username': 'day2-student', 'password': PASSWORD})
check(response.status_code == 200, 'general login success 200')
general_csrf = response.json()['csrf_token']

state_response = monitor.get(NEXT + '/api/auth/me')
check('Set-Cookie' in state_response.headers, 'Next forwards Set-Cookie')
state = state_response.json()
response = monitor.post(NEXT + '/api/auth/login',
                        headers={'X-CSRF-Token': state['csrf_token']},
                        json={'username': 'day2-operator', 'password': PASSWORD + '-wrong'})
check(response.status_code == 401, 'Next forwards monitor login failure 401')
response = monitor.post(NEXT + '/api/auth/login',
                        headers={'X-CSRF-Token': state['csrf_token']},
                        json={'username': 'day2-operator', 'password': PASSWORD})
check(response.status_code == 200, 'Next forwards monitor login success 200')
headers = {'X-CSRF-Token': response.json()['csrf_token']}
check(monitor.get(NEXT + '/api/auth/me').json()['user']['username'] == 'day2-operator',
      'Next forwards Cookie and retains login')
response = general.post(GENERAL + '/board/new',
                        data={'title': 'Day2 test post', 'body': 'persisted body',
                              'csrf_token': general_csrf}, allow_redirects=False)
check(response.status_code == 303, 'post create 303')
post_path = response.headers['Location']
post_id = int(post_path.rsplit('/', 1)[1])
check('Day2 test post' in general.get(GENERAL + post_path).text, 'post read from DB')
response = general.post(GENERAL + post_path + '/edit',
                        data={'title': 'Day2 edited post', 'body': 'edited body',
                              'csrf_token': general_csrf}, allow_redirects=False)
check(response.status_code == 303, 'post update 303')
check('Day2 edited post' in general.get(GENERAL + post_path).text, 'post reread updated')

response = monitor.post(NEXT + '/api/notes', headers=headers,
                        json={'title': 'Day2 test note', 'body': 'persisted note'})
check(response.status_code == 201, 'note create via Next 201')
note_id = response.json()['note']['id']
note_path = f'/api/notes/{note_id}'
check(monitor.get(NEXT + note_path).json()['note']['title'] == 'Day2 test note', 'note read')
response = monitor.put(NEXT + note_path, headers=headers,
                       json={'title': 'Day2 edited note', 'body': 'edited note'})
check(response.status_code == 200, 'note update via Next')
check(monitor.get(NEXT + note_path).json()['note']['title'] == 'Day2 edited note', 'note reread')
check(monitor.post(NEXT + '/api/notes', json={'title': 'x', 'body': 'x'}).status_code == 403,
      'missing CSRF rejected through Next')
check(monitor.post(NEXT + '/api/notes', headers=headers, json={}).status_code == 400,
      'invalid note input 400')

check(requests.post(MONITOR + '/api/events', json={}).status_code == 401,
      'event missing token rejected')
check(requests.post(MONITOR + '/api/events', headers={'X-Event-Token': 'wrong'},
                    json={}).status_code == 401, 'event wrong token rejected')
check(requests.post(MONITOR + '/api/events', headers={'X-Event-Token': TOKEN},
                    json={}).status_code == 400, 'event invalid payload rejected')
check(monitor.post(NEXT + '/api/events', headers=headers, json={}).status_code == 404,
      'Next blocks browser event ingestion')
check(monitor.get(NEXT + '/api/unknown').status_code == 404, 'Next API allowlist')
events = monitor.get(NEXT + '/api/events').json()['events']
check(any(e['event_type'] == 'login_failure' and e['status_code'] == 401 for e in events),
      'general login_failure 401 delivered and queried')
check(any(e['event_type'] == 'login_success' and e['status_code'] == 200 for e in events),
      'general login_success 200 delivered and queried')
check(requests.get(GENERAL + '/api/sentry-test').status_code == 401,
      'Sentry test requires login')
response = general.get(GENERAL + '/api/sentry-test')
check(response.status_code == 200 and response.json()['status'] == 'ok',
      'fixed Sentry test returns normal JSON')

for host, name, sql_file, table, row_id in [
    ('general-db', 'general_test', '/sql/general.sql', 'posts', post_id),
    ('monitor-db', 'monitor_test', '/sql/monitor.sql', 'notes', note_id),
]:
    with db(host, name) as conn:
        before = conn.execute(f'SELECT title, body FROM {table} WHERE id=%s', (row_id,)).fetchone()
        conn.execute(Path(sql_file).read_text())
        after = conn.execute(f'SELECT title, body FROM {table} WHERE id=%s', (row_id,)).fetchone()
        check(before == after and before is not None, f'{name} deploy.sql rerun preserves data')
        if table == 'posts':
            new_id = conn.execute("INSERT INTO posts(title,body) VALUES('sequence check','body') RETURNING id").fetchone()[0]
            check(new_id > row_id, 'post sequence remains valid after SQL rerun')

# Delete only the rows just created by this test in the isolated databases.
check(general.post(GENERAL + post_path + '/delete', data={'csrf_token': general_csrf},
                   allow_redirects=False).status_code == 303, 'post delete')
check(general.get(GENERAL + post_path).status_code == 404, 'deleted post not found')
check(monitor.delete(NEXT + note_path, headers=headers).status_code == 200, 'note delete via Next')
check(monitor.get(NEXT + note_path).status_code == 404, 'deleted note not found')
check(monitor.post(NEXT + '/api/auth/logout', headers=headers).status_code == 200,
      'monitor logout via Next')
check(monitor.get(NEXT + '/api/notes').status_code == 401, 'logout clears session')
print(f'ALL {passed} CHECKS PASSED', flush=True)
