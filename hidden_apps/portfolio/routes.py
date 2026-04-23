"""Portfolio API routes."""

from flask import Blueprint, jsonify, request

from hidden_apps.portfolio import api

portfolio_bp = Blueprint("portfolio", __name__, url_prefix="/api/portfolio")


@portfolio_bp.route("/transactions", methods=["GET"])
def list_portfolio_transactions():
    payload, status_code = api.list_transactions_response()
    return jsonify(payload), status_code


@portfolio_bp.route("/transactions", methods=["POST"])
def append_portfolio_transaction():
    payload, status_code = api.append_transaction_response(request.get_json())
    return jsonify(payload), status_code


@portfolio_bp.route("/positions", methods=["GET"])
def portfolio_positions():
    payload, status_code = api.positions_response()
    return jsonify(payload), status_code
