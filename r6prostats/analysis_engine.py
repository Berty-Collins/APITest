import logging
from typing import List, Dict, Optional
from .parser_models import MatchData, Team, MapPlay, Operator
from .analysis_models import (
    TeamMapPreferences, MapStats, TeamOperatorPreferences, OperatorStats,
    GlobalMapStats, GlobalOperatorStats, MapPrediction, OperatorBanSuggestion
)

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

    def suggest_maps_to_play(self, team_name: str, opponent_team_name: str, num_suggestions: int = 3) -> List[MapPrediction]:
        """
        Suggests maps for team_name to play against opponent_team_name.
        """
        suggestions: List[MapPrediction] = []

        team_prefs = self.get_team_map_preferences(team_name)
        opponent_prefs = self.get_team_map_preferences(opponent_team_name)

        if not team_prefs:
            logging.warning(f"Cannot generate map suggestions: No data for {team_name}")
            return []
        if not opponent_prefs:
            logging.warning(f"Cannot generate map suggestions: No data for {opponent_team_name}")
            # Could still suggest based on team_name's strengths if opponent data is missing
            # For now, returning empty if opponent data is crucial for comparison.

        # Consider all maps played by either team or globally known
        all_map_names = set(team_prefs.map_stats.keys()) | set(opponent_prefs.map_stats.keys())
        if not all_map_names and self.global_map_stats: # Fallback to global maps if no team data
            all_map_names = set(self.global_map_stats.map_stats.keys())

        map_scores: Dict[str, float] = {}
        map_reasoning: Dict[str, Dict[str, str]] = {}

        for map_name in all_map_names:
            score = 0.0
            reasons = {}

            team_map_stat = team_prefs.map_stats.get(map_name)
            opp_map_stat = opponent_prefs.map_stats.get(map_name)

            # Factor 1: Team's own win rate on the map
            if team_map_stat and team_map_stat.times_played > 0:
                score += team_map_stat.win_rate * 0.4 # Weight: 40%
                reasons["team_wr"] = f"{team_name} WR: {team_map_stat.win_rate:.1f}% ({team_map_stat.wins}W-{team_map_stat.losses}L)"
                if team_map_stat.times_played < 2: # Lower confidence for low play count
                    score *= 0.7
                    reasons["team_wr_confidence"] = "Low play count for team"

            # Factor 2: Opponent's win rate on the map (lower is better for us)
            if opp_map_stat and opp_map_stat.times_played > 0:
                score += (100 - opp_map_stat.win_rate) * 0.4 # Weight: 40%
                reasons["opponent_wr"] = f"{opponent_team_name} WR: {opp_map_stat.win_rate:.1f}% ({opp_map_stat.wins}W-{opp_map_stat.losses}L)"
                if opp_map_stat.times_played < 2: # Lower confidence for low play count
                     score *= 0.7 # If they also have low play count, it's less reliable
                     reasons["opponent_wr_confidence"] = "Low play count for opponent"
            elif not opp_map_stat: # Opponent hasn't played it, could be a good pick
                score += 50 * 0.4 # Assume average (50%) opponent performance, scaled by weight
                reasons["opponent_wr"] = f"{opponent_team_name} has no recorded plays on this map."


            # Factor 3: Head-to-head (Placeholder - needs H2H data structure)
            # For now, this factor is skipped.
            # if h2h_data_available:
            #     score += h2h_advantage_score * 0.2 # Weight: 20%

            # Factor 4: Play Rate / Comfort (Higher play rate for team_name is good)
            if team_map_stat and team_map_stat.times_played > 1 : # Min 2 plays to be considered comfort
                 # Normalize play rate against team's total map plays (approx)
                total_maps_played_by_team = sum(ms.times_played for ms in team_prefs.map_stats.values())
                if total_maps_played_by_team > 0:
                    comfort_score = (team_map_stat.times_played / total_maps_played_by_team) * 100 * 0.2 # Weight: 20%
                    score += comfort_score
                    reasons["team_comfort"] = f"{team_name} play count: {team_map_stat.times_played}"

            map_scores[map_name] = score
            map_reasoning[map_name] = reasons

        # Sort maps by score
        sorted_maps = sorted(map_scores.items(), key=lambda item: item[1], reverse=True)

        for map_name, score_val in sorted_maps[:num_suggestions]:
            reason_texts = [f"{k}: {v}" for k,v in map_reasoning[map_name].items()]
            full_reasoning = f"Suggested due to: Score ({score_val:.1f}). " + "; ".join(reason_texts)
            suggestions.append(MapPrediction(
                map_name=map_name,
                confidence_score=min(score_val / 100, 1.0), # Normalize score to 0-1 confidence
                reasoning=full_reasoning,
                supporting_stats=map_reasoning[map_name]
            ))

        return suggestions

    def suggest_operator_bans(self, team_name: str, opponent_team_name: str, map_name: str, num_suggestions: int = 2) -> List[OperatorBanSuggestion]:
        """
        Suggests operators for team_name to ban against opponent_team_name on a specific map.
        """
        suggestions: List[OperatorBanSuggestion] = []
        opponent_op_prefs = self.get_team_operator_preferences(opponent_team_name)

        if not opponent_op_prefs:
            logging.warning(f"Cannot generate operator ban suggestions: No operator data for opponent {opponent_team_name}")
            return []

        # Get opponent's operator stats on the specific map
        opp_ops_on_map = opponent_op_prefs.operator_stats.get(map_name, {})
        if not opp_ops_on_map:
            logging.info(f"{opponent_team_name} has no specific operator stats recorded for {map_name}. Considering overall stats.")
            opp_ops_on_map = opponent_op_prefs.operator_stats.get(None, {}) # Fallback to overall stats

        op_scores: Dict[str, float] = {}
        op_reasoning: Dict[str, Dict[str, str]] = {}

        for op_name, stats in opp_ops_on_map.items():
            score = 0.0
            reasons = {}

            if stats.times_picked > 0:
                # Factor 1: Opponent's Win Rate with this Operator on this Map (or overall if map-specific is not available)
                # Higher win rate = higher priority to ban
                op_win_rate = stats.win_rate_when_picked
                score += op_win_rate * 0.6 # Weight: 60%
                reasons["opponent_op_wr"] = f"{opponent_team_name} WR with {op_name} on {map_name if map_name in opponent_op_prefs.operator_stats else 'overall'}: {op_win_rate:.1f}% ({stats.map_wins_when_picked}W / {stats.times_picked}P)"

                if stats.times_picked < 2 and map_name in opponent_op_prefs.operator_stats : # Low confidence for map-specific low pick count
                    score *= 0.7
                    reasons["opponent_op_wr_confidence"] = "Low pick count on this map"

                # Factor 2: Opponent's Pick Rate of this Operator on this Map (or overall)
                # Higher pick rate = more likely they'll pick it, so higher disruption value if banned
                # Approximate pick rate: (times_picked_op_on_map / total_maps_played_by_opponent_on_map)
                # This needs opponent's map play count on this specific map.
                opponent_map_stats = self.get_team_map_preferences(opponent_team_name)
                opp_map_play_count = 0
                if opponent_map_stats and map_name in opponent_map_stats.map_stats:
                    opp_map_play_count = opponent_map_stats.map_stats[map_name].times_played

                if opp_map_play_count > 0:
                    op_pick_rate_on_map = (stats.times_picked / opp_map_play_count) * 100
                    score += op_pick_rate_on_map * 0.4 # Weight: 40%
                    reasons["opponent_op_pr"] = f"{op_name} Pick Rate by {opponent_team_name} on {map_name}: {op_pick_rate_on_map:.1f}% ({stats.times_picked}P / {opp_map_play_count} Maps)"
                elif stats.times_picked > 0: # If map play count is zero but op was picked (e.g. overall stats)
                    # Use a general "high pick" indicator if overall picks are significant
                    # This part is a bit tricky without knowing total opportunities for picking.
                    # For now, just use a small bonus if picked multiple times overall.
                    if opponent_op_prefs.operator_stats.get(None, {}).get(op_name, OperatorStats(op_name)).times_picked > 3:
                         score += 10 # Small arbitrary bonus
                         reasons["opponent_op_overall_pick"] = f"{op_name} picked {opponent_op_prefs.operator_stats.get(None, {}).get(op_name).times_picked} times overall by {opponent_team_name}"


            # Factor 3: Global ban rate for this operator on this map (if available)
            # This requires global_operator_stats to have per-map operator stats
            if self.global_operator_stats.per_map_operator_stats.get(map_name, {}).get(op_name):
                global_op_stat_on_map = self.global_operator_stats.per_map_operator_stats[map_name][op_name]
                if global_op_stat_on_map.times_banned > 0 and self.global_map_stats.map_stats.get(map_name, MapStats(map_name)).times_played > 0:
                    global_ban_rate_on_map = (global_op_stat_on_map.times_banned / self.global_map_stats.map_stats[map_name].times_played) * 100
                    score += global_ban_rate_on_map * 0.1 # Small weight: 10%
                    reasons["global_op_ban_rate"] = f"Global Ban Rate for {op_name} on {map_name}: {global_ban_rate_on_map:.1f}%"

            if score > 0: # Only consider operators with some reason to be banned
                op_scores[op_name] = score
                op_reasoning[op_name] = reasons

        # Sort operators by score
        sorted_ops = sorted(op_scores.items(), key=lambda item: item[1], reverse=True)

        for op_name, score_val in sorted_ops[:num_suggestions]:
            reason_texts = [f"{k}: {v}" for k,v in op_reasoning[op_name].items()]
            full_reasoning = f"Suggest banning {op_name} on {map_name} (Score: {score_val:.1f}). Reasons: " + "; ".join(reason_texts)
            suggestions.append(OperatorBanSuggestion(
                operator_name=op_name,
                map_name=map_name,
                reasoning=full_reasoning,
                priority=int(score_val), # Use score as priority for now
                supporting_stats=op_reasoning[op_name]
            ))

        return suggestions


