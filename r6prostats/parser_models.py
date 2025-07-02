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

@dataclass
class MapPlay:
    map_name: str
    winner_team_name: Optional[str] = None # Name of the team that won this map
    team1_score: int = 0
    team2_score: int = 0

    team1_operator_bans: List[str] = field(default_factory=list)
    team2_operator_bans: List[str] = field(default_factory=list)

    team1_operator_picks_overall: List[Operator] = field(default_factory=list)
    team2_operator_picks_overall: List[Operator] = field(default_factory=list)

@dataclass
class MatchData:
    # Fields without default values first
    team1: Team
    team2: Team

    # Fields with default values next
    match_id: Optional[str] = None
    date: Optional[str] = None
    tournament_name: Optional[str] = None

    team1_score: int = 0 # Overall maps won
    team2_score: int = 0 # Overall maps won

    winner_team_name: Optional[str] = None

    map_pick_bans: List[MapPickBan] = field(default_factory=list)
    maps_played: List[MapPlay] = field(default_factory=list)

    raw_wikitext: Optional[str] = None
    source_url: Optional[str] = None
