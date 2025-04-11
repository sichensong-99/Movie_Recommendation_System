from flask import Flask, render_template,flash,request,redirect,url_for,session,jsonify,render_template_string,Response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bcrypt import Bcrypt
from pymongo import MongoClient # Database connector
from bson.objectid import ObjectId # For ObjectId to work
from datetime import datetime, timedelta
from bson import ObjectId
import os
import secrets
import requests
from functools import lru_cache
from uuid import uuid4
import re
import json
import uuid
from reportlab.pdfgen import canvas
from io import StringIO
import csv



app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
bcrypt = Bcrypt(app) 

@lru_cache(maxsize=20)
def get_popular_movies(page):
    api_key = "0530fc67fb10c009b85f55ef0a0ec0d6"
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={api_key}&language=en-US&page={page}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else {}

mongo_uri = os.environ.get("MONGO_URI")

if mongo_uri:
    client = MongoClient(mongo_uri)
else:
    mongodb_host = os.environ.get('MONGO_HOST', 'localhost')
    mongodb_port = int(os.environ.get('MONGO_PORT', '27017'))
    client = MongoClient(mongodb_host, mongodb_port)

db = client.camp2023  

todos = db.movies                 
users = db.users                 
movie_cache = db.movie_cache     
movies_collection = movie_cache  
logs = db.logs  



title = "Movie List"
heading = "Welcome to Sia's Movie Rating System"

@app.route("/")
def movies():
    # Display all movies
    movies = todos.find()
    a1 = "active" if request.path == "/list" else ""
    return render_template('main.html', movies=movies, a1=a1, t=title)



@app.route("/action", methods=["POST"])
def action():
    name = request.form.get("name")
    comment = request.form.get("comment")
    date = request.form.get("date")
    rate = request.form.get("rate")
    movie_id = request.form.get("movie_id")

    username = session.get('username')

    if username is None:
        return redirect(url_for('login'))

    try:
        movie_id = int(movie_id)
    except (ValueError, TypeError):
        return "❌ Invalid movie ID", 400

    todos.insert_one({
        "name": name,             
        "movie_id": movie_id,     # TMDb ID
        "comment": comment,
        "date": date,
        "rate": rate,
        "username": username
    })

    return redirect(url_for('movie_detail', movie_id=movie_id))



@app.route("/list")
def movie_list():
    page = int(request.args.get("page", 1))
    per_page = 10
    skip = (page - 1) * per_page
    a1 = "active"
    username = get_current_username()

    genre_map = {
        28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime", 99: "Documentary",
        18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
        9648: "Mystery", 10749: "Romance", 878: "Sci-Fi", 10770: "TV Movie", 53: "Thriller",
        10752: "War", 37: "Western"
    }

    cursor = movie_cache.find().skip(skip).limit(per_page)
    movies = []
    for m in cursor:
        d = m.get("detail", {})
        genres_raw = d.get("genres", [])

        if genres_raw and isinstance(genres_raw[0].get("id"), int):
            genres = [genre_map.get(g["id"], "Unknown") for g in genres_raw]
        else:
            genres = [g.get("name", "Unknown") for g in genres_raw]

        movies.append({
            "id": m["_id"],
            "title": d.get("title", "N/A"),
            "year": d.get("release_date", "")[:4],
            "genres": genres,
            "plot": d.get("overview", "N/A"),
            "posterUrl": f"https://image.tmdb.org/t/p/w200{d.get('poster_path')}" if d.get("poster_path") else ""
        })

    total = movie_cache.count_documents({})
    total_pages = (total + per_page - 1) // per_page

    return render_template("list.html",
                           a1=a1,
                           username=username,
                           movies=movies,
                           current_page=page,
                           total_pages=total_pages,
                           total=total)

@app.route("/export/movie_list.csv")
def export_movie_list_csv():
    page = int(request.args.get("page", 1))
    per_page = 10
    skip = (page - 1) * per_page

    cursor = movie_cache.find().skip(skip).limit(per_page)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Year", "Genres", "Plot", "Poster URL"])

    for m in cursor:
        d = m.get("detail", {})
        genres = [g.get("name", "Unknown") for g in d.get("genres", [])]
        writer.writerow([
            m["_id"],
            d.get("title", "N/A"),
            d.get("release_date", "")[:4],
            ", ".join(genres),
            d.get("overview", ""),
            f"https://image.tmdb.org/t/p/w200{d.get('poster_path', '')}" if d.get("poster_path") else ""
        ])

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=movie_list.csv"})

