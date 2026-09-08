import pandas as pd
import numpy as np
import os
from fuzzywuzzy import fuzz


BASE_DIR = os.path.abspath(os.getcwd())
MOVIES_CSV = os.path.join(BASE_DIR, 'movies.csv')
IMAGES_CSV = os.path.join(BASE_DIR, 'movie_images.csv')


DEFAULT_IMAGE_URL = '/static/defaultposter.jpg'


def get_trailer_search_url(title, year):
    query = '+'.join(str(title).split()) + '+' + str(year) + '+trailer'
    return f"https://www.youtube.com/results?search_query={query}"


def recom(movie_title_input):
    """
    Given a movie title, returns a list of top 10 recommended movies based on Jaccard similarity
    of combined weighted word sets from title, genres, overview, cast, and director.
    """
    movies = pd.read_csv(MOVIES_CSV, on_bad_lines='skip', low_memory=False)
    img = pd.read_csv(IMAGES_CSV, on_bad_lines='skip', low_memory=False)

    # Ensure movie_id is string and trimmed
    movies['movie_id'] = movies['movie_id'].astype(str).str.strip()
    img['movie_id'] = img['movie_id'].astype(str).str.strip()

    df = movies.copy().reset_index(drop=True)

    if 'movie_id' not in df.columns:
        df['movie_id'] = df.index

    df['movie_id'] = df['movie_id'].astype(str).str.strip()

    features = ['title', 'genres', 'overview', 'cast', 'director']
    for feature in features:
        df[feature] = df[feature].fillna('')

    def get_word_set(row):
        title_words = row['title'].lower().split()
        genres_words = [g.strip() for g in row['genres'].lower().split(',')] if row['genres'] else []
        overview_words = row['overview'].lower().split()
        cast_words = [c.strip() for c in row['cast'].lower().split(',')] if row['cast'] else []
        director_words = row['director'].lower().split()
        word_list = title_words * 4 + overview_words * 3 + genres_words * 2 + cast_words + director_words
        return set(word_list)

    df['word_set'] = df.apply(get_word_set, axis=1)

    movie_title = movie_title_input.strip().lower()
    titles = df['title'].str.strip().str.lower()

    # Fuzzy matching with threshold 75
    matches = [(title, fuzz.ratio(movie_title, title)) for title in titles]
    matches = [m for m in matches if m[1] >= 75]
    print("Top fuzzy matches:", sorted(matches, key=lambda x: x[1], reverse=True)[:10])
   
    
    if not matches:
        raise ValueError(f"Movie titled '{movie_title_input}' not found in the database.")

    # Pick best match
    best_match_title = max(matches, key=lambda x: x[1])[0]

    matched = df[df['title'].str.strip().str.lower() == best_match_title]

    movie_id = matched.iloc[0]['movie_id']
    target_set = matched.iloc[0]['word_set']

    def jaccard_similarity(set1, set2):
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        return len(intersection) / len(union) if union else 0

    similarities = [
        (row['movie_id'], jaccard_similarity(target_set, row['word_set']))
        for _, row in df.iterrows() if row['movie_id'] != movie_id
    ]

    top_similar_movies = sorted(similarities, key=lambda x: x[1], reverse=True)[:10]

    def get_image_url(mid):
        match = img[img['movie_id'] == mid]
        if match.empty:
            return DEFAULT_IMAGE_URL
        url = match.iloc[0].get('image_url', '')
        return url if isinstance(url, str) and url.strip() else DEFAULT_IMAGE_URL

    final_list = []
    for mid, _ in top_similar_movies:
        row = df[df['movie_id'] == mid].iloc[0]
        title = row.get("title", "")
        image_url = get_image_url(mid)
        year = row.get("year", "")
        director = row.get("director", "")
        trailer_url = get_trailer_search_url(title, year)
        final_list.append({
            "movie_id": mid,
            "title": title,
            "image_url": image_url,
            "year": year,
            "director": director,
            "trailer_url": trailer_url
        })

    return final_list


def movie_display():
    """
    Returns a list of 10 randomly selected movies with their image URLs, years, directors,
    and trailer search URLs, for display purposes (e.g., homepage).
    """
    movies = pd.read_csv(MOVIES_CSV, on_bad_lines='skip', low_memory=False)
    img = pd.read_csv(IMAGES_CSV, on_bad_lines='skip', low_memory=False)

    # movie_id is string and trimmed
    movies['movie_id'] = movies['movie_id'].astype(str).str.strip()
    img['movie_id'] = img['movie_id'].astype(str).str.strip()

    final_list = []
    max_len = min(len(movies), len(img))
    rand_indices = np.random.choice(movies.index, min(10, max_len), replace=False)

    def get_image_url(mid):
        match = img[img['movie_id'] == mid]
        if match.empty:
            return DEFAULT_IMAGE_URL
        url = match.iloc[0].get('image_url', '')
        return url if isinstance(url, str) and url.strip() else DEFAULT_IMAGE_URL

    for idx in rand_indices:
        row = movies.iloc[idx]
        mid = row.get('movie_id', None)
        if mid is None:
            continue
        title = row.get('title', '')
        image_url = get_image_url(mid)
        year = row.get('year', '')
        director = row.get('director', '')
        trailer_url = get_trailer_search_url(title, year)
        final_list.append({
            "movie_id": mid,
            "title": title,
            "image_url": image_url,
            "year": year,
            "director": director,
            "trailer_url": trailer_url
        })

    return final_list
