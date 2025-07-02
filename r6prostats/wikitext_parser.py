import mwparserfromhell
import re
import logging
from typing import Optional, List, Dict
from .parser_models import MatchData, Team, Player, MapPlay, Operator, MapPickBan

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Known aliases or common variations for operator names
OPERATOR_ALIASES = {
    "jager": "Jäger",
    "capitao": "Capitão",
    "caveira": "Caveira",
    "hibana": "Hibana",
    "echo": "Echo",
    "ying": "Ying",
    "ela": "Ela",
    "dokkaebi": "Dokkaebi",
    "vigil": "Vigil",
    "lion": "Lion",
    "finka": "Finka",
    "maestro": "Maestro",
    "clash": "Clash",
    "kaid": "Kaid",
    "mozzie": "Mozzie",
    "nokk": "Nøkk",
    "warden": "Warden",
    "goyo": "Goyo",
    "amaru": "Amaru",
    "kali": "Kali",
    "oryx": "Oryx",
    "iana": "Iana",
    "melusi": "Melusi",
    "ace": "Ace",
    "zero": "Zero",
    "aruni": "Aruni",
    "flores": "Flores",
    "thunderbird": "Thunderbird",
    "osa": "Osa",
    "thorn": "Thorn",
    "azami": "Azami",
    "sens": "Sens",
    "grim": "Grim",
    "solis": "Solis",
    "brava": "Brava",
    "fenrir": "Fenrir",
    "ram": "Ram",
    # Add more as needed
}

def normalize_operator_name(name: str) -> str:
    name = name.strip().lower()
    name = OPERATOR_ALIASES.get(name, name.capitalize())
    # Further specific normalizations if an op has multiple common display names
    if name == "Smoke": return "Smoke" # Ensure correct capitalization if it was 'smoke'
    if name == "Mute": return "Mute"
    # ... etc for all original operators if needed, though capitalize should handle most
    return name

