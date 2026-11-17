"""
Moctale — Premium Movie Recommendation Web Application
Backend Server: Flask REST API + Static Frontend Delivery
"""

import os
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from src.recommender import recommender
from src.tmdb_client import tmdb_client

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)

# Configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "moctale-cinema-secret-key-2026")
app.config["JSON_SORT_KEYS"] = False

# Ensure model artifacts are loaded at application startup
try:
    recommender.load_artifacts()
    logger.info("Moctale recommendation engine preloaded successfully.")
except Exception as e:
    logger.error("Failed to preload model artifacts: %s", e)


@app.route("/")
def index():
    """Serve the primary Moctale single-page application with pre-seeded archive films."""
    try:
        archive_res = recommender.get_archive_movies(page=1, limit=8)
        archive_movies = archive_res.get("movies", []) if archive_res.get("success") else []
    except Exception as e:
        logger.error("Error pre-rendering archive movies: %s", e)
        archive_movies = []
    return render_template("index.html", archive_movies=archive_movies)


@app.route("/ml-engine")
@app.route("/architecture")
def ml_engine():
    """Serve the dedicated interactive Machine Learning Engine showcase page."""
    return render_template("ml_engine.html")


@app.route("/health")
def health():
    """Health check endpoint for Render and monitoring."""
    return jsonify({
        "status": "healthy",
        "service": "moctale-movie-recommender",
        "movies_loaded": len(recommender.movies_df) if recommender.is_loaded else 0,
    }), 200


@app.route("/api/search")
def api_search():
    """
    Search movie catalog.
    Query parameters:
        q: search query string
        limit: max results (default: 8, max: 20)
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"query": "", "results": [], "count": 0}), 200

    try:
        limit = min(int(request.args.get("limit", 8)), 20)
    except ValueError:
        limit = 8

    results = recommender.search_movies(query, limit=limit)
    return jsonify({
        "query": query,
        "results": results,
        "count": len(results),
    }), 200


@app.route("/api/recommend")
def api_recommend():
    """
    Generate movie recommendations.
    Query parameters:
        movie: movie title string or integer TMDB ID
        top_k: number of recommendations (default: 5, max: 10)
    """
    query = request.args.get("movie", "").strip()
    if not query:
        return jsonify({
            "success": False,
            "message": "Missing required query parameter: 'movie'",
            "selected_movie": None,
            "recommendations": [],
        }), 400

    try:
        top_k = min(int(request.args.get("top_k", 5)), 10)
    except ValueError:
        top_k = 5

    try:
        data = recommender.recommend(query, top_k=top_k, enrich_tmdb=True)
        status_code = 200 if data["success"] else 404
        return jsonify(data), status_code
    except Exception as e:
        logger.error("Error generating recommendations for '%s': %s", query, e, exc_info=True)
        return jsonify({
            "success": False,
            "message": "An error occurred while generating recommendations.",
            "error": str(e),
        }), 500


@app.route("/api/movie/<int:movie_id>")
def api_movie_details(movie_id):
    """Retrieve full movie details including TMDB metadata."""
    try:
        movie = recommender.get_movie_by_id(movie_id, enrich_tmdb=True)
        if not movie:
            return jsonify({"success": False, "message": f"Movie ID {movie_id} not found."}), 404
        return jsonify({"success": True, "movie": movie}), 200
    except Exception as e:
        logger.error("Error retrieving movie %s: %s", movie_id, e)
        return jsonify({"success": False, "message": "Failed to retrieve movie details."}), 500


@app.route("/api/featured")
def api_featured():
    """Retrieve curated collection of featured films for hero and explore sections."""
    try:
        featured = recommender.get_featured_movies(limit=8)
        return jsonify({"success": True, "count": len(featured), "movies": featured}), 200
    except Exception as e:
        logger.error("Error retrieving featured movies: %s", e)
        return jsonify({"success": False, "movies": []}), 500


@app.route("/api/archive")
def api_archive():
    """
    Retrieve poster-first paginated movies for the Archive view.
    Query parameters:
        page: int (default 1)
        limit: int (default 8, max 24)
    """
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        page = 1

    try:
        limit = min(max(int(request.args.get("limit", 8)), 1), 24)
    except ValueError:
        limit = 8

    try:
        data = recommender.get_archive_movies(page=page, limit=limit)
        return jsonify(data), 200
    except Exception as e:
        logger.error("Error retrieving archive page %s: %s", page, e, exc_info=True)
        return jsonify({"success": False, "message": "Failed to retrieve archive.", "movies": []}), 500


@app.route("/api/ml-stats")
def api_ml_stats():
    """Retrieve verified dimensional and algorithmic statistics for the ML Engine showcase."""
    try:
        stats = recommender.get_ml_stats()
        return jsonify({"success": True, "stats": stats}), 200
    except Exception as e:
        logger.error("Error retrieving ML statistics: %s", e)
        return jsonify({"success": False, "message": "Failed to retrieve ML statistics."}), 500


@app.route("/api/ml-inspect")
def api_ml_inspect():
    """
    Inspect a movie's internal feature vector and similarity calculations.
    Query parameters:
        movie: title string or integer TMDB ID
    """
    query = request.args.get("movie", "Inception").strip()
    try:
        data = recommender.inspect_movie_ml(query)
        status_code = 200 if data["success"] else 404
        return jsonify(data), status_code
    except Exception as e:
        logger.error("Error inspecting ML for movie '%s': %s", query, e)
        return jsonify({"success": False, "message": "ML inspection failed.", "error": str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404
    return render_template("index.html")


@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "error": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    logger.info("Starting Moctale Web Application on port %d...", port)
    app.run(host="0.0.0.0", port=port, debug=debug)
