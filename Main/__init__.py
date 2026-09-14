import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

PACKAGE_DIR = os.path.abspath(os.path.dirname(__file__))
BASE_DIR = os.path.dirname(PACKAGE_DIR)

# Use absolute asset paths so templates are found whether the server is started
# with ``python run.py``, ``flask run``, or from an IDE with another working
# directory.
app = Flask(
    __name__,
    template_folder=os.path.join(PACKAGE_DIR, 'templates'),
    static_folder=os.path.join(PACKAGE_DIR, 'static'),
)
app.config['SECRET_KEY'] = 'my-fixed-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(BASE_DIR, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

from sqlalchemy import inspect, text

from Main import routes  # noqa: F401
from Main.models import User

ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'admin@moviehub.com'


def _ensure_admin_setup():
    with app.app_context():
        db.create_all()
        try:
            columns = [col['name'] for col in inspect(db.engine).get_columns('user')]
            if 'is_admin' not in columns:
                db.session.execute(text('ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0'))
                db.session.commit()
        except Exception:
            db.session.rollback()

        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User.query.filter_by(email=ADMIN_EMAIL).first()
        if not admin:
            admin = User.query.filter_by(email='admin@moviehub.local').first()

        if admin:
            admin.email = ADMIN_EMAIL
            admin.username = admin.username or 'admin'
            admin.is_admin = True
            db.session.commit()
        else:
            hashed = bcrypt.generate_password_hash('Admin123!').decode('utf-8')
            db.session.add(User(
                username='admin',
                email=ADMIN_EMAIL,
                password=hashed,
                is_admin=True,
            ))
            db.session.commit()


_ensure_admin_setup()
from Main import admin  # noqa: E402,F401 
