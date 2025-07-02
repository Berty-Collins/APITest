import argparse
import logging
from typing import List
from r6prostats.fetcher import DataFetcher
from r6prostats.wikitext_parser import WikitextParser
from r6prostats.analysis_engine import AnalysisEngine
from r6prostats.mock_data import ALL_MOCK_MATCHES # For --use-mock-data
from r6prostats.parser_models import MatchData # For type hinting

# Configure basic logging for the CLI
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_and_parse_data(fetcher: DataFetcher, parser: WikitextParser, team_names: List[str], tournament_pages: List[str]) -> List[MatchData]:
    """
    Fetches and parses data for specified teams and tournaments.
    This is a simplified fetching strategy. A more robust version would discover match pages.
    For now, we assume tournament_pages contain links or are match pages themselves.
    """
    all_match_data = []
    processed_pages = set()

    # Strategy 1: Fetch specific tournament overview pages and parse matches from them
    # This is highly dependent on Liquipedia page structure and template usage.
    # For this initial CLI, we'll assume direct match pages or simple structures.

    # Strategy 2: Get match history pages for teams (if such pages exist and are structured)
    # Example: "Category:TeamName matches" or similar.
    # For now, we'll rely on user providing direct match page titles or tournament pages
    # that the parser might handle if they embed MatchMaps templates directly.

    page_titles_to_fetch = list(tournament_pages) # Start with explicitly provided tournament/match pages

    # Attempt to find match pages via categories if team names are provided
    # This is a more advanced fetching strategy that might be too complex for initial CLI.
    # For now, we'll keep it simple: use provided tournament_pages as source of matches.

    if not page_titles_to_fetch:
        logger.warning("No tournament/match pages specified. Fetching will be limited.")
        # If we had a way to get ALL relevant match pages, this is where it would go.
        # For now, if no pages are given, we can't fetch much beyond what mock data offers.


    for page_title in page_titles_to_fetch:
        if page_title in processed_pages:
            continue
        logger.info(f"Fetching content for page: {page_title}")
        wikitext = fetcher.get_page_content(page_title)
        if wikitext:
            # The current parser.parse_match_page expects a single match per page.
            # If a tournament page contains multiple {{MatchMaps}} templates,
            # the parser would need to be adapted, or we'd need to pre-process
            # the wikitext to split it into individual match template sections.
            # For simplicity, we assume `parse_match_page` can handle it or it's a direct match page.
            match_data = parser.parse_match_page(page_title, wikitext)
            if match_data:
                # Filter by team_names if provided
                if team_names:
                    if match_data.team1.name in team_names or match_data.team2.name in team_names:
                        all_match_data.append(match_data)
                        logger.info(f"Added match: {match_data.team1.name} vs {match_data.team2.name}")
                else: # If no specific teams, add all parsed matches
                    all_match_data.append(match_data)
                    logger.info(f"Added match: {match_data.team1.name} vs {match_data.team2.name}")
            processed_pages.add(page_title)
        else:
            logger.warning(f"No wikitext content found for {page_title}")

    if not all_match_data and not tournament_pages: # If no pages specified and thus no data fetched
        logger.info("No pages specified for fetching. No live data retrieved.")

    # This is a very basic fetching strategy. A real application would need
    # a more robust way to discover all relevant match pages, perhaps by:
    # 1. Starting from main tournament pages (e.g., "Six Invitational 2023")
    # 2. Parsing these pages to find links to group stage pages, playoff brackets, etc.
    # 3. Recursively finding all {{MatchMaps}} template usages or links to match report pages.
    # 4. Using category members (e.g., "Category:Six Invitational 2023 Matches").

    return all_match_data


