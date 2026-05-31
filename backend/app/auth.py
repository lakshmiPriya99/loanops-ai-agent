from functools import wraps

from flask import jsonify, request


ROLE_ORDER = {"viewer": 0, "processor": 1, "underwriter": 2, "admin": 3}


def current_actor():
    return {
        "email": request.headers.get("X-User-Email", "processor@example.com"),
        "role": request.headers.get("X-User-Role", "processor"),
    }


def require_role(min_role: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            actor = current_actor()
            if ROLE_ORDER.get(actor["role"], -1) < ROLE_ORDER[min_role]:
                return jsonify({"error": f"{min_role} role required"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator
