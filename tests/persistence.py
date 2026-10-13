"""Keep test-only rows and verify reads across application container recreation."""
import os
import sys
import psycopg
import requests

mode = sys.argv[1]
password = os.environ['TEST_ACCOUNT_PASSWORD']
db_password = os.environ['TEST_DB_PASSWORD']
for host, database, table in [('general-db', 'general_test', 'posts'),
                               ('monitor-db', 'monitor_test', 'notes')]:
    with psycopg.connect(host=host, dbname=database, user='test_user',
                         password=db_password, sslmode='disable') as conn:
        if mode == 'prepare':
            existing = conn.execute(f'SELECT id FROM {table} WHERE title=%s', ('Day2 persistence sentinel',)).fetchone()
            if not existing:
                conn.execute(f'INSERT INTO {table}(title,body) VALUES(%s,%s)',
                             ('Day2 persistence sentinel', 'preserved across app recreation'))
        row = conn.execute(f'SELECT id,body FROM {table} WHERE title=%s', ('Day2 persistence sentinel',)).fetchone()
        assert row and row[1] == 'preserved across app recreation'
        if mode == 'verify':
            if table == 'posts':
                response = requests.get(f'http://general-api:5101/posts/{row[0]}')
                assert response.status_code == 200 and response.json()['body'] == row[1]
            else:
                session = requests.Session()
                base = 'http://monitor-web:3100'
                csrf = session.get(base + '/api/auth/me').json()['csrf_token']
                response = session.post(base + '/api/auth/login', headers={'X-CSRF-Token': csrf},
                                        json={'username': 'day2-operator', 'password': password})
                assert response.status_code == 200
                response = session.get(base + f'/api/notes/{row[0]}')
                assert response.status_code == 200 and response.json()['note']['body'] == row[1]
        print(f'PASS {mode}: {database}.{table} persistence sentinel')
