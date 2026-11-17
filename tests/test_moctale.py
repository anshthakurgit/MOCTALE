"""
Moctale — Automated Test Suite
Covers: Data integrity, model artifacts, search, recommendations, edge cases, TMDB resilience, and Flask REST API.
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.recommender import recommender
from src.tmdb_client import TMDBClient
from app import app


class TestMoctaleSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Ensure recommender is initialized once for all tests."""
        recommender.load_artifacts()
        cls.client = app.test_client()

    # 1. Dataset & Artifact Integrity Tests
    def test_01_artifacts_loaded(self):
        """Verify model artifacts loaded cleanly."""
        self.assertTrue(recommender.is_loaded)
        self.assertIsNotNone(recommender.movies_df)
        self.assertGreater(len(recommender.movies_df), 4700)

    def test_02_no_duplicate_movie_ids(self):
        """Ensure no duplicate movie IDs exist in the processed dataset."""
        movie_ids = recommender.movies_df["movie_id"]
        self.assertEqual(len(movie_ids), len(movie_ids.unique()))

    def test_03_no_index_gaps(self):
        """Verify DataFrame index is continuous and 0-indexed with no gaps."""
        df = recommender.movies_df
        self.assertEqual(df.index[0], 0)
        self.assertEqual(df.index[-1], len(df) - 1)

    def test_04_required_columns_present(self):
        """Verify all critical columns exist in the metadata DataFrame."""
        required = ["movie_id", "title", "title_lower", "overview", "genres_list", "director"]
        for col in required:
            self.assertIn(col, recommender.movies_df.columns)

    # 2. Search & Fuzzy Matching Tests
    def test_05_search_exact_match(self):
        """Test searching for exact title 'Avatar'."""
        results = recommender.search_movies("Avatar", limit=5)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["title"], "Avatar")

    def test_06_search_prefix_match(self):
        """Test prefix matching for 'the dark'."""
        results = recommender.search_movies("the dark", limit=5)
        self.assertGreater(len(results), 0)
        titles = [r["title"].lower() for r in results]
        self.assertTrue(any("dark" in t for t in titles))

    def test_07_search_fuzzy_typo(self):
        """Test search fuzzy typo correction for 'inteception'."""
        results = recommender.search_movies("inteception", limit=5)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["title"], "Inception")

    def test_08_search_empty_query(self):
        """Test search with empty query returns empty list."""
        results = recommender.search_movies("", limit=5)
        self.assertEqual(results, [])

    # 3. Recommendation Engine Tests
    def test_09_recommend_avatar(self):
        """Test recommendations for 'Avatar'."""
        res = recommender.recommend("Avatar", top_k=5, enrich_tmdb=False)
        self.assertTrue(res["success"])
        self.assertEqual(res["selected_movie"]["title"], "Avatar")
        self.assertEqual(len(res["recommendations"]), 5)
        
        # Verify Avatar is excluded from its own recommendations
        rec_titles = [r["title"] for r in res["recommendations"]]
        self.assertNotIn("Avatar", rec_titles)

    def test_10_recommend_by_movie_id(self):
        """Test recommendations using integer TMDB ID (19995 for Avatar)."""
        res = recommender.recommend(19995, top_k=5, enrich_tmdb=False)
        self.assertTrue(res["success"])
        self.assertEqual(res["selected_movie"]["title"], "Avatar")

    def test_11_recommend_end_of_dataset_movie(self):
        """Test recommendation for movie at the exact end of dataset ('My Date with Drew')."""
        last_movie = recommender.movies_df.iloc[-1]["title"]
        res = recommender.recommend(last_movie, top_k=5, enrich_tmdb=False)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["recommendations"]), 5)

    def test_12_recommend_invalid_movie(self):
        """Test recommendation for a non-existent movie."""
        res = recommender.recommend("NonExistentFakeMovieXYZ", top_k=5, enrich_tmdb=False)
        self.assertFalse(res["success"])
        self.assertIsNone(res["selected_movie"])
        self.assertEqual(res["recommendations"], [])

    # 4. TMDB Client & Fallback Tests
    def test_13_tmdb_fallback_on_invalid_id(self):
        """Ensure TMDB client returns a safe fallback for invalid ID without throwing."""
        client = TMDBClient()
        meta = client.get_movie_metadata(-999)
        self.assertIsNotNone(meta)
        self.assertIn("poster_url", meta)
        self.assertTrue(meta["poster_url"].endswith(".svg"))

    def test_14_tmdb_client_offline_behavior(self):
        """Ensure client falls back safely when credentials are missing or wrong."""
        dummy_client = TMDBClient(api_key="invalid_key", access_token="")
        meta = dummy_client.get_movie_metadata(99999999)
        self.assertIsNotNone(meta)
        self.assertEqual(meta["poster_url"], "/static/images/poster_placeholder.svg")

    # 5. Flask API Route Tests
    def test_15_flask_health_endpoint(self):
        """Verify GET /health returns 200 and healthy status."""
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["status"], "healthy")

    def test_16_flask_search_api(self):
        """Verify GET /api/search?q=pulp."""
        r = self.client.get("/api/search?q=pulp")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertGreater(data["count"], 0)
        self.assertEqual(data["results"][0]["title"], "Pulp Fiction")

    def test_17_flask_recommend_api(self):
        """Verify GET /api/recommend?movie=Interstellar."""
        r = self.client.get("/api/recommend?movie=Interstellar&top_k=5")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["selected_movie"]["title"], "Interstellar")
        self.assertEqual(len(data["recommendations"]), 5)

    def test_18_flask_recommend_missing_param(self):
        """Verify GET /api/recommend without 'movie' parameter returns 400."""
        r = self.client.get("/api/recommend")
        self.assertEqual(r.status_code, 400)

    def test_19_flask_featured_api(self):
        """Verify GET /api/featured returns curated movies."""
        r = self.client.get("/api/featured")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["movies"]), 4)

    def test_20_flask_movie_details_api(self):
        """Verify GET /api/movie/<id> returns movie metadata."""
        # Movie ID 19995 = Avatar
        r = self.client.get("/api/movie/19995")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["movie"]["title"], "Avatar")

    # 6. Archive Pagination & Poster-First Tests
    def test_21_archive_pagination(self):
        """Verify GET /api/archive returns requested page size and pagination metadata."""
        r = self.client.get("/api/archive?page=1&limit=12")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["movies"]), 12)
        self.assertEqual(data["page"], 1)
        self.assertTrue(data["has_more"])
        self.assertGreater(data["total_available"], 24)

    def test_22_archive_no_duplicates(self):
        """Verify page 1 and page 2 have zero overlapping movie IDs."""
        r1 = self.client.get("/api/archive?page=1&limit=12")
        r2 = self.client.get("/api/archive?page=2&limit=12")
        ids_p1 = {m["movie_id"] for m in r1.get_json()["movies"]}
        ids_p2 = {m["movie_id"] for m in r2.get_json()["movies"]}
        overlap = ids_p1.intersection(ids_p2)
        self.assertEqual(len(overlap), 0, f"Found duplicate movie IDs across pages: {overlap}")

    def test_23_archive_poster_first(self):
        """Verify all archive movies have verified TMDB posters and not placeholders."""
        r = self.client.get("/api/archive?page=1&limit=12")
        movies = r.get_json()["movies"]
        for m in movies:
            self.assertIn("poster_url", m)
            self.assertTrue(m["poster_url"].startswith("https://image.tmdb.org/t/p/w500/"))

    def test_24_archive_invalid_params(self):
        """Verify boundary pagination parameters are normalized safely."""
        r = self.client.get("/api/archive?page=-5&limit=999")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["page"], 1)
        self.assertLessEqual(len(data["movies"]), 24)

    # 7. ML Engine & Inspection Route Tests
    def test_25_ml_stats_api(self):
        """Verify GET /api/ml-stats returns verified dimensions and statistics."""
        r = self.client.get("/api/ml-stats")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["success"])
        stats = data["stats"]
        self.assertEqual(stats["total_movies"], 4800)
        self.assertEqual(stats["vocabulary_size"], 5000)
        self.assertAlmostEqual(stats["matrix_sparsity_percent"], 99.39, places=1)

    def test_26_ml_inspect_api(self):
        """Verify GET /api/ml-inspect returns deep vector and similarity breakdown."""
        r = self.client.get("/api/ml-inspect?movie=Inception")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["title"], "Inception")
        self.assertGreater(data["active_feature_dimensions"], 0)
        self.assertGreater(len(data["synthesized_tag_sample"]), 0)
        self.assertEqual(len(data["recommendations"]), 5)

    def test_27_ml_engine_routes(self):
        """Verify both /ml-engine and /architecture render the ML Engine template."""
        r1 = self.client.get("/ml-engine")
        self.assertEqual(r1.status_code, 200)
        self.assertIn(b"The Intelligence Behind Moctale", r1.data)

        r2 = self.client.get("/architecture")
        self.assertEqual(r2.status_code, 200)
        self.assertIn(b"The Intelligence Behind Moctale", r2.data)


if __name__ == "__main__":
    unittest.main()
