# Local Movie Recommendation System

A local Flask-based movie recommendation web app designed for browsing movies, creating a personalized watchlist, and getting recommendations based on movie metadata. The app uses SQLite for user and watchlist storage and CSV files for the movie catalog and poster data.

## Project purpose

This application is meant to provide a lightweight movie discovery experience without depending on external databases or cloud services. It combines:

- a local movie catalog in CSV format
- a rule-based collaborative-style recommendation engine using metadata similarity
- user accounts with watchlists
- admin management tools for movies, users, and watchlists
- a polished frontend built with Flask templates and Tailwind CSS

---

## Tech stack

- Python 3
- Flask
- Flask-SQLAlchemy
- Flask-Login
- Flask-Bcrypt
- Flask-WTF
- Pandas
- NumPy
- FuzzyWuzzy
- SQLite
- Tailwind CSS (via CDN)
- Jinja2 templates

---

## Project structure

```text
Local Movie Recommendation System/
├── Main/
│   ├── __init__.py
│   ├── admin.py
│   ├── decorators.py
│   ├── form.py
│   ├── models.py
│   ├── recomm.py
│   ├── routes.py
│   ├── static/
│   │   ├── main.css
│   │   ├── images/
│   │   └── profile_pics/
│   └── templates/
│       ├── _admin_nav.html
│       ├── _movie_card.html
│       ├── account.html
│       ├── admin_dashboard.html
│       ├── admin_movie_form.html
│       ├── admin_movies.html
│       ├── admin_user_form.html
│       ├── admin_users.html
│       ├── admin_watchlist.html
│       ├── home.html
│       ├── layout.html
│       ├── login.html
│       ├── movieinfo.html
│       ├── recommender.html
│       ├── register.html
│       ├── search_results.html
│       └── sample.html
├── createtables.py
├── imdb_top_1000.csv
├── movies.csv
├── movie_images.csv
├── run.py
├── site.db
└── README.md
```

---

## Key files and responsibilities

### run.py
This is the application entry point. It starts the Flask app:

```python
from Main import app

if __name__ == '__main__':
    app.run(debug=True)
```

When executed, it launches the web server in debug mode.

### Main/__init__.py
This file initializes the core application runtime:

- creates the Flask app
- configures the SQLite database path
- sets up SQLAlchemy
- configures password hashing
- initializes Flask-Login
- ensures the app imports the route layer and admin layer
- creates the database tables
- automatically configures the default admin user if it does not exist

Important behavior:

- `SECRET_KEY` is set to a fixed local value for development
- database is stored in `site.db`
- default admin user is created if missing
- admin credentials default to:
  - username: `admin`
  - email: `admin@moviehub.com`
  - password: `Admin123!`

### Main/models.py
Defines the database models:

- `User`: stores username, email, profile image, hashed password, admin flag
- `UserWatchlist`: stores relationships between users and movies, along with the time added

This is the persistence layer for accounts and watchlist management.

### Main/form.py
Contains the Flask-WTF form classes used throughout the app:

- `RegistrationForm`
- `LoginForm`
- `UpdateAccount`
- `MovieForm`
- `SearchForm`
- `AdminMovieForm`
- `AdminUserForm`
- `AdminWatchlistForm`
- `CsrfOnlyForm`

These forms enforce validation for login, registration, profile updates, movie edits, and admin actions.

### Main/decorators.py
Defines `admin_required`, a decorator that protects routes so only administrators can access management views.

### Main/recomm.py
This is the recommendation engine module.

It contains:

- `recom(movie_title_input)`: finds similar movies using metadata similarity
- `movie_display()`: returns random featured movies for the homepage
- `resolve_youtube_trailer(title, year)`: builds a YouTube trailer lookup embed URL
- `enlarge_poster(url)`: upgrades poster quality by resizing the image URL

Recommendation approach:

- reads `movies.csv` and `movie_images.csv`
- normalizes and compares metadata such as title, genres, overview, cast, and director
- uses fuzzy matching to handle near matches in movie names
- computes Jaccard-style similarity between word sets
- returns the best matches with poster and trailer metadata

### Main/routes.py
This is the main user-facing route layer. It controls the public and authenticated flows of the app.

#### Public routes
- `/` and `/home` → homepage with featured movies
- `/about` → about page
- `/register` → user registration
- `/login` → login screen
- `/logout` → logout

#### Authenticated user routes
- `/recommender` → recommendation form and results
- `/movie/<movie_id>` → movie detail page
- `/account` → profile editing and watchlist viewing
- `/search` → fuzzy search across movie catalog
- `/trailer` → trailer embed endpoint for the frontend
- `/surprise` → random movie detail screen
- `/add_to_watchlist/<movie_id>` → add movie to user watchlist
- `/remove_from_watchlist/<movie_id>` → remove movie from watchlist

#### Admin redirect shortcuts
- `/uploadmovie` → redirects to admin movie creation
- `/deletemovie` → redirects to admin movies page

### Main/admin.py
The admin interface and management backend.

This file contains routes for:

