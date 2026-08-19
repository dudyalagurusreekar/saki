"""
Sprint 5 Reliability Test Suite: Entity Resolution, Query Understanding & Semantic Relevance Gate
Verifies:
1. Multi-signal relevance evaluation (Topic/Entity/Location/Intent/Coverage).
2. Topic and location relationship preservation.
3. Separation between RELATED and SUFFICIENT (e.g. generic software intro vs version release).
4. Local query discrimination (food vs history vs weather vs tourism for the same entity).
5. Ambiguous entity handling.
"""

import pytest
from backend.services.action_engine import (
    decide_action,
    parse_query_understanding,
    ACTION_LOCAL_REASONING,
    ACTION_WEB_SEARCH,
    FRESHNESS_STABLE,
    FRESHNESS_CURRENT,
    FRESHNESS_LIVE
)
from backend.services.evidence_engine import (
    RelevanceGate,
    EvidenceIntelligenceEngine,
    EVIDENCE_STATUS_SUFFICIENT,
    EVIDENCE_STATUS_INSUFFICIENT
)


class TestSprint5EntityAndSemanticRelevance:

    def test_01_food_in_vijayawada_relevance_discrimination(self):
        """
        TEST 1: Query 'special food in Vijayawada'
        Verify: food-relevant results accepted; history and weather results rejected.
        """
        query = "special food in Vijayawada"
        qu = parse_query_understanding(query)

        assert qu.primary_entity == "Vijayawada"
        assert qu.location == "Vijayawada"
        assert qu.topic == "food"
        assert qu.intent == "recommendation"

        candidates = [
            {
                "title": "Famous Foods and Traditional Dishes of Vijayawada",
                "snippet": "Popular dishes visitors must try in Vijayawada include Andhra spicy meals, punugulu, gongura pachadi, and local sweets.",
                "url": "https://food.andhratourism.gov.in/vijayawada-specialties",
                "domain": "food.andhratourism.gov.in"
            },
            {
                "title": "History of Vijayawada - Ancient Dynasties and Rulers",
                "snippet": "Vijayawada has an ancient historical heritage ruled by the Gajapatis, Chalukyas, and British empire across centuries.",
                "url": "https://history.example.com/vijayawada-past",
                "domain": "history.example.com"
            },
            {
                "title": "Vijayawada Live Weather and Temperature Forecast",
                "snippet": "Current weather in Vijayawada is 34 degrees Celsius with sunny skies and 65% humidity.",
                "url": "https://weather.example.com/vijayawada",
                "domain": "weather.example.com"
            }
        ]

        evaluations = RelevanceGate.evaluate_relevance_detailed(query, candidates)

        assert len(evaluations) == 3
        # Candidate 0: Food -> RELEVANT
        assert evaluations[0].relevance_state == "RELEVANT"
        assert evaluations[0].topic_match is True
        assert evaluations[0].location_match is True
        assert evaluations[0].relevance_score >= 0.70

        # Candidate 1: History -> IRRELEVANT
        assert evaluations[1].relevance_state == "IRRELEVANT"
        assert evaluations[1].topic_match is False

        # Candidate 2: Weather -> IRRELEVANT
        assert evaluations[2].relevance_state == "IRRELEVANT"
        assert evaluations[2].topic_match is False

        # Evidence package should only synthesize claims from relevant items
        package = EvidenceIntelligenceEngine.process_and_synthesize(query, candidates)
        assert package.evidence_status == EVIDENCE_STATUS_SUFFICIENT
        assert len(package.claims) == 1
        assert "punugulu" in package.claims[0].text

    def test_02_fastapi_version_related_vs_sufficient(self):
        """
        TEST 2: Query 'latest FastAPI version'
        Verify: release/version results accepted; generic introductory overview rejected/down-ranked.
        """
        query = "latest FastAPI version"
        qu = parse_query_understanding(query)

        assert qu.primary_entity == "FastAPI"
        assert qu.topic == "software_version"
        assert qu.intent == "version_query"

        candidates = [
            {
                "title": "Release FastAPI 0.115.0 - tiangolo/fastapi GitHub",
                "snippet": "FastAPI version 0.115.0 official release notes, latest fixes and Pydantic v2 support published on PyPI.",
                "url": "https://github.com/tiangolo/fastapi/releases/tag/0.115.0",
                "domain": "github.com"
            },
            {
                "title": "FastAPI Tutorial - First Steps and Overview",
                "snippet": "FastAPI is a modern, high-performance web framework for building APIs with Python 3.8+ based on standard Python type hints.",
                "url": "https://fastapi.tiangolo.com/tutorial/first-steps/",
                "domain": "fastapi.tiangolo.com"
            }
        ]

        evaluations = RelevanceGate.evaluate_relevance_detailed(query, candidates)

        # Candidate 0 (Release notes) -> RELEVANT & SUFFICIENT
        assert evaluations[0].relevance_state == "RELEVANT"
        assert evaluations[0].coverage_score >= 0.90
        assert evaluations[0].relevance_score >= 0.80

        # Candidate 1 (Generic overview) -> IRRELEVANT / INSUFFICIENT for version query
        assert evaluations[1].relevance_state == "IRRELEVANT"
        assert evaluations[1].coverage_score < 0.30

    def test_03_what_is_fastapi_static_knowledge_path(self):
        """
        TEST 3: Query 'what is FastAPI?'
        Verify: routes to static local knowledge (web_required = False).
        """
        decision = decide_action("what is FastAPI?")
        assert decision.requires_world_access is False
        assert decision.temporal_requirement == FRESHNESS_STABLE
        assert decision.action in [ACTION_LOCAL_REASONING, "CODING"]
        assert decision.query_understanding.topic == "software_framework"
        assert decision.query_understanding.intent == "general_explanation"

    def test_04_places_to_visit_in_vijayawada(self):
        """
        TEST 4: Query 'best places to visit in Vijayawada'
        Verify: places/attractions results accepted; weather and history rejected.
        """
        query = "best places to visit in Vijayawada"
        qu = parse_query_understanding(query)

        assert qu.primary_entity == "Vijayawada"
        assert qu.topic == "tourism"
        assert qu.intent == "recommendation"

        candidates = [
            {
                "title": "Top Tourist Places to Visit in Vijayawada",
                "snippet": "Must-visit attractions in Vijayawada include Kanaka Durga Temple, Prakasam Barrage, Undavalli Caves, and Bhavani Island.",
                "url": "https://tourism.andhra.gov.in/vijayawada",
                "domain": "tourism.andhra.gov.in"
            },
            {
                "title": "Vijayawada Weather News",
                "snippet": "Heavy rainfall predicted in Vijayawada with temperatures dropping to 24C.",
                "url": "https://weather.com/vijayawada",
                "domain": "weather.com"
            }
        ]

        evaluations = RelevanceGate.evaluate_relevance_detailed(query, candidates)
        assert evaluations[0].relevance_state == "RELEVANT"
        assert evaluations[0].topic_match is True
        assert evaluations[1].relevance_state == "IRRELEVANT"
        assert evaluations[1].topic_match is False

    def test_05_weather_in_vijayawada(self):
        """
        TEST 5: Query 'weather in Vijayawada'
        Verify: weather results accepted; food and history results rejected.
        """
        query = "weather in Vijayawada"
        qu = parse_query_understanding(query)

        assert qu.topic == "weather"
        assert qu.intent == "live_update"
        assert qu.temporal_requirement == FRESHNESS_LIVE

        candidates = [
            {
                "title": "Vijayawada Current Weather and 7-Day Forecast",
                "snippet": "Vijayawada weather is currently 32°C with sunny skies, 60% humidity, and light winds.",
                "url": "https://accuweather.com/vijayawada",
                "domain": "accuweather.com"
            },
            {
                "title": "Top Restaurants and Food in Vijayawada",
                "snippet": "Explore the best spicy biryani and sweets in Vijayawada restaurants.",
                "url": "https://foodie.com/vijayawada",
                "domain": "foodie.com"
            }
        ]

        evaluations = RelevanceGate.evaluate_relevance_detailed(query, candidates)
        assert evaluations[0].relevance_state == "RELEVANT"
        assert evaluations[0].coverage_score >= 0.90
        assert evaluations[1].relevance_state == "IRRELEVANT"

    def test_06_history_of_vijayawada(self):
        """
        TEST 6: Query 'history of Vijayawada'
        Verify: history results accepted; food/restaurant results rejected.
        """
        query = "history of Vijayawada"
        qu = parse_query_understanding(query)

        assert qu.topic == "history"
        assert qu.intent == "factual_lookup"

        candidates = [
            {
                "title": "Historical Background and Heritage of Vijayawada",
                "snippet": "Vijayawada's ancient history dates back centuries, with inscriptions from the Chalukyas and rulers who built heritage monuments.",
                "url": "https://archaeology.gov.in/vijayawada",
                "domain": "archaeology.gov.in"
            },
            {
                "title": "Vijayawada Best Street Food Joints",
                "snippet": "Try tasty punugulu, dosas, and filter coffee across busy food stalls in Vijayawada.",
                "url": "https://streetfood.com/vijayawada",
                "domain": "streetfood.com"
            }
        ]

        evaluations = RelevanceGate.evaluate_relevance_detailed(query, candidates)
        assert evaluations[0].relevance_state == "RELEVANT"
        assert evaluations[0].topic_match is True
        assert evaluations[1].relevance_state == "IRRELEVANT"
        assert evaluations[1].topic_match is False

    def test_07_movies_in_2026(self):
        """
        TEST 7: Query 'good movies in 2026'
        Verify: 2026 movie recommendations accepted; generic 1970s cinema history rejected.
        """
        query = "good movies in 2026"
        qu = parse_query_understanding(query)

        assert qu.topic == "movies"
        assert qu.intent == "recommendation"
        assert qu.temporal_requirement == FRESHNESS_CURRENT

        candidates = [
            {
                "title": "Best Movies in 2026 - Top Rated Film Releases",
                "snippet": "Highly anticipated 2026 movie releases, box office reviews, and recommendations for top films hitting theatres in 2026.",
                "url": "https://imdb.com/list/2026-movies",
                "domain": "imdb.com"
            },
            {
                "title": "A Retrospective on 1970s Classical Cinema",
                "snippet": "An essay analyzing cinema movements and director aesthetics from 1970 to 1979 in global Hollywood.",
                "url": "https://cinemaessay.com/1970s",
                "domain": "cinemaessay.com"
            }
        ]

        evaluations = RelevanceGate.evaluate_relevance_detailed(query, candidates)
        assert evaluations[0].relevance_state == "RELEVANT"
        assert evaluations[0].coverage_score >= 0.90
        assert evaluations[1].relevance_state == "IRRELEVANT"

    def test_08_ambiguous_entity_handling(self):
        """
        TEST 8: Query 'tell me about Saki' or 'Saki'
        Verify: system flags ambiguous entity without false confident assumptions.
        """
        qu_saki = parse_query_understanding("tell me about Saki")
        assert qu_saki.primary_entity == "Saki"
        assert qu_saki.is_ambiguous is True
        assert qu_saki.entity_type == "ambiguous"

        qu_gemini = parse_query_understanding("tell me about Gemini")
        assert qu_gemini.primary_entity == "Gemini"
        assert qu_gemini.is_ambiguous is True
