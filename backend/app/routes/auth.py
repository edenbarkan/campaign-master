from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from app.extensions import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__)

ALLOWED_ROLES = {"buyer", "partner", "admin"}


@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    role = (payload.get("role") or "").strip().lower()

    if not email or not password or role not in ALLOWED_ROLES:
        return jsonify({"error": "invalid_payload"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email_in_use"}), 400

    user = User(email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return (
        jsonify(
            {
                "access_token": token,
                "user": {"id": user.id, "email": user.email, "role": user.role.upper()},
            }
        ),
        201,
    )


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email or not password:
        return jsonify({"error": "invalid_payload"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid_credentials"}), 401

    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify(
        {
            "access_token": token,
            "user": {"id": user.id, "email": user.email, "role": user.role.upper()},
        }
    )


@auth_bp.route("/api/auth/me", methods=["GET"])
@jwt_required()
def me():
    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_identity"}), 401
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "not_found"}), 404
    return jsonify(
        {"user": {"id": user.id, "email": user.email, "role": user.role.upper()}}
    )
