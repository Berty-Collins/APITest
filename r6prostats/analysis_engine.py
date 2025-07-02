import logging
from typing import List, Dict, Optional
from .parser_models import MatchData, Team, MapPlay, Operator
from .analysis_models import TeamMapPreferences, MapStats, TeamOperatorPreferences, OperatorStats, GlobalMapStats, GlobalOperatorStats

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AnalysisEngine:
    """
    Performs calculations and derivations based on processed match data.
    """

    def __init__(self, all_matches: List[MatchData]):
        """
        Initializes the engine with all match data to be analyzed.
        In a real application, this data would come from the DataStore.
        """
        self.matches = all_matches
        self.teams_data: Dict[str, List[MatchData]] = self._organize_matches_by_team()

        # Global statistics containers
        self.global_map_stats = GlobalMapStats()
        self.global_operator_stats = GlobalOperatorStats()

        self._precompute_global_stats()


    def _organize_matches_by_team(self) -> Dict[str, List[MatchData]]:
        teams_data: Dict[str, List[MatchData]] = {}
        for match in self.matches:
            if match.team1 and match.team1.name:
                teams_data.setdefault(match.team1.name, []).append(match)
            if match.team2 and match.team2.name:
                teams_data.setdefault(match.team2.name, []).append(match)
        return teams_data

    def _precompute_global_stats(self):
        """
        Computes global statistics for maps and operators across all matches.
        """
        logging.info("Precomputing global statistics...")
        for match in self.matches:
            for map_play in match.maps_played:
                if not map_play.map_name or map_play.map_name.lower() in ["none", "tbd", "default"]:
                    continue

                # Update Global Map Stats
                self.global_map_stats.map_stats.setdefault(map_play.map_name, MapStats(map_name=map_play.map_name))
                g_map_stat = self.global_map_stats.map_stats[map_play.map_name]
                g_map_stat.times_played += 1
                g_map_stat.rounds_won += map_play.team1_score + map_play.team2_score # Total rounds played on this map instance
                # Note: Global map wins/losses don't make sense without a team perspective,
                # but rounds_won here can mean total rounds decided on this map.
                # Let's refine rounds_won/lost for global to be total rounds played to avoid confusion.
                # For now, this 'rounds_won' is just sum of scores.

                # Update Global Operator Stats (Picks)
                # Team 1 Picks
                for op in map_play.team1_operator_picks_overall:
                    is_map_winner = map_play.winner_team_name == match.team1.name
                    self.global_operator_stats.record_operator_pick(op.name, map_play.map_name, is_map_winner)
                # Team 2 Picks
                for op in map_play.team2_operator_picks_overall:
                    is_map_winner = map_play.winner_team_name == match.team2.name
                    self.global_operator_stats.record_operator_pick(op.name, map_play.map_name, is_map_winner)

                # Update Global Operator Stats (Bans)
                for op_name in map_play.team1_operator_bans:
                    self.global_operator_stats.record_operator_ban(op_name, map_play.map_name)
                for op_name in map_play.team2_operator_bans:
                    self.global_operator_stats.record_operator_ban(op_name, map_play.map_name)
        logging.info("Finished precomputing global statistics.")


    def get_team_map_preferences(self, team_name: str) -> Optional[TeamMapPreferences]:
        """
        Calculates map preferences for a specific team.
        Includes win rates, pick rates, ban rates on maps.
        """
        if team_name not in self.teams_data:
            logging.warning(f"No match data found for team: {team_name}")
            return None

        team_matches = self.teams_data[team_name]
        preferences = TeamMapPreferences(team_name=team_name)

        for match in team_matches:
            is_team1 = match.team1.name == team_name
            # opponent_team_name = match.team2.name if is_team1 else match.team1.name

            # Analyze map pick/ban phase if available in MatchData (not fully implemented in parser yet)
            # for mpb in match.map_pick_bans:
            #     if mpb.team_name == team_name:
            #         if mpb.action.startswith("picked"):
            #             preferences.update_map_stats(mpb.map_name, played=False, won=False, picked=True, banned=False, opponent_banned=False)
            #         elif mpb.action.startswith("banned"):
            #              preferences.update_map_stats(mpb.map_name, played=False, won=False, picked=False, banned=True, opponent_banned=False)
            #     elif mpb.action.startswith("banned"): # Opponent banned this map
            #         preferences.update_map_stats(mpb.map_name, played=False, won=False, picked=False, banned=False, opponent_banned=True)


            for map_play in match.maps_played:
                if not map_play.map_name or map_play.map_name.lower() in ["none", "tbd", "default"]:
                    continue

                map_played_by_team = True # If it's in maps_played for a team's match, they played it.

                team_won_map = False
                rounds_won_by_team = 0
                rounds_lost_by_team = 0

                if is_team1:
                    if map_play.winner_team_name == team_name : team_won_map = True
                    rounds_won_by_team = map_play.team1_score
                    rounds_lost_by_team = map_play.team2_score
                else: # Team is team2
                    if map_play.winner_team_name == team_name: team_won_map = True
                    rounds_won_by_team = map_play.team2_score
                    rounds_lost_by_team = map_play.team1_score

                # For pick/ban stats, we need data from the pre-match map selection phase.
                # The current parser doesn't fully extract this yet.
                # For now, `picked`, `banned`, `opponent_banned` flags in `update_map_stats` will be False.
                # This part needs enhancement once the parser provides `match.map_pick_bans` data.
                preferences.update_map_stats(
                    map_name=map_play.map_name,
                    played=map_played_by_team,
                    won=team_won_map,
                    picked=False, # Placeholder: requires pre-match pick/ban data
                    banned=False, # Placeholder
                    opponent_banned=False, # Placeholder
                    rounds_won=rounds_won_by_team,
                    rounds_lost=rounds_lost_by_team
                )

        # Calculate pick/ban rates if total matches where map could be picked/banned is known
        # This requires knowing the full map pool for each tournament/match.
        # For now, times_picked_by_team, etc., are absolute counts.

        return preferences

    def get_team_operator_preferences(self, team_name: str) -> Optional[TeamOperatorPreferences]:
        """
        Calculates operator pick/ban preferences for a specific team, optionally per map.
        """
        if team_name not in self.teams_data:
            logging.warning(f"No match data found for team: {team_name}")
            return None

        team_matches = self.teams_data[team_name]
        preferences = TeamOperatorPreferences(team_name=team_name)

        for match in team_matches:
            is_team1 = match.team1.name == team_name

            for map_play in match.maps_played:
                if not map_play.map_name or map_play.map_name.lower() in ["none", "tbd", "default"]:
                    continue

                map_won_by_team = (map_play.winner_team_name == team_name)

                # Record picks for the specified team
                ops_picked_by_team = map_play.team1_operator_picks_overall if is_team1 else map_play.team2_operator_picks_overall
                for op in ops_picked_by_team:
                    if op.name: # Ensure operator has a name
                        preferences.record_operator_pick(op.name, map_play.map_name, map_won_by_team)

                # Record bans by the specified team
                bans_by_team = map_play.team1_operator_bans if is_team1 else map_play.team2_operator_bans
                for op_name in bans_by_team:
                    preferences.record_operator_ban_by_team(op_name, map_play.map_name)

                # Record bans by the opponent against this team
                bans_by_opponent = map_play.team2_operator_bans if is_team1 else map_play.team1_operator_bans
                for op_name in bans_by_opponent:
                    preferences.record_operator_ban_by_opponent(op_name, map_play.map_name)
        return preferences

    # Other methods to be implemented later:
    # def get_operator_ban_rates(...)
    # def predict_best_maps(...)
    # def get_match_history(...)
    # def identify_common_strats(...)


