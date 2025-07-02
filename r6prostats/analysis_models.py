from dataclasses import dataclass, field
from typing import Dict, Optional, List

@dataclass
class MapStats:
    map_name: str
    times_played: int = 0
    wins: int = 0
    losses: int = 0
    rounds_won: int = 0
    rounds_lost: int = 0
    # For team-specific stats on this map
    times_picked_by_team: int = 0 # How many times this team picked this map
    times_banned_by_team: int = 0 # How many times this team banned this map
    times_opponent_banned: int = 0 # How many times opponents banned this map against this team

    @property
    def win_rate(self) -> float:
        return (self.wins / self.times_played) * 100 if self.times_played > 0 else 0.0

    @property
    def round_win_rate(self) -> float:
        total_rounds = self.rounds_won + self.rounds_lost
        return (self.rounds_won / total_rounds) * 100 if total_rounds > 0 else 0.0

@dataclass
class OperatorStats:
    operator_name: str
    # Overall stats for this operator on a specific map or across all maps
    times_picked: int = 0
    wins_when_picked: int = 0 # Match wins when this operator was picked by the team
    map_wins_when_picked: int = 0 # Map wins when this operator was picked by the team
    rounds_won_when_picked: int = 0 # If per-round data becomes available

    times_banned: int = 0 # How many times this operator was banned by any team in analyzed matches
    times_banned_by_team: int = 0 # How many times this specific team banned this operator
    times_banned_by_opponent: int = 0 # How many times opponents banned this op against this team

    # Could add side-specific stats if applicable (e.g., attack_picks, defense_picks)

    @property
    def pick_rate(self) -> float: # This would need total possible picks context
        # Pick rate is complex: needs (times_picked / total_maps_played_by_team_where_op_available)
        # For now, this is just a placeholder concept.
        return 0.0

    @property
    def win_rate_when_picked(self) -> float: # Map win rate
        return (self.map_wins_when_picked / self.times_picked) * 100 if self.times_picked > 0 else 0.0

    @property
    def ban_rate(self) -> float: # This needs total matches analyzed context
        # Ban rate: (times_banned / total_maps_analyzed_where_op_is_bannable)
        return 0.0


@dataclass
class TeamMapPreferences:
    team_name: str
    map_stats: Dict[str, MapStats] = field(default_factory=dict) # Keyed by map name

    def update_map_stats(self, map_name: str, played: bool, won: bool, picked: bool, banned: bool, opponent_banned: bool, rounds_won: int = 0, rounds_lost: int = 0):
        if map_name not in self.map_stats:
            self.map_stats[map_name] = MapStats(map_name=map_name)

        stat = self.map_stats[map_name]
        if played:
            stat.times_played += 1
            if won:
                stat.wins += 1
            else:
                stat.losses += 1
            stat.rounds_won += rounds_won
            stat.rounds_lost += rounds_lost
        if picked:
            stat.times_picked_by_team +=1
        if banned:
            stat.times_banned_by_team +=1
        if opponent_banned:
            stat.times_opponent_banned +=1


