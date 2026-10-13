"""Real Sentry SDK/Flask integration, memory transport; no remote Sentry access."""
import os
import runpy
import sys
from unittest.mock import patch
sys.path.insert(0, '/app')
import sentry_sdk
from sentry_sdk.transport import Transport
from flask import Flask

events = []
test_password = os.environ['TEST_ACCOUNT_PASSWORD']
test_header = os.environ['EVENT_TOKEN']


class MemoryTransport(Transport):
    def capture_envelope(self, envelope):
        for item in envelope.items:
            if item.type == 'event':
                events.append(item.get_event())


original_init = sentry_sdk.init


def initialize_in_memory(**options):
    return original_init(**options, transport=MemoryTransport)


os.environ.update(SENTRY_DSN='https://public@example.invalid/1',
                  SENTRY_ENVIRONMENT='offline-check', APP_VERSION='offline-test')
for service, module_path in [('mini-general', '/app/observability.py'),
                              ('mini-monitor', '/monitor-observability.py')]:
    configure = runpy.run_path(module_path)['configure_errors']
    with patch('sentry_sdk.init', side_effect=initialize_in_memory):
        configure(service)
    app = Flask(service)
    app.logger.disabled = True

    @app.post('/offline-crash')
    def crash():
        sentry_sdk.set_user({'id': 'test-user'})
        return 1 / 0

    before = len(events)
    response = app.test_client().post('/offline-crash', json={'password': test_password},
                                      headers={'X-Private-Token': test_header})
    sentry_sdk.flush()
    assert response.status_code == 500 and len(events) > before
    event = events[-1]
    assert event['exception']['values'][-1]['type'] == 'ZeroDivisionError'
    assert event['environment'] == 'offline-check' and event['release'] == 'offline-test'
    assert event['tags']['service'] == service
    assert 'user' not in event
    assert not any(key in event.get('request', {}) for key in ['data', 'cookies', 'headers', 'query_string'])
    assert test_password not in str(event) and test_header not in str(event)
    print(f'PASS {service}: real Sentry SDK captures Flask exception with sensitive request/user data removed; memory transport only')
