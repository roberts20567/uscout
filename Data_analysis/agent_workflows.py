import time
import json
import re
import firebase_admin
from firebase_admin import credentials, firestore
from crewai import Task, Crew
# Import the initialized agents
from crew_scouting import agent_a_sentinel, agent_b_gm, agent_c_tactician, agent_d_matchmaker

# --- INITIALIZATION ---
try:
    cred = credentials.Certificate('../firebase_cred.json')
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"Error initializing Firebase: {e}")


# --- UTILS ---
def extract_json_from_text(text):
    """Helper to extract a JSON dictionary from an LLM output string."""
    # 1. Try to extract specifically from a markdown JSON block
    md_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL | re.IGNORECASE)
    if md_match:
        try: return json.loads(md_match.group(1))
        except: pass
        
    # 2. Fallback to grabbing everything from the first { to the last }
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try: return json.loads(match.group(0))
        except Exception as e: print(f"   [!] JSON parsing error: {e}")
    return {}


# --- MATH & SYNERGY RECALCULATION ROUTINE ---
def recalculate_player(doc_ref, player_data, new_deficit=None, new_comp_factor=None):
    """
    Triggered whenever base stats, news, or squad deficits change.
    Recalculates Dynamic Rating and Synergy Score using the core formulas.
    """
    bpi = float(player_data.get('base_bpi', 0.0))
    fit = float(player_data.get('fit_rating', 0.0))
    delta_news = float(player_data.get('delta_news', 0.0))
    comp_factor = float(new_comp_factor) if new_comp_factor is not None else float(player_data.get('complementary_factor', 1.0))
    
    # Determine the current urgency (use updated one if provided, else current)
    urgency = float(new_deficit) if new_deficit is not None else float(player_data.get('squad_deficit_urgency', 0.5))

    # Formula 1: Rdyn = (BPI) + Δnews + Fit Rating
    dynamic_rating = max(0.0, bpi + delta_news + fit)
    
    # Formula 2: Ssyn = (Rdyn * Deficit) * CompFactor
    synergy_score = (dynamic_rating * urgency) * comp_factor
    
    # Trend Indicator Logic
    trend = "STABLE"
    if delta_news > 5.0: 
        trend = "RISING"
    elif delta_news < -5.0: 
        trend = "FALLING"

    # CRITICAL: Check if values actually changed to prevent infinite loops with the Firestore listener
    current_dr = round(float(player_data.get('dynamic_rating', 0.0)), 2)
    current_ss = round(float(player_data.get('synergy_score', 0.0)), 2)
    new_dr = round(dynamic_rating, 2)
    new_ss = round(synergy_score, 2)

    if current_dr != new_dr or current_ss != new_ss:
        doc_ref.update({
            "dynamic_rating": new_dr,
            "squad_deficit_urgency": urgency,
            "synergy_score": new_ss,
            "trend_indicator": trend
        })
        print(f"   [Recalculation] Updated {player_data.get('name', 'Unknown')}: Rdyn: {new_dr} | Ssyn: {new_ss}")


def squad_needs_listener(col_snapshot, changes, read_time):
    """
    Listener attached to the 'squad_deficits' config document.
    When Agent B pushes a change to the team's needs, recalculate scores.
    """
    print("\n[EVENT] Squad Deficit Map changed! Recalculating prospects.")
    for change in changes:
        if change.type.name in ['ADDED', 'MODIFIED']:
            deficits = change.document.to_dict()
            
            # Stream all players and update those affected by the new deficit priorities
            players_ref = db.collection('u_dynamic_shadow_prospects')
            for player_doc in players_ref.stream():
                p_data = player_doc.to_dict()
                pos = p_data.get('position', 'UNKNOWN')
                
                # Map specific developer_name position to general keys
                gen_pos = "UNKNOWN"
                if "GOALKEEPER" in pos: gen_pos = "GOALKEEPER"
                elif "FULLBACK" in pos or "WINGBACK" in pos: gen_pos = "FULLBACK"
                elif "CENTER_BACK" in pos or "DEFENDER" in pos: gen_pos = "CENTER_BACK"
                elif "MIDFIELDER" in pos: gen_pos = "MIDFIELDER"
                elif "WINGER" in pos: gen_pos = "WINGER"
                elif "ATTACKER" in pos or "STRIKER" in pos: gen_pos = "ATTACKER"

                # Only recalculate if the deficit for their position changed
                new_def = deficits.get(gen_pos)
                if new_def is not None and new_def != p_data.get('squad_deficit_urgency'):
                    recalculate_player(player_doc.reference, p_data, new_deficit=new_def)


