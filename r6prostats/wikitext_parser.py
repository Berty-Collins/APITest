import mwparserfromhell
import re
import logging
from typing import Optional, List, Dict
from .parser_models import MatchData, Team, Player, MapPlay, Operator, MapPickBan, Map

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Comprehensive Operator Aliases
OPERATOR_ALIASES = {
    # Attackers
    "sledge": "Sledge",
    "thatcher": "Thatcher",
    "ash": "Ash",
    "thermite": "Thermite",
    "twitch": "Twitch",
    "montagne": "Montagne",
    "glaz": "Glaz",
    "fuze": "Fuze",
    "blitz": "Blitz",
    "iq": "IQ",
    "buck": "Buck",
    "blackbeard": "Blackbeard",
    "capitao": "Capitão",
    "hibana": "Hibana",
    "jackal": "Jackal",
    "ying": "Ying",
    "zofia": "Zofia",
    "dokkaebi": "Dokkaebi",
    "lion": "Lion",
    "finka": "Finka",
    "maverick": "Maverick",
    "nomad": "Nomad",
    "gridlock": "Gridlock",
    "nokk": "Nøkk", # Nøkk
    "amaru": "Amaru",
    "kali": "Kali",
    "iana": "Iana",
    "ace": "Ace",
    "zero": "Zero",
    "flores": "Flores",
    "osa": "Osa",
    "sens": "Sens",
    "grim": "Grim",
    "brava": "Brava",
    "ram": "Ram",
    # Defenders
    "smoke": "Smoke",
    "mute": "Mute",
    "castle": "Castle",
    "pulse": "Pulse",
    "doc": "Doc",
    "rook": "Rook",
    "kapkan": "Kapkan",
    "tachanka": "Tachanka",
    "jager": "Jäger", # Jäger
    "jäger": "Jäger",
    "bandit": "Bandit",
    "frost": "Frost",
    "valkyrie": "Valkyrie",
    "caveira": "Caveira",
    "echo": "Echo",
    "mira": "Mira",
    "lesion": "Lesion",
    "ela": "Ela",
    "vigil": "Vigil",
    "maestro": "Maestro",
    "alibi": "Alibi",
    "clash": "Clash",
    "kaid": "Kaid",
    "mozzie": "Mozzie",
    "warden": "Warden",
    "goyo": "Goyo",
    "wamai": "Wamai",
    "oryx": "Oryx",
    "melusi": "Melusi",
    "aruni": "Aruni",
    "thunderbird": "Thunderbird",
    "thorn": "Thorn",
    "azami": "Azami",
    "solis": "Solis",
    "fenrir": "Fenrir",
    # Common misspellings or variations
    "jager": "Jäger",
    "capitao": "Capitão",
    "nokk": "Nøkk",
    # Add any other common variations you encounter
}

def normalize_operator_name(name: str) -> str:
    if not isinstance(name, str):
        return "UnknownOperator"

    name_stripped = name.strip()
    name_lower = name_stripped.lower()

    # Check aliases first
    if name_lower in OPERATOR_ALIASES:
        return OPERATOR_ALIASES[name_lower]

    # If not in aliases, try capitalizing (handles cases like "ash" -> "Ash")
    # and also handles already correctly capitalized names.
    # This also helps if an alias was missed but the capitalization is the only issue.
    return name_stripped.capitalize()