@app.route("/export/movie/<int:movie_id>.csv")
def export_movie_detail_csv(movie_id):
    movie_data = movie_cache.find_one({"_id": movie_id})
    if not movie_data:
        return "Movie not found", 404

    detail = movie_data.get("detail", {})
    credits = movie_data.get("credits", {})
    reviews = movie_data.get("reviews", [])
    comments = list(todos.find({"movie_id": movie_id}))

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Field", "Value"])

    writer.writerow(["Title", detail.get("title", "N/A")])
    writer.writerow(["Release Year", detail.get("release_date", "")[:4]])
    writer.writerow(["Genres", ", ".join([g.get("name", "") for g in detail.get("genres", [])])])
    writer.writerow(["Plot", detail.get("overview", "")])

    writer.writerow([])
    writer.writerow(["--- TMDb Reviews ---"])
    for r in reviews:
        writer.writerow(["Author", r.get("author", "")])
        writer.writerow(["Content", r.get("content", "")])
        writer.writerow([])

    writer.writerow([])
    writer.writerow(["--- Local Comments ---"])
    for c in comments:
        writer.writerow(["User", c.get("username", "")])
        writer.writerow(["Comment", c.get("comment", "")])
        writer.writerow(["Rating", c.get("rate", "")])
        writer.writerow(["Date", c.get("date", "")])
        writer.writerow([])

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=movie_{movie_id}.csv"})


@app.route("/export/comments.csv")
def export_comments_csv():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["username", "movie_id", "name", "rate", "comment", "date"])

    for c in todos.find():
        writer.writerow([
            c.get("username", ""),
            c.get("movie_id", ""),
            c.get("name", ""),
            c.get("rate", ""),
            c.get("comment", ""),
            c.get("date", "")
        ])

    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=comments.csv"}
    )

@app.route("/export/users.json")
def export_users_json():
    user_list = list(users.find({}, {"_id": 0, "password": 0}))
    return Response(
        json.dumps(user_list, indent=2),
        mimetype='application/json',
        headers={"Content-Disposition": "attachment;filename=users.json"}
    )

@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    api_key = "0530fc67fb10c009b85f55ef0a0ec0d6"
    now = datetime.utcnow()
    expire_after = timedelta(days=7)

    cache_entry = movie_cache.find_one({"_id": movie_id})

    if not cache_entry or (now - cache_entry.get("cached_at", now)) > expire_after:
        detail_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&language=en-US"
        credits_url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={api_key}&language=en-US"
        reviews_url = f"https://api.themoviedb.org/3/movie/{movie_id}/reviews?api_key={api_key}&language=en-US"

        try:
            detail = requests.get(detail_url).json()
            credits = requests.get(credits_url).json()
            reviews = requests.get(reviews_url).json().get("results", [])
        except Exception as e:
            print(f"❌ Error fetching TMDb data: {e}")
            detail, credits, reviews = {}, {}, []

        movie_cache.replace_one(
            {"_id": movie_id},
            {
                "_id": movie_id,
                "detail": detail,
                "credits": credits,
                "reviews": reviews,
                "cached_at": now
            },
            upsert=True
        )
    else:
        detail = cache_entry.get("detail", {})
        credits = cache_entry.get("credits", {})
        reviews = cache_entry.get("reviews", [])

    # Genre / Director / Cast
    genres = [g["name"] for g in detail.get("genres", [])]
    director = next((c["name"] for c in credits.get("crew", []) if c.get("job") == "Director"), "N/A")
    actors = ", ".join([a["name"] for a in credits.get("cast", [])[:5]]) if credits.get("cast") else "N/A"

    # Pagination setup
    tmdb_page = int(request.args.get("tmdb_page", 1))
    local_page = int(request.args.get("local_page", 1))
    per_page = 10

    # TMDb reviews pagination
    total_tmdb_reviews = len(reviews)
    total_tmdb_pages = (total_tmdb_reviews + per_page - 1) // per_page
    paged_reviews = reviews[(tmdb_page - 1) * per_page : tmdb_page * per_page]

    # Local comments pagination
    all_local_comments = list(todos.find({"movie_id": movie_id}).sort("date", -1))
    total_local_comments = len(all_local_comments)
    total_local_pages = (total_local_comments + per_page - 1) // per_page
    paged_local_comments = all_local_comments[(local_page - 1) * per_page : local_page * per_page]
    recommendations = cache_entry.get("recommendations", [])

    return render_template(
        "detail.html",
        movie=detail,
        genres=genres,
        director=director,
        actors=actors,
        reviews=paged_reviews,
        tmdb_page=tmdb_page,
        total_tmdb_pages=total_tmdb_pages,
        local_comments=paged_local_comments,
        local_page=local_page,
        total_local_pages=total_local_pages,
        username=session.get("username"),
        credits=credits,
        recommendations=recommendations,
        now=datetime.now
    )