def display_team_stats(engine: AnalysisEngine, team_name: str):
    logger.info(f"Fetching statistics for team: {team_name}...")
    team_map_prefs = engine.get_team_map_preferences(team_name)
    team_op_prefs = engine.get_team_operator_preferences(team_name)

    if not team_map_prefs and not team_op_prefs:
        print(f"No data found for team: {team_name}")
        return

    print(f"\n--- Statistics for {team_name} ---")

    if team_map_prefs:
        print("\n  Map Preferences (Sorted by Win Rate):")
        if team_map_prefs.map_stats:
            sorted_maps = sorted(team_map_prefs.map_stats.items(), key=lambda item: item[1].win_rate, reverse=True)
            for map_name, stats in sorted_maps:
                print(f"    {map_name}: Played {stats.times_played}, WR: {stats.win_rate:.1f}% ({stats.wins}W-{stats.losses}L), Round WR: {stats.round_win_rate:.1f}%")
        else:
            print("    No map statistics available.")

    if team_op_prefs:
        print("\n  Overall Operator Preferences (Top 5 Picked):")
        if None in team_op_prefs.operator_stats and team_op_prefs.operator_stats[None]:
            # Sort by times picked for overall summary
            sorted_ops_overall = sorted(team_op_prefs.operator_stats[None].items(), key=lambda item: item[1].times_picked, reverse=True)
            for i, (op_name, stats) in enumerate(sorted_ops_overall):
                if i >= 5 and stats.times_picked < 1 : break # Show at least top 5 or any picked ops
                if stats.times_picked > 0 :
                    print(f"    {op_name}: Picked {stats.times_picked} times (WR: {stats.win_rate_when_picked:.1f}%), Banned by team: {stats.times_banned_by_team}, Banned by opp: {stats.times_banned_by_opponent}")
        else:
            print("    No overall operator statistics available.")

        # Example: Show top picked operator for each map they played
        print("\n  Top Operator Pick per Map (if available):")
        map_specific_ops_found = False
        for map_name, op_stats_dict in team_op_prefs.operator_stats.items():
            if map_name is None: continue # Skip overall stats here
            if op_stats_dict:
                top_op_on_map = sorted(op_stats_dict.items(), key=lambda item: item[1].times_picked, reverse=True)
                if top_op_on_map:
                    op_name, stats = top_op_on_map[0]
                    if stats.times_picked > 0:
                        print(f"    {map_name} -> Top Pick: {op_name} (Picked {stats.times_picked}, WR: {stats.win_rate_when_picked:.1f}%)")
                        map_specific_ops_found = True
        if not map_specific_ops_found:
             print("    No map-specific operator pick data available.")


def display_map_suggestions(engine: AnalysisEngine, team_name: str, opponent_name: str, num_suggestions: int):
    logger.info(f"Generating map suggestions for {team_name} vs {opponent_name}...")
    suggestions = engine.suggest_maps_to_play(team_name, opponent_name, num_suggestions)

    if not suggestions:
        print(f"No map suggestions available for {team_name} vs {opponent_name}.")
        return

    print(f"\n--- Map Suggestions for {team_name} vs {opponent_name} ---")
    for i, suggestion in enumerate(suggestions):
        print(f"  Suggestion {i+1}: Play {suggestion.map_name} (Confidence: {suggestion.confidence_score:.2f})")
        print(f"    Reasoning: {suggestion.reasoning}")
        # print("    Supporting Stats:")
        # for stat, value in suggestion.supporting_stats.items():
        #     print(f"      {stat}: {value}")

def display_ban_suggestions(engine: AnalysisEngine, team_name: str, opponent_name: str, map_name: str, num_suggestions: int):
    logger.info(f"Generating operator ban suggestions for {team_name} vs {opponent_name} on {map_name}...")
    suggestions = engine.suggest_operator_bans(team_name, opponent_name, map_name, num_suggestions)

    if not suggestions:
        print(f"No operator ban suggestions available for {team_name} vs {opponent_name} on {map_name}.")
        return

    print(f"\n--- Operator Ban Suggestions for {team_name} vs {opponent_name} on {map_name} ---")
    for i, suggestion in enumerate(suggestions):
        print(f"  Ban Suggestion {i+1}: Ban {suggestion.operator_name} (Priority: {suggestion.priority})")
        print(f"    Reasoning: {suggestion.reasoning}")
        # print("    Supporting Stats:")
        # for stat, value in suggestion.supporting_stats.items():
        #     print(f"      {stat}: {value}")