# --- AGENT A: THE SENTINEL (News & Sentiment Injector) ---
def agent_a_inject_news(player_id, news_text):
    """Uses CrewAI to process raw text and replace the quantitative Δ in the DB."""
    print(f"\n[Agent A: Sentinel] Analyzing news for ID {player_id}: '{news_text}'")
    
    doc_ref = db.collection('u_dynamic_shadow_prospects').document(str(player_id))
    doc = doc_ref.get()
    
    if not doc.exists:
        print(f"   [!] Player ID {player_id} not found in database.")
        return
        
    p_data = doc.to_dict()
    player_name = p_data.get("name", f"Player {player_id}")
    
    task = Task(
        description=f"""
        Analyze the following news text about player {player_name}:
        '{news_text}'
        Determine the 'delta_news' impact on his dynamic rating (scale -15.0 to +15.0).
        Output ONLY a JSON containing 'delta_news' (float) and 'reasoning' (string).""",
        expected_output="JSON object with 'delta_news' and 'reasoning'",
        agent=agent_a_sentinel
    )
    
    crew = Crew(agents=[agent_a_sentinel], tasks=[task], verbose=False)
    result = crew.kickoff()
    
    parsed = extract_json_from_text(str(result))
    sentiment_delta = float(parsed.get('delta_news', 0.0))
    reasoning = parsed.get('reasoning', 'No reasoning provided.')
    
    print(f"   -> LLM Reasoned Sentiment Δ: {sentiment_delta} ({reasoning})")
    doc_ref.update({
        "delta_news": sentiment_delta,
        "reason": reasoning
    })
    print(f"   -> Successfully replaced delta_news for {player_name} in the database.")


