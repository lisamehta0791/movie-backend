# 🎬 AI-Powered Movie Recommendation Platform (Backend)

This project is a backend REST API built using FastAPI that provides mood-based movie recommendations.

It integrates:
- Gemini API for mood → genre conversion
- TMDB API for fetching movie recommendations
- MySQL database for storing search history and favourites

---

## 🚀 Features

- Accepts user mood input
- Converts mood to movie genre using Gemini API
- Fetches movies from TMDB API
- Stores search history in MySQL database
- Allows saving favourite movies
- Retrieves saved favourites
- Fully API-based backend system

---

## 🛠 Tech Stack

- **Backend Framework:** FastAPI (Python)
- **Database:** MySQL
- **AI API:** Google Gemini API
- **Movie API:** TMDB API
- **Version Control:** Git & GitHub

---

## 📌 API Endpoints

### 1️⃣ GET /

Checks whether the API is running.

**Response Example**
```json
{
  "message": "Movie Recommendation API is running with MySQL"
}
2️⃣ POST /recommend

Accepts mood input and returns movie recommendations.

Request Body

{
  "mood": "happy"
}


Response Example

{
  "mood": "happy",
  "detected_genre": "Comedy",
  "movies": [...]
}

3️⃣ POST /add-test-favourite

Adds a movie to the favourites database.

Request Body

{
  "movie_id": "123",
  "title": "Inception",
  "genre": "Sci-Fi"
}


Response

{
  "message": "Movie added successfully"
}

4️⃣ GET /favourites

Returns all saved favourite movies.

Response Example

[
  {
    "movie_id": "123",
    "title": "Inception",
    "genre": "Sci-Fi"
  }
]
🗄 Database Structure
Table: search_history

id (Primary Key)

mood

detected_genre

Table: favourites

id (Primary Key)

movie_id

title

genre

⚙️ How to Run Locally

Clone the repository

git clone https://github.com/lisamehta0791/movie-backend.git


Navigate to project folder

cd movie-backend


Create virtual environment

python -m venv venv


Activate virtual environment

venv\Scripts\activate


Install dependencies

pip install -r requirements.txt


Create a .env file and add:

GEMINI_API_KEY=your_key_here
TMDB_API_KEY=your_key_here
DB_HOST=localhost
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=your_database


Run the server

uvicorn main:app --reload


Open Swagger Docs:

http://127.0.0.1:8000/docs
