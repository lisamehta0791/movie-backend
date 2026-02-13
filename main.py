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

# ---------------- ROOT ---------------- #

@app.get("/")
def read_root():
    return {"message": "Movie Recommendation API is running with MySQL"}

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

ALLOWED_GENRES = list(GENRE_MAP.keys())

# ---------------- GEMINI FUNCTION ---------------- #

def get_genre_from_gemini(mood: str):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("GEMINI API KEY NOT FOUND")
        return "Drama"

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"

    headers = {
        "Content-Type": "application/json"
    }

    prompt = f"""
You are a movie expert.

Based on the mood below, return ONLY ONE genre 
from this list exactly as written:

Action
Comedy
Drama
Horror
Romance
Thriller
Sci-Fi

Mood: {mood}

Return only the genre word.
"""

    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        result = response.json()

        genre = result["candidates"][0]["content"]["parts"][0]["text"].strip()

        if genre not in ALLOWED_GENRES:
            print("Gemini returned invalid genre:", genre)
            return "Drama"

        return genre

    except Exception as e:
        print("GEMINI ERROR:", e)
        return "Drama"

# ---------------- TMDB FUNCTION ---------------- #

def get_movies_from_tmdb(genre: str):
    api_key = os.getenv("TMDB_API_KEY")

    if not api_key:
        print("TMDB API KEY NOT FOUND")
        return {"results": []}

    genre_id = GENRE_MAP.get(genre, 18)

    url = f"https://api.themoviedb.org/3/discover/movie?api_key={api_key}&with_genres={genre_id}"

    try:
        response = requests.get(url, timeout=10)
        return response.json()
    except Exception as e:
        print("TMDB ERROR:", e)
        return {"results": []}

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
    except Exception as e:
        print("DB ERROR:", e)

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

    except Exception as e:
        print("DB ERROR:", e)
        return {"message": "Failed to add movie"}

# ---------------- GET FAVOURITES ---------------- #

@app.get("/favourites")
def get_favourites():
    try:
        query = "SELECT * FROM favourites"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception as e:
        print("DB ERROR:", e)
        return []
