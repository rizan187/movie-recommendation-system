from math import ceil

import pandas as pd
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from Main import app, bcrypt, db
from Main.decorators import admin_required
from Main.form import AdminMovieForm, AdminUserForm, AdminWatchlistForm, CsrfOnlyForm
from Main.models import User, UserWatchlist
from Main.routes import IMAGES_CSV, MOVIES_CSV, delete_row_by_id, get_movie_details_by_id, upload_to_csv


def load_movies():
    if not pd.io.common.file_exists(MOVIES_CSV):
        return pd.DataFrame(columns=['movie_id', 'title', 'genres', 'overview', 'cast', 'director', 'year', 'image_url'])

    movies = pd.read_csv(MOVIES_CSV, on_bad_lines='skip', low_memory=False, dtype=str)
    movies['movie_id'] = movies['movie_id'].astype(str).str.strip()

    if pd.io.common.file_exists(IMAGES_CSV):
        images = pd.read_csv(IMAGES_CSV, on_bad_lines='skip', low_memory=False, dtype=str)
        images['movie_id'] = images['movie_id'].astype(str).str.strip()
        image_cols = ['movie_id', 'image_url'] if 'image_url' in images.columns else ['movie_id']
        movies = movies.merge(images[image_cols], on='movie_id', how='left')
    else:
        movies['image_url'] = ''

    if 'image_url' not in movies.columns:
        movies['image_url'] = ''
    else:
        movies['image_url'] = movies['image_url'].fillna('')
    return movies


def next_movie_id(movies_df):
    ids = pd.to_numeric(movies_df['movie_id'], errors='coerce').dropna()
    if ids.empty:
        return '1'
    return str(int(ids.max()) + 1)


def write_movies_csv(df):
    columns = ['movie_id', 'title', 'genres', 'overview', 'cast', 'director', 'year']
    df[columns].to_csv(MOVIES_CSV, index=False)


def write_images_csv(movie_id, title, image_url):
    movie_id = str(movie_id).strip()
    if pd.io.common.file_exists(IMAGES_CSV):
        images = pd.read_csv(IMAGES_CSV, on_bad_lines='skip', low_memory=False, dtype=str)
        images['movie_id'] = images['movie_id'].astype(str).str.strip()
        if 'title' not in images.columns:
            images['title'] = ''
        if 'image_url' not in images.columns:
            images['image_url'] = ''
        if (images['movie_id'] == movie_id).any():
            images.loc[images['movie_id'] == movie_id, 'title'] = title
            images.loc[images['movie_id'] == movie_id, 'image_url'] = image_url
        else:
            images = pd.concat([
                images,
                pd.DataFrame([{'movie_id': movie_id, 'title': title, 'image_url': image_url}])
            ], ignore_index=True)
        images.to_csv(IMAGES_CSV, index=False)
    else:
        pd.DataFrame([{'movie_id': movie_id, 'title': title, 'image_url': image_url}]).to_csv(IMAGES_CSV, index=False)


@app.route('/admin')
@admin_required
def admin_dashboard():
    movies = load_movies()
    users = User.query.order_by(User.id.asc()).all()
    watchlist_count = UserWatchlist.query.count()
    admin_count = User.query.filter_by(is_admin=True).count()
    return render_template(
        'admin_dashboard.html',
        title='Admin Dashboard',
        movie_count=len(movies),
        user_count=len(users),
        watchlist_count=watchlist_count,
        admin_count=admin_count,
        recent_users=users[-5:][::-1],
        recent_movies=movies.tail(5).iloc[::-1].to_dict('records') if not movies.empty else [],
    )


@app.route('/admin/movies')
@admin_required
def admin_movies():
    query = request.args.get('q', '').strip()
    page = max(int(request.args.get('page', 1) or 1), 1)
    per_page = 20
    movies = load_movies()
    if query and not movies.empty:
        mask = (
            movies['title'].fillna('').str.lower().str.contains(query.lower(), na=False)
            | movies['movie_id'].fillna('').str.contains(query, na=False)
            | movies['director'].fillna('').str.lower().str.contains(query.lower(), na=False)
        )
        movies = movies[mask]
    total = len(movies)
    pages = max(ceil(total / per_page), 1)
    page = min(page, pages)
    start = (page - 1) * per_page
    rows = movies.iloc[start:start + per_page].to_dict('records') if total else []
    return render_template(
        'admin_movies.html',
        title='Manage Movies',
        movies=rows,
        query=query,
        page=page,
        pages=pages,
        total=total,
        csrf_form=CsrfOnlyForm(),
    )


@app.route('/admin/movies/new', methods=['GET', 'POST'])
@admin_required
def admin_movie_create():
    form = AdminMovieForm()
    movies = load_movies()
    if request.method == 'GET' and not form.movie_id.data:
        form.movie_id.data = next_movie_id(movies)
    if form.validate_on_submit():
        upload_to_csv(MOVIES_CSV, [
            form.movie_id.data.strip(),
            form.title.data.strip(),
            form.genres.data.strip(),
            form.overview.data.strip(),
            form.cast.data.strip(),
            form.director.data.strip(),
            form.year.data,
        ])
        write_images_csv(form.movie_id.data.strip(), form.title.data.strip(), form.image_url.data.strip())
        flash('Movie created successfully.', 'success')
        return redirect(url_for('admin_movies'))
    return render_template('admin_movie_form.html', title='Add Movie', form=form, mode='create')


