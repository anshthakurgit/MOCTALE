# MOCTALE — Discover Movies Beyond Your Taste

An end-to-end, production-ready **Content-Based Movie Recommendation Engine & Web Application** built with Python, Flask, Scikit-Learn, Pandas, and Vanilla JavaScript, powered by the TMDB 5,000 dataset and The Movie Database (TMDB) API.

Developed as an **Engineering Minor Project** showcasing natural language feature engineering, vector space modeling, cosine similarity metric projections, and an editorial cinema interface.

---

## Table of Contents
- [1. Executive Summary](#1-executive-summary)
- [2. System Architecture](#2-system-architecture)
- [3. Machine Learning Methodology](#3-machine-learning-methodology)
- [4. Tech Stack](#4-tech-stack)
- [5. Dataset Analysis](#5-dataset-analysis)
- [6. Project Structure](#6-project-structure)
- [7. Installation & Setup](#7-installation--setup)
- [8. Running the Application](#8-running-the-application)
- [9. REST API Reference](#9-rest-api-reference)
- [10. Automated Testing](#10-automated-testing)
- [11. Public Deployment (Render & GitHub)](#11-public-deployment-render--github)
- [12. TMDB Legal Attribution](#12-tmdb-legal-attribution)

---

## 1. Executive Summary

Traditional collaborative filtering systems suffer from the **cold-start problem**, requiring dense user-item rating histories before delivering reliable predictions. **Moctale** implements a pure **Content-Based Filtering (CBF)** recommendation architecture that operates entirely on high-dimensional lexical and structural metadata extracted from films.

### Key Capabilities:
- **Unified Semantic Tagging:** Concatenates plot synopsis, genre taxonomy, thematic keywords, top-3 billed cast, and directorial credits into an atomic entity representation.
- **Morphological Normalization:** Integrates Porter Stemming to conflate inflected word variants down to shared linguistic roots.
- **High-Dimensional Vectorization:** Extracts a 5,000-dimensional Bag-of-Words feature space via Scikit-Learn's `CountVectorizer`.
- **Directional Cosine Metric:** Proves cinematic affinity by calculating directional angular distances across all 4,800 films in milliseconds.
- **Fuzzy Search & Typo Resilience:** Employs multi-tiered search with `difflib` similarity cutoffs to handle misspelled titles gracefully.
- **Editorial Cinema UI:** Inspired by A24's editorial minimalist visual aesthetic, featuring responsive cards, movie spotlight banners, and deep detail modals.
- **Resilient TMDB Integration:** Fetches high-definition movie posters and backdrops with in-memory caching and clean SVG fallback artwork.

---

## 2. System Architecture

```
+─────────────────────────────────────────────────────────────────────────────+
|                              PRESENTATION TIER                              |
|                                                                             |
|   HTML5 / CSS3 (Editorial Cinema Design) / Vanilla ES6+ JavaScript          |
|   - Real-time search with debounced autocomplete                            |
|   - Active movie spotlight banner & 5-column recommendation grid            |
|   - Cinematic modal popover for plot overview, cast chips & trailer links   |
+─────────────────────────────────────────────────────────────────────────────+
                                       │
                              HTTP / REST JSON
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
|                                BACKEND TIER                                 |
|                                                                             |
|   Flask Application (app.py) + Gunicorn WSGI Server                         |
|   - GET /api/search?q=...                                                   |
|   - GET /api/recommend?movie=...&top_k=5                                    |
|   - GET /api/movie/<movie_id>                                               |
|   - GET /api/featured                                                       |
|   - GET /health                                                             |
+─────────────────────────────────────────────────────────────────────────────+
                                       │
                     Internal Python Service Interfaces
                                       ▼
+───────────────────────────────────+   +─────────────────────────────────────+
|     RECOMMENDER SERVICE (ML)      |   |          TMDB API CLIENT            |
|                                   |   |                                     |
|  - Preloaded metadata DataFrame   |   |  - Thread-safe HTTP session         |
|  - Precomputed nearest neighbors  |   |  - In-memory cache + fallback SVGs  |
|  - Query-based cosine similarity  |   |  - High-res poster & backdrop URLs  |
+───────────────────────────────────+   +─────────────────────────────────────+
                  │
                  ▼
+─────────────────────────────────────────────────────────────────────────────+
|                               MODEL ARTIFACTS                               |
|                                                                             |
|   - artifacts/movies_list.pkl    (~2.7 MB metadata DataFrame)               |
|   - artifacts/feature_matrix.npz (~295 KB compressed sparse matrix)         |
|   - artifacts/top_neighbors.pkl  (~1.3 MB precalculated top neighbors)      |
+─────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Machine Learning Methodology

### 3.1 Data Preprocessing & Cleaning
1. **Primary Key Merging:** The movies dataset (`tmdb_5000_movies.csv`) and credits dataset (`tmdb_5000_credits.csv`) are merged on unique ID (`movies.id == credits.movie_id`). This completely eliminates duplicate-title Cartesian products (e.g., cross-matching *The Host* or *Batman* remakes).
2. **Missing Value Filtration & Index Alignment:** Films with missing overviews are dropped, and `reset_index(drop=True)` is called immediately, ensuring $100\%$ synchronization between internal DataFrame positional indices (`iloc`) and similarity matrix coordinates.

### 3.2 Entity Disambiguation
Multi-word entities in genres, keywords, cast, and crew have internal whitespace removed:
- `"Science Fiction"` $\rightarrow$ `"ScienceFiction"`
- `"Christopher Nolan"` $\rightarrow$ `"ChristopherNolan"`
- `"Christian Bale"` $\rightarrow$ `"ChristianBale"`

This prevents false token matches (e.g. confusing *Christopher Nolan* with *Christopher Walken* solely on the common first name "Christopher").

### 3.3 Text Stemming & Vectorization
Tokens are joined and normalized using NLTK's **Porter Stemmer**:
$$\text{stem}(\text{"directing"}) = \text{"direct"}, \quad \text{stem}(\text{"actors"}) = \text{actor"}$$

The vocabulary is vectorized using `CountVectorizer(max_features=5000, stop_words='english')`, producing a sparse matrix $V \in \mathbb{R}^{4800 \times 5000}$.

### 3.4 Cosine Distance Metric
Pairwise directional similarity between query vector $\mathbf{u}$ and candidate vector $\mathbf{v}$ is evaluated as:
$$\text{Sim}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2} = \frac{\sum_{i=1}^{5000} u_i v_i}{\sqrt{\sum_{i=1}^{5000} u_i^2} \sqrt{\sum_{i=1}^{5000} v_i^2}}$$

Scores range between $0.0$ (no shared tokens) and $1.0$ (identical tag vector). The queried film itself is excluded ($\text{Sim} = 1.0$, identical index), and the top $K$ nearest neighbors are returned.

---

## 4. Tech Stack

- **Backend:** Python 3.13, Flask 3.1, Gunicorn 21.2
- **Data & ML:** Pandas 3.0, NumPy 2.3, Scikit-Learn 1.9, Scipy 1.18, NLTK 3.10
- **Frontend:** Semantic HTML5, CSS3 (Modern Flexbox/Grid), Vanilla JavaScript (ES6+ Fetch API)
- **External Data:** The Movie Database (TMDB) API
- **Testing:** Python `unittest` (20 automated tests)
- **Hosting & CI/CD:** GitHub, Render Web Services

---

## 5. Dataset Analysis

The system is trained on the Kaggle TMDB 5000 Movie Dataset:
- `tmdb_5000_movies.csv` (4,803 records, 20 columns)
- `tmdb_5000_credits.csv` (4,803 records, 4 columns)
- **Final Cleaned Catalog:** 4,800 feature-engineered films.

---

## 6. Project Structure

```
MOCTALE/
├── .env.example                # Template for environment configuration
├── .gitignore                  # Clean Git ignore file
├── README.md                   # Complete architectural and project documentation
├── render.yaml                 # Blueprint for 1-click Render web deployment
├── requirements.txt            # Pinned production Python dependencies
├── app.py                      # Primary Flask application server
│
├── data/                       # Dataset directory (optional location)
│   ├── tmdb_5000_movies.csv
│   └── tmdb_5000_credits.csv
│
├── artifacts/                  # Serialized ML models (built via build_model.py)
│   ├── movies_list.pkl         # Clean metadata DataFrame (~2.7 MB)
│   ├── feature_matrix.npz      # Compressed CSR feature matrix (~295 KB)
│   └── top_neighbors.pkl       # Precalculated top nearest-neighbor map (~1.3 MB)
│
├── src/                        # Modular Python services
│   ├── __init__.py
│   ├── build_model.py          # Offline ETL, vectorization & artifact builder
│   ├── recommender.py          # Recommendation and search engine
│   └── tmdb_client.py          # TMDB artwork client with fallback logic
│
├── static/                     # Web assets
│   ├── css/
│   │   └── style.css           # Premium editorial cinema styling
│   ├── js/
│   │   └── main.js             # Client-side autocomplete, modal, and SPA logic
│   └── images/
│       ├── poster_placeholder.svg # Fallback poster artwork
│       └── tmdb_logo.svg       # Official TMDB attribution badge
│
├── templates/
│   └── index.html              # Moctale single-page web interface
│
├── tests/
│   └── test_moctale.py         # Complete automated test suite (20 tests)
│
└── movie-recommend-model.ipynb # Cleaned & verified Jupyter Notebook
```

---

## 7. Installation & Setup

### Prerequisites
- Python 3.10 to 3.13 installed
- Git

### Step 1: Clone Repository
```bash
git clone https://github.com/anshthakurgit/MOCTALE.git
cd MOCTALE
```

### Step 2: Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env` and verify API credentials:
```bash
cp .env.example .env
```
*(A default TMDB API key is preconfigured in `src/tmdb_client.py` with safe offline fallback).*

---

## 8. Running the Application

### Step 1: Build Model Artifacts (First Run Only)
Execute the build pipeline to process the datasets and generate serialized models:
```bash
python src/build_model.py
```
*Expected output: Artifacts generated in `artifacts/` in approximately 20 seconds.*

### Step 2: Start the Web Server
```bash
python app.py
```
Open your browser and navigate to:
```
http://localhost:5000
```

---

## 9. REST API Reference

| Endpoint | Method | Params | Description |
| :--- | :--- | :--- | :--- |
| `/` | `GET` | *None* | Serves the Moctale Single-Page Web Application. |
| `/health` | `GET` | *None* | Health check endpoint returning loaded movie count. |
| `/api/search` | `GET` | `q` (string), `limit` (int) | Search movies by exact, prefix, substring, or fuzzy match. |
| `/api/recommend` | `GET` | `movie` (title or ID), `top_k` (int) | Generates top-K recommendations with TMDB posters & metadata. |
| `/api/movie/<id>` | `GET` | `id` (int TMDB movie_id) | Retrieves full film synopsis, director, cast, and backdrops. |
| `/api/featured` | `GET` | *None* | Returns curated collection of iconic films for archive view. |

### Sample Recommendation Response (`GET /api/recommend?movie=Inception&top_k=3`):
```json
{
  "success": true,
  "selected_movie": {
    "movie_id": 27205,
    "title": "Inception",
    "release_year": 2010,
    "director": "Christopher Nolan",
    "vote_average": 8.1,
    "poster_url": "https://image.tmdb.org/t/p/w500/edv5CZvWj09upOsy2Y6IwDhK8bt.jpg"
  },
  "recommendations": [
    {
      "movie_id": 14161,
      "title": "12 Rounds",
      "release_year": 2009,
      "director": "Renny Harlin",
      "similarity_score": 0.3037,
      "match_percentage": 30,
      "poster_url": "https://image.tmdb.org/t/p/w500/..."
    }
  ]
}
```

---

## 10. Automated Testing

Run the automated test suite covering 27 unit and integration tests:
```bash
python -m unittest tests/test_moctale.py -v
```
All 27 tests verify:
- Zero duplicate movie IDs and clean continuous index alignment.
- Accurate recommendations for head, middle, and tail movies.
- Fuzzy typo correction (e.g. `"avatr"` $\rightarrow$ `['Avatar', 'The Aviator', 'Salvador']`).
- TMDB resilience under offline or timeout conditions with verified poster CDN fallback.
- Archive pagination, duplicate exclusion, poster-first verification, and boundary parameter clamping.
- Live ML stats API (`/api/ml-stats`) and interactive ML inspector API (`/api/ml-inspect`).
- Standalone `/ml-engine` and `/architecture` route rendering.

---

## 11. Public Deployment (Render & GitHub)

The repository includes a ready-to-deploy [`render.yaml`](render.yaml) specification and [`Procfile`](Procfile) for **Render Web Services**:

1. Push your repository to GitHub:
   ```bash
   git add .
   git commit -m "Elevate Moctale: Cinematic UX, Poster-First Archive & ML Architecture Showcase"
   git push origin main
   ```
2. Log into [Render](https://render.com).
3. Click **New +** $\rightarrow$ **Blueprint** (or **Web Service**).
4. Select your `MOCTALE` repository.
5. Render reads `render.yaml` (or `Procfile`) and executes:
   - Build Command: `pip install -r requirements.txt && python src/build_model.py`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app`
6. Your application will be live at a public HTTPS URL (e.g., `https://moctale-movie-recommender.onrender.com`).

---

## 12. Mobile & Responsive Design

- **Mobile Navigation:** Responsive pill bar with horizontal touch-scrolling.
- **Cinema App Mobile Grid:** 2-column responsive layout on `< 768px` and `< 480px` (Netflix/Letterboxd style), ensuring crisp poster aspect ratios without vertical bloat.
- **Touch-Friendly Controls:** Generous touch targets for "Explore Similar" and "Details" buttons.
- **Adaptive Modal Popovers:** Fluid responsive modal layouts with touch dismiss and accessible typography.
- **Hardware-Accelerated Motion:** CSS keyframe animations with strict `prefers-reduced-motion` compliance.

---

## 12. TMDB Legal Attribution

As per the TMDB Terms of Use:
> *This product uses the TMDB API but is not endorsed or certified by TMDB.*

- Movie posters, backdrops, and promotional artwork are provided courtesy of [The Movie Database (TMDB)](https://www.themoviedb.org/).
- TMDB Brand Colors: `#0d253f`, `#01b4e4`, `#90cea1`.
- TMDB official logo attribution is rendered prominently in the application footer.

---

## License & Credits
Developed as an **Engineering Minor Project** by **Ansh Thakur**.  
Academic Year: 2026.