@app.route("/comment")
def movies_lists():
    # Display all Tasks
    todos_l = todos.find()
    username = get_current_username()
    a1 = "active"
    return render_template('comment.html', a1=a1, todos=todos_l, username=username,t=title, h=heading)
def get_current_username():
    # Assuming you store the username in the session during login
    return session.get('username')
#	if(str(redir)=="http://localhost:5000/search"):
#		redir+="?key="+id+"&refer="+refer

@app.route("/add")
def add():
    username = get_current_username()

    # Check if the user is not logged in
    if username is None:
        # Redirect to the login page
        return redirect(url_for('login'))

    # Render the add.html template with the username
    return render_template('add.html', username=username, h=heading, t=title)
def get_current_username():
    # Assuming you store the username in the session during login
    return session.get('username')

@app.route("/search")
def search():
    query = request.args.get("query", "")
    movies = []

    if query:
        search_query = {"detail.title": {"$regex": query, "$options": "i"}}
        cursor = movies_collection.find(search_query).limit(50)

        for m in cursor:
            d = m.get("detail", {})
            movies.append({
                "id": m["_id"],
                "title": d.get("title", "N/A"),
                "year": d.get("release_date", "")[:4],
                "genres": [g.get("name") for g in d.get("genres", [])],
                "plot": d.get("overview", "N/A")
            })

    return render_template("search.html", results=movies, query=query)


@app.route("/remove")
def remove():
    # Deleting a Task with various references
    key = request.values.get("_id")

    # Delete the comment from the 'todos' collection
    todos.delete_one({"_id": ObjectId(key)})

    # Delete the comment from the 'movies_collection' collection
    movies_collection.delete_one({"_id": ObjectId(key)})

    # Flash a success message
    flash("Comment removed successfully!", "success")

    # Redirect to the referring page (or the home page if no referrer is present)
    return redirect(request.referrer or "/")

@app.route("/update/<comment_id>", methods=["GET", "POST"])
def update(comment_id):
    if request.method == "POST":
        # Retrieve the updated data from the form
        updated_name = request.form.get("name")
        updated_comment = request.form.get("comment")
        updated_date = request.form.get("date")
        updated_rate = request.form.get("rate")

        # Update the comment in the database
        todos.update_one({"_id": ObjectId(comment_id)}, {"$set": {
            "name": updated_name,
            "comment": updated_comment,
            "date": updated_date,
            "rate": updated_rate
        }})

        # Redirect to comment.html after updating
        return redirect(url_for('movies_lists'))
    else:
        # Retrieve the existing comment data
        comment_data = todos.find_one({"_id": ObjectId(comment_id)})

        # Check if the user is logged in
        if "username" in session:
            username = session["username"]
        else:
            username = None

        # Pass the comment data and username to the update.html template
        return render_template('update.html', comment=comment_data, username=username, title="Update Comment", a1="active")

