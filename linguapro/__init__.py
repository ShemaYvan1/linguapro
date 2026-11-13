"""LinguaPro enrollment system (Laboratories 7 and 8)."""
import os

from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    # LINGUAPRO_DB lets a test use another database file; by default the file is instance/linguapro.db
    app.config.from_mapping(DATABASE=os.environ.get("LINGUAPRO_DB") or os.path.join(app.instance_path, "linguapro.db"))
    if test_config:
        app.config.update(test_config)
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)

    from . import db, routes

    db.init_app(app)
    app.register_blueprint(routes.bp)
    with app.app_context():
        db.init_db_if_needed()

    @app.cli.command("init-db")
    def init_db_command():
        """Create the tables and demo data if the database does not exist yet."""
        db.init_db_if_needed()
        print("Database ready:", app.config["DATABASE"])

    return app
