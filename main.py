from fastapi import FastAPI
from pydantic import BaseModel
import mysql.connector
from dotenv import load_dotenv
import os
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------- LOAD ENV ---------------- #

load_dotenv()

app = FastAPI()

# ---------------- HTTP SESSION (RETRY) ---------------- #

session = requests.Session()
retry = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET", "POST"],
)
session.mount("https://", HTTPAdapter(max_retries=retry))

# ---------------- DATABASE CONNECTION ---------------- #

db = None
cursor = None


def get_db_cursor():
    global db, cursor

    if db is None or not db.is_connected():
        db = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )
        cursor = db.cursor(dictionary=True)

    return db, cursor


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
    "Sci-Fi": 878,
}

ALLOWED_GENRES = list(GENRE_MAP.keys())

GENRE_NORMALIZATION_MAP = {
    "action": "Action",
    "comedy": "Comedy",
    "drama": "Drama",
    "horror": "Horror",
    "romance": "Romance",
    "thriller": "Thriller",
    "scifi": "Sci-Fi",
    "sci fi": "Sci-Fi",
    "sci-fi": "Sci-Fi",
}


def normalize_genre(raw_text: str):
    if not raw_text:
        return None

    cleaned = re.sub(r"[^a-zA-Z\s-]", " ", raw_text).lower().strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    if cleaned in GENRE_NORMALIZATION_MAP:
        return GENRE_NORMALIZATION_MAP[cleaned]

    for key, canonical in GENRE_NORMALIZATION_MAP.items():
        if re.search(rf"\b{re.escape(key)}\b", cleaned):
            return canonical

    return None


# ---------------- GEMINI FUNCTION ---------------- #

def get_genre_from_gemini(mood: str):
    api_key = os.getenv("GEMINI_API_KEY")
    preferred_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    if not api_key:
        print("GEMINI API KEY NOT FOUND")
        return "Drama"

    headers = {"Content-Type": "application/json"}

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

    # Try preferred model first, then fall back.
    models_to_try = [preferred_model, "gemini-2.0-flash", "gemini-1.5-flash"]

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        try:
            response = session.post(url, headers=headers, json=data, timeout=20)
            if response.status_code == 429:
                print("GEMINI RATE LIMITED (429): too many requests/quota exceeded")
                return "Drama"


            if response.status_code == 404:
                print(f"GEMINI MODEL NOT FOUND: {model}")
                continue

            response.raise_for_status()
            result = response.json()

            if "candidates" not in result:
                print("GEMINI BAD RESPONSE:", result)
                return "Drama"

            raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            genre = normalize_genre(raw_text)

            if not genre or genre not in ALLOWED_GENRES:
                print("Gemini returned invalid genre:", raw_text)
                return "Drama"

            return genre

        except Exception as e:
            print(f"GEMINI ERROR ({model}):", e)

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
        response = session.get(url, timeout=20)
        response.raise_for_status()
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
        db, cursor = get_db_cursor()
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
        "movies": movies.get("results", []),
    }


# ---------------- ADD FAVOURITE ---------------- #

@app.post("/add-test-favourite")
def add_test_favourite(movie: TestMovie):
    try:
        db, cursor = get_db_cursor()
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
        _, cursor = get_db_cursor()
        query = "SELECT * FROM favourites"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception as e:
        print("DB ERROR:", e)
        return []