class WikitextParser:
    def __init__(self):
        pass

    def _extract_template_param(self, template, param_name: str, default: Optional[str] = None) -> Optional[str]:
        if template.has(param_name):
            value_node = template.get(param_name).value
            try:
                return str(value_node.strip_code(normalize=True, collapse=True)).strip()
            except Exception:
                return str(value_node).strip()
        return default

    def _extract_team_name(self, template, param_prefix: str) -> str:
        name_param = f"{param_prefix}name"
        direct_param = param_prefix

        name_to_check = None
        if template.has(name_param):
            name_to_check = template.get(name_param).value
        elif template.has(direct_param):
             name_to_check = template.get(direct_param).value

        if name_to_check:
            nested_templates = name_to_check.filter_templates()
            if nested_templates and (nested_templates[0].name.matches("TeamLink") or nested_templates[0].name.matches("tl")):
                if nested_templates[0].has(1):
                    return str(nested_templates[0].get(1).value).strip()
            return str(name_to_check.strip_code(normalize=True, collapse=True)).strip()

        return "Unknown Team"


    def parse_match_page(self, page_title: str, wikitext: str) -> Optional[MatchData]:
        logging.info(f"Starting to parse match page: {page_title}")
        parsed_wikitext = mwparserfromhell.parse(wikitext)

        tournament_name_from_page = page_title.split('/')[0] if '/' in page_title else page_title

        potential_match_templates = ["MatchMaps", "MatchResults", "Scorebox", "MatchRecap", "BracketMatch", "MatchSummary"]

        match_template = None
        for tpl_name_pattern in potential_match_templates:
            found_templates = parsed_wikitext.filter_templates(matches=lambda t: t.name.lower().strip().startswith(tpl_name_pattern.lower()))
            if found_templates:
                match_template = found_templates[0]
                logging.info(f"Found match template: {match_template.name.strip()}")
                break

        if not match_template:
            logging.warning(f"No suitable match overview template found on page {page_title}.")
            map_plays = self._parse_individual_map_plays(parsed_wikitext, "UnknownTeam1", "UnknownTeam2")
            if map_plays:
                return MatchData(
                    team1=Team(name="Team 1 (Inferred)"),
                    team2=Team(name="Team 2 (Inferred)"),
                    match_id=page_title,
                    maps_played=map_plays,
                    tournament_name=tournament_name_from_page,
                    raw_wikitext=wikitext,
                    source_url=f"https://liquipedia.net/rainbowsix/{page_title.replace(' ', '_')}"
                )
            return None

        team1_name = self._extract_team_name(match_template, "team1") or \
                     self._extract_team_name(match_template, "t1") or \
                     self._extract_template_param(match_template, "team1name") or \
                     self._extract_template_param(match_template, "opponent1") or \
                     "Team 1"
        team2_name = self._extract_team_name(match_template, "team2") or \
                     self._extract_team_name(match_template, "t2") or \
                     self._extract_template_param(match_template, "team2name") or \
                     self._extract_template_param(match_template, "opponent2") or \
                     "Team 2"

        team1_score_overall_str = self._extract_template_param(match_template, "team1score", "0") or \
                                  self._extract_template_param(match_template, "score1", "0") or \
                                  self._extract_template_param(match_template, "games1", "0") or "0"
        team2_score_overall_str = self._extract_template_param(match_template, "team2score", "0") or \
                                  self._extract_template_param(match_template, "score2", "0") or \
                                  self._extract_template_param(match_template, "games2", "0") or "0"

        team1_score_overall = int(team1_score_overall_str) if team1_score_overall_str.strip().isdigit() else 0
        team2_score_overall = int(team2_score_overall_str) if team2_score_overall_str.strip().isdigit() else 0

        date_str = self._extract_template_param(match_template, "date")

        winner_team_name = None
        if match_template.has("winner"):
            winner_val = self._extract_template_param(match_template, "winner")
            if winner_val == "1": winner_team_name = team1_name
            elif winner_val == "2": winner_team_name = team2_name
            elif winner_val and winner_val.lower() not in ["draw", "skip", "tbd", " forfeits"]: # direct name, ignore draw/skip
                 # Check if winner_val is one of the team names to avoid assigning "W" or similar as winner
                if winner_val.lower() == team1_name.lower():
                    winner_team_name = team1_name
                elif winner_val.lower() == team2_name.lower():
                    winner_team_name = team2_name
                elif winner_val not in ["1","2","0","TBD","TBA", "N/A", ""]: # if it's not a numerical indicator or placeholder
                     winner_team_name = winner_val # Assume it's a direct name if not 1 or 2
        elif team1_score_overall > team2_score_overall:
            winner_team_name = team1_name
        elif team2_score_overall > team1_score_overall:
            winner_team_name = team2_name

        match_data = MatchData(
            team1=Team(name=team1_name),
            team2=Team(name=team2_name),
            match_id=page_title,
            team1_score=team1_score_overall,
            team2_score=team2_score_overall,
            winner_team_name=winner_team_name,
            date=date_str,
            tournament_name=self._extract_template_param(match_template, "tournament", tournament_name_from_page),
            raw_wikitext=wikitext,
            source_url=f"https://liquipedia.net/rainbowsix/{page_title.replace(' ', '_')}"
        )

        match_data.maps_played = self._parse_individual_map_plays(match_template, team1_name, team2_name)

        # Recalculate overall score based on map wins if scores were initially 0 or seem inconsistent
        if team1_score_overall == 0 and team2_score_overall == 0 and match_data.maps_played:
            calculated_t1_score = sum(1 for mp in match_data.maps_played if mp.winner_team_name == team1_name)
            calculated_t2_score = sum(1 for mp in match_data.maps_played if mp.winner_team_name == team2_name)
            match_data.team1_score = calculated_t1_score
            match_data.team2_score = calculated_t2_score
            if calculated_t1_score > calculated_t2_score:
                match_data.winner_team_name = team1_name
            elif calculated_t2_score > calculated_t1_score:
                match_data.winner_team_name = team2_name
            elif calculated_t1_score == calculated_t2_score and calculated_t1_score > 0 : # if it's a draw in maps
                 match_data.winner_team_name = "Draw" # Or handle as per specific tournament rules for draws

        logging.info(f"Successfully parsed match data for {page_title}. Maps found: {len(match_data.maps_played)}")
        return match_data

    def _parse_individual_map_plays(self, wikitext_node, team1_name: str, team2_name: str) -> List[MapPlay]:
        maps_played_list: List[MapPlay] = []
        i = 1
        while True:
            map_name = None
            map_play_data = {} # Store intermediate data for the current map
            current_map_processed = False

            # Try to find a nested map template first, e.g. map1={{Map ...}}
            # Common Liquipedia template for map details is often just {{Map}}.
            # Sometimes it's {{MapV2}}, {{MapRecapV2}} or game-specific like {{Game}}.
            map_param_node = wikitext_node.get(f"map{i}") if hasattr(wikitext_node, 'has') and wikitext_node.has(f"map{i}") else None

            map_recap_template = None
            if map_param_node:
                map_sub_templates = map_param_node.value.filter_templates(recursive=False)
                if map_sub_templates and (map_sub_templates[0].name.lower().strip().startswith("map") or "recap" in map_sub_templates[0].name.lower().strip() or map_sub_templates[0].name.lower().strip().startswith("game")):
                    map_recap_template = map_sub_templates[0]
                    map_name = self._extract_template_param(map_recap_template, "map")
                elif not map_sub_templates: # mapX=MapName (direct value, not a template)
                     map_name = str(map_param_node.value.strip_code(normalize=True, collapse=True)).strip()

            # If map_name wasn't found in a nested template via mapX, try flat parameters like mapXmap
            if not map_name:
                map_name = self._extract_template_param(wikitext_node, f"map{i}map")

            if not map_name or map_name.lower() in ["none", "tbd", "", "default", "d", "decider"]: # Skip if map name is invalid or placeholder
                # Check if there's a 'vod' parameter for this map index, which might indicate a played map without explicit name
                vod_param = self._extract_template_param(wikitext_node, f"map{i}vod") or self._extract_template_param(wikitext_node, f"vodgame{i}")
                if not vod_param and not match_template.has(f"map{i+1}map") and not match_template.has(f"map{i+1}"): # Check if there's a next map
                    break # No more maps likely
                i += 1
                if i > 10: break # Safety break
                continue

            map_play = MapPlay(map_name=map_name)

            # Scores: Try from sub-template first, then from main template
            if map_recap_template:
                map_play.team1_score = int(self._extract_template_param(map_recap_template, "score1", self._extract_template_param(map_recap_template, "team1score", "0")) or "0")
                map_play.team2_score = int(self._extract_template_param(map_recap_template, "score2", self._extract_template_param(map_recap_template, "team2score", "0")) or "0")
                score_str_sub = self._extract_template_param(map_recap_template, "score")
                if score_str_sub and '-' in score_str_sub and (map_play.team1_score == 0 and map_play.team2_score == 0):
                    s1, s2 = score_str_sub.split('-', 1)
                    map_play.team1_score = int(s1.strip()) if s1.strip().isdigit() else 0
                    map_play.team2_score = int(s2.strip()) if s2.strip().isdigit() else 0

                winner_flag = self._extract_template_param(map_recap_template, "winner") or self._extract_template_param(map_recap_template, "mapwin")
                if winner_flag == "1": map_play.winner_team_name = team1_name
                elif winner_flag == "2": map_play.winner_team_name = team2_name

            # Fallback to scores from the main MatchMaps template if not found in sub-template or no sub-template
            if map_play.team1_score == 0 and map_play.team2_score == 0:
                score_str = self._extract_template_param(wikitext_node, f"map{i}score")
                if score_str and '-' in score_str:
                    s1, s2 = score_str.split('-', 1)
                    map_play.team1_score = int(s1.strip()) if s1.strip().isdigit() else 0
                    map_play.team2_score = int(s2.strip()) if s2.strip().isdigit() else 0
                else:
                    map_play.team1_score = int(self._extract_template_param(wikitext_node, f"map{i}team1score", "0") or "0")
                    map_play.team2_score = int(self._extract_template_param(wikitext_node, f"map{i}team2score", "0") or "0")

            # Determine map winner if not set by 'mapwin' or 'winner' flag
            if not map_play.winner_team_name:
                if map_play.team1_score > map_play.team2_score:
                    map_play.winner_team_name = team1_name
                elif map_play.team2_score > map_play.team1_score:
                    map_play.winner_team_name = team2_name

            # Operator bans and picks
            # This part is highly dependent on the specific templates used for R6 (e.g., {{OperatorLineup}}, {{PickBan}})
            # It might be directly in MatchMaps (mapXteamYbanZ, mapXteamYopZ) or nested in mapX's sub-template's 'details' param
            op_lineup_source_template = map_recap_template if map_recap_template and map_recap_template.has("details") else wikitext_node

            if map_recap_template and map_recap_template.has("details"):
                 details_param_value = map_recap_template.get("details").value
                 op_lineup_tpl_list = details_param_value.filter_templates(matches=lambda t: t.name.lower().strip() in ["operatorlineup", "pickban", "picksandbans", "r6operatorscoreboard"])
                 if op_lineup_tpl_list:
                     op_lineup_source_template = op_lineup_tpl_list[0]

            for ban_idx in range(1, 6): # Max 5 bans
                t1_b = self._extract_template_param(op_lineup_source_template, f"t1ban{ban_idx}") or \
                       self._extract_template_param(op_lineup_source_template, f"team1ban{ban_idx}") or \
                       self._extract_template_param(op_lineup_source_template, f"b1{ban_idx}") # Common in some templates
                if t1_b and t1_b.lower() != "none": map_play.team1_operator_bans.append(normalize_operator_name(t1_b))

                t2_b = self._extract_template_param(op_lineup_source_template, f"t2ban{ban_idx}") or \
                       self._extract_template_param(op_lineup_source_template, f"team2ban{ban_idx}") or \
                       self._extract_template_param(op_lineup_source_template, f"b2{ban_idx}")
                if t2_b and t2_b.lower() != "none": map_play.team2_operator_bans.append(normalize_operator_name(t2_b))

            for op_idx in range(1, 6): # 5 operators per team
                t1_op = self._extract_template_param(op_lineup_source_template, f"t1p{op_idx}") or \
                        self._extract_template_param(op_lineup_source_template, f"team1op{op_idx}")
                if t1_op and t1_op.lower() != "none": map_play.team1_operator_picks_overall.append(Operator(name=normalize_operator_name(t1_op)))

                t2_op = self._extract_template_param(op_lineup_source_template, f"t2p{op_idx}") or \
                        self._extract_template_param(op_lineup_source_template, f"team2op{op_idx}")
                if t2_op and t2_op.lower() != "none": map_play.team2_operator_picks_overall.append(Operator(name=normalize_operator_name(t2_op)))

            if map_play.map_name: # Ensure map_name is valid before adding
                maps_played_list.append(map_play)

            i += 1
            if i > 10: # Safety break for while loop (e.g., max 7 maps in a Bo7, 10 is very generous)
                logging.warning(f"Breaking map parsing loop after 10 iterations for parent template.")
                break
        return maps_played_list

    def parse_team_page(self, page_title: str, wikitext: str) -> Optional[Team]:
        logging.info(f"Parsing team page: {page_title}")
        parsed_wikitext = mwparserfromhell.parse(wikitext)
        # Common template name for team infoboxes
        infobox_templates = parsed_wikitext.filter_templates(matches=lambda t: t.name.lower().strip().startswith("infobox team"))

        if not infobox_templates:
            logging.warning(f"No {{Infobox Team}} template found on page {page_title}.")
            # Fallback: use page title as team name if no infobox
            return Team(name=page_title.replace("(team)", "").strip().replace("_", " "))


        infobox = infobox_templates[0]
        team_name = self._extract_template_param(infobox, "name", page_title.replace("(team)", "").strip().replace("_", " "))
        region = self._extract_template_param(infobox, "region")

        team = Team(name=team_name, region=region)

        # Roster parsing: common parameters are p1, p2, ... or player1, player2, ...
        # Also check for parameters like coach, sub1, etc.
        player_params = []
        for k in range(1, 11): # Check for p1-p10, player1-player10
            player_params.append(f"p{k}")
            player_params.append(f"player{k}")
        # Add common named player slots
        player_params.extend(["captain", "coach", "sub1", "sub2", "standin1", "standin2"])
        # Add roster parameters often used like |player1=... |player2=...
        # Some templates use |Player 1=, |Player 2= etc.
        for num in range(1, 8): # Check for Player 1 to Player 7
            player_params.append(f"Player {num}")


        processed_players = set() # To avoid duplicate player entries if multiple params point to same player

        for param_base in player_params:
            player_name_val = None
            # Check for direct player name, e.g., p1=PlayerName
            if infobox.has(param_base):
                player_node = infobox.get(param_base).value

                # Check for {{Player|Name}} or {{flag|country}} {{Player|Name}}
                player_templates = player_node.filter_templates(matches=lambda t: t.name.matches("Player"))
                if player_templates:
                    if player_templates[0].has(1): # First unnamed parameter is usually player name
                         player_name_val = str(player_templates[0].get(1).value).strip()
                else:
                    # If not a {{Player}} template, try to get text, might be wikilink or plain text
                    player_name_val = str(player_node.strip_code(normalize=True, collapse=True)).strip()
                    # Remove flag templates if they are just text like {{flag|de}}
                    player_name_val = re.sub(r"\{\{flag\|.*?\}\}\s*", "", player_name_val).strip()


            # Also check for p1link=PlayerName (less common now but good for robustness)
            if not player_name_val and infobox.has(f"{param_base}link"):
                player_name_val = self._extract_template_param(infobox, f"{param_base}link")

            if player_name_val and player_name_val.lower() not in ["", "tbd"] and player_name_val not in processed_players:
                team.roster.append(Player(name=player_name_val))
                processed_players.add(player_name_val)

        # Alternative roster parsing if it's in a section like "==Roster==" with {{PlayerCard}}
        # This requires more advanced section parsing. For now, focusing on Infobox.

        logging.info(f"Parsed team: {team.name}, Region: {team.region}, Roster size: {len(team.roster)}")
        return team

    def parse_operator_page(self, page_title: str, wikitext: str) -> Optional[Operator]:
        logging.info(f"Parsing operator page: {page_title}")
        parsed_wikitext = mwparserfromhell.parse(wikitext)

        infobox_templates = parsed_wikitext.filter_templates(matches=lambda t: t.name.lower().strip().startswith("infobox operator"))
        side = None
        op_name_from_title = page_title.split('/')[-1].replace('_', ' ') # Get name from title as fallback
        op_name = normalize_operator_name(op_name_from_title)


        if not infobox_templates:
            logging.warning(f"No {{Infobox Operator}} found on {page_title}. Using page title as name.")
            # Infer side from categories if possible
            page_text_lower = wikitext.lower()
            if "[[category:attack operators]]" in page_text_lower or "[[category:attacker operators]]" in page_text_lower : side = "Attacker"
            elif "[[category:defense operators]]" in page_text_lower or "[[category:defender operators]]" in page_text_lower: side = "Defender"
        else:
            infobox = infobox_templates[0]
            op_name = normalize_operator_name(self._extract_template_param(infobox, "name", op_name_from_title))

            side_str = self._extract_template_param(infobox, "side")
            if side_str:
                side_str = side_str.lower()
                if "attack" in side_str: side = "Attacker"
                elif "defen" in side_str: side = "Defender"

            if not side: # If side not found in infobox, try categories
                page_text_lower = wikitext.lower()
                if "[[category:attack operators]]" in page_text_lower or "[[category:attacker operators]]" in page_text_lower: side = "Attacker"
                elif "[[category:defense operators]]" in page_text_lower or "[[category:defender operators]]" in page_text_lower: side = "Defender"

        logging.info(f"Parsed operator: {op_name}, Side: {side}")
        return Operator(name=op_name, side=side)

    def parse_map_page(self, page_title: str, wikitext: str) -> Optional[Map]:
        logging.info(f"Parsing map page: {page_title}")
        map_name = page_title.split('/')[-1].replace('_', ' ')

        parsed_wikitext = mwparserfromhell.parse(wikitext)
        infobox_templates = parsed_wikitext.filter_templates(matches=lambda t: t.name.lower().strip().startswith("infobox map"))
        if infobox_templates:
            infobox = infobox_templates[0]
            name_from_infobox = self._extract_template_param(infobox, "name")
            if name_from_infobox:
                map_name = name_from_infobox

        logging.info(f"Parsed map: {map_name}")
        return Map(name=map_name)