- `/admin` → admin dashboard summary
- `/admin/movies` → list, search, and paginate movies
- `/admin/movies/new` → create a movie
- `/admin/movies/<movie_id>/edit` → edit a movie
- `/admin/movies/<movie_id>/delete` → delete a movie
- `/admin/users` → list users
- `/admin/users/new` → create a user
- `/admin/users/<int:user_id>/edit` → edit a user
- `/admin/users/<int:user_id>/delete` → delete a user
- `/admin/watchlist` → manage user movie watchlists
- `/admin/watchlist/<int:entry_id>/delete` → remove a watchlist item

This is the system control layer for the catalog and role management.

---

## Data files and workflow

### movies.csv
This is the primary movie catalog. It stores:

- `movie_id`
- `title`
- `genres`
- `overview`
- `cast`
- `director`
- `year`

It is the main dataset used for search, recommendation, and movie details.

### movie_images.csv
Stores movie poster URLs keyed by `movie_id`.

This helps the frontend display poster images and supports poster enlargement logic.

### imdb_top_1000.csv
This appears to be a reference dataset, likely imported or used for the project’s movie seed data or analysis. It is not the main operational catalog used by the Flask routes, which primarily reference `movies.csv`.

### site.db
The SQLite database that stores application data such as:

- users
- admin flags
- watchlist records

The app creates and maintains tables automatically through SQLAlchemy and the project bootstrap.

---

## Application workflow

### 1. App startup
When the project starts:

1. `run.py` loads the app.
2. `Main/__init__.py` initializes Flask, database, and login system.
3. database tables are created with `db.create_all()`.
4. the app ensures the admin exists.
5. routes are imported and registered.

### 2. User lifecycle
A user can:

- register an account
- log in
- update profile information and avatar
- add and remove movies from a watchlist
- search for movies
- view movie details and trailers
- receive recommendations for a selected movie

### 3. Recommendation lifecycle
The recommendation flow is:

1. User enters a movie title in the recommender page.
2. `recom()` loads the movie catalog.
3. fuzzy matching finds the closest title match
4. metadata is converted into weighted word sets
5. Jaccard similarity is calculated against all other movies
6. top matches are ranked and returned
7. template renders the recommended movies with posters, year, director, and trailer links

### 4. Admin lifecycle
The admin can:

- access the dashboard
- view movie totals, user totals, and watchlist totals
- create, edit, and delete movies
- create, edit, and delete users
- manage user watchlists

This logic is protected by `admin_required` and uses the admin-specific routes defined in `Main/admin.py`.

---

## Template layer overview

The frontend is rendered using Jinja2 templates under `Main/templates/`.

### Core templates
- `layout.html` → common layout, navigation, search bar, user menu, mobile menu, flashed messages
- `home.html` → homepage hero and featured movie grid
- `movieinfo.html` → detail view for a single movie
- `account.html` → profile management and user watchlist display
- `login.html` and `register.html` → authentication pages
- `search_results.html` → search result page
- `recommender.html` → recommendation input and result output

### Admin templates
- `admin_dashboard.html`
- `admin_movies.html`
- `admin_movie_form.html`
- `admin_users.html`
- `admin_user_form.html`
- `admin_watchlist.html`

### Shared component templates
- `_movie_card.html` → reusable movie tile UI for homepage and other pages
- `_admin_nav.html` → admin navigation control

The app uses a dark cinematic UI built around Tailwind styling and consistent card-based layouts.

---

## Authentication and authorization

The project uses Flask-Login to handle user sessions.

- `login_manager.login_view = 'login'` forces users to sign in before protected routes
- `admin_required` checks `current_user.is_admin`
- routes for user profile and recommendation functionality are protected behind `@login_required`
- admin routes are protected behind `@admin_required`

This gives a clean separation between public views, user functionality, and administrative functionality.

---

## Static assets

The static folder contains:

- CSS styling
- uploaded profile pictures in `profile_pics/`
- image assets under `images/`

Profile pictures are uploaded by users and saved locally under the app’s static profile directory.

---

## Run instructions

From the project root, run:

```bash
python run.py
```

Then open the app in a browser:

```text
http://localhost:5000/
```

If you are running a local web environment such as XAMPP, this project can also be served using the project folder as the app root if configured accordingly.

---

## Notes for presentation/demo

This project is best presented by showing:

1. the homepage with featured movie cards
2. the movie detail page with poster and trailer link
3. registration and login flow
4. the recommender experience for a selected film
5. the user watchlist management panel
6. the admin dashboard for managing movie catalog and accounts
7. the search feature and fuzzy matching behavior

The strongest business value of the app is that it works offline locally and is easy to demo without external services beyond general web access for trailer lookups.

---

## Summary

This application is a full-stack local movie recommendation platform with three major layers:

- data layer: CSV + SQLite
- app logic: Flask routes, forms, recommendation engine, admin management
- presentation layer: Jinja templates with Tailwind styling

It is structured to be understandable, extensible, and demo-friendly while keeping all important logic close to the app’s core entry points.
