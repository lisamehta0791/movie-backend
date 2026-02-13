# 🎬 AI-Powered Movie Recommendation Platform (Backend)

## 📌 Project Overview
This project is a backend implementation of an AI-Powered Movie Recommendation Platform developed for AWS Cloud Club | VIT Chennai.

The system:
- Accepts a user's mood
- Converts mood into a movie genre using Gemini API
- Fetches movie recommendations from TMDB API
- Stores search history in MySQL database
- Allows users to save favourite movies
- Retrieves saved favourites

---

## 🚀 Tech Stack Used

- Backend Framework: FastAPI (Python)
- Database: MySQL
- AI API: Google Gemini API
- Movie Data API: TMDB API
- Language: Python
- Version Control: Git & GitHub

---

## 📡 API Endpoints

### 1️⃣ GET /
Returns API status message.

Response:
```json
{
  "message": "Movie Recommendation API is running with MySQL"
}