if __name__ == '__main__':
    from .mock_data import ALL_MOCK_MATCHES # Import mock data
    from .analysis_models import MapPrediction, OperatorBanSuggestion # Import for type hint if needed earlier

    all_test_matches = ALL_MOCK_MATCHES
    engine = AnalysisEngine(all_matches=all_test_matches)

    # --- Test Team Map Preferences ---
    print("\n--- G2 Esports Map Preferences ---")
    g2_map_prefs = engine.get_team_map_preferences("G2 Esports")
    if g2_map_prefs:
        for map_name, stats in sorted(g2_map_prefs.map_stats.items(), key=lambda item: item[1].win_rate, reverse=True):
            print(f"  Map: {map_name}")
            print(f"    Played: {stats.times_played}, Wins: {stats.wins} (Rate: {stats.win_rate:.2f}%)")
            print(f"    Rounds Won: {stats.rounds_won}, Rounds Lost: {stats.rounds_lost} (Round WR: {stats.round_win_rate:.2f}%)")

    # --- Test Team Operator Preferences ---
    print("\n--- G2 Esports Operator Preferences (Overall) ---")
    g2_op_prefs = engine.get_team_operator_preferences("G2 Esports")
    if g2_op_prefs and None in g2_op_prefs.operator_stats: # Check overall stats
        sorted_ops = sorted(g2_op_prefs.operator_stats[None].items(), key=lambda item: item[1].times_picked, reverse=True)
        for op_name, stats in sorted_ops[:5]: # Print top 5 picked
            if stats.times_picked > 0:
                print(f"  Operator: {op_name}")
                print(f"    Picked: {stats.times_picked} times, Map Wins when Picked: {stats.map_wins_when_picked} (WR: {stats.win_rate_when_picked:.2f}%)")
                print(f"    Banned by G2: {stats.times_banned_by_team}, Banned by Opponent: {stats.times_banned_by_opponent}")

    # --- Test Suggestion Logic ---
    print("\n--- Map Suggestions for G2 Esports vs FaZe Clan ---")
    map_suggestions = engine.suggest_maps_to_play("G2 Esports", "FaZe Clan", num_suggestions=3)
    if map_suggestions:
        for i, suggestion in enumerate(map_suggestions):
            print(f"  Suggestion {i+1}: Play {suggestion.map_name} (Confidence: {suggestion.confidence_score:.2f})")
            print(f"    Reasoning: {suggestion.reasoning}")
            # for k, v in suggestion.supporting_stats.items():
            #     print(f"      {k}: {v}")
    else:
        print("  No map suggestions available.")

    print("\n--- Map Suggestions for SSG vs G2 Esports ---")
    map_suggestions_ssg_g2 = engine.suggest_maps_to_play("SSG", "G2 Esports", num_suggestions=3)
    if map_suggestions_ssg_g2:
        for i, suggestion in enumerate(map_suggestions_ssg_g2):
            print(f"  Suggestion {i+1}: Play {suggestion.map_name} (Confidence: {suggestion.confidence_score:.2f})")
            print(f"    Reasoning: {suggestion.reasoning}")
    else:
        print("  No map suggestions available for SSG vs G2.")


    print("\n--- Operator Ban Suggestions for G2 Esports vs FaZe Clan on Oregon ---")
    oregon_ban_suggestions = engine.suggest_operator_bans("G2 Esports", "FaZe Clan", "Oregon", num_suggestions=2)
    if oregon_ban_suggestions:
        for i, suggestion in enumerate(oregon_ban_suggestions):
            print(f"  Ban Suggestion {i+1}: Ban {suggestion.operator_name} on {suggestion.map_name} (Priority: {suggestion.priority})")
            print(f"    Reasoning: {suggestion.reasoning}")
            # for k, v in suggestion.supporting_stats.items():
            #     print(f"      {k}: {v}")
    else:
        print("  No operator ban suggestions available for Oregon.")

    print("\n--- Operator Ban Suggestions for G2 Esports vs FaZe Clan on Bank ---")
    bank_ban_suggestions = engine.suggest_operator_bans("G2 Esports", "FaZe Clan", "Bank", num_suggestions=2)
    if bank_ban_suggestions:
        for i, suggestion in enumerate(bank_ban_suggestions):
            print(f"  Ban Suggestion {i+1}: Ban {suggestion.operator_name} on {suggestion.map_name} (Priority: {suggestion.priority})")
            print(f"    Reasoning: {suggestion.reasoning}")
    else:
        print("  No operator ban suggestions available for Bank.")

    print("\n--- Operator Ban Suggestions for SSG vs G2 Esports on Oregon ---")
    ssg_g2_oregon_bans = engine.suggest_operator_bans("SSG", "G2 Esports", "Oregon", num_suggestions=2)
    if ssg_g2_oregon_bans:
        for i, suggestion in enumerate(ssg_g2_oregon_bans):
            print(f"  Ban Suggestion {i+1}: Ban {suggestion.operator_name} on {suggestion.map_name} (Priority: {suggestion.priority})")
            print(f"    Reasoning: {suggestion.reasoning}")
    else:
        print("  No operator ban suggestions available for SSG vs G2 on Oregon.")


    print("\nAnalysisEngine module with suggestion logic implemented and tested with mock data.")