def main():
    parser = argparse.ArgumentParser(description="R6ProStats - Liquipedia Data Analyzer and Suggester")
    parser.add_argument("--use-mock-data", action="store_true", help="Use mock data instead of fetching from Liquipedia.")
    parser.add_argument("--tournament-pages", nargs='+', default=[], help="List of Liquipedia tournament/match page titles to fetch data from (e.g., 'Six_Invitational/2023/Playoffs/Grand_Final'). Required if not using mock data for analysis.")
    parser.add_argument("--team-filter", action="append", dest="team_filters", default=[], help="Filter fetched data for this team (can be specified multiple times, e.g., --team-filter G2 --team-filter FaZe).")

    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Subparser for team statistics
    stats_parser = subparsers.add_parser("team_stats", help="Display statistics for a specific team.")
    stats_parser.add_argument("--team", required=True, help="Name of the team to get stats for.")

    # Subparser for map suggestions
    map_suggest_parser = subparsers.add_parser("suggest_map", help="Suggest maps for a team to play against an opponent.")
    map_suggest_parser.add_argument("--team", required=True, help="Your team's name.")
    map_suggest_parser.add_argument("--opponent", required=True, help="Opponent team's name.")
    map_suggest_parser.add_argument("--num", type=int, default=3, help="Number of map suggestions to provide.")

    # Subparser for operator ban suggestions
    ban_suggest_parser = subparsers.add_parser("suggest_bans", help="Suggest operator bans for a team against an opponent on a specific map.")
    ban_suggest_parser.add_argument("--team", required=True, help="Your team's name.")
    ban_suggest_parser.add_argument("--opponent", required=True, help="Opponent team's name.")
    ban_suggest_parser.add_argument("--map", required=True, help="The map for which to suggest bans.")
    ban_suggest_parser.add_argument("--num", type=int, default=2, help="Number of ban suggestions to provide.")

    args = parser.parse_args()

    all_match_data_for_engine = []

    if args.use_mock_data:
        logger.info("Using mock data.")
        all_match_data_for_engine = ALL_MOCK_MATCHES
        # If specific teams are requested with mock data, filter the mock data
        if args.team_filters:
            all_match_data_for_engine = [
                m for m in ALL_MOCK_MATCHES if m.team1.name in args.team_filters or m.team2.name in args.team_filters
            ]
            if not all_match_data_for_engine:
                 logger.warning(f"No mock data matches found for specified teams: {args.team_filters}. Using all mock data.")
                 all_match_data_for_engine = ALL_MOCK_MATCHES # Fallback to all if filter yields nothing
    else:
        if not args.tournament_pages:
            parser.error("--tournament-pages are required if not using --use-mock-data.")

        logger.info("Initializing DataFetcher and WikitextParser for live data...")
        fetcher = DataFetcher()
        wikitext_parser = WikitextParser()
        # Type hint for clarity, though not strictly necessary here
        live_fetched_data: List[MatchData] = fetch_and_parse_data(fetcher, wikitext_parser, args.team_filters, args.tournament_pages)
        all_match_data_for_engine = live_fetched_data

    if not all_match_data_for_engine:
        logger.error("No match data available (either mock or fetched) to initialize the AnalysisEngine. Exiting.")
        return

    engine = AnalysisEngine(all_matches=all_match_data_for_engine)

    if args.command == "team_stats":
        display_team_stats(engine, args.team)
    elif args.command == "suggest_map":
        display_map_suggestions(engine, args.team, args.opponent, args.num)
    elif args.command == "suggest_bans":
        display_ban_suggestions(engine, args.team, args.opponent, args.map, args.num)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
