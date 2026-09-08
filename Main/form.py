from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, IntegerField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, URL
from flask_wtf.file import FileField, FileAllowed
from Main.models import User
import pandas as pd

class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                             validators=[DataRequired()])
    confirm_pswd = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                             validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UpdateAccount(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'jpeg', 'png'])])
    submit = SubmitField('Update')

    def validate_username(self, username):
        # Allow current username without raising error
        if username.data != getattr(self, 'original_username', None):
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        # Allow current email without raising error
        if email.data != getattr(self, 'original_email', None):
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')

class MovieForm(FlaskForm):
    moviename = StringField('Movie Name', validators=[DataRequired()])
    submit = SubmitField('Get Recommendations')

class UploadMovie(FlaskForm):
    movie_id = StringField('Movie ID', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    genres = StringField('Genres', validators=[DataRequired()])
    overview = TextAreaField('Overview', validators=[DataRequired()])
    cast = StringField('Cast', validators=[DataRequired()])
    director = StringField('Director', validators=[DataRequired()])
    year = IntegerField('Year', validators=[DataRequired()])
    image_url = StringField('Image URL', validators=[DataRequired(), URL()])
    submit = SubmitField('Upload Movie')

    def validate_movie_id(self, movie_id):
        df = pd.read_csv('movies.csv', on_bad_lines='skip', low_memory=False) if pd.io.common.file_exists('movies.csv') else None
        if df is not None:
            existing_ids = df['movie_id'].astype(str).str.strip().tolist()
            if movie_id.data.strip() in existing_ids:
                raise ValidationError('Movie ID already exists. Please enter a unique ID.')

class DeleteMovie(FlaskForm):
    movie_id = StringField('Movie ID', validators=[DataRequired()])
    submit = SubmitField('Delete Movie')

    def validate_movie_id(self, movie_id):
        df = pd.read_csv('movies.csv', on_bad_lines='skip', low_memory=False) if pd.io.common.file_exists('movies.csv') else None
        if df is not None:
            existing_ids = df['movie_id'].astype(str).str.strip().tolist()
            if movie_id.data.strip() not in existing_ids:
                raise ValidationError('Movie ID not found.')

# <-- SearchForm  -->
class SearchForm(FlaskForm):
    query = StringField('Search Movies', validators=[DataRequired(), Length(min=1, max=100)])
    submit = SubmitField('Search')


class AdminMovieForm(FlaskForm):
    movie_id = StringField('Movie ID', validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    genres = StringField('Genres', validators=[DataRequired()])
    overview = TextAreaField('Overview', validators=[DataRequired()])
    cast = StringField('Cast', validators=[DataRequired()])
    director = StringField('Director', validators=[DataRequired()])
    year = IntegerField('Year', validators=[DataRequired()])
    image_url = StringField('Image URL', validators=[DataRequired(), URL()])
    submit = SubmitField('Save Movie')

    def __init__(self, original_movie_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_movie_id = original_movie_id

    def validate_movie_id(self, movie_id):
        if self.original_movie_id and movie_id.data.strip() == str(self.original_movie_id).strip():
            return
        df = pd.read_csv('movies.csv', on_bad_lines='skip', low_memory=False) if pd.io.common.file_exists('movies.csv') else None
        if df is not None:
            existing_ids = df['movie_id'].astype(str).str.strip().tolist()
            if movie_id.data.strip() in existing_ids:
                raise ValidationError('Movie ID already exists. Please enter a unique ID.')


class AdminUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password')
    is_admin = BooleanField('Administrator')
    submit = SubmitField('Save User')

    def __init__(self, original_username=None, original_email=None, require_password=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email
        self.require_password = require_password

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')

    def validate_password(self, password):
        if self.require_password and not password.data:
            raise ValidationError('Password is required.')
        if password.data and len(password.data) < 4:
            raise ValidationError('Password must be at least 4 characters.')


class AdminWatchlistForm(FlaskForm):
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    movie_id = StringField('Movie ID', validators=[DataRequired()])
    submit = SubmitField('Add to Watchlist')


class CsrfOnlyForm(FlaskForm):
    pass
