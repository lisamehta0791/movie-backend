from fastapi import FastAPI
from pydantic import BaseModel
import mysql.connector
from dotenv import load_dotenv
import os
import requests

# ---------------- LOAD ENV ---------------- #

load_dotenv()

app = FastAPI()

# ---------------- DATABASE CONNECTION ---------------- #

db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)

cursor = db.cursor(dictionary=True)

# ---------------- MODELS ---------------- #

class MoodInput(BaseModel):
    mood: str

class TestMovie(BaseModel):
    movie_id: str
    title: str
    genre: str

# ---------------- GENRE MAP ---------------- #

GENRE_MAP = {
    "Action": 28,
    "Comedy": 35,
    "Drama": 18,
    "Horror": 27,
    "Romance": 10749,
    "Thriller": 53,
    "Sci-Fi": 878
}

# ---------------- ROOT ---------------- #

@app.get("/")
def read_root():
    return {"message": "Movie Recommendation API is running with MySQL"}

# ---------------- GEMINI FUNCTION ---------------- #

def get_genre_from_gemini(mood: str):
    api_key = os.getenv("GEMINI_API_KEY")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"""
Convert this mood into ONE movie genre only.

Choose strictly from:
Action, Comedy, Drama, Horror, Romance, Thriller, Sci-Fi.

Mood: {mood}

Return only the genre word.
"""
                    }
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data, timeout=10)
    result = response.json()

    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Clean the output properly
    for genre in GENRE_MAP.keys():
        if genre.lower() in raw_text.lower():
            return genre

    # If Gemini gives something unexpected, just return its cleaned text
    return raw_text

# ---------------- TMDB FUNCTION ---------------- #

def get_movies_from_tmdb(genre: str):
    api_key = os.getenv("TMDB_API_KEY")

    genre_id = GENRE_MAP.get(genre)

    # If Gemini returned something invalid, skip TMDB safely
    if not genre_id:
        return {"results": []}

    url = f"https://api.themoviedb.org/3/discover/movie?api_key={api_key}&with_genres={genre_id}"

    response = requests.get(url, timeout=10)
    return response.json()

# ---------------- RECOMMEND ENDPOINT ---------------- #

@app.post("/recommend")
def recommend_movies(data: MoodInput):
    mood = data.mood

    genre = get_genre_from_gemini(mood)

    movies = get_movies_from_tmdb(genre)

    try:
        query = """
        INSERT INTO search_history (mood, detected_genre)
        VALUES (%s, %s)
        """
        cursor.execute(query, (mood, genre))
        db.commit()
    except:
        pass

    return {
        "mood": mood,
        "detected_genre": genre,
        "movies": movies.get("results", [])
    }

# ---------------- ADD FAVOURITE ---------------- #

@app.post("/add-test-favourite")
def add_test_favourite(movie: TestMovie):
    try:
        query = """
        INSERT INTO favourites (movie_id, title, genre)
        VALUES (%s, %s, %s)
        """
        values = (movie.movie_id, movie.title, movie.genre)

        cursor.execute(query, values)
        db.commit()

        return {"message": "Movie added successfully"}
    except:
        return {"message": "Failed to add movie"}

# ---------------- GET FAVOURITES ---------------- #

@app.get("/favourites")
def get_favourites():
    try:
        cursor.execute("SELECT * FROM favourites")
        return cursor.fetchall()
    except:
        return []