# --- AGENT B: THE AUDITOR (GM Injector) ---
def agent_b_process_match_file(match_json_path):
    """
    Parses a match JSON file, updates individual player stats (key_stats_used) in Firestore,
    and uses Agent B to evaluate the new squad deficits based on the match result.
    """
    print(f"\n[Agent B & C: GM & Tactician] Initiating post-match evaluation from {match_json_path}...")
    
    try:
        with open(match_json_path, "r", encoding="utf-8") as f:
            match_data = json.load(f)
    except Exception as e:
        print(f"Error reading match file: {e}")
        return
        
    match_name = match_data.get("name", "Wyscout Match Data")
    match_result_stats = {"score": match_name}
    individual_match_stats = {}

    # 1. Extract player stats from the Wyscout JSON structure
    for player in match_data.get("players", []):
        pid = player.get("playerId")
        if not pid: continue
        
        # Sidenote mapping: U Cluj player IDs start with 'U'
        db_pid = f"U{pid}"
        
        total = player.get("total", {})
        percent = player.get("percent", {})
        p_stats = {}

        # Map Wyscout 'total' fields to your exact DB field names
        stat_mapping_total = {
            "goals": "Goals", "assists": "Assists", "shotsOnTarget": "Shots On Target",
            "shotsBlocked": "Shots Blocked", "shots": "Shots Total",
            "successfulPasses": "Accurate Passes", "passesToFinalThird": "Passes In Final Third",
            "passes": "Passes", "longPasses": "Long Balls", "throughPasses": "Through Balls",
            "successfulCrosses": "Accurate Crosses", "crosses": "Total Crosses",
            "aerialDuelsWon": "Aerials Won", "aerialDuels": "Aerials",
            "duelsWon": "Duels Won", "duels": "Total Duels",
            "interceptions": "Interceptions", "clearances": "Clearances",
            "successfulDribbles": "Successful Dribbles", "dribbles": "Dribble Attempts",
            "keyPasses": "Key Passes", "recoveries": "Ball Recovery", "losses": "Possession Lost",
            "gkSaves": "Saves", "gkCleanSheets": "Cleansheets",
            "yellowCards": "Yellowcards", "redCards": "Redcards", "fouls": "Fouls",
            "minutesOnField": "Minutes Played", "offsides": "Offsides"
        }

        # Map Wyscout 'percent' fields to DB percentages
        stat_mapping_percent = {
            "successfulPasses": "Accurate Passes Percentage",
            "successfulCrosses": "Successful Crosses Percentage",
            "aerialDuelsWon": "Aerials Won Percentage",
            "duelsWon": "Duels Won Percentage"
        }

        # Extract available mapped stats
        for ws_key, db_key in stat_mapping_total.items():
            if ws_key in total: p_stats[db_key] = float(total[ws_key])
        for ws_key, db_key in stat_mapping_percent.items():
            if ws_key in percent: p_stats[db_key] = float(percent[ws_key])

        # Calculate missing derived stats
        if "aerialDuels" in total and "aerialDuelsWon" in total:
            p_stats["Aerials Lost"] = float(total["aerialDuels"] - total["aerialDuelsWon"])
        if "duels" in total and "duelsWon" in total:
            p_stats["Duels Lost"] = float(total["duels"] - total["duelsWon"])

        if p_stats:
            individual_match_stats[db_pid] = p_stats

    # 2. Update the database 'key_stats_used' for each player
    if individual_match_stats:
        print(f"   -> Updating key_stats_used for {len(individual_match_stats)} players...")
        batch = db.batch()
        for pid, stats in individual_match_stats.items():
            match_mins = stats.get("Minutes Played", 0.0)
            if match_mins <= 0:
                continue  # Only process if the player actually played
                
            doc_ref = db.collection('u_players_calculated').document(str(pid))
            doc = doc_ref.get()
            
            if doc.exists:
                db_data = doc.to_dict()
                key_stats = db_data.get('key_stats_used', {})
                
                old_mins = key_stats.get("Minutes Played", 0.0)
                old_ninety_s = max(3.0, old_mins / 90.0)
                
                new_mins = old_mins + match_mins
                new_ninety_s = max(3.0, new_mins / 90.0)
                
                nested_update = {}
                
                # 1. Update existing stats in DB (Un-normalize -> Add -> Re-normalize)
                for stat, old_val in key_stats.items():
                    is_flat_stat = "Percentage" in stat or "Rating" in stat or stat in ["Minutes Played", "Appearances", "Lineups"]
                    
                    if stat == "Minutes Played":
                        nested_update[f"key_stats_used.{stat}"] = new_mins
                    elif stat == "Appearances":
                        nested_update[f"key_stats_used.{stat}"] = old_val + 1
                    elif is_flat_stat:
                        # Flat stats like percentages are averaged
                        if stat in stats:
                            nested_update[f"key_stats_used.{stat}"] = round((old_val + stats[stat]) / 2, 2)
                    else:
                        # Volume stats: reverse per-90, add new match raw volume, apply new per-90
                        raw_old = old_val * old_ninety_s
                        raw_match = stats.get(stat, 0.0)
                        raw_new = raw_old + raw_match
                        nested_update[f"key_stats_used.{stat}"] = round(raw_new / new_ninety_s, 2)
                        
                # 2. Add brand new stats from this match that weren't tracked in the DB yet
                for stat, match_val in stats.items():
                    if f"key_stats_used.{stat}" not in nested_update and stat not in key_stats:
                        is_flat_stat = "Percentage" in stat or "Rating" in stat or stat in ["Minutes Played", "Appearances", "Lineups"]
                        if is_flat_stat:
                            nested_update[f"key_stats_used.{stat}"] = round(match_val, 2)
                        else:
                            nested_update[f"key_stats_used.{stat}"] = round(match_val / new_ninety_s, 2)

                if nested_update:
                    batch.update(doc_ref, nested_update)
                    
        try:
            batch.commit()
            print("   -> Stats updated successfully! Cloud Functions will auto-recalculate ratings.")
        except Exception as e:
            print(f"   -> [!] Error updating player stats (Document might not exist): {e}")

    # 3. Prepare Tasks for Agent B and Agent C
    task_desc_b = f"""
    U Cluj just finished a match: {match_name}. 
    Match Result Stats: {json.dumps(match_result_stats)}
    Individual Player Match Stats: {json.dumps(individual_match_stats)}
    
    Based on the match result and how the individual players performed, evaluate the team's weaknesses.
    Output ONLY a JSON with ONE key:
    'squad_deficits': A map of positions ("GOALKEEPER", "FULLBACK", "CENTER_BACK", "MIDFIELDER", "WINGER", "ATTACKER") to an urgency float (0.0 to 1.0).
    Example:
    {{
        "squad_deficits": {{"CENTER_BACK": 0.90, "ATTACKER": 0.40}}
    }}
    """
    
    task_b = Task(
        description=task_desc_b,
        expected_output="JSON object with 'squad_deficits'.",
        agent=agent_b_gm
    )
    
    task_desc_c = f"""
    U Cluj just finished a match: {match_name}. 
    Match Result Stats: {json.dumps(match_result_stats)}
    Individual Player Match Stats: {json.dumps(individual_match_stats)}
    
    Based on these match stats, evaluate the specific statistical areas where the team failed.
    Output ONLY a JSON boolean map representing TEAM_WORST_STATS. Set failed areas to true and good areas to false.
    You MUST ONLY use the following exact keys in your JSON:
    "Saves", "Saves Insidebox", "Cleansheets", "Accurate Passes Percentage", "Accurate Passes", "Long Balls Won", "Clearances", "Duels Won Percentage", "Interceptions", "Ball Recovery", "Passes In Final Third", "Successful Crosses Percentage", "Accurate Crosses", "Successful Dribbles", "Key Passes", "Chances Created", "Shots Blocked", "Shots On Target", "Aerials Won Percentage", "Tacles Won Percentage", "Tackles Won Percentage".
    Example: {{"Aerials Won Percentage": true, "Saves": false}}
    """
    
    task_c = Task(
        description=task_desc_c,
        expected_output="JSON boolean map of stats.",
        agent=agent_c_tactician
    )
    
    crew = Crew(agents=[agent_b_gm, agent_c_tactician], tasks=[task_b, task_c], verbose=False)
    result = crew.kickoff()
    
    squad_deficits_parsed = extract_json_from_text(str(task_b.output))
    squad_deficits = squad_deficits_parsed.get("squad_deficits", squad_deficits_parsed)
    
    team_worst_stats = extract_json_from_text(str(task_c.output))
    
    if squad_deficits:
        print(f"   -> Pushing new Deficit Map: {squad_deficits}")
        db.collection('u_config').document('squad_deficits').set(squad_deficits, merge=True)
        
    if team_worst_stats:
        print(f"   -> Pushing new Worst Stats Map: {team_worst_stats}")
        db.collection('u_config').document('team_worst_stats').set(team_worst_stats, merge=True)


