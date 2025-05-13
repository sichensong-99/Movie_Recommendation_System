# 🎬 Moving Recommendation System
  A full-stack Flask web application for browsing, reviewing, rating and exporting movie data. Integrated with The Movie Database (TMDb) API and MongoDB, this app provides real-time popular movies, user authentication, admin features, comment management, and data export tools.
## 🏠 Feature
- 🎥 View popular movies (fetched from TMDb)

- 🔤 Movie detail pages with plot, cast, director, and reviews

- ✍️ Add personal reviews and ratings (authenticated users only)

- 🔍 Search movies by title, genre, year, or TMDb ID

- 📥 Export data as CSV or JSON:

  - Movie list

  - Movie detail (with local & TMDb reviews)

  - User comments

  - Registered users (JSON only)

- 📈 Admin dashboard with login logs and comment activity

- 🎓 User login, registration, password reset

- 📊 Comment search and in-place management

- 📚 Caching for TMDb data with scheduled re-import
## 📚 Tech Stack
- Backend: Python, Flask

- Frontend: Jinja2 Templates, HTML/CSS, JavaScript

- Database: MongoDB

- External API: TMDb API

- Security: Flask-Bcrypt, hashed passwords, session control
## 🔧 Setup Instructions
1. Clone the repo
<pre>
  git clone https://github.com/your-username/movie-rating-app.git
  cd movie-rating-app 
</pre>
2. Install dependencies
<pre>
  pip install -r requirements.txt
</pre>
3. Set environment variables
<pre>
export MONGO_URI='your_mongodb_connection_string'
export FLASK_APP=app.py
export FLASK_ENV=development
</pre>