if __name__ == '__main__':
    # This section is for basic testing of the parser.
    # Requires sample wikitext data.
    parser = WikitextParser()

    # Example: Test with a hypothetical simplified MatchMaps wikitext
    sample_match_wikitext = """
{{MatchMaps
|team1=G2 Esports
|team2=FaZe Clan
|team1score=2
|team2score=1
|date=2023-02-19
|tournament=Six Invitational 2023
|map1map=Bank
|map1team1score=7
|map1team2score=5
|map1team1ban1=Thatcher |map1team1ban2=Kaid
|map1team2ban1=Maverick |map1team2ban2=Mira
|map1team1op1=Ace |map1team1op2=Thermite |map1team1op3=Hibana |map1team1op4=Nomad |map1team1op5=Iana
|map1team2op1=Kapkan |map1team2op2=Smoke |map1team2op3=Mute |map1team2op4=Valkyrie |map1team2op5=Warden
|map2map=Oregon
|map2team1score=4
|map2team2score=7
|map2team1ban1=CAPITAO |map2team2ban1=JAEGER
|map2team1op1=Sledge |map2team1op2=Buck |map2team1op3=Zofia |map2team1op4=Flores |map2team1op5=Gridlock
|map2team2op1=Aruni |map2team2op2=Lesion |map2team2op3=Melusi |map2team2op4=Wamai |map2team2op5=Azami
|map3=Kafe Dostoyevsky
|map3score=7-2
|map3team1ban1=Ying |map3team2ban1=Valkyrie
|map3team1op1=Thatcher |map3team1op2=Ace |map3team1op3=Nomad |map3team1op4=Zero |map3team1op5=Osa
|map3team2op1=Smoke |map3team2op2=Mute |map3team2op3=Kaid |map3team2op4=Jäger |map3team2op5=Solis
}}
"""
    logging.info("\\n--- Parsing Sample Match Wikitext ---")
    parsed_match_data = parser.parse_match_page("Six Invitational/2023/Grand Final", sample_match_wikitext)
    if parsed_match_data:
        print(f"Match: {parsed_match_data.team1.name} vs {parsed_match_data.team2.name}, Score: {parsed_match_data.team1_score}-{parsed_match_data.team2_score}")
        print(f"Winner: {parsed_match_data.winner_team_name}, Date: {parsed_match_data.date}, Tournament: {parsed_match_data.tournament_name}")
        for map_play in parsed_match_data.maps_played:
            print(f"  Map: {map_play.map_name}, Score: {map_play.team1_score}-{map_play.team2_score}, Winner: {map_play.winner_team_name}")
            print(f"    T1 Bans: {map_play.team1_operator_bans}")
            print(f"    T2 Bans: {map_play.team2_operator_bans}")
            print(f"    T1 Picks: {[op.name for op in map_play.team1_operator_picks_overall]}")
            print(f"    T2 Picks: {[op.name for op in map_play.team2_operator_picks_overall]}")
    else:
        print("Failed to parse sample match wikitext.")

    sample_team_wikitext = """
{{Infobox Team
|name=Team Secret
|image=Team Secret logo.png
|region=Europe
|p1={{Player|Slebben}}
|p2=[[ASTRO]]
|p3=Gruby
|p4role=Captain
|p4=jume
|p5=Savage
}}
"""
    logging.info("\\n--- Parsing Sample Team Wikitext ---")
    parsed_team_data = parser.parse_team_page("Team Secret", sample_team_wikitext)
    if parsed_team_data:
        print(f"Team: {parsed_team_data.name}, Region: {parsed_team_data.region}")
        print(f"Roster: {[player.name for player in parsed_team_data.roster] if parsed_team_data.roster else 'No roster found'}")
    else:
        print("Failed to parse sample team wikitext.")

    sample_operator_wikitext_attacker = """
{{Infobox Operator
|name=Ash
|side=Attacker
}}
[[Category:Attack operators]]
"""
    logging.info("\\n--- Parsing Sample Operator Wikitext (Ash) ---")
    parsed_op_data_ash = parser.parse_operator_page("Ash", sample_operator_wikitext_attacker)
    if parsed_op_data_ash:
        print(f"Operator: {parsed_op_data_ash.name}, Side: {parsed_op_data_ash.side}")

    print("\\nWikitextParser module implementation with basic functions and examples.")
