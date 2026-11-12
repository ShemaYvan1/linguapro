"""LinguaPro enrollment system: MVP (Laboratory 7)."""
import os

from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(DATABASE=os.path.join(app.instance_path, "linguapro.db"))
    if test_config:
        app.config.update(test_config)
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)

    from . import db, routes

    db.init_app(app)
    app.register_blueprint(routes.bp)
    with app.app_context():
        db.init_db_if_needed()
    return app