@app.route("/about")
def about():
	return render_template('about.html',t=title,h=heading)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Hash the password before storing it
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        # Check if the username already exists
        existing_user = users.find_one({"username": username})
        if existing_user:
            return render_template("register.html", error="Username already exists", sign_in_url="/login")

        # Store the user in the database
        users.insert_one({"username": username, "password": hashed_password})

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session.clear()

        username = request.form.get("username")
        password = request.form.get("password")

        user = users.find_one({"username": username})

        if user and bcrypt.check_password_hash(user["password"], password):
            session["username"] = username
            session_id = str(uuid4())
            session["session_id"] = session_id

            logs.update_many(
                {"username": username, "logout_time": None},
                {
                    "$set": {
                        "logout_time": datetime.utcnow(),
                        "logout_reason": "auto-logout-on-new-login"
                    }
                }
            )

            logs.insert_one({
                "username": username,
                "login_time": datetime.utcnow(),
                "logout_time": None,
                "ip": request.remote_addr,
                "user_agent": request.headers.get("User-Agent"),
                "session_id": session_id
            })

            if user.get("is_admin"):
                return redirect(url_for('admin_dashboard'))

            previous_page = session.pop('currentPage', None)
            return redirect(previous_page or url_for('dashboard'))

        else:
            return render_template("login.html", error="Invalid username or password", show_options=True)

    return render_template("login.html", show_options=False)


@app.route("/dashboard")
def dashboard():
    # Check if the user is logged in
    if "username" in session:
        return render_template("dashboard.html", username=session["username"])
    else:
        # Redirect to the login page if not logged in
        return redirect("/login")
    
@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        username = request.form.get("username")
        new_password = request.form.get("new_password")

        # Check if the username exists
        user = users.find_one({"username": username})

        if user:
            # Update the user's password in the database
            hashed_password = bcrypt.generate_password_hash(new_password).decode("utf-8")
            users.update_one({"_id": user["_id"]}, {"$set": {"password": hashed_password}})
            return redirect("/login")
        else:
            flash("Username not found. Please check your username and try again.", "error")

    return render_template("reset_password.html")

@app.route("/search-json", methods=["GET"])
def search_json():
    refer = request.args.get("refer", "title")
    key = request.args.get("key", "").strip()
    page = int(request.args.get("page", 1))
    per_page = 10
    skip = (page - 1) * per_page

    field_map = {
        "title": "detail.title",
        "year": "detail.release_date",
        "genres": "detail.genres.name",
        "tmdb_id": "detail.id"
    }
    mapped_field = field_map.get(refer, "detail.title")

    query = {}

    if mapped_field == "detail.id":
        # TMDb ID: must be numeric
        try:
            query = {mapped_field: int(key)}
        except ValueError:
            return jsonify({
                "html": "<tr><td colspan='8'>❌ Invalid TMDb ID (must be a number).</td></tr>",
                "total": 0,
                "page": 1,
                "pages": 1
            })

    elif mapped_field == "detail.genres.name":
        # Optionally map common aliases (e.g. sci-fi → Science Fiction)
        genre_alias_map = {
            "sci-fi": "Science Fiction",
            "scifi": "Science Fiction",
            "romcom": "Romance",
            "bio": "Biography",
            "doc": "Documentary"
        }
        genre_name = genre_alias_map.get(key.lower(), key)
        query = {
            "detail.genres": {
                "$elemMatch": {
                    "name": re.compile(genre_name, re.IGNORECASE)
                }
            }
        }

    elif mapped_field == "detail.release_date":
        query = {mapped_field: {"$regex": key}}

    else:
        query = {mapped_field: {"$regex": key, "$options": "i"}}

    total = movies_collection.count_documents(query)
    cursor = movies_collection.find(query).skip(skip).limit(per_page)

    movies = []
    for m in cursor:
        d = m.get("detail", {})
        movies.append({
            "id": m["_id"],
            "title": d.get("title", "N/A"),
            "year": d.get("release_date", "")[:4],
            "genres": [g.get("name", "") for g in d.get("genres", [])],
            "plot": d.get("overview", "N/A"),
            "posterUrl": f"https://image.tmdb.org/t/p/w200{d.get('poster_path')}" if d.get("poster_path") else ""
        })

    search_results_html = render_template(
        "search_results_fragment.html",
        movies=movies,
        username=session.get("username")
    )

    return jsonify({
        "html": search_results_html,
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page
    })


