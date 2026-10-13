import os
from flask import Flask, abort
from routes.posts import posts_bp
from routes.auth import auth_bp
from auth_helpers import configure_session, no_cache, template_auth
from error_handlers import register_error_handlers
from request_logging import record_request

from auth_helpers import api_access_error
from observability import configure_errors

configure_errors('mini-general')
app = Flask(__name__)
app.json.ensure_ascii = False
configure_session(app, "general_session")
app.register_blueprint(posts_bp)
app.register_blueprint(auth_bp)
app.context_processor(template_auth)
register_error_handlers(app)
app.after_request(no_cache)
app.after_request(record_request)


@app.get('/health')
def health():
    return {'service': 'general', 'status': 'ok'}


@app.get('/api/sentry-test')
def sentry_test():
    if os.environ.get('ENABLE_SENTRY_TEST', 'false').lower() != 'true':
        abort(404)
    error = api_access_error()
    if error:
        return error
    # 오류 위치를 확인한 뒤 이 응답 부분을 수정한다.
    result = 1 / 0
    return {'result': result}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
