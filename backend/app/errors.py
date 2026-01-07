from http import HTTPStatus
from flask import jsonify


def json_error(status_code, message=None):
    """Return a consistent JSON error response."""
    if message is None:
        try:
            message = HTTPStatus(status_code).phrase
        except ValueError:
            message = 'Error'
    return jsonify({'error': message}), status_code
