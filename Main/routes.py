import pandas as pd
import os
import csv
import random
from csv import writer
from flask import render_template, url_for, flash, redirect, request, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from Main.decorators import admin_required
from PIL import Image
from fuzzywuzzy import fuzz
import secrets
from Main import app, db, bcrypt
from Main.form import (
    RegistrationForm, LoginForm, MovieForm,
    UpdateAccount
)
from Main.models import User, UserWatchlist  
from Main.recomm import recom, movie_display, resolve_youtube_trailer, enlarge_poster

# CSV file paths
BASE_DIR = os.path.abspath(os.getcwd())
MOVIES_CSV = os.path.join(BASE_DIR, 'movies.csv')
IMAGES_CSV = os.path.join(BASE_DIR, 'movie_images.csv')

MAX_WATCHLIST_ITEMS = 5

def get_trailer_search_url(title, year):
    # YouTube search URL for trailer
    query = '+'.join(str(title).split()) + '+' + str(year) + '+trailer'
    return f"https://www.youtube.com/results?search_query={query}"

def get_movie_details_by_id(movie_id):
    with open(MOVIES_CSV, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['movie_id'].strip() == str(movie_id).strip():
                return row
    return None

@app.route('/movie/<movie_id>')
def movie_info(movie_id):
    movie = get_movie_details_by_id(movie_id)
    if not movie:
        flash("Movie not found.", "warning")
        return redirect(request.referrer or url_for('home'))

    image_url = None
    with open(IMAGES_CSV, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['movie_id'].strip() == str(movie_id).strip():
                image_url = row.get('image_url', None)
                break
    movie['image_url'] = enlarge_poster(image_url) if image_url else url_for('static', filename='default_movie.jpg')

    movie['trailer_url'] = get_trailer_search_url(movie.get('title', ''), movie.get('year', ''))

    return render_template('movieinfo.html', movie=movie, image_url=movie.get('image_url'))

@app.route('/add_to_watchlist/<movie_id>', methods=['POST'])
@login_required
def add_to_watchlist(movie_id):
    count = UserWatchlist.query.filter_by(user_id=current_user.id).count()
    if count >= MAX_WATCHLIST_ITEMS:
        flash("You can only add up to 5 movies to your watchlist. Please remove some first.", "warning")
        return redirect(request.referrer or url_for('account'))

    exists = UserWatchlist.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if exists:
        flash("This movie is already in your watchlist.", "info")
        return redirect(request.referrer or url_for('account'))

    new_entry = UserWatchlist(user_id=current_user.id, movie_id=movie_id)
    db.session.add(new_entry)
    db.session.commit()
    flash("Movie added to your watchlist!", "success")
    return redirect(request.referrer or url_for('account'))

@app.route('/remove_from_watchlist/<movie_id>', methods=['POST'])
@login_required
def remove_from_watchlist(movie_id):
    entry = UserWatchlist.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if entry:
        db.session.delete(entry)
        db.session.commit()
        flash("Movie removed from your watchlist.", "success")
    else:
        flash("Movie not found in your watchlist.", "danger")
    return redirect(request.referrer or url_for('account'))

@app.route("/")
@app.route("/home")
def home():
    movies_list = movie_display()  # This helps movie_display to include trailer_url in recomm.py
    return render_template('home.html', content=movies_list)

@app.route("/about")
def about():
    posts = [{'author': 'Sagar Jha', 'title': 'Content Based Movie Recommender'}]
    return render_template('about.html', posts=posts, title="About")

# Registration, Login, Logout, and Account Management routes

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Account Created for {form.username.data}!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

# Login, Logout, and Account Management routes are defined below
@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('User Login Successful!', 'success')
            if next_page:
                return redirect(next_page)
            if getattr(user, 'is_admin', False):
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('account'))
        else:
            flash('Login Unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route("/recommender", methods=['GET', 'POST'])
@login_required
def recommender():
    form = MovieForm()
    if form.validate_on_submit():
        movie = form.moviename.data
        try:
            final_list = recom(movie)  # This helps recom to include trailer_url for each movie
            flash('Here are the following recommendations for you', 'success')
            return render_template('recommender.html', title='Recommender', form=form, final=final_list)
        except ValueError as e:
            flash(str(e), 'danger')
    return render_template('recommender.html', title='Recommender', form=form)

# Admin routes for managing movies and users
def upload_to_csv(file_name, row):
    file_exists = os.path.isfile(file_name)
    write_header = False
    if not file_exists or os.stat(file_name).st_size == 0:
        write_header = True

    with open(file_name, 'a', newline='', encoding='utf-8') as f:
        csv_writer = writer(f)
        if write_header:
            if file_name == MOVIES_CSV:
                csv_writer.writerow(['movie_id', 'title', 'genres', 'overview', 'cast', 'director', 'year'])
            elif file_name == IMAGES_CSV:
                csv_writer.writerow(['movie_id', 'image_url'])
        csv_writer.writerow(row)

@app.route("/uploadmovie", methods=['GET', 'POST'])
@admin_required
def uploadmovie():
    return redirect(url_for('admin_movie_create'))

def delete_row_by_id(file_name, movie_id):
    lines = []
    found = False
    movie_id = str(movie_id).strip()

    with open(file_name, 'r', newline='', encoding='utf-8') as readFile:
        reader = csv.reader(readFile)
        header = next(reader)
        lines.append(header)
        for row in reader:
            if row and str(row[0]).strip() == movie_id:
                found = True
            else:
                lines.append(row)

    if found:
        with open(file_name, 'w', newline='', encoding='utf-8') as writeFile:
            csv.writer(writeFile).writerows(lines)
    return found

@app.route("/deletemovie", methods=['GET', 'POST'])
@admin_required
def deletemovie():
    return redirect(url_for('admin_movies'))

def save_picture(form_picture):
    
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccount()
    form.original_username = current_user.username
    form.original_email = current_user.email

    if form.validate_on_submit():
        if form.picture.data:
            pic_file = save_picture(form.picture.data)
            current_user.image_file = pic_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        db.session.refresh(current_user)
        flash('Your account has been updated', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email

    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    from datetime import datetime
    timestamp = int(datetime.utcnow().timestamp())

    watchlist_entries = UserWatchlist.query.filter_by(user_id=current_user.id).all()
    watchlist_movies = []
    for entry in watchlist_entries:
        details = get_movie_details_by_id(entry.movie_id)
        if details:
            details['trailer_url'] = get_trailer_search_url(details.get('title', ''), details.get('year', ''))
            watchlist_movies.append(details)

    return render_template('account.html', title='Account', image_file=image_file, form=form, timestamp=timestamp, watchlist=watchlist_movies)

#Routes for search, trailer resolution, and surprise movie recommendation
@app.route("/search")
@login_required
def search():
    query = request.args.get('q', '').strip()
    results = []

    if len(query) < 3:
        return render_template('search_results.html', results=[], query=query)

    if query:
        with open(MOVIES_CSV, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row['title'].lower()
                genres = row['genres'].lower()
                overview = row['overview'].lower()
                cast = row['cast'].lower()
                director = row['director'].lower()
                q = query.lower()

                # Calculate fuzzy scores
                title_score = fuzz.partial_ratio(q, title)
                genres_score = fuzz.partial_ratio(q, genres)
                overview_score = fuzz.partial_ratio(q, overview)
                cast_score = fuzz.partial_ratio(q, cast)
                director_score = fuzz.partial_ratio(q, director)

                # Skiping if score is too low
                if max(title_score, genres_score, overview_score, cast_score, director_score) < 80:
                    continue

                # Given more weight to title
                total_score = title_score * 10 + genres_score * 3 + overview_score + cast_score * 2 + director_score * 2

                image_url = None
                with open(IMAGES_CSV, newline='', encoding='utf-8') as f_img:
                    reader_img = csv.DictReader(f_img)
                    for img_row in reader_img:
                        if img_row['movie_id'].strip() == row['movie_id'].strip():
                            image_url = img_row.get('image_url', None)
                            break
                if not image_url:
                    image_url = url_for('static', filename='default_movie.jpg')
                else:
                    image_url = enlarge_poster(image_url)

                trailer_url = get_trailer_search_url(row['title'], row['year'])

                results.append({
                    'movie_id': row['movie_id'],
                    'title': row['title'],
                    'genres': row['genres'],
                    'overview': row['overview'],
                    'cast': row['cast'],
                    'director': row['director'],
                    'year': row['year'],
                    'image_url': image_url,
                    'score': total_score,
                    'trailer_url': trailer_url
                })

        # Sort results descending by score
        results.sort(key=lambda x: x['score'], reverse=True)

        # Limiting to top 20 results
        results = results[:20]

    return render_template('search_results.html', results=results, query=query)


@app.route('/trailer')
def trailer():
    title = request.args.get('title', '').strip()
    year = request.args.get('year', '').strip()
    if not title:
        return jsonify({'embed_url': ''}), 400
    return jsonify({'embed_url': resolve_youtube_trailer(title, year)})


@app.route('/surprise')
@login_required
def surprise():
    with open(MOVIES_CSV, newline='', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
        movie = random.choice(reader)

    image_url = None
    with open(IMAGES_CSV, newline='', encoding='utf-8') as f_img:
        reader_img = csv.DictReader(f_img)
        for img_row in reader_img:
            if img_row['movie_id'].strip() == movie['movie_id'].strip():
                image_url = img_row.get('image_url', None)
                break
    if not image_url:
        image_url = url_for('static', filename='default_movie.jpg')
    else:
        image_url = enlarge_poster(image_url)

    trailer_url = get_trailer_search_url(movie.get('title', ''), movie.get('year', ''))
    
    movie['trailer_url'] = trailer_url

    return render_template('movieinfo.html', movie=movie, image_url=image_url)