# --- AGENT D: THE MATCHMAKER ---
def agent_d_worst_stats_listener(col_snapshot, changes, read_time):
    """
    When Agent C updates TEAM_WORST_STATS, Agent D evaluates ONLY shortlisted prospects 
    to modify their complementary_factor. This avoids processing 10,000 records.
    """
    for change in changes:
        if change.type.name in ['MODIFIED', 'ADDED']:
            worst_stats = change.document.to_dict()
            
            # Guardrail: Check if there are actually any true weaknesses flagged
            if not any(worst_stats.values()):
                print("\n[Agent D: Matchmaker] TEAM_WORST_STATS updated, but no weaknesses found (all False). Skipping matchmaking.")
                continue
                
            print("\n[Agent D: Matchmaker] TEAM_WORST_STATS updated! Fetching highly rated shortlist...")
            
            # OPTIMIZATION: Only evaluate players who are currently decent (e.g. Dynamic Rating >= 70)
            shortlist_ref = db.collection('u_dynamic_shadow_prospects').where('dynamic_rating', '>=', 70.0).limit(6)
            
            for player_doc in shortlist_ref.stream():
                p_data = player_doc.to_dict()
                name = p_data.get('name')
                stats = p_data.get('key_stats_used', {})
                
                # Agent D analyzes if the player's stats solve the team's worst stats
                task_d = Task(
                    description=f"""
                    U Cluj's current worst stats are: {worst_stats}
                    Prospect {name} has these stats: {stats}
                    If {name} excels in the areas where U Cluj is currently weak (true values), 
                    output ONLY a JSON with a 'complementary_factor' float (between 1.0 and 1.5) and a 'reason' string explaining the tactical fit.
                    Example: {{"complementary_factor": 1.25, "reason": "Excellent aerial duel win rate addresses the team's weakness."}}""",
                    expected_output="JSON with complementary_factor float and reason string.",
                    agent=agent_d_matchmaker
                )
                crew_d = Crew(agents=[agent_d_matchmaker], tasks=[task_d], verbose=False)
                res = crew_d.kickoff()
                
                parsed_res = extract_json_from_text(str(res))
                new_cf = float(parsed_res.get('complementary_factor', 1.0))
                reasoning = parsed_res.get('reason', 'No reasoning provided.')
                
                print(f"   -> Agent D assigned CF: {new_cf} to {name} ({reasoning})")
                
                # Update the database. This inherently triggers the recalculation listener.
                player_doc.reference.update({
                    'complementary_factor': new_cf,
                    'reason': reasoning
                })


# --- SCENARIO INJECTOR FOR HACKATHON PRESENTATION ---
if __name__ == "__main__":
    # 1. Agent C watches the Deficit Map for ripple-effect adjustments
    config_ref = db.collection('u_config').document('squad_deficits')
    config_watch = config_ref.on_snapshot(squad_needs_listener)
    
    # 2. Agent D watches TEAM_WORST_STATS to trigger the Matchmaker
    worst_stats_ref = db.collection('u_config').document('team_worst_stats')
    worst_stats_watch = worst_stats_ref.on_snapshot(agent_d_worst_stats_listener)
    
    print("Event-Driven Cloud Workflows initialized and listening to Firestore...")
    
    # Keep the daemon running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down AI Scouting Agents.")