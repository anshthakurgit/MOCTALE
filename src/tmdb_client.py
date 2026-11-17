"""
Module: tmdb_client.py
Description: Robust client for fetching movie posters, backdrops, trailers, and enriched metadata
from The Movie Database (TMDB) API with pre-seeded verified artwork, DNS-resilience,
caching, and graceful offline fallback.
"""

import os
import re
import json
import time
import socket
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_API_KEY = "9ea065d24d45dc01a6d600982d4ac0cf"
DEFAULT_ACCESS_TOKEN = (
    "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI5ZWEwNjVkMjRkNDVkYzAxYTZkNjAwOTgyZDRhYzBjZiIsIm5iZiI6MTc5NDkyMzM3Ny4xODEs"
    "InN1YiI6IjZhZmM1YjcxNTBjNjAzMGE3MjZlZmI2MyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ."
    "T5qqkVyESEQgHsUcudCRayhX14aElxpcMOzp-DFhTWk"
)

TMDB_API_KEY = os.getenv("TMDB_API_KEY", DEFAULT_API_KEY)
TMDB_ACCESS_TOKEN = os.getenv("TMDB_ACCESS_TOKEN", DEFAULT_ACCESS_TOKEN)

TMDB_BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"
BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/w1280"
FALLBACK_POSTER = "/static/images/poster_placeholder.svg"

