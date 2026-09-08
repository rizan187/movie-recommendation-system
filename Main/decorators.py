from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user, login_required


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not getattr(current_user, 'is_admin', False):
            flash('Only administrators can manage movies, users, and other system data.', 'danger')
            return redirect(url_for('home'))
        return view(*args, **kwargs)
    return wrapped