@app.route("/logout")
def logout():
    username = session.get("username")
    session_id = session.get("session_id")

    if username and session_id:
        logs.update_one(
            {"username": username, "session_id": session_id},
            {
                "$set": {
                    "logout_time": datetime.utcnow(),
                    "logout_reason": "user_click_logout"
                }
            }
        )

    session.pop("username", None)
    session.pop("session_id", None)

    return redirect(url_for("main_page"))


@app.route("/admin/dashboard")
def admin_dashboard():
    username = session.get("username")
    user = users.find_one({"username": username})

    if not user or not user.get("is_admin"):
        return "❌ Access denied. Admins only.", 403

    page = int(request.args.get("page", 1))
    per_page = 10
    skip = (page - 1) * per_page

    login_logs = list(db.logs.find().sort("login_time", -1).skip(skip).limit(per_page))
    total_logs = db.logs.count_documents({})
    total_pages = (total_logs + per_page - 1) // per_page

    comment_count = todos.count_documents({})
    active_users = len(todos.distinct("username"))
    recent_comments = list(todos.find().sort("date", -1).limit(10))

    return render_template("admin_dashboard.html",
                           username=username,
                           logs=login_logs,
                           comment_count=comment_count,
                           active_users=active_users,
                           recent_comments=recent_comments,
                           log_page=page,
                           log_total_pages=total_pages)


'''
@app.route("/make-admin")
def make_admin():
    username = session.get("username")
    if not username:
        return "❌ Please log in first."

    users.update_one({"username": username}, {"$set": {"is_admin": True}})
    return f"✅ User '{username}' is now an admin." '''

@app.route("/import/movies", methods=["GET"])
def import_movies():
    username = session.get("username")
    if not username:
        return "❌ Please log in first.", 403

    user = users.find_one({"username": username})
    if not user or not user.get("is_admin"):
        return "❌ Access denied. Admin only.", 403

    page = int(request.args.get("page", 1))
    api_key = "0530fc67fb10c009b85f55ef0a0ec0d6"
    imported = 0
    failed_movies = []

    try:
        url = f"https://api.themoviedb.org/3/movie/popular?api_key={api_key}&language=en-US&page={page}"
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        return f"❌ Failed to fetch TMDb data: {str(e)}", 500

    for movie in data.get("results", []):
        movie_id = movie["id"]
        try:
            detail_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&language=en-US"
            credits_url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={api_key}&language=en-US"
            reviews_url = f"https://api.themoviedb.org/3/movie/{movie_id}/reviews?api_key={api_key}&language=en-US"
            recommendations_url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations?api_key={api_key}&language=en-US"

            detail = requests.get(detail_url).json()
            credits = requests.get(credits_url).json()
            reviews = requests.get(reviews_url).json().get("results", [])
            recommendations = requests.get(recommendations_url).json().get("results", [])

            movie_cache.replace_one(
                {"_id": movie_id},
                {
                    "_id": movie_id,
                    "detail": detail,
                    "credits": credits,
                    "reviews": reviews,
                    "recommendations": recommendations,
                    "cached_at": datetime.utcnow()
                },
                upsert=True
            )
            imported += 1
        except Exception as e:
            failed_movies.append({"id": movie_id, "error": str(e)})

    return render_template("import_result.html", count=imported, failed=failed_movies, page=page)


@app.route("/export/current_page.csv")
def export_current_page_csv():
    page = int(request.args.get("page", 1))
    per_page = 10
    skip = (page - 1) * per_page

    cursor = movie_cache.find().skip(skip).limit(per_page)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Year", "Genres", "Plot", "Poster URL"])

    for m in cursor:
        d = m.get("detail", {})
        genres = [g.get("name", "Unknown") for g in d.get("genres", [])]
        writer.writerow([
            m["_id"],
            d.get("title", "N/A"),
            d.get("release_date", "")[:4],
            ", ".join(genres),
            d.get("overview", ""),
            f"https://image.tmdb.org/t/p/w200{d.get('poster_path', '')}" if d.get("poster_path") else ""
        ])

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={
        "Content-Disposition": f"attachment;filename=page_{page}_movies.csv"
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