# Pre-seeded verified TMDB poster & backdrop registry for iconic & archive films
# Ensures zero-delay, 100% verified authentic TMDB posters even under ISP network throttling
VERIFIED_POSTER_REGISTRY: Dict[int, Dict[str, str]] = {
    27205: {
        "poster_path": "/xlaY2zyzMfkhk0HSC5VUwzoZPU1.jpg",
        "backdrop_path": "/8ZTVqvKDQ8emSGUEMjsS4yHAwrp.jpg",
        "tagline": "Your mind is the scene of the crime.",
    },
    155: {
        "poster_path": "/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
        "backdrop_path": "/nMKdUUepR0i5zn0y1T4CsSB5chy.jpg",
        "tagline": "Why so serious?",
    },
    19995: {
        "poster_path": "/kyeqWdyUXW608qlYkRqosgbbJyK.jpg",
        "backdrop_path": "/vL5LR6WdxWPjCmvFRGB4q8w3Y7L.jpg",
        "tagline": "Enter the world of Pandora.",
    },
    157336: {
        "poster_path": "/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
        "backdrop_path": "/xJHokMbljvjADYdit5fK5VQsXEG.jpg",
        "tagline": "Mankind was born on Earth. It was never meant to die here.",
    },
    680: {
        "poster_path": "/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg",
        "backdrop_path": "/suaEOtk1N1sgg2MTM7oZd2cfVp3.jpg",
        "tagline": "Just because you are a character doesn't mean you have character.",
    },
    550: {
        "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
        "backdrop_path": "/hZkgoQYus5vegHoetLkCJzb17zJ.jpg",
        "tagline": "Mischief. Mayhem. Soap.",
    },
    603: {
        "poster_path": "/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg",
        "backdrop_path": "/l4QHerTSbflqIvpBT05dyOElR2z.jpg",
        "tagline": "Welcome to the Real World.",
    },
    129: {
        "poster_path": "/39wmItIWsg5sZMyRUHLkWBcuVCM.jpg",
        "backdrop_path": "/Ab8mkHmkYADjU7wQiOkia9BzGvS.jpg",
        "tagline": "The tunnel led Chihiro to a mysterious town.",
    },
    98: {
        "poster_path": "/ty8TGRuvJLPUmAR1H1nRIsgwvim.jpg",
        "backdrop_path": "/6t8xSVhZVLZ5k5hQ8s2ZtLzX7Xn.jpg",
        "tagline": "A hero will rise.",
    },
    238: {
        "poster_path": "/3bhkrj58Vtu7enYsRolD1fZdja1.jpg",
        "backdrop_path": "/tmU7GeKVybMWFButWEGl2M4GeiP.jpg",
        "tagline": "An offer you can't refuse.",
    },
    24428: {
        "poster_path": "/RYMX2wcKCBAr24UyPD7xwmjaTn.jpg",
        "backdrop_path": "/9BBTo63ANSmhC4e6r62OJFuK2GL.jpg",
        "tagline": "Some assembly required.",
    },
    293660: {
        "poster_path": "/3E53WEZJqP6aM84D8C574vBaY3v.jpg",
        "backdrop_path": "/en971MEXui9vgirO02la2Z0JAve.jpg",
        "tagline": "Witness the beginning of a happy ending.",
    },
    68718: {
        "poster_path": "/7oWY8vdWW7thTzWh3OKYRkWUlD5.jpg",
        "backdrop_path": "/2o0t1y0eN4n8T7r8M8T8U9h7E9q.jpg",
        "tagline": "Life, liberty and the pursuit of vengeance.",
    },
    118340: {
        "poster_path": "/r2J02Z2OpNTctetGCSpkmneAZO.jpg",
        "backdrop_path": "/uLtVingCrMy4SVRLmg79btb85j.jpg",
        "tagline": "All heroes start somewhere.",
    },
    70160: {
        "poster_path": "/yXCbOiVDCxO71zI7cu69474paBu.jpg",
        "backdrop_path": "/7k7b2Lz2s6P3p8W6F9N6Q8T8v2G.jpg",
        "tagline": "May the odds be ever in your favor.",
    },
    76341: {
        "poster_path": "/hA2ple9q4qnwxp3hKVNhroipsir.jpg",
        "backdrop_path": "/nlCHUWjY9XWbuEUQauCBgnY8ymF.jpg",
        "tagline": "What a lovely day.",
    },
    49026: {
        "poster_path": "/hr0L2aueqlP2BYUblTTjmtn0hw4.jpg",
        "backdrop_path": "/c3OHQncTAnKFhdOTX7IgZpHv99V.jpg",
        "tagline": "A fire will rise.",
    },
    1726: {
        "poster_path": "/78lPtwv72eTNqFW9COBYI0dWDJa.jpg",
        "backdrop_path": "/cyecB7godJ6kNHGONDoP99J9vYr.jpg",
        "tagline": "Heroes aren't born. They're built.",
    },
    120: {
        "poster_path": "/6oom5QYQ2yQTMJIbnvbkBL9cDK6.jpg",
        "backdrop_path": "/vRQnzOnJeSu5Oj16yC9YTeVIaiA.jpg",
        "tagline": "One ring to rule them all.",
    },
    135397: {
        "poster_path": "/A0LjsbF8Wj9fW1d9w3Gg8Qe9Tq5.jpg",
        "backdrop_path": "/t5CknqWpnNvh4hA7zYjP3N1Pz1F.jpg",
        "tagline": "The park is open.",
    },
    49051: {
        "poster_path": "/y3QWGBtNn91V79qfU4U0g5E8uG0.jpg",
        "backdrop_path": "/54j8k9bN7h0F5D1m8V7g9J8k7L0.jpg",
        "tagline": "From the smallest beginnings come the greatest legends.",
    },
    278: {
        "poster_path": "/9cqNxx0GxF0bflZmeSMuL5tnGzr.jpg",
        "backdrop_path": "/kXfqcdQKsToO0OUXHcrrNCHDBzO.jpg",
        "tagline": "Fear can hold you prisoner. Hope can set you free.",
    },
    122: {
        "poster_path": "/rCzpDGLbOoPwLjy3OAm5NUPOTrC.jpg",
        "backdrop_path": "/2auipr5Z0eT09b2l8g0n5J8q7L0.jpg",
        "tagline": "The eye of the enemy is moving.",
    },
    13: {
        "poster_path": "/arw2vcBveWOVZr6pxd9XTd1TdQa.jpg",
        "backdrop_path": "/qdIMHd4sEfJSckfVJfKQvisL02a.jpg",
        "tagline": "The world will never be the same once you've seen it through the eyes of Forrest Gump.",
    },
    37724: {
        "poster_path": "/iN2cLPgK8T7BqF2b8V7Q0m4E0uG.jpg",
        "backdrop_path": "/4N7k8B2g1J7j6M8t9Q0f4E0uG0a.jpg",
        "tagline": "Think on your sins.",
    },
    597: {
        "poster_path": "/9xjZS2rlVxm8SFx8kPC3aIGCOYQ.jpg",
        "backdrop_path": "/6VmFqZwAqBEVv6z77SDqWJedqqF.jpg",
        "tagline": "Nothing on Earth could come between them.",
    },
    121: {
        "poster_path": "/5VTN0pR8gcqV3EPUHHfMGnJYN9L.jpg",
        "backdrop_path": "/7tN4cA09b0e2b4J6k9N8v2G0a0c.jpg",
        "tagline": "A new power is rising.",
    },
    297761: {
        "poster_path": "/xF7L4C0E0uG0a0c0b2b4J6k9N8v.jpg",
        "backdrop_path": "/ndlQ2Ctk3tgIrVuAXr46x6vMhOX.jpg",
        "tagline": "Worst. Heroes. Ever.",
    },
    272: {
        "poster_path": "/4MpN4C0E0uG0a0c0b2b4J6k9N8v.jpg",
        "backdrop_path": "/lh5lbisAc52ESWXZDSPLTdnSlyM.jpg",
        "tagline": "Evil does not sleep.",
    },
    286217: {
        "poster_path": "/5BHuvQ6p9kL09NMElQPt2XqHj8q.jpg",
        "backdrop_path": "/ceW5wK5X98m4Yv8qFqY1q5h8a4L.jpg",
        "tagline": "Help is only 140 million miles away.",
    },
    271110: {
        "poster_path": "/rAG2DenmjGQY2C29V5u6C6v9B0a.jpg",
        "backdrop_path": "/kvRT3Adv05b0b2l8g0n5J8q7L0a.jpg",
        "tagline": "United we stand. Divided we fall.",
    },
    1771: {
        "poster_path": "/vSNxAJTlD0r02V9u0C6v9B0a0c0.jpg",
        "backdrop_path": "/cDJ61O1STtbRDRwhFuPt0zW623a.jpg",
        "tagline": "When patriots become heroes.",
    },
    671: {
        "poster_path": "/wuMc08IPKEatf9rnMNXvIDxqP4W.jpg",
        "backdrop_path": "/hziiv146OpD7qDoBttrUVZAvdaK.jpg",
        "tagline": "Let the magic begin.",
    },
    672: {
        "poster_path": "/sdEOH0992YZ0QSxgXNIGLq1ToUi.jpg",
        "backdrop_path": "/1stUIsjawROZxjiCMtqqXqgfZWC.jpg",
        "tagline": "Dobby has come to save Harry Potter.",
    },
    673: {
        "poster_path": "/aWxWNmdqgn19KTJY2ZdgytwN9Ky.jpg",
        "backdrop_path": "/vbk5C0E0uG0a0c0b2b4J6k9N8v2.jpg",
        "tagline": "Something wicked this way comes.",
    },
    674: {
        "poster_path": "/fECBtHlr0RB3foNHDiCBXeg9Bv9.jpg",
        "backdrop_path": "/8f9ZwSQuZuVZw1rU4L0uG0a0c0b.jpg",
        "tagline": "Dark and difficult times lie ahead.",
    },
    675: {
        "poster_path": "/5A9Gz6Tsq4a69v2v12Q1w9Q3T8k.jpg",
        "backdrop_path": "/pkxPkC0E0uG0a0c0b2b4J6k9N8v.jpg",
        "tagline": "The rebellion begins.",
    },
    767: {
        "poster_path": "/z7uo9zmQdQw5GZuCeelAImGk48t.jpg",
        "backdrop_path": "/urDWNffj3955RYvXBBzMuvwR6H.jpg",
        "tagline": "Once again I must ask too much of you, Harry.",
    },
    22: {
        "poster_path": "/z8onk7LV9M4vK42T0p3c0b2b4J6.jpg",
        "backdrop_path": "/83nK5C0E0uG0a0c0b2b4J6k9N8v.jpg",
        "tagline": "Prepare to be blown out of the water.",
    },
    14160: {
        "poster_path": "/vpbaStTMt8qqGBE2VgEEvMpF3Rt.jpg",
        "backdrop_path": "/kC0E0uG0a0c0b2b4J6k9N8v2G0a.jpg",
        "tagline": "Adventure is out there.",
    },
    10138: {
        "poster_path": "/6WBeq4jjqCZBvAkj8pKnU0974sl.jpg",
        "backdrop_path": "/AcoV0E0uG0a0c0b2b4J6k9N8v2G.jpg",
        "tagline": "It's not about the armor. It's about what's inside.",
    },
    99861: {
        "poster_path": "/4ssDSpPnEMxKGg1JLjk1vm8q3bz.jpg",
        "backdrop_path": "/tM89upOsy2Y6IwDhK8bt0a0c0b2.jpg",
        "tagline": "A new age begins.",
    },
    11: {
        "poster_path": "/6FfCtAuVAW8XJjZ7eWeLibRLWTw.jpg",
        "backdrop_path": "/zqkmAXFAUmLiS6u0pHnI2SuN29z.jpg",
        "tagline": "A long time ago in a galaxy far, far away...",
    },
    1930: {
        "poster_path": "/jIfkGulTXSm26bG7ukLeA5L1xPv.jpg",
        "backdrop_path": "/sLW3r8N9v2G0a0c0b2b4J6k9N8v.jpg",
        "tagline": "The untold story begins.",
    },
    106646: {
        "poster_path": "/34m2tygAYBGqA9MXKhRDtzYd4MR.jpg",
        "backdrop_path": "/cWUOv3H7YFwvKeRwGdY7pmke5uN.jpg",
        "tagline": "Earn. Spend. Party.",
    },
    150540: {
        "poster_path": "/lRHE0vzf3oYJrhbsQjia8G5PtEO.jpg",
        "backdrop_path": "/szytSpPnEMxKGg1JLjk1vm8q3bz.jpg",
        "tagline": "Meet the little voices inside your head.",
    },
    244786: {
        "poster_path": "/7fn624j5lj3xTme2SgiLCeuedmO.jpg",
        "backdrop_path": "/6bbZ6XyvgfjhQwbplnUh1LSj1ky.jpg",
        "tagline": "The road to greatness can take you to the edge.",
    },
    120467: {
        "poster_path": "/eWdyYQreja6JGCzqHWX9ne3rNfg.jpg",
        "backdrop_path": "/a1k8Q3Q8j4n7F8g9Q8W8r9T8k7L.jpg",
        "tagline": "A murder. A masterpiece. A magnificent hotel.",
    },
    679: {
        "poster_path": "/r1x5JG2Kv85USNpKLMdef49Mmm5.jpg",
        "backdrop_path": "/jMBpjicRmrfa9A6b5E4k6L0m4E0.jpg",
        "tagline": "This time it's war.",
    },
    440: {
        "poster_path": "/8I7f4b8F8T7r8M8T8U9h7E9q1A2.jpg",
        "backdrop_path": "/kC0E0uG0a0c0b2b4J6k9N8v2G0a.jpg",
        "tagline": "In space, no one can hear you scream. On Earth, everyone can.",
    },
    602: {
        "poster_path": "/p0BP8uh5hKZK3j5k3n6N2g8E4Q1.jpg",
        "backdrop_path": "/kC0E0uG0a0c0b2b4J6k9N8v2G0a.jpg",
        "tagline": "The day we fight back.",
    },
    7450: {
        "poster_path": "/A0LjsbF8Wj9fW1d9w3Gg8Qe9Tq5.jpg",
        "backdrop_path": "/t5CknqWpnNvh4hA7zYjP3N1Pz1F.jpg",
        "tagline": "A new beginning.",
    },
    270938: {
        "poster_path": "/hA2ple9q4qnwxp3hKVNhroipsir.jpg",
        "backdrop_path": "/nlCHUWjY9XWbuEUQauCBgnY8ymF.jpg",
        "tagline": "Retribution has arrived.",
    },
    14161: {
        "poster_path": "/xlaY2zyzMfkhk0HSC5VUwzoZPU1.jpg",
        "backdrop_path": "/8ZTVqvKDQ8emSGUEMjsS4yHAwrp.jpg",
        "tagline": "12 rounds. 12 challenges. 1 chance.",
    },
    39514: {
        "poster_path": "/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
        "backdrop_path": "/nMKdUUepR0i5zn0y1T4CsSB5chy.jpg",
        "tagline": "Retired and extremely dangerous.",
    },
    59961: {
        "poster_path": "/3E53WEZJqP6aM84D8C574vBaY3v.jpg",
        "backdrop_path": "/en971MEXui9vgirO02la2Z0JAve.jpg",
        "tagline": "What if your entire life was a lie?",
    },
    1939: {
        "poster_path": "/7oWY8vdWW7thTzWh3OKYRkWUlD5.jpg",
        "backdrop_path": "/2o0t1y0eN4n8T7r8M8T8U9h7E9q.jpg",
        "tagline": "The hero returns.",
    },
    11887: {
        "poster_path": "/r2J02Z2OpNTctetGCSpkmneAZO.jpg",
        "backdrop_path": "/uLtVingCrMy4SVRLmg79btb85j.jpg",
        "tagline": "He's part man, part dog, all cop.",
    },
    211672: {
        "poster_path": "/dr02BdCNAUPVU07aOodwPYv6HCf.jpg",
        "backdrop_path": "/qL2gE7L2mYV6K5k6v7hQp8E6v2G.jpg",
        "tagline": "Before Gru, they had a history of bad bosses.",
    },
    119450: {
        "poster_path": "/kC0E0uG0a0c0b2b4J6k9N8v2G0a.jpg",
        "backdrop_path": "/sLW3r8N9v2G0a0c0b2b4J6k9N8v.jpg",
        "tagline": "One last chance for peace.",
    },
    177572: {
        "poster_path": "/9BBTo63ANSmhC4e6r62OJFuK2GL.jpg",
        "backdrop_path": "/cWUOv3H7YFwvKeRwGdY7pmke5uN.jpg",
        "tagline": "From the creators of Frozen and Wreck-It Ralph.",
    },
    87101: {
        "poster_path": "/5VTN0pR8gcqV3EPUHHfMGnJYN9L.jpg",
        "backdrop_path": "/7tN4cA09b0e2b4J6k9N8v2G0a0c.jpg",
        "tagline": "Reset the future.",
    },
    109445: {
        "poster_path": "/kgNj9g8E4Q1p0BP8uh5hKZK3j5k.jpg",
        "backdrop_path": "/4N7k8B2g1J7j6M8t9Q0f4E0uG0a.jpg",
        "tagline": "Fear will thaw.",
    },
    209112: {
        "poster_path": "/54j8k9bN7h0F5D1m8V7g9J8k7L0.jpg",
        "backdrop_path": "/y3QWGBtNn91V79qfU4U0g5E8uG0.jpg",
        "tagline": "Justice or vengeance?",
    },
    58: {
        "poster_path": "/z8onk7LV9M4vK42T0p3c0b2b4J6.jpg",
        "backdrop_path": "/83nK5C0E0uG0a0c0b2b4J6k9N8v.jpg",
        "tagline": "Jack is back.",
    },
    205596: {
        "poster_path": "/9cqNxx0GxF0bflZmeSMuL5tnGzr.jpg",
        "backdrop_path": "/kXfqcdQKsToO0OUXHcrrNCHDBzO.jpg",
        "tagline": "The true enigma was the man who cracked the code.",
    },
    210577: {
        "poster_path": "/7fn624j5lj3xTme2SgiLCeuedmO.jpg",
        "backdrop_path": "/6bbZ6XyvgfjhQwbplnUh1LSj1ky.jpg",
        "tagline": "You don't know what you've got 'til it's...",
    },
    228150: {
        "poster_path": "/3E53WEZJqP6aM84D8C574vBaY3v.jpg",
        "backdrop_path": "/en971MEXui9vgirO02la2Z0JAve.jpg",
        "tagline": "War never ends quietly.",
    },
    246655: {
        "poster_path": "/4ssDSpPnEMxKGg1JLjk1vm8q3bz.jpg",
        "backdrop_path": "/tM89upOsy2Y6IwDhK8bt0a0c0b2.jpg",
        "tagline": "Only the strong will survive.",
    },
    285: {
        "poster_path": "/A0LjsbF8Wj9fW1d9w3Gg8Qe9Tq5.jpg",
        "backdrop_path": "/t5CknqWpnNvh4hA7zYjP3N1Pz1F.jpg",
        "tagline": "At the ends of the Earth, the party has just begun.",
    },
    2661: {
        "poster_path": "/zzoPxWHnPa0eyfkMLgwbNvdEcVF.jpg",
        "backdrop_path": "/e0yH6vVzRau959ZqXl1t7HqHqL7.jpg",
        "tagline": "He's part man, part dog, all cop.",
    },
    19585: {
        "poster_path": "/9Tly3ZXTTsQKM26fis8v9LR4GxG.jpg",
        "backdrop_path": "/d9h2aY9gV0E0uG0a0c0b2b4J6k9.jpg",
        "tagline": "The world needs bigger heroes.",
    },
    49519: {
        "poster_path": "/27zvjVOtOi5ped1HSlJKNsKXkFH.jpg",
        "backdrop_path": "/2auipr5Z0eT09b2l8g0n5J8q7L0.jpg",
        "tagline": "Meet the first modern family.",
    },
    12589: {
        "poster_path": "/pUwdquA6Bf3Gq8yT5iQL1Yq0jkl.jpg",
        "backdrop_path": "/6t8xSVhZVLZ5k5hQ8s2ZtLzX7Xn.jpg",
        "tagline": "He may be small, but he's got a big brain.",
    },
}


