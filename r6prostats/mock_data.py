from .parser_models import Team, Operator, MapPlay, MatchData

# --- Mock Data Definitions ---

# Teams
g2 = Team(name="G2 Esports", region="EU")
faze = Team(name="FaZe Clan", region="LATAM")
ssg = Team(name="SSG", region="NA")
secret = Team(name="Team Secret", region="EU") # Adding for the "Secret" test case

# Operators (simplified)
thermite = Operator(name="Thermite", side="Attacker")
hibana = Operator(name="Hibana", side="Attacker")
ace = Operator(name="Ace", side="Attacker")
thatcher = Operator(name="Thatcher", side="Attacker")
sledge = Operator(name="Sledge", side="Attacker")
buck = Operator(name="Buck", side="Attacker")
zofia = Operator(name="Zofia", side="Attacker")
flores = Operator(name="Flores", side="Attacker")
gridlock = Operator(name="Gridlock", side="Attacker")
nomad = Operator(name="Nomad", side="Attacker")
iana = Operator(name="Iana", side="Attacker")
zero = Operator(name="Zero", side="Attacker")
osa = Operator(name="Osa", side="Attacker")
capitao = Operator(name="Capitao", side="Attacker") # Corrected from Capitão for consistency if not normalized yet
ying = Operator(name="Ying", side="Attacker")


kaid = Operator(name="Kaid", side="Defender")
mira = Operator(name="Mira", side="Defender")
smoke = Operator(name="Smoke", side="Defender")
mute = Operator(name="Mute", side="Defender")
jager = Operator(name="Jäger", side="Defender") # Corrected to Jäger
valkyrie = Operator(name="Valkyrie", side="Defender")
kapkan = Operator(name="Kapkan", side="Defender")
warden = Operator(name="Warden", side="Defender")
aruni = Operator(name="Aruni", side="Defender")
lesion = Operator(name="Lesion", side="Defender")
melusi = Operator(name="Melusi", side="Defender")
wamai = Operator(name="Wamai", side="Defender")
azami = Operator(name="Azami", side="Defender")
solis = Operator(name="Solis", side="Defender")


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
    match_id="match1_g2_vs_faze", team1=g2, team2=faze, team1_score=1, team2_score=1, # Maps won
    maps_played=[match1_map1, match1_map2], tournament_name="Test Tournament 1", date="2023-01-15"
)

# Match 2: G2 vs SSG
match2_map1 = MapPlay(
    map_name="Oregon", winner_team_name="G2 Esports", team1_score=7, team2_score=3,
    team1_operator_bans=["Kaid", "Smoke"], team2_operator_bans=["Ace", "Thermite"],
    team1_operator_picks_overall=[hibana, thatcher, mute, jager, valkyrie], # G2's picks
    team2_operator_picks_overall=[ace, thermite, mira, smoke, kaid] # SSG's picks
)
match2 = MatchData(
    match_id="match2_g2_vs_ssg", team1=g2, team2=ssg, team1_score=1, team2_score=0,
    maps_played=[match2_map1], tournament_name="Test Tournament 2", date="2023-01-20"
)

# Match 3: FaZe vs SSG
match3_map1 = MapPlay(
    map_name="Clubhouse", winner_team_name="FaZe Clan", team1_score=7, team2_score=4,
    team1_operator_bans=["Thermite", "Kaid"], team2_operator_bans=["Thatcher", "Mira"],
    team1_operator_picks_overall=[ace, hibana, smoke, mute, jager], # FaZe's picks
    team2_operator_picks_overall=[thermite, thatcher, valkyrie, kaid, mira]  # SSG's picks
)
match3 = MatchData(
    match_id="match3_faze_vs_ssg", team1=faze, team2=ssg, team1_score=1, team2_score=0,
    maps_played=[match3_map1], tournament_name="Test Tournament 3", date="2023-01-25"
)

# Match 4: Secret vs G2 (Secret wins)
match4_map1 = MapPlay(
    map_name="Kafe Dostoyevsky", winner_team_name="Team Secret", team1_score=7, team2_score=5,
    team1_operator_bans=["Nomad", "Valkyrie"], team2_operator_bans=["Thatcher", "Kaid"],
    team1_operator_picks_overall=[ace, zofia, mute, smoke, jager], # Secret's picks
    team2_operator_picks_overall=[thermite, hibana, valkyrie, mira, wamai]  # G2's picks
)
match4 = MatchData(
    match_id="match4_secret_vs_g2", team1=secret, team2=g2, team1_score=1, team2_score=0, # Secret wins the match
    maps_played=[match4_map1], tournament_name="Test Tournament 4", date="2023-02-01"
)


ALL_MOCK_MATCHES = [match1, match2, match3, match4]

# You can add more mock data here as needed for testing different scenarios.
# For example, matches involving "Team Secret" if you want to test `teamstats "Secret"`

if __name__ == '__main__':
    # This block is just for verifying the mock data itself if you run this file directly.
    print(f"Loaded {len(ALL_MOCK_MATCHES)} mock matches.")
    for m in ALL_MOCK_MATCHES:
        print(f"Match: {m.match_id}, {m.team1.name} vs {m.team2.name}, Score: {m.team1_score}-{m.team2_score}")
        for mp in m.maps_played:
            print(f"  Map: {mp.map_name}, Score: {mp.team1_score}-{mp.team2_score}, Winner: {mp.winner_team_name}")
            print(f"    T1 Picks: {[op.name for op in mp.team1_operator_picks_overall]}")
            print(f"    T2 Picks: {[op.name for op in mp.team2_operator_picks_overall]}")
            print(f"    T1 Bans: {mp.team1_operator_bans}")
            print(f"    T2 Bans: {mp.team2_operator_bans}")
        print("-" * 10)
