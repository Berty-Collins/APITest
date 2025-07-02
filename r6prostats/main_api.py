from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from .fetcher import DataFetcher
from .wikitext_parser import WikitextParser
from .analysis_engine import AnalysisEngine
from .mock_data import ALL_MOCK_MATCHES
from .parser_models import MatchData as ParserMatchData # Avoid conflict with FastAPI's MatchData
from .analysis_models import TeamMapPreferences, TeamOperatorPreferences, MapPrediction, OperatorBanSuggestion

app = FastAPI(
    title="R6ProStats API",
    description="API for Rainbow Six Siege pro match analytics and suggestions.",
    version="0.1.0"
)

# CORS (Cross-Origin Resource Sharing) middleware
# Allows frontend (even if served from a different port during development) to access the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for simplicity in this context
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods
    allow_headers=["*"], # Allow all headers
)

# Global instances (consider proper dependency injection for larger apps)
# For simplicity, we initialize them here. In a prod app, you might manage lifespan differently.
data_fetcher = DataFetcher()
wikitext_parser = WikitextParser()
# Analysis engine will be initialized based on data source per request

def get_engine(use_mock_data: bool, tournament_pages: Optional[List[str]] = None, team_filters: Optional[List[str]] = None) -> AnalysisEngine:
    """Helper to initialize AnalysisEngine with mock or live data."""
    match_data_list: List[ParserMatchData] = []
    if use_mock_data:
        print("API: Using mock data")
        match_data_list = ALL_MOCK_MATCHES
        if team_filters:
            match_data_list = [
                m for m in match_data_list if m.team1.name in team_filters or m.team2.name in team_filters
            ]
    else:
        if not tournament_pages:
            raise HTTPException(status_code=400, detail="tournament_pages are required if not using mock_data.")
        print(f"API: Fetching live data from pages: {tournament_pages} for teams: {team_filters}")
        # This is a simplified fetch_and_parse logic for the API, similar to CLI's
        # A more robust solution would be needed for production.
        processed_pages = set()
        for page_title in tournament_pages:
            if page_title in processed_pages:
                continue
            wikitext = data_fetcher.get_page_content(page_title)
            if wikitext:
                match = wikitext_parser.parse_match_page(page_title, wikitext)
                if match:
                    if team_filters:
                        if match.team1.name in team_filters or match.team2.name in team_filters:
                            match_data_list.append(match)
                    else:
                        match_data_list.append(match)
                processed_pages.add(page_title)
            else:
                 print(f"API: No wikitext found for {page_title}")


    if not match_data_list:
        # If live data fetch yields nothing, and mock data wasn't requested, this is an issue.
        # Or if mock data was filtered to nothing.
        error_msg = "No match data available to initialize AnalysisEngine."
        if not use_mock_data and not match_data_list :
             error_msg = f"Could not fetch or parse any relevant match data from provided pages: {tournament_pages} for teams: {team_filters}."
        elif use_mock_data and not match_data_list and team_filters:
            error_msg = f"No mock data found matching team filters: {team_filters}."

        print(f"API Error: {error_msg}")
        raise HTTPException(status_code=404, detail=error_msg)

    print(f"API: Initializing AnalysisEngine with {len(match_data_list)} matches.")
    return AnalysisEngine(all_matches=match_data_list)

@app.get("/team-stats/{team_name}", response_model=dict)
async def get_team_stats_api(
    team_name: str,
    use_mock_data: bool = Query(True, description="Use mock data instead of live fetching"),
    tournament_pages: Optional[List[str]] = Query(None, description="List of Liquipedia page titles for live data"),
    team_filters: Optional[List[str]] = Query(None, description="Filter data for these specific teams (affects data pool for analysis)")
):
    """
    Get statistics for a specific team, including map preferences and operator preferences.
    If using live data, `tournament_pages` should specify where to look for matches.
    `team_filters` can be used to narrow down the set of matches considered for analysis, even with mock data.
    """
    try:
        engine = get_engine(use_mock_data, tournament_pages, team_filters if team_filters else [team_name])
    except HTTPException as e:
        raise e # Re-raise HTTPException from get_engine
    except Exception as e:
        print(f"API Error in get_engine: {e}")
        raise HTTPException(status_code=500, detail=f"Error initializing analysis engine: {str(e)}")


    map_prefs = engine.get_team_map_preferences(team_name)
    op_prefs = engine.get_team_operator_preferences(team_name)

    if not map_prefs and not op_prefs:
        raise HTTPException(status_code=404, detail=f"No data found for team: {team_name}")

    return {
        "team_name": team_name,
        "map_preferences": map_prefs.map_stats if map_prefs else {},
        "operator_preferences": op_prefs.operator_stats if op_prefs else {} # This returns the raw nested dict
    }