@dataclass
class TeamOperatorPreferences:
    team_name: str
    # Operator stats per map, or overall if map_name is None
    # Structure: Dict[Optional[map_name], Dict[operator_name, OperatorStats]]
    operator_stats: Dict[Optional[str], Dict[str, OperatorStats]] = field(default_factory=lambda: {None: {}}) # Default with overall stats

    def _ensure_op_stats_exist(self, operator_name: str, map_name: Optional[str] = None):
        if map_name not in self.operator_stats:
            self.operator_stats[map_name] = {}
        if operator_name not in self.operator_stats[map_name]:
            self.operator_stats[map_name][operator_name] = OperatorStats(operator_name=operator_name)

    def record_operator_pick(self, operator_name: str, map_name: Optional[str], map_won: bool):
        self._ensure_op_stats_exist(operator_name, map_name) # For specific map
        self._ensure_op_stats_exist(operator_name, None) # For overall

        self.operator_stats[map_name][operator_name].times_picked += 1
        self.operator_stats[None][operator_name].times_picked += 1
        if map_won:
            self.operator_stats[map_name][operator_name].map_wins_when_picked += 1
            self.operator_stats[None][operator_name].map_wins_when_picked += 1

    def record_operator_ban_by_team(self, operator_name: str, map_name: Optional[str]):
        self._ensure_op_stats_exist(operator_name, map_name)
        self._ensure_op_stats_exist(operator_name, None)
        self.operator_stats[map_name][operator_name].times_banned_by_team += 1
        self.operator_stats[None][operator_name].times_banned_by_team += 1
        # Also increment general ban count
        self.operator_stats[map_name][operator_name].times_banned += 1
        self.operator_stats[None][operator_name].times_banned += 1

    def record_operator_ban_by_opponent(self, operator_name: str, map_name: Optional[str]):
        self._ensure_op_stats_exist(operator_name, map_name)
        self._ensure_op_stats_exist(operator_name, None)
        self.operator_stats[map_name][operator_name].times_banned_by_opponent += 1
        self.operator_stats[None][operator_name].times_banned_by_opponent += 1
        # Also increment general ban count
        self.operator_stats[map_name][operator_name].times_banned += 1
        self.operator_stats[None][operator_name].times_banned += 1

# Placeholder for strat identification, very conceptual
@dataclass
class StratPattern:
    name: str # e.g., "Aggressive Oregon Attack"
    operator_core: List[str] # Key operators often seen in this strat
    map_name: Optional[str] = None
    team_name: Optional[str] = None
    frequency: int = 0
    win_rate: float = 0.0

# Placeholder for map prediction output
@dataclass
class MapPrediction:
    map_name: str
    predicted_winner: Optional[str] = None
    confidence_score: float = 0.0 # 0.0 to 1.0
    reasoning: Optional[str] = None # Brief explanation
    supporting_stats: Dict[str, str] = field(default_factory=dict) # e.g. {"team_a_wr": "70%", "team_b_wr": "30%"}

@dataclass
class OperatorBanSuggestion:
    operator_name: str
    map_name: str # The map for which this ban is suggested
    reasoning: str # Textual explanation
    priority: int = 0 # Higher is more important
    supporting_stats: Dict[str, str] = field(default_factory=dict)


# Global stats (not tied to a specific team)
@dataclass
class GlobalMapStats:
    map_stats: Dict[str, MapStats] = field(default_factory=dict) # Keyed by map name

@dataclass
class GlobalOperatorStats:
    # Overall operator stats across all teams and maps
    operator_stats: Dict[str, OperatorStats] = field(default_factory=dict) # Keyed by operator name
    # Could also have per-map global operator stats: Dict[map_name, Dict[operator_name, OperatorStats]]
    per_map_operator_stats: Dict[str, Dict[str, OperatorStats]] = field(default_factory=dict)

    def _ensure_op_stats_exist(self, operator_name: str, map_name: Optional[str] = None):
        target_dict = self.operator_stats if map_name is None else self.per_map_operator_stats.setdefault(map_name, {})
        if operator_name not in target_dict:
            target_dict[operator_name] = OperatorStats(operator_name=operator_name)

    def record_operator_pick(self, operator_name: str, map_name: str, map_won: bool):
        # Record in global overall
        self._ensure_op_stats_exist(operator_name, None)
        self.operator_stats[operator_name].times_picked += 1
        if map_won:
            self.operator_stats[operator_name].map_wins_when_picked +=1

        # Record in global per-map
        self._ensure_op_stats_exist(operator_name, map_name)
        self.per_map_operator_stats[map_name][operator_name].times_picked += 1
        if map_won:
            self.per_map_operator_stats[map_name][operator_name].map_wins_when_picked +=1

    def record_operator_ban(self, operator_name: str, map_name: str):
        # Record in global overall
        self._ensure_op_stats_exist(operator_name, None)
        self.operator_stats[operator_name].times_banned += 1

        # Record in global per-map
        self._ensure_op_stats_exist(operator_name, map_name)
        self.per_map_operator_stats[map_name][operator_name].times_banned += 1