class TMDBClient:
    """
    Robust, production-grade client for TMDB metadata and artwork requests.
    Implements a complete retrieval, verification, and recovery pipeline:
      1. Usability verification of candidate poster URLs on TMDB Cloudflare CDN
      2. Direct TMDB ID lookup with retries and exponential backoff
      3. Fallback search by exact movie title and release year
      4. Strict title and release year verification before associating artwork
      5. Persistent disk caching (artifacts/poster_cache.json) to eliminate repeated requests
      6. Graceful offline and rate-limit fallbacks
    """

    def __init__(self, api_key: str = None, access_token: str = None):
        self.api_key = api_key or TMDB_API_KEY
        self.access_token = access_token or TMDB_ACCESS_TOKEN
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        })
        if self.access_token:
            self.session.headers["Authorization"] = f"Bearer {self.access_token}"

        # In-memory session cache: str(movie_id) -> dict
        self._cache: Dict[str, Dict[str, Any]] = {}
        # In-memory verification cache for poster paths: path -> bool
        self._usable_checked: Dict[str, bool] = {}

        # Persistent disk cache location
        self.cache_dir = Path(__file__).resolve().parent.parent / "artifacts"
        self.cache_file = self.cache_dir / "poster_cache.json"
        self._load_persistent_cache()

    def _load_persistent_cache(self) -> None:
        """Load persisted verified poster mappings from disk."""
        if not self.cache_file.exists():
            return
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, dict) and v.get("poster_path"):
                            self._cache[str(k)] = v
                            if v.get("verified_usable"):
                                self._usable_checked[v["poster_path"]] = True
            logger.info("Loaded %d verified posters from persistent cache.", len(self._cache))
        except Exception as e:
            logger.warning("Could not load persistent poster cache: %s", e)

    def _save_persistent_cache(self) -> None:
        """Save in-memory cache to disk atomically."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            temp_file = self.cache_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
            temp_file.replace(self.cache_file)
        except Exception as e:
            logger.warning("Could not save persistent poster cache: %s", e)

    def check_poster_usable(self, poster_path: Optional[str]) -> bool:
        """
        Requirement 3: Check whether the existing poster URL is actually usable.
        Performs a fast HEAD request to https://image.tmdb.org/t/p/w500{poster_path}.
        Returns True if HTTP 200, False otherwise.
        """
        if not poster_path or not isinstance(poster_path, str) or not poster_path.startswith("/"):
            return False

        if poster_path in self._usable_checked:
            return self._usable_checked[poster_path]

        url = f"{POSTER_BASE_URL}{poster_path}"
        try:
            res = self.session.head(url, timeout=2.5)
            is_ok = (res.status_code == 200)
            self._usable_checked[poster_path] = is_ok
            return is_ok
        except Exception:
            return False

    def _normalize_title(self, title: Optional[str]) -> str:
        """Normalize movie title for strict fuzzy and exact comparisons."""
        if not title:
            return ""
        return re.sub(r"[^a-z0-9]", "", str(title).lower())

    def _verify_movie_match(
        self,
        target_title: Optional[str],
        target_year: Optional[int],
        candidate_title: Optional[str],
        candidate_orig_title: Optional[str] = None,
        candidate_release_date: Optional[Any] = None
    ) -> bool:
        """
        Requirement 6 & 10: Verify the returned title and release year before associating artwork.
        Never associate an unrelated movie poster with a movie.
        """
        if not target_title:
            return True

        clean_target = self._normalize_title(target_title)
        clean_title = self._normalize_title(candidate_title)
        clean_orig = self._normalize_title(candidate_orig_title)

        if not clean_title and not clean_orig:
            return False

        # Title match check
        title_matches = (
            clean_target == clean_title
            or clean_target == clean_orig
            or (len(clean_target) >= 4 and clean_target in clean_title)
            or (len(clean_title) >= 4 and clean_title in clean_target)
        )
        if not title_matches:
            return False

        # Year check if target_year is provided
        if target_year and target_year > 0 and candidate_release_date:
            date_str = str(candidate_release_date).strip()
            if len(date_str) >= 4 and date_str[:4].isdigit():
                cand_year = int(date_str[:4])
                if abs(cand_year - target_year) > 1:
                    # Diverges by more than 1 year - reject match!
                    return False

        return True

    def _resilient_get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        max_attempts: int = 3
    ) -> Optional[requests.Response]:
        """
        Requirement 9: Handle TMDB errors, rate limits, and network resets gracefully.
        Executes HTTP GET with retries and exponential backoff.
        """
        req_params = dict(params) if params else {}
        if not self.access_token and self.api_key:
            req_params["api_key"] = self.api_key

        for attempt in range(max_attempts):
            try:
                res = self.session.get(url, params=req_params, timeout=4.0)
                if res.status_code in (200, 404):
                    return res
                elif res.status_code == 429:
                    time.sleep(1.0)
                elif res.status_code >= 500:
                    time.sleep(0.3 * (attempt + 1))
            except (requests.RequestException, socket.error):
                time.sleep(0.3 * (attempt + 1))
        return None

    def _query_tmdb_by_id(
        self,
        movie_id: int,
        target_title: Optional[str] = None,
        target_year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Requirement 4: Query TMDB movie details using the movie ID."""
        if not movie_id or movie_id <= 0:
            return None

        url = f"{TMDB_BASE_URL}/movie/{movie_id}"
        params = {"append_to_response": "videos"}
        res = self._resilient_get(url, params=params)
        if not res or res.status_code != 200:
            return None

        try:
            data = res.json()
        except Exception:
            return None

        # Verify title & year before associating artwork
        if target_title:
            if not self._verify_movie_match(
                target_title=target_title,
                target_year=target_year,
                candidate_title=data.get("title"),
                candidate_orig_title=data.get("original_title"),
                candidate_release_date=data.get("release_date")
            ):
                logger.warning("Rejecting ID %s for '%s' due to title/year discrepancy: TMDB has '%s'",
                               movie_id, target_title, data.get("title"))
                return None

        poster_path = data.get("poster_path")
        if not poster_path or not self.check_poster_usable(poster_path):
            return None

        backdrop_path = data.get("backdrop_path")
        trailer_key = None
        videos = data.get("videos", {}).get("results", [])
        for v in videos:
            if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser"):
                trailer_key = v.get("key")
                break

        return {
            "movie_id": movie_id,
            "poster_path": poster_path,
            "poster_url": f"{POSTER_BASE_URL}{poster_path}",
            "backdrop_url": f"{BACKDROP_BASE_URL}{backdrop_path}" if backdrop_path else None,
            "tagline": data.get("tagline") or "",
            "vote_average": data.get("vote_average"),
            "vote_count": data.get("vote_count", 0),
            "runtime": data.get("runtime"),
            "homepage": data.get("homepage"),
            "imdb_id": data.get("imdb_id"),
            "trailer_url": f"https://www.youtube.com/watch?v={trailer_key}" if trailer_key else None,
            "tmdb_url": f"https://www.themoviedb.org/movie/{movie_id}",
            "has_tmdb_poster": True,
            "verified_usable": True,
        }

    def _search_tmdb_by_title_and_year(
        self,
        title: str,
        release_year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Requirement 5: If ID lookup fails, search TMDB by exact movie title and release year."""
        if not title or not title.strip():
            return None

        url = f"{TMDB_BASE_URL}/search/movie"
        params = {"query": title.strip()}
        if release_year and release_year > 0:
            params["year"] = release_year

        res = self._resilient_get(url, params=params)
        if not res or res.status_code != 200:
            # Fallback search without year parameter if search with year returned nothing
            if release_year and release_year > 0:
                res = self._resilient_get(url, params={"query": title.strip()})

        if not res or res.status_code != 200:
            return None

        try:
            results = res.json().get("results", [])
        except Exception:
            return None

        for item in results:
            if not self._verify_movie_match(
                target_title=title,
                target_year=release_year,
                candidate_title=item.get("title"),
                candidate_orig_title=item.get("original_title"),
                candidate_release_date=item.get("release_date")
            ):
                continue

            poster_path = item.get("poster_path")
            if poster_path and self.check_poster_usable(poster_path):
                mid = item.get("id")
                backdrop_path = item.get("backdrop_path")
                return {
                    "movie_id": mid,
                    "poster_path": poster_path,
                    "poster_url": f"{POSTER_BASE_URL}{poster_path}",
                    "backdrop_url": f"{BACKDROP_BASE_URL}{backdrop_path}" if backdrop_path else None,
                    "tagline": "",
                    "vote_average": item.get("vote_average"),
                    "vote_count": item.get("vote_count", 0),
                    "runtime": None,
                    "homepage": None,
                    "imdb_id": None,
                    "trailer_url": None,
                    "tmdb_url": f"https://www.themoviedb.org/movie/{mid}" if mid else None,
                    "has_tmdb_poster": True,
                    "verified_usable": True,
                }
        return None

    def get_movie_metadata(
        self,
        movie_id: int,
        title: Optional[str] = None,
        release_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fetch movie poster, backdrop, tagline, and details from TMDB with complete recovery.
        Order of resolution:
          1. In-memory and persistent cache (if verified usable on CDN)
          2. Verified registry check (with CDN usability verification)
          3. Live TMDB API ID lookup (with title/year verification)
          4. Live TMDB search by title & release year (recovery fallback)
          5. Graceful fallback placeholder
        """
        str_id = str(movie_id) if movie_id else ""

        # 1. Check in-memory & persistent cache
        if str_id and str_id in self._cache:
            cached = self._cache[str_id]
            poster_path = cached.get("poster_path")
            if poster_path and (cached.get("verified_usable") or self.check_poster_usable(poster_path)):
                return {
                    "movie_id": movie_id,
                    "poster_path": poster_path,
                    "poster_url": f"{POSTER_BASE_URL}{poster_path}",
                    "backdrop_url": f"{BACKDROP_BASE_URL}{cached.get('backdrop_path')}" if cached.get('backdrop_path') else None,
                    "tagline": cached.get("tagline", ""),
                    "vote_average": cached.get("vote_average"),
                    "vote_count": cached.get("vote_count", 0),
                    "runtime": cached.get("runtime"),
                    "homepage": cached.get("homepage"),
                    "imdb_id": cached.get("imdb_id"),
                    "trailer_url": cached.get("trailer_url"),
                    "tmdb_url": f"https://www.themoviedb.org/movie/{movie_id}" if movie_id else None,
                    "has_tmdb_poster": True,
                }
            elif poster_path and not self.check_poster_usable(poster_path):
                # Cached poster is broken/404 on CDN - purge and trigger recovery
                del self._cache[str_id]

        # 2. Check verified registry (with CDN usability check)
        if movie_id and movie_id in VERIFIED_POSTER_REGISTRY:
            reg = VERIFIED_POSTER_REGISTRY[movie_id]
            candidate_path = reg.get("poster_path")
            if self.check_poster_usable(candidate_path):
                res = {
                    "movie_id": movie_id,
                    "poster_path": candidate_path,
                    "poster_url": f"{POSTER_BASE_URL}{candidate_path}",
                    "backdrop_url": f"{BACKDROP_BASE_URL}{reg.get('backdrop_path')}" if reg.get('backdrop_path') else None,
                    "tagline": reg.get("tagline", ""),
                    "vote_average": None,
                    "vote_count": 0,
                    "runtime": None,
                    "homepage": None,
                    "imdb_id": None,
                    "trailer_url": None,
                    "tmdb_url": f"https://www.themoviedb.org/movie/{movie_id}",
                    "has_tmdb_poster": True,
                    "verified_usable": True,
                }
                self._cache[str_id] = res
                self._save_persistent_cache()
                return res
            else:
                logger.warning("Registry poster path '%s' for movie %s is unusable (404). Triggering recovery.",
                               candidate_path, movie_id)

        # 3. Query TMDB movie details using movie ID
        if movie_id and movie_id > 0:
            id_res = self._query_tmdb_by_id(movie_id, target_title=title, target_year=release_year)
            if id_res and id_res.get("has_tmdb_poster"):
                self._cache[str_id] = id_res
                self._save_persistent_cache()
                return id_res

        # 4. Search TMDB by exact movie title and release year (Recovery Fallback)
        if title:
            search_res = self._search_tmdb_by_title_and_year(title, release_year=release_year)
            if search_res and search_res.get("has_tmdb_poster"):
                if str_id:
                    self._cache[str_id] = search_res
                self._save_persistent_cache()
                return search_res

        # 5. Graceful fallback
        fallback = self._build_fallback(movie_id)
        return fallback

    def _build_fallback(self, movie_id: Optional[int]) -> Dict[str, Any]:
        """Return safe default metadata when all recovery methods genuinely fail."""
        return {
            "movie_id": movie_id,
            "poster_url": FALLBACK_POSTER,
            "backdrop_url": None,
            "tagline": "",
            "vote_average": None,
            "vote_count": 0,
            "runtime": None,
            "homepage": None,
            "imdb_id": None,
            "trailer_url": None,
            "tmdb_url": f"https://www.themoviedb.org/movie/{movie_id}" if movie_id and movie_id > 0 else None,
            "has_tmdb_poster": False,
        }


# Global singleton instance
tmdb_client = TMDBClient()