if __name__ == '__main__':
    # --- Mock Data for Testing ---
    # Teams
    g2 = Team(name="G2 Esports")
    faze = Team(name="FaZe Clan")
    ssg = Team(name="SSG")

    # Operators (simplified)
    thermite = Operator(name="Thermite")
    hibana = Operator(name="Hibana")
    ace = Operator(name="Ace")
    kaid = Operator(name="Kaid")
    mira = Operator(name="Mira")
    smoke = Operator(name="Smoke")
    mute = Operator(name="Mute")
    jager = Operator(name="Jäger")
    valkyrie = Operator(name="Valkyrie")
    thatcher = Operator(name="Thatcher")

    # Match 1: G2 vs FaZe
    match1_map1 = MapPlay(
        map_name="Oregon", winner_team_name="G2 Esports", team1_score=7, team2_score=5,
        team1_operator_bans=["Kaid", "Mira"], team2_operator_bans=["Thatcher", "Ace"],
        team1_operator_picks_overall=[thermite, hibana, smoke, mute, jager], # G2's picks
        team2_operator_picks_overall=[ace, thatcher, valkyrie, kaid, mira]  # FaZe's picks
    )
    match1_map2 = MapPlay(
        map_name="Bank", winner_team_name="FaZe Clan", team1_score=6, team2_score=8,
        team1_operator_bans=["Mira", "Valkyrie"], team2_operator_bans=["Thermite", "Hibana"],
        team1_operator_picks_overall=[ace, thatcher, smoke, mute, jager], # G2's picks
        team2_operator_picks_overall=[thermite, hibana, valkyrie, kaid, mira]  # FaZe's picks
    )
    match1 = MatchData(
        match_id="match1", team1=g2, team2=faze, team1_score=1, team2_score=1, # Maps won
        maps_played=[match1_map1, match1_map2], tournament_name="Test Tournament 1"
    )

    # Match 2: G2 vs SSG
    match2_map1 = MapPlay(
        map_name="Oregon", winner_team_name="G2 Esports", team1_score=7, team2_score=3,
        team1_operator_bans=["Kaid", "Smoke"], team2_operator_bans=["Ace", "Thermite"],
        team1_operator_picks_overall=[hibana, thatcher, mute, jager, valkyrie], # G2's picks
        team2_operator_picks_overall=[ace, thermite, mira, smoke, kaid] # SSG's picks
    )
    match2 = MatchData(
        match_id="match2", team1=g2, team2=ssg, team1_score=1, team2_score=0,
        maps_played=[match2_map1], tournament_name="Test Tournament 2"
    )

    # Match 3: FaZe vs SSG
    match3_map1 = MapPlay(
        map_name="Clubhouse", winner_team_name="FaZe Clan", team1_score=7, team2_score=4,
        team1_operator_bans=["Thermite", "Kaid"], team2_operator_bans=["Thatcher", "Mira"],
        team1_operator_picks_overall=[ace, hibana, smoke, mute, jager], # FaZe's picks
        team2_operator_picks_overall=[thermite, thatcher, valkyrie, kaid, mira]  # SSG's picks
    )
    match3 = MatchData(
        match_id="match3", team1=faze, team2=ssg, team1_score=1, team2_score=0,
        maps_played=[match3_map1], tournament_name="Test Tournament 3"
    )

    all_test_matches = [match1, match2, match3]
    engine = AnalysisEngine(all_matches=all_test_matches)

    # --- Test Team Map Preferences ---
    print("\n--- G2 Esports Map Preferences ---")
    g2_map_prefs = engine.get_team_map_preferences("G2 Esports")
    if g2_map_prefs:
        for map_name, stats in g2_map_prefs.map_stats.items():
            print(f"  Map: {map_name}")
            print(f"    Played: {stats.times_played}, Wins: {stats.wins} (Rate: {stats.win_rate:.2f}%)")
            print(f"    Rounds Won: {stats.rounds_won}, Rounds Lost: {stats.rounds_lost} (Rate: {stats.round_win_rate:.2f}%)")
            # print(f"    Picked by G2: {stats.times_picked_by_team}, Banned by G2: {stats.times_banned_by_team}, Banned by Opp: {stats.times_opponent_banned}")

    print("\n--- FaZe Clan Map Preferences ---")
    faze_map_prefs = engine.get_team_map_preferences("FaZe Clan")
    if faze_map_prefs:
        for map_name, stats in faze_map_prefs.map_stats.items():
            print(f"  Map: {map_name}")
            print(f"    Played: {stats.times_played}, Wins: {stats.wins} (Rate: {stats.win_rate:.2f}%)")
            print(f"    Rounds Won: {stats.rounds_won}, Rounds Lost: {stats.rounds_lost} (Rate: {stats.round_win_rate:.2f}%)")

    # --- Test Team Operator Preferences ---
    print("\n--- G2 Esports Operator Preferences (Overall) ---")
    g2_op_prefs = engine.get_team_operator_preferences("G2 Esports")
    if g2_op_prefs and None in g2_op_prefs.operator_stats: # Check overall stats
        # Sort by times picked for readability
        sorted_ops = sorted(g2_op_prefs.operator_stats[None].items(), key=lambda item: item[1].times_picked, reverse=True)
        for op_name, stats in sorted_ops:
            if stats.times_picked > 0 or stats.times_banned_by_team > 0 or stats.times_banned_by_opponent > 0:
                print(f"  Operator: {op_name}")
                print(f"    Picked: {stats.times_picked} times, Map Wins when Picked: {stats.map_wins_when_picked} (WR: {stats.win_rate_when_picked:.2f}%)")
                print(f"    Banned by G2: {stats.times_banned_by_team}, Banned by Opponent: {stats.times_banned_by_opponent}")

    print("\n--- G2 Esports Operator Preferences (Oregon) ---")
    if g2_op_prefs and "Oregon" in g2_op_prefs.operator_stats:
        sorted_ops_oregon = sorted(g2_op_prefs.operator_stats["Oregon"].items(), key=lambda item: item[1].times_picked, reverse=True)
        for op_name, stats in sorted_ops_oregon:
             if stats.times_picked > 0 or stats.times_banned_by_team > 0 or stats.times_banned_by_opponent > 0:
                print(f"  Operator: {op_name} on Oregon")
                print(f"    Picked: {stats.times_picked} times, Map Wins when Picked: {stats.map_wins_when_picked} (WR: {stats.win_rate_when_picked:.2f}%)")
                print(f"    Banned by G2: {stats.times_banned_by_team}, Banned by Opponent: {stats.times_banned_by_opponent}")

    # --- Test Global Stats ---
    print("\n--- Global Map Stats ---")
    for map_name, stats in engine.global_map_stats.map_stats.items():
        print(f"  Map: {map_name}, Times Played Globally: {stats.times_played}")

    print("\n--- Global Operator Stats (Overall) ---")
    # Sort by times picked for readability
    sorted_global_ops = sorted(engine.global_operator_stats.operator_stats.items(), key=lambda item: item[1].times_picked, reverse=True)
    for op_name, stats in sorted_global_ops:
        if stats.times_picked > 0 or stats.times_banned > 0:
            print(f"  Operator: {op_name}")
            print(f"    Picked Globally: {stats.times_picked} times, Map Wins when Picked: {stats.map_wins_when_picked} (WR: {stats.win_rate_when_picked:.2f}%)")
            print(f"    Banned Globally: {stats.times_banned}")

    print("\nAnalysisEngine module with map preference functionality (and stubs for operator prefs) implemented.")