@app.get("/suggest/maps", response_model=List[MapPrediction])
async def suggest_maps_api(
    team_a: str = Query(..., description="Your team's name"),
    team_b: str = Query(..., description="Opponent team's name"),
    num_suggestions: int = Query(3, ge=1, le=10, description="Number of map suggestions"),
    use_mock_data: bool = Query(True, description="Use mock data"),
    tournament_pages: Optional[List[str]] = Query(None, description="List of Liquipedia page titles for live data"),
    team_filters: Optional[List[str]] = Query(None, description="Filter data for these teams (e.g., include only matches of team_a and team_b)")
):
    """
    Suggest maps for Team A to play against Team B.
    """
    # Ensure both teams are part of the filter if live data is used broadly
    current_filters = list(team_filters) if team_filters else []
    if team_a not in current_filters: current_filters.append(team_a)
    if team_b not in current_filters: current_filters.append(team_b)

    try:
        engine = get_engine(use_mock_data, tournament_pages, current_filters)
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"API Error in get_engine: {e}")
        raise HTTPException(status_code=500, detail=f"Error initializing analysis engine: {str(e)}")

    suggestions = engine.suggest_maps_to_play(team_a, team_b, num_suggestions)
    if not suggestions:
        # Don't raise 404, an empty list is a valid response if no suggestions can be made
        print(f"API: No map suggestions generated for {team_a} vs {team_b}")
    return suggestions

@app.get("/suggest/operator-bans", response_model=List[OperatorBanSuggestion])
async def suggest_operator_bans_api(
    team_a: str = Query(..., description="Your team's name (who is banning)"),
    team_b: str = Query(..., description="Opponent team's name (whose operators to ban)"),
    map_name: str = Query(..., description="The map for which to suggest bans"),
    num_suggestions: int = Query(2, ge=1, le=5, description="Number of ban suggestions"),
    use_mock_data: bool = Query(True, description="Use mock data"),
    tournament_pages: Optional[List[str]] = Query(None, description="List of Liquipedia page titles for live data"),
    team_filters: Optional[List[str]] = Query(None, description="Filter data for these teams")
):
    """
    Suggest operators for Team A to ban against Team B on a specific map.
    """
    current_filters = list(team_filters) if team_filters else []
    if team_a not in current_filters: current_filters.append(team_a)
    if team_b not in current_filters: current_filters.append(team_b)

    try:
        engine = get_engine(use_mock_data, tournament_pages, current_filters)
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"API Error in get_engine: {e}")
        raise HTTPException(status_code=500, detail=f"Error initializing analysis engine: {str(e)}")

    suggestions = engine.suggest_operator_bans(team_a, team_b, map_name, num_suggestions)
    if not suggestions:
        print(f"API: No operator ban suggestions generated for {team_a} vs {team_b} on {map_name}")
    return suggestions

# Basic root endpoint
@app.get("/")
async def read_root():
    return {"message": "Welcome to R6ProStats API. Visit /docs for API documentation."}

# To run this FastAPI app (example, not run by the agent):
# uvicorn r6prostats.main_api:app --reload
# The agent will create this file, then proceed to create HTML/JS.
# Note: Print statements are for agent's visibility in this environment, use proper logging in prod.

print("FastAPI main_api.py created.")
print("Next steps would be to create static HTML/JS files for the front-end.")
