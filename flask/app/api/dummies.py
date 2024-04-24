from flask import Blueprint, jsonify, request
from ..models import db, Dummies


bp = Blueprint('dummies', __name__, url_prefix='/dummies')


@bp.route('/', methods=['POST'])
def dummy():
    data = request.get_json()

    dummy_data = data['text']

    print(dummy_data)

    db.session.add(Dummies(dummy=dummy_data))
    db.session.commit()

    return jsonify({
        "result": "success"
    }), 200
