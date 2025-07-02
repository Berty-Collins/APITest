from dataclasses import dataclass, field
from typing import Optional, List, Dict

@dataclass
class Operator:
    name: str
    side: Optional[str] = None # Attacker, Defender

@dataclass
class Map:
    name: str
    # Could add more map-specific details here if needed, like image URLs from Liquipedia

@dataclass
class Player:
    name: str
    # Could add more player details, e.g., link to their Liquipedia page

@dataclass
class Team:
    name: str
    region: Optional[str] = None
    roster: List[Player] = field(default_factory=list)
    # Could add more team details, e.g., link to Liquipedia page, logo URL

@dataclass
class MapPickBan:
    map_name: str
    action: str # "picked_by_team1", "picked_by_team2", "banned_by_team1", "banned_by_team2", "decider"
    team_name: Optional[str] = None # Team that picked/banned, if applicable

@dataclass
class OperatorPhase:
    # Operators picked by team1 during this phase (e.g., attack or defense)
    team1_picks: List[Operator] = field(default_factory=list)
    # Operators picked by team2 during this phase
    team2_picks: List[Operator] = field(default_factory=list)
    # Could also add team names here if they switch sides, or assume Team1 is always Attack first on their pick etc.
    # For simplicity, we'll assume fixed roles or handle contextually during parsing.

@dataclass
class MapPlay:
    map_name: str
    winner_team_name: Optional[str] = None # Name of the team that won this map
    team1_score: int = 0
    team2_score: int = 0

    # Operator bans for this specific map
    # Storing as list of operator names for now. Could be List[Operator]
    team1_operator_bans: List[str] = field(default_factory=list)
    team2_operator_bans: List[str] = field(default_factory=list)

    # Operator picks. This can be complex due to attack/defense phases.
    # For now, let's consider a list of phases or a simplified representation.
    # This part will likely need the most refinement based on template structure.
    # Simplified: all ops picked by each team on this map.
    # A more detailed structure might be a list of OperatorPhase objects if rounds are detailed.
    team1_operator_picks_overall: List[Operator] = field(default_factory=list)
    team2_operator_picks_overall: List[Operator] = field(default_factory=list)

    # If individual round data is available and parsed:
    # rounds: List[RoundData] # Where RoundData would detail per-round picks/outcomes

@dataclass
class MatchData:
    match_id: Optional[str] = None # Could be Liquipedia page title or a generated ID
    date: Optional[str] = None
    tournament_name: Optional[str] = None

    team1: Team
    team2: Team

    # Overall match score
    team1_score: int = 0 # Overall maps won
    team2_score: int = 0 # Overall maps won

    winner_team_name: Optional[str] = None # Name of the overall match winner

    # Map picks and bans before the match starts (if available)
    map_pick_bans: List[MapPickBan] = field(default_factory=list)

    # Details of each map played in the series
    maps_played: List[MapPlay] = field(default_factory=list)

    # Raw wikitext for reference or re-parsing
    raw_wikitext: Optional[str] = None

    # URL of the Liquipedia page
    source_url: Optional[str] = None

# Example usage (not for the file itself, just for thought):
# team_g2 = Team(name="G2 Esports", region="EU")
# team_faze = Team(name="FaZe Clan", region="LATAM")
# match = MatchData(team1=team_g2, team2=team_faze, tournament_name="Six Invitational 2023")
# map_play_oregon = MapPlay(map_name="Oregon", team1_score=7, team2_score=5, winner_team_name="G2 Esports")
# match.maps_played.append(map_play_oregon)