class WikitextParser:
    """
    Parses raw wikitext from Liquipedia pages to extract structured data,
    primarily focusing on match details.
    """

    def __init__(self):
        pass

    def _extract_template_param(self, template, param_name: str, default: Optional[str] = None) -> Optional[str]:
        """Helper to get a parameter value from a mwparserfromhell template."""
        if template.has(param_name):
            return str(template.get(param_name).value).strip()
        return default

    def _extract_team_name(self, template, param_prefix: str) -> str:
        """Extracts team name, checking for {{TeamLink}} or direct name."""
        name_param = f"{param_prefix}name"
        if template.has(name_param):
            value = template.get(name_param).value
            # Check if the value itself is a template (e.g., {{TeamLink|G2 Esports}})
            nested_templates = value.filter_templates()
            if nested_templates and (nested_templates[0].name.matches("TeamLink") or nested_templates[0].name.matches("tl")):
                if nested_templates[0].has(1):
                    return str(nested_templates[0].get(1).value).strip()
            return str(value).strip() # Direct name

        # Fallback for some older or different template structures if team name is directly in param like 'team1' or 'team2'
        # This is less common for structured match templates but good to be aware of.
        # if template.has(param_prefix): # e.g. param_prefix = 'team1'
        #     value = template.get(param_prefix).value
        #     # ... similar logic to check for TeamLink ...
        #     return str(value).strip()

        return "Unknown Team"


    def parse_match_page(self, page_title: str, wikitext: str) -> Optional[MatchData]:
        """
        Parses the wikitext of a match page (typically a subpage of a tournament).
        This is a complex task as template usage can vary.
        We'll start by looking for common templates like {{MatchRecap}} or {{MatchMaps}}.
        """
        logging.info(f"Starting to parse match page: {page_title}")
        parsed_wikitext = mwparserfromhell.parse(wikitext)

        # Try to find general match information first (teams, date, tournament)
        # This might be in a {{MatchRecap}}, {{Infobox Match}}, or similar
        # For now, let's assume primary data is within a {{MatchMaps}} or similar detailed template
        # Or it could be that team names are passed as arguments or inferred from page context.

        team1_name = "Team A (Placeholder)" # Placeholder, to be found
        team2_name = "Team B (Placeholder)" # Placeholder
        tournament_name_from_page = page_title.split('/')[0] if '/' in page_title else page_title # Basic inference

        # Attempt to find {{MatchSchedule}} or {{MatchRecap}} for overall scores and team names
        # This part is highly dependent on Liquipedia's specific templates for R6
        # For example, {{MatchMaps}} template seems to be a common one.

        match_summary_template = None
        # Look for templates that define the match participants and overall score.
        # Common names could be MatchSummary, Infobox Match, BracketMatch, etc.
        # This will require inspection of actual Liquipedia R6 pages.
        # For now, we'll try to extract from something like MatchMaps or assume they are known.

        # Let's assume we find a template that gives us the main teams.
        # Example: {{SomeMatchOverview |team1=G2 Esports |team2=FaZe Clan |tournament=Six Invitational 2023}}
        # This is hypothetical. The real structure will be based on `test_data/six_invitational_2023_match.txt`

        # Try to find {{MatchSeries}} or {{MatchMaps}} which often contains detailed per-map info
        # In R6, {{MatchMaps}} is very common for detailed results.
        match_maps_templates = parsed_wikitext.filter_templates(matches=lambda t: t.name.matches("MatchMaps") or t.name.matches("MatchResults"))

        if not match_maps_templates:
            logging.warning(f"No {{MatchMaps}} or {{MatchResults}} template found on page {page_title}. Cannot parse detailed match data yet.")
            # We might still be able to get some info if other templates exist.
            # For now, return None if this critical template is missing.
            return None

        # Assuming the first MatchMaps template is the primary one for the match
        # This might need adjustment if multiple such templates exist for different stages
        match_template = match_maps_templates[0]

        team1_name = self._extract_template_param(match_template, "team1", "Team 1")
        team2_name = self._extract_template_param(match_template, "team2", "Team 2")

        # Extracting overall scores (maps won)
        team1_score_overall = int(self._extract_template_param(match_template, "team1score", "0") or "0")
        team2_score_overall = int(self._extract_template_param(match_template, "team2score", "0") or "0")

        date_str = self._extract_template_param(match_template, "date")

        winner_team_name = None
        if team1_score_overall > team2_score_overall:
            winner_team_name = team1_name
        elif team2_score_overall > team1_score_overall:
            winner_team_name = team2_name

        match_data = MatchData(
            match_id=page_title,
            team1=Team(name=team1_name),
            team2=Team(name=team2_name),
            team1_score=team1_score_overall,
            team2_score=team2_score_overall,
            winner_team_name=winner_team_name,
            date=date_str,
            tournament_name=self._extract_template_param(match_template, "tournament", tournament_name_from_page),
            raw_wikitext=wikitext,
            source_url=f"https://liquipedia.net/rainbowsix/{page_title.replace(' ', '_')}"
        )

        # --- Parse Map Picks and Bans (if available in MatchMaps header) ---
        # Example: {{MatchMaps|map1pick=TeamA|map1=Oregon|map2ban=TeamB|map2=Kafe...}}
        # This is highly speculative and depends on the exact template params used.
        # For now, we'll focus on per-map details often found in sub-templates.

        # --- Parse individual maps played ---
        # {{MatchMaps}} usually has map1, map2, ... parameters which themselves can be templates
        # like {{MapRecap}} or direct data.
        # Or, it might use parameters like |map1map=Oregon |map1team1score=7 |map1team2score=5 ...

        i = 1
        while True:
            map_param_name = f"map{i}"
            if not match_template.has(map_param_name):
                # Some templates might use map1map, map2map etc. directly if not nested
                map_name_direct = self._extract_template_param(match_template, f"map{i}map")
                if not map_name_direct:
                    break # No more maps

                # This is a simplified path if map data is flat in MatchMaps
                map_play = MapPlay(map_name=map_name_direct)
                map_play.team1_score = int(self._extract_template_param(match_template, f"map{i}team1score", "0") or "0")
                map_play.team2_score = int(self._extract_template_param(match_template, f"map{i}team2score", "0") or "0")

                # Winner of this specific map
                if map_play.team1_score > map_play.team2_score:
                    map_play.winner_team_name = team1_name
                elif map_play.team2_score > map_play.team1_score:
                    map_play.winner_team_name = team2_name

                # Operator bans for this map (highly specific to template structure)
                # Example: map1team1ban1, map1team1ban2, map1team2ban1, map1team2ban2
                for ban_idx in range(1, 6): # Assuming up to 5 bans per team, usually 2-3
                    t1_ban = self._extract_template_param(match_template, f"map{i}team1ban{ban_idx}")
                    if t1_ban: map_play.team1_operator_bans.append(normalize_operator_name(t1_ban))
                    t2_ban = self._extract_template_param(match_template, f"map{i}team2ban{ban_idx}")
                    if t2_ban: map_play.team2_operator_bans.append(normalize_operator_name(t2_ban))

                # Operator picks for this map (even more specific)
                # Example: map1team1op1, map1team1op2, ..., map1team2op1, ...
                # This is a very simplified model. Real R6 templates might have attack/defense phase ops.
                for op_idx in range(1, 6): # 5 operators per team
                    t1_op = self._extract_template_param(match_template, f"map{i}team1op{op_idx}")
                    if t1_op: map_play.team1_operator_picks_overall.append(Operator(name=normalize_operator_name(t1_op)))
                    t2_op = self._extract_template_param(match_template, f"map{i}team2op{op_idx}")
                    if t2_op: map_play.team2_operator_picks_overall.append(Operator(name=normalize_operator_name(t2_op)))

                if map_play.map_name and map_play.map_name.lower() != "none" and map_play.map_name.lower() != "tbd":
                     match_data.maps_played.append(map_play)

            else: # map_param_name exists, likely means it contains a nested template like {{Map}} or {{MapRecap}}
                map_details_node = match_template.get(map_param_name).value

                # Check if map_details_node is itself a template
                map_sub_templates = map_details_node.filter_templates()

                if not map_sub_templates:
                    # Sometimes map name is directly there, and scores are separate
                    # e.g. map1=Oregon, map1score=7-5
                    map_name_val = str(map_details_node).strip()
                    if not map_name_val or map_name_val.lower() == "none" or map_name_val.lower() == "tbd":
                        i += 1
                        continue # Skip if map name is 'none' or 'tbd'

                    map_play = MapPlay(map_name=map_name_val)
                    score_str = self._extract_template_param(match_template, f"map{i}score") # e.g., "7-5"
                    if score_str and '-' in score_str:
                        s1, s2 = score_str.split('-', 1)
                        map_play.team1_score = int(s1.strip())
                        map_play.team2_score = int(s2.strip())
                    else: # Try individual scores
                         map_play.team1_score = int(self._extract_template_param(match_template, f"map{i}team1score", "0") or "0")
                         map_play.team2_score = int(self._extract_template_param(match_template, f"map{i}team2score", "0") or "0")


                    # Winner of this specific map
                    if map_play.team1_score > map_play.team2_score:
                        map_play.winner_team_name = team1_name
                    elif map_play.team2_score > map_play.team1_score:
                        map_play.winner_team_name = team2_name

                    # Operator bans and picks would follow similar logic as above, using map{i}teamXbanY etc.
                    for ban_idx in range(1, 6):
                        t1_ban = self._extract_template_param(match_template, f"map{i}team1ban{ban_idx}")
                        if t1_ban: map_play.team1_operator_bans.append(normalize_operator_name(t1_ban))
                        t2_ban = self._extract_template_param(match_template, f"map{i}team2ban{ban_idx}")
                        if t2_ban: map_play.team2_operator_bans.append(normalize_operator_name(t2_ban))

                    for op_idx in range(1, 6):
                        t1_op = self._extract_template_param(match_template, f"map{i}team1op{op_idx}")
                        if t1_op: map_play.team1_operator_picks_overall.append(Operator(name=normalize_operator_name(t1_op)))
                        t2_op = self._extract_template_param(match_template, f"map{i}team2op{op_idx}")
                        if t2_op: map_play.team2_operator_picks_overall.append(Operator(name=normalize_operator_name(t2_op)))

                    if map_play.map_name:
                         match_data.maps_played.append(map_play)

                else: # map_details_node contains sub-templates
                    # This is where we'd parse a {{MapRecapV2}} or similar template if Liquipedia R6 uses them
                    # For example: {{Map|map=Oregon|score=7-5|team1=G2|team2=FaZe|mapwin=1
                    #             |team1side=attack |team1score=4 |team2score=2
                    #             |team2side=attack |team1score2=3 |team2score2=3
                    #             |details={{OperatorLineup|...bans...|...picks...}}}}
                    # This structure is common in other Liquipedia games. R6 might differ.
                    # We need to inspect actual R6 match pages to confirm the sub-template structure.

                    # Let's assume a generic {{Map}} or {{MapRecapV2}} structure for now
                    # This part is highly illustrative and needs to be adapted based on real R6 templates
                    map_recap_template = map_sub_templates[0] # Assuming the first one is the main recap

                    map_name_from_sub = self._extract_template_param(map_recap_template, "map")
                    if not map_name_from_sub or map_name_from_sub.lower() == "none" or map_name_from_sub.lower() == "tbd":
                        i += 1
                        continue

                    map_play = MapPlay(map_name=map_name_from_sub)

                    # Scores from sub-template
                    map_play.team1_score = int(self._extract_template_param(map_recap_template, "team1score", "0") or "0")
                    map_play.team2_score = int(self._extract_template_param(map_recap_template, "team2score", "0") or "0")

                    # Fallback if only 'score=X-Y' is present in sub-template
                    if map_play.team1_score == 0 and map_play.team2_score == 0:
                        score_str_sub = self._extract_template_param(map_recap_template, "score")
                        if score_str_sub and '-' in score_str_sub:
                            s1, s2 = score_str_sub.split('-', 1)
                            map_play.team1_score = int(s1.strip())
                            map_play.team2_score = int(s2.strip())

                    if map_recap_template.has("mapwin"):
                        map_winner_flag = self._extract_template_param(map_recap_template, "mapwin")
                        if map_winner_flag == "1": map_play.winner_team_name = team1_name
                        elif map_winner_flag == "2": map_play.winner_team_name = team2_name
                    elif map_play.team1_score > map_play.team2_score:
                        map_play.winner_team_name = team1_name
                    elif map_play.team2_score > map_play.team1_score:
                        map_play.winner_team_name = team2_name

                    # Operator bans and picks from a nested {{OperatorLineup}} or similar
                    # This is the most complex part and requires deep inspection of R6 templates
                    details_template = map_recap_template.get("details").value.filter_templates() if map_recap_template.has("details") else []
                    if details_template and (details_template[0].name.matches("OperatorLineup") or details_template[0].name.matches("PickBan")):
                        op_lineup_tpl = details_template[0]
                        # Example params: team1ban1, team1ban2, team2ban1, team2ban2
                        # team1atk1, team1atk2,... team1def1, team1def2,... (if roles are split)
                        # Or simply team1op1, team1op2...
                        for ban_idx in range(1, 6): # Max 5 bans, usually 2-3
                            t1_b = self._extract_template_param(op_lineup_tpl, f"team1ban{ban_idx}")
                            if t1_b: map_play.team1_operator_bans.append(normalize_operator_name(t1_b))
                            t2_b = self._extract_template_param(op_lineup_tpl, f"team2ban{ban_idx}")
                            if t2_b: map_play.team2_operator_bans.append(normalize_operator_name(t2_b))

                        # Simplified picks for now
                        for op_idx in range(1, 6):
                            t1_op_sub = self._extract_template_param(op_lineup_tpl, f"team1op{op_idx}")
                            if t1_op_sub: map_play.team1_operator_picks_overall.append(Operator(name=normalize_operator_name(t1_op_sub)))
                            t2_op_sub = self._extract_template_param(op_lineup_tpl, f"team2op{op_idx}")
                            if t2_op_sub: map_play.team2_operator_picks_overall.append(Operator(name=normalize_operator_name(t2_op_sub)))

                        # A more detailed parsing would look for atk/def specific ops if template supports
                        # e.g. team1atk_op1 ... team1def_op1 ...

                    if map_play.map_name:
                        match_data.maps_played.append(map_play)
            i += 1
            if i > 10: # Safety break for while loop, usually max 5 maps Bo5
                logging.warning(f"Breaking map parsing loop after 10 iterations for {page_title}")
                break

        logging.info(f"Successfully parsed basic match data for {page_title}. Maps found: {len(match_data.maps_played)}")
        for m_idx, m_play in enumerate(match_data.maps_played):
            logging.debug(f"  Map {m_idx+1}: {m_play.map_name}, Score: {m_play.team1_score}-{m_play.team2_score}, Winner: {m_play.winner_team_name}")
            logging.debug(f"    T1 Bans: {m_play.team1_operator_bans}, T2 Bans: {m_play.team2_operator_bans}")
            logging.debug(f"    T1 Picks: {[op.name for op in m_play.team1_operator_picks_overall]}, T2 Picks: {[op.name for op in m_play.team2_operator_picks_overall]}")

        return match_data

    def parse_team_page(self, page_title: str, wikitext: str) -> Optional[Team]:
        """
        Parses a team page to extract roster, region, etc.
        Looks for templates like {{Infobox Team}}.
        """
        logging.info(f"Parsing team page: {page_title}")
        parsed_wikitext = mwparserfromhell.parse(wikitext)
        infobox_templates = parsed_wikitext.filter_templates(matches=lambda t: t.name.matches("Infobox Team"))

        if not infobox_templates:
            logging.warning(f"No {{Infobox Team}} template found on page {page_title}.")
            # Fallback: use page title as team name if no infobox
            return Team(name=page_title.replace("(team)", "").strip())


        infobox = infobox_templates[0]
        team_name = self._extract_template_param(infobox, "name", page_title)
        region = self._extract_template_param(infobox, "region")

        team = Team(name=team_name, region=region)

        # Roster parsing: often uses parameters like 'p1', 'p1link', 'p1flag' or {{Player|PlayerName}}
        # This is a simplified approach. Real roster sections can be complex (active, inactive, subs).
        for i in range(1, 8): # Assuming up to 7 players listed (p1 to p7)
            player_name_param = f"p{i}"
            player_role_param = f"p{i}role" # e.g., Captain, Sub

            if infobox.has(player_name_param):
                player_name_node = infobox.get(player_name_param).value
                player_name = ""

                # Check for {{Player|Name}} template
                player_templates = player_name_node.filter_templates(matches=lambda t: t.name.matches("Player"))
                if player_templates:
                    player_name = str(player_templates[0].get(1).value).strip()
                else:
                    # Direct name, might have wikilinks [[Player Name]] or [[Player Name|Display Name]]
                    wikilinks = player_name_node.filter_wikilinks()
                    if wikilinks:
                        player_name = str(wikilinks[0].title).strip()
                    else:
                        player_name = str(player_name_node).strip()

                if player_name:
                    team.roster.append(Player(name=player_name))

        # Alternative roster parsing if it's in a section like "==Roster==" with {{PlayerCard}}
        # This requires more advanced section parsing. For now, focusing on Infobox.

        logging.info(f"Parsed team: {team.name}, Region: {team.region}, Roster size: {len(team.roster)}")
        return team

    def parse_operator_page(self, page_title: str, wikitext: str) -> Optional[Operator]:
        """
        Parses an operator page. For now, mainly confirms name and extracts side (Attacker/Defender).
        """
        logging.info(f"Parsing operator page: {page_title}")
        parsed_wikitext = mwparserfromhell.parse(wikitext)

        # Look for {{Infobox Operator}}
        infobox_templates = parsed_wikitext.filter_templates(matches=lambda t: t.name.matches("Infobox Operator"))
        if not infobox_templates:
            logging.warning(f"No {{Infobox Operator}} found on {page_title}. Using page title as name.")
            # Basic inference for side based on common categories if no infobox
            side = None
            if "Category:Attack operators" in wikitext: side = "Attacker"
            elif "Category:Defense operators" in wikitext: side = "Defender"
            return Operator(name=normalize_operator_name(page_title), side=side)

        infobox = infobox_templates[0]
        op_name = self._extract_template_param(infobox, "name", page_title)
        op_name = normalize_operator_name(op_name)

        side_str = self._extract_template_param(infobox, "side")
        if side_str:
            side_str = side_str.lower()
            if "attack" in side_str: side = "Attacker"
            elif "defen" in side_str: side = "Defender" # defen for defense/defender
            else: side = None
        else: # Try to infer from categories within the page content
            if parsed_wikitext.filter_wikilinks(matches=lambda l: "Category:Attack operators" in str(l.title)):
                side = "Attacker"
            elif parsed_wikitext.filter_wikilinks(matches=lambda l: "Category:Defense operators" in str(l.title)):
                side = "Defender"
            else:
                side = None


        logging.info(f"Parsed operator: {op_name}, Side: {side}")
        return Operator(name=op_name, side=side)

    def parse_map_page(self, page_title: str, wikitext: str) -> Optional[Map]:
        """
        Parses a map page. For now, mainly confirms the name.
        """
        logging.info(f"Parsing map page: {page_title}")
        # Usually map pages are simpler, {{Infobox Map}} might exist
        # For now, just use the page title as the map name
        map_name = page_title.split('/')[-1] # In case of subpages like "Maps/Oregon"

        # Could look for {{Infobox Map}} and extract 'name' param if it exists
        # parsed_wikitext = mwparserfromhell.parse(wikitext)
        # infobox_map = parsed_wikitext.filter_templates(matches=lambda t: t.name.matches("Infobox Map"))
        # if infobox_map:
        #     map_name = self._extract_template_param(infobox_map[0], "name", map_name)

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
    logging.info("\n--- Parsing Sample Match Wikitext ---")
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
|name=G2 Esports
|image=G2 Esports.png
|region=Europe
|p1={{Player|Kantoraketti}}
|p2=[[Benja]]
|p3=Alem4o
|p4role=Captain
|p4=Virtue
|p5=Doki
}}
"""
    logging.info("\n--- Parsing Sample Team Wikitext ---")
    parsed_team_data = parser.parse_team_page("G2 Esports", sample_team_wikitext)
    if parsed_team_data:
        print(f"Team: {parsed_team_data.name}, Region: {parsed_team_data.region}")
        print(f"Roster: {[player.name for player in parsed_team_data.roster]}")
    else:
        print("Failed to parse sample team wikitext.")

    sample_operator_wikitext_attacker = """
{{Infobox Operator
|name=Ash
|side=Attacker
}}
[[Category:Attack operators]]
"""
    sample_operator_wikitext_defender = """
{{Infobox Operator
|name=Jäger
|side=Defender
}}
[[Category:Defense operators]]
"""
    logging.info("\n--- Parsing Sample Operator Wikitext (Ash) ---")
    parsed_op_data_ash = parser.parse_operator_page("Ash", sample_operator_wikitext_attacker)
    if parsed_op_data_ash:
        print(f"Operator: {parsed_op_data_ash.name}, Side: {parsed_op_data_ash.side}")

    logging.info("\n--- Parsing Sample Operator Wikitext (Jäger) ---")
    parsed_op_data_jager = parser.parse_operator_page("Jäger", sample_operator_wikitext_defender)
    if parsed_op_data_jager:
        print(f"Operator: {parsed_op_data_jager.name}, Side: {parsed_op_data_jager.side}")

    print("\nWikitextParser module implementation with basic functions and examples.")
