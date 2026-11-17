"""
Module: build_model.py
Description: End-to-end data extraction, preprocessing, vectorization, and artifact serialization
for the Moctale content-based recommendation engine.
"""

import os
import ast
import pickle
import logging
from pathlib import Path
import numpy as np
import pandas as pd
from nltk.stem.porter import PorterStemmer
from sklearn.feature_extraction.text import CountVectorizer
from scipy import sparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"


def find_dataset(filename: str) -> Path:
    """Locate a dataset file in candidate directories."""
    candidates = [
        BASE_DIR / filename,
        BASE_DIR / "data" / filename,
        BASE_DIR / "MOCTALE" / filename,
        Path.cwd() / filename,
        Path.cwd() / "data" / filename,
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"Could not locate dataset file: {filename}")


def convert_genres_keywords(obj) -> list:
    """Extract list of genre or keyword names from JSON string."""
    names = []
    if not isinstance(obj, str):
        return names
    try:
        data = ast.literal_eval(obj)
        for item in data:
            if isinstance(item, dict) and "name" in item:
                names.append(item["name"])
    except Exception:
        pass
    return names


def convert_cast(obj, top_n: int = 3) -> list:
    """Extract top N cast members from JSON string."""
    cast = []
    if not isinstance(obj, str):
        return cast
    try:
        data = ast.literal_eval(obj)
        for item in data[:top_n]:
            if isinstance(item, dict) and "name" in item:
                cast.append(item["name"])
    except Exception:
        pass
    return cast


def fetch_director(obj) -> list:
    """Extract director name from crew JSON string."""
    director = []
    if not isinstance(obj, str):
        return director
    try:
        data = ast.literal_eval(obj)
        for item in data:
            if isinstance(item, dict) and item.get("job") == "Director":
                director.append(item["name"])
                break
    except Exception:
        pass
    return director


def build():
    """Main build function to process raw data and generate serialized artifacts."""
    logger.info("Starting Moctale ML artifact build pipeline...")

    movies_path = find_dataset("tmdb_5000_movies.csv")
    credits_path = find_dataset("tmdb_5000_credits.csv")
    logger.info("Found movies dataset: %s", movies_path)
    logger.info("Found credits dataset: %s", credits_path)

    movies = pd.read_csv(movies_path)
    credits = pd.read_csv(credits_path)
    logger.info("Raw shapes - Movies: %s, Credits: %s", movies.shape, credits.shape)

    # 1. Merge datasets by unique primary key (id == movie_id)
    # This prevents the Cartesian duplicate product caused by merging on 'title'
    merged = movies.merge(credits, left_on="id", right_on="movie_id")
    logger.info("Merged dataset shape by unique ID: %s", merged.shape)

    # 2. Select relevant fields and preserve extra display metadata for UI
    fields = [
        "id",
        "title_x",
        "overview",
        "genres",
        "keywords",
        "cast",
        "crew",
        "vote_average",
        "release_date",
        "runtime",
    ]
    df = merged[fields].copy()
    df.rename(columns={"id": "movie_id", "title_x": "title"}, inplace=True)

    # 3. Handle missing values & strictly reset index to prevent desynchronization
    df.dropna(subset=["overview"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    logger.info("Dataset shape after dropna and reset_index: %s", df.shape)

    # 4. Feature engineering
    logger.info("Extracting genres, keywords, cast, and director...")
    raw_genres = df["genres"].apply(convert_genres_keywords)
    raw_keywords = df["keywords"].apply(convert_genres_keywords)
    raw_cast = df["cast"].apply(convert_cast)
    raw_director = df["crew"].apply(fetch_director)

    # Store clean human-readable versions for display
    df["genres_list"] = raw_genres
    df["keywords_list"] = raw_keywords
    df["cast_list"] = raw_cast
    df["director_list"] = raw_director
    df["director"] = raw_director.apply(lambda x: x[0] if len(x) > 0 else "Unknown")

    # Format release year
    df["release_year"] = pd.to_datetime(df["release_date"], errors="coerce").dt.year.fillna(0).astype(int)

    # Strip whitespace from entity tokens (e.g. 'Science Fiction' -> 'ScienceFiction')
    genres_tokens = raw_genres.apply(lambda x: [i.replace(" ", "") for i in x])
    keywords_tokens = raw_keywords.apply(lambda x: [i.replace(" ", "") for i in x])
    cast_tokens = raw_cast.apply(lambda x: [i.replace(" ", "") for i in x])
    director_tokens = raw_director.apply(lambda x: [i.replace(" ", "") for i in x])
    overview_tokens = df["overview"].apply(lambda x: x.split() if isinstance(x, str) else [])

    # Synthesize unified tag corpus
    df["tags_list"] = overview_tokens + genres_tokens + keywords_tokens + cast_tokens + director_tokens
    df["tags"] = df["tags_list"].apply(lambda x: " ".join(x).lower())
    df["title_lower"] = df["title"].str.lower().str.strip()

    # 5. Word Stemming using PorterStemmer
    logger.info("Applying PorterStemmer to tag corpus...")
    ps = PorterStemmer()
    df["tags"] = df["tags"].apply(lambda text: " ".join([ps.stem(word) for word in text.split()]))

    # 6. Bag-of-Words Vectorization using CountVectorizer
    logger.info("Vectorizing tags corpus (max_features=5000, stop_words='english')...")
    cv = CountVectorizer(max_features=5000, stop_words="english")
    feature_matrix = cv.fit_transform(df["tags"])
    logger.info("Feature matrix generated: %s, non-zero entries: %s", feature_matrix.shape, feature_matrix.nnz)

    # 7. Serialize artifacts
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # Keep a lightweight DataFrame for metadata lookups
    metadata_cols = [
        "movie_id",
        "title",
        "title_lower",
        "overview",
        "genres_list",
        "keywords_list",
        "cast_list",
        "director",
        "vote_average",
        "release_year",
        "runtime",
    ]
    movies_metadata = df[metadata_cols].copy()

    metadata_file = ARTIFACTS_DIR / "movies_list.pkl"
    with open(metadata_file, "wb") as f:
        pickle.dump(movies_metadata, f)
    logger.info("Saved metadata artifact: %s (size: %.2f KB)", metadata_file, metadata_file.stat().st_size / 1024)

    # Save sparse feature matrix (extremely fast, lightweight ~1.5 MB)
    matrix_file = ARTIFACTS_DIR / "feature_matrix.npz"
    sparse.save_npz(matrix_file, feature_matrix)
    logger.info("Saved sparse feature matrix: %s (size: %.2f KB)", matrix_file, matrix_file.stat().st_size / 1024)

    # Also precalculate and save top-20 nearest neighbors index to make lookups O(1) in production!
    logger.info("Precomputing top nearest-neighbor indices for ultra-fast production queries...")
    from sklearn.metrics.pairwise import cosine_similarity
    
    # We can compute top-30 indices per movie in chunks to keep memory usage low:
    top_indices_map = {}
    chunk_size = 500
    n_movies = feature_matrix.shape[0]
    
    for i in range(0, n_movies, chunk_size):
        end = min(i + chunk_size, n_movies)
        chunk_sim = cosine_similarity(feature_matrix[i:end], feature_matrix)
        for row_idx in range(chunk_sim.shape[0]):
            global_idx = i + row_idx
            # Sort descending, exclude self (index 0 after sort is self with score 1.0)
            sorted_row = np.argsort(chunk_sim[row_idx])[::-1]
            top_neighbors = []
            for neighbor_idx in sorted_row:
                if neighbor_idx != global_idx:
                    top_neighbors.append((int(neighbor_idx), float(np.round(chunk_sim[row_idx][neighbor_idx], 4))))
                if len(top_neighbors) >= 20:
                    break
            top_indices_map[global_idx] = top_neighbors

    top_neighbors_file = ARTIFACTS_DIR / "top_neighbors.pkl"
    with open(top_neighbors_file, "wb") as f:
        pickle.dump(top_indices_map, f)
    logger.info("Saved precomputed top neighbors: %s (size: %.2f KB)", top_neighbors_file, top_neighbors_file.stat().st_size / 1024)

    logger.info("All model artifacts built successfully!")


if __name__ == "__main__":
    build()