@app.route('/admin/movies/<movie_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_movie_edit(movie_id):
    movies = load_movies()
    match = movies[movies['movie_id'] == str(movie_id).strip()]
    if match.empty:
        flash('Movie not found.', 'warning')
        return redirect(url_for('admin_movies'))
    row = match.iloc[0].to_dict()
    form = AdminMovieForm(original_movie_id=movie_id)
    if form.validate_on_submit():
        idx = movies.index[movies['movie_id'] == str(movie_id).strip()]
        movies.loc[idx, 'movie_id'] = form.movie_id.data.strip()
        movies.loc[idx, 'title'] = form.title.data.strip()
        movies.loc[idx, 'genres'] = form.genres.data.strip()
        movies.loc[idx, 'overview'] = form.overview.data.strip()
        movies.loc[idx, 'cast'] = form.cast.data.strip()
        movies.loc[idx, 'director'] = form.director.data.strip()
        movies.loc[idx, 'year'] = str(form.year.data)
        write_movies_csv(movies)
        write_images_csv(form.movie_id.data.strip(), form.title.data.strip(), form.image_url.data.strip())
        if form.movie_id.data.strip() != str(movie_id).strip():
            UserWatchlist.query.filter_by(movie_id=str(movie_id).strip()).update(
                {'movie_id': form.movie_id.data.strip()}
            )
            db.session.commit()
        flash('Movie updated successfully.', 'success')
        return redirect(url_for('admin_movies'))
    if request.method == 'GET':
        form.movie_id.data = row.get('movie_id', '')
        form.title.data = row.get('title', '')
        form.genres.data = row.get('genres', '')
        form.overview.data = row.get('overview', '')
        form.cast.data = row.get('cast', '')
        form.director.data = row.get('director', '')
        try:
            form.year.data = int(float(row.get('year') or 0))
        except (TypeError, ValueError):
            form.year.data = None
        form.image_url.data = row.get('image_url', '')
    return render_template('admin_movie_form.html', title='Edit Movie', form=form, mode='edit')


@app.route('/admin/movies/<movie_id>/delete', methods=['POST'])
@admin_required
def admin_movie_delete(movie_id):
    form = CsrfOnlyForm()
    if not form.validate_on_submit():
        flash('Invalid request.', 'danger')
        return redirect(url_for('admin_movies'))
    deleted = delete_row_by_id(MOVIES_CSV, movie_id)
    delete_row_by_id(IMAGES_CSV, movie_id)
    UserWatchlist.query.filter_by(movie_id=str(movie_id).strip()).delete()
    db.session.commit()
    if deleted:
        flash('Movie deleted successfully.', 'success')
    else:
        flash('Movie not found.', 'warning')
    return redirect(url_for('admin_movies'))


@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.order_by(User.id.asc()).all()
    return render_template(
        'admin_users.html',
        title='Manage Users',
        users=users,
        csrf_form=CsrfOnlyForm(),
    )


@app.route('/admin/users/new', methods=['GET', 'POST'])
@admin_required
def admin_user_create():
    form = AdminUserForm(require_password=True)
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=bcrypt.generate_password_hash(form.password.data).decode('utf-8'),
            is_admin=bool(form.is_admin.data),
        )
        db.session.add(user)
        db.session.commit()
        flash('User created successfully.', 'success')
        return redirect(url_for('admin_users'))
    return render_template('admin_user_form.html', title='Add User', form=form, mode='create')


@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_user_edit(user_id):
    user = User.query.get_or_404(user_id)
    form = AdminUserForm(original_username=user.username, original_email=user.email, require_password=False)
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.is_admin = bool(form.is_admin.data)
        if form.password.data:
            user.password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin_users'))
    if request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.is_admin.data = bool(user.is_admin)
    return render_template('admin_user_form.html', title='Edit User', form=form, mode='edit', user=user)


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_user_delete(user_id):
    form = CsrfOnlyForm()
    if not form.validate_on_submit():
        flash('Invalid request.', 'danger')
        return redirect(url_for('admin_users'))
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete your own account while logged in.', 'warning')
        return redirect(url_for('admin_users'))
    UserWatchlist.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/watchlist', methods=['GET', 'POST'])
@admin_required
def admin_watchlist():
    form = AdminWatchlistForm()
    form.user_id.choices = [(u.id, f'{u.username} ({u.email})') for u in User.query.order_by(User.username).all()]
    if form.validate_on_submit():
        movie = get_movie_details_by_id(form.movie_id.data.strip())
        if not movie:
            flash('Movie ID not found.', 'warning')
        elif UserWatchlist.query.filter_by(user_id=form.user_id.data, movie_id=form.movie_id.data.strip()).first():
            flash('That movie is already in this user watchlist.', 'info')
        else:
            db.session.add(UserWatchlist(user_id=form.user_id.data, movie_id=form.movie_id.data.strip()))
            db.session.commit()
            flash('Watchlist item added.', 'success')
            return redirect(url_for('admin_watchlist'))
    entries = UserWatchlist.query.order_by(UserWatchlist.added_on.desc()).all()
    rows = []
    for entry in entries:
        user = User.query.get(entry.user_id)
        movie = get_movie_details_by_id(entry.movie_id) or {}
        rows.append({
            'id': entry.id,
            'username': user.username if user else 'Unknown',
            'email': user.email if user else '',
            'movie_id': entry.movie_id,
            'title': movie.get('title', 'Unknown movie'),
            'added_on': entry.added_on,
        })
    return render_template(
        'admin_watchlist.html',
        title='Manage Watchlists',
        form=form,
        entries=rows,
        csrf_form=CsrfOnlyForm(),
    )


@app.route('/admin/watchlist/<int:entry_id>/delete', methods=['POST'])
@admin_required
def admin_watchlist_delete(entry_id):
    form = CsrfOnlyForm()
    if not form.validate_on_submit():
        flash('Invalid request.', 'danger')
        return redirect(url_for('admin_watchlist'))
    entry = UserWatchlist.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash('Watchlist item deleted.', 'success')
    return redirect(url_for('admin_watchlist'))
