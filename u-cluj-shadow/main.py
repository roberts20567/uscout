import json
import os
import random
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. CONFIGURATION & U CLUJ TACTICAL PROFILES ---

# Deficit Map: G_gap (Squad Deficit Urgency by Position)
# Simulates Agent B: The "General Manager" output
SQUAD_DEFICIT_MAP = {
    "GOALKEEPER": 0.5,
    "FULLBACK": 0.5,
    "CENTER_BACK": 0.5,     # Urgent need! e.g., lost 3-0, bad aerial duels
    "MIDFIELDER": 0.5,
    "WINGER": 0.5,
    "ATTACKER": 0.5
}

# Team Weaknesses for Complementary Factor calculation
# Simulates Agent C's logic mapping prospect strengths to U Cluj weaknesses
TEAM_WORST_STATS = {
    "Saves": False,             # U Cluj's goalkeeping is shaky
    "Saves Insidebox": False,
    "Cleansheets": False,
    "Accurate Passes Percentage": False,
    "Accurate Passes": False,
    "Long Balls Won": False,
    "Clearances": False,
    "Duels Won Percentage": False,
    "Interceptions": False,
    "Ball Recovery": False,
    "Passes In Final Third": False,
    "Successful Crosses Percentage": False,
    "Accurate Crosses": False,
    "Successful Dribbles": False,
    "Key Passes": False,
    "Chances Created": False,
    "Shots Blocked": False,
    "Shots On Target": False,
    "Aerials Won Percentage": False,
    "Tacles Won Percentage": False,
    "Tackles Won Percentage": False,
}

def normalize_stat(value, max_expected):
    """Normalize a raw stat into a 0-100 scale."""
    if value is None:
        return 0
    return min(100.0, (float(value) / max_expected) * 100.0)

def calculate_bpi(position_code, stats_dict):
    """
    Calculate the Base Performance Index (BPI): ∑(Stat_i × Weight_i)
    """
    position_code = position_code.upper()
    
    # --- STRICT DATA COMPLETENESS CHECK ---
    required_stats = []
    if "GOALKEEPER" in position_code:
        required_stats = ["Saves", "Saves Insidebox", "Cleansheets", "Accurate Passes Percentage", "Accurate Passes", "Long Balls Won", "Clearances"]
    elif "FULLBACK" in position_code or "WINGBACK" in position_code:
        required_stats = ["Duels Won Percentage", "Interceptions", "Ball Recovery", "Accurate Passes Percentage", "Passes In Final Third", "Successful Crosses Percentage", "Accurate Crosses", "Successful Dribbles", "Key Passes"]
        # Handle typo variant gracefully for tackles
        if "Tacles Won Percentage" not in stats_dict and "Tackles Won Percentage" not in stats_dict:
            return None
    elif "CENTER_BACK" in position_code or "DEFENDER" in position_code:
        required_stats = ["Duels Won Percentage", "Aerials Won Percentage", "Clearances", "Interceptions", "Shots Blocked", "Accurate Passes Percentage", "Long Balls Won"]
    elif "MIDFIELDER" in position_code:
        required_stats = ["Accurate Passes Percentage", "Passes In Final Third", "Duels Won Percentage", "Ball Recovery", "Interceptions", "Key Passes", "Chances Created", "Successful Dribbles"]
    elif "WINGER" in position_code:
        required_stats = ["Successful Dribbles", "Chances Created", "Accurate Passes Percentage", "Successful Crosses Percentage", "Accurate Crosses", "Ball Recovery"]
    elif "ATTACKER" in position_code or "STRIKER" in position_code:
        required_stats = ["Shots On Target", "Aerials Won Percentage", "Duels Won Percentage", "Accurate Passes Percentage", "Key Passes"]
    else:
        required_stats = ["Accurate Passes Percentage", "Interceptions"]

    for stat in required_stats:
        if stat not in stats_dict:
            print(f"Missing required stat: {stat}")
            if (stat == "Aerials Won Percentage" and "Aerials Won" in stats_dict):
                stats_dict["Aerials Won Percentage"] = stats_dict["Aerials Won"]
            else:
                return None

    bpi = 0.0
    
    # Advanced Tactical Percentages (Default to 50 if missing)
    pass_acc = stats_dict.get("Accurate Passes Percentage", 50.0)
    tackle_win_pct = stats_dict.get("Tacles Won Percentage", stats_dict.get("Tackles Won Percentage", 50.0))
    duel_win_pct = stats_dict.get("Duels Won Percentage", 50.0)
    aerial_win_pct = stats_dict.get("Aerials Won Percentage", 50.0)
    cross_acc = stats_dict.get("Successful Crosses Percentage", 30.0)
    
    # Calculate 'Per 90' factor. Force minimum 3 full matches (270 mins) to prevent 
    # massive stat inflation for youth players who only played 10 minutes all season.
    ninety_s = max(3.0, stats_dict.get("Minutes Played", 0) / 90.0)

    # Volume metrics (Converted to Per 90 Minutes)
    goals = stats_dict.get("Goals", 0) / ninety_s
    assists = stats_dict.get("Assists", 0) / ninety_s
    interceptions = stats_dict.get("Interceptions", 0) / ninety_s
    clearances = stats_dict.get("Clearances", 0) / ninety_s
    ball_recovery = stats_dict.get("Ball Recovery", 0) / ninety_s
    key_passes = stats_dict.get("Key Passes", 0) / ninety_s
    chances_created = stats_dict.get("Chances Created", 0) / ninety_s
    dribbles = stats_dict.get("Successful Dribbles", 0) / ninety_s
    blocked_shots = stats_dict.get("Shots Blocked", 0) / ninety_s
    final_third_passes = stats_dict.get("Passes In Final Third", 0) / ninety_s
    accurate_crosses = stats_dict.get("Accurate Crosses", 0) / ninety_s
    long_balls_won = stats_dict.get("Long Balls Won", 0) / ninety_s
    saves = stats_dict.get("Saves", 0) / ninety_s
    clean_sheets = stats_dict.get("Cleansheets", 0) / ninety_s
    shots_on_target = stats_dict.get("Shots On Target", 0) / ninety_s
    saves_insidebox = stats_dict.get("Saves Insidebox", 0) / ninety_s
    high_claims = stats_dict.get("Good High Claim", 0) / ninety_s
    punches = stats_dict.get("Punches", 0) / ninety_s
    errors = stats_dict.get("Error Lead To Goal", 0) / ninety_s
    accurate_passes = stats_dict.get("Accurate Passes", 0) / ninety_s

    # Normalizations (Targets updated to Per 90 World-Class maximums)
    n_goals = normalize_stat(goals, 0.8)
    n_assists = normalize_stat(assists, 0.5)
    n_interceptions = normalize_stat(interceptions, 2.5)
    n_clearances = normalize_stat(clearances, 5.0)
    n_ball_recovery = normalize_stat(ball_recovery, 8.0)
    n_key_passes = normalize_stat(key_passes, 2.5)
    n_chances_created = normalize_stat(chances_created, 2.0)
    n_dribbles = normalize_stat(dribbles, 3.5)
    n_blocked_shots = normalize_stat(blocked_shots, 1.2)
    n_final_third = normalize_stat(final_third_passes, 10.0)
    n_acc_crosses = normalize_stat(accurate_crosses, 2.0)
    n_long_balls = normalize_stat(long_balls_won, 4.0)
    n_saves = normalize_stat(saves, 4.0)
    n_clean_sheets = normalize_stat(clean_sheets, 0.4)
    n_shots_on_target = normalize_stat(shots_on_target, 1.5)
    n_saves_insidebox = normalize_stat(saves_insidebox, 2.5)
    n_box_control = normalize_stat(high_claims + punches, 0.8)
    n_dist_volume = normalize_stat(accurate_passes, 35.0)

    if "GOALKEEPER" in position_code:
        # GK Profile: Shot Stopping (40%), Distribution/Footwork (40%), Box Control/Set Pieces (20%)
        shot_stopping = (n_saves * 0.4) + (n_saves_insidebox * 0.3) + (n_clean_sheets * 0.3)
        distribution = (pass_acc * 0.5) + (n_dist_volume * 0.3) + (n_long_balls * 0.2)
        box_control = (n_box_control * 0.7) + (n_clearances * 0.3)
        
        penalty = min(errors * 100.0, 15.0) # Up to -15 BPI deduction for error-proneness
        bpi = (shot_stopping * 0.40) + (distribution * 0.40) + (box_control * 0.20) - penalty
        
    elif "FULLBACK" in position_code or "WINGBACK" in position_code:
        # Fullback Profile: Def (35%), Build-up (40%), Off (25%)
        defensive = (tackle_win_pct * 0.3) + (duel_win_pct * 0.3) + (n_interceptions * 0.2) + (n_ball_recovery * 0.2)
        buildup = (pass_acc * 0.3) + (n_final_third * 0.3) + (cross_acc * 0.2) + (n_acc_crosses * 0.2)
        offensive = (n_dribbles * 0.4) + (n_key_passes * 0.3) + (n_assists * 0.2) + (n_goals * 0.1)
        bpi = (defensive * 0.35) + (buildup * 0.40) + (offensive * 0.25)
        
    elif "CENTER_BACK" in position_code or "DEFENDER" in position_code:
        # Center Back Profile: Def (70%), Build-up (30%)
        defensive = (duel_win_pct * 0.25) + (aerial_win_pct * 0.25) + (n_clearances * 0.2) + (n_interceptions * 0.15) + (n_blocked_shots * 0.15)
        buildup = (pass_acc * 0.6) + (n_long_balls * 0.4)
        bpi = (defensive * 0.70) + (buildup * 0.30)
        
    elif "MIDFIELDER" in position_code:
        # Midfielder: Build-up (40%), Def (30%), Off (30%)
        buildup = (pass_acc * 0.5) + (n_final_third * 0.5)
        defensive = (duel_win_pct * 0.4) + (n_ball_recovery * 0.3) + (n_interceptions * 0.3)
        offensive = (n_key_passes * 0.4) + (n_chances_created * 0.3) + (n_dribbles * 0.3)
        bpi = (buildup * 0.40) + (defensive * 0.30) + (offensive * 0.30)
        
    elif "WINGER" in position_code:
        # Winger: Off (60%), Build-up (30%), Def (10%)
        offensive = (n_dribbles * 0.3) + (n_chances_created * 0.2) + (n_goals * 0.25) + (n_assists * 0.25)
        buildup = (pass_acc * 0.4) + (cross_acc * 0.3) + (n_acc_crosses * 0.3)
        defensive = n_ball_recovery
        bpi = (offensive * 0.60) + (buildup * 0.30) + (defensive * 0.10)
        
    elif "ATTACKER" in position_code or "STRIKER" in position_code:
        # Attacker: Scoring (60%), Target Man (20%), Link-up (20%)
        scoring = (n_goals * 0.6) + (n_shots_on_target * 0.4)
        target = (aerial_win_pct * 0.5) + (duel_win_pct * 0.5)
        linkup = (pass_acc * 0.5) + (n_key_passes * 0.5)
        bpi = (scoring * 0.60) + (target * 0.20) + (linkup * 0.20)
        
    else:
        bpi = (n_goals + n_assists + n_interceptions + pass_acc) / 4

    return min(100.0, max(0.0, bpi))

def get_generalized_position(position_code):
    pos = position_code.upper()
    if "GOALKEEPER" in pos: return "GOALKEEPER"
    if "FULLBACK" in pos or "WINGBACK" in pos: return "FULLBACK"
    if "CENTER_BACK" in pos or "DEFENDER" in pos: return "CENTER_BACK"
    if "MIDFIELDER" in pos: return "MIDFIELDER"
    if "WINGER" in pos: return "WINGER"
    if "ATTACKER" in pos or "STRIKER" in pos: return "ATTACKER"
    return "UNKNOWN"

def calculate_fit_rating(stats_dict):
    """
    Simulates Agent D: The "Coach's Persona" Filter.
    Evaluates discipline, stamina, work-rate, and reliability.
    Returns a score bounded between 0.0 and 20.0.
    """
    fit_score = 10.0  # Base neutral score
    
    minutes = stats_dict.get("Minutes Played", 0)
    appearances = stats_dict.get("Appearances", 0)
    yellows = stats_dict.get("Yellowcards", 0)
    reds = stats_dict.get("Redcards", 0)
    fouls = stats_dict.get("Fouls", 0)

    # 1. Availability & Stamina (Up to +10 points)
    if minutes > 2000:
        fit_score += 10.0
    elif minutes > 1000:
        fit_score += 6.0
    elif minutes > 500:
        fit_score += 3.0
        
    # 2. Discipline & Reliability (Deductions)
    penalty = (reds * 4.0) + (yellows * 0.5)
    
    if appearances > 0:
        fouls_per_game = fouls / appearances
        if fouls_per_game > 1.5:
            penalty += 3.0  # Coach Sabău penalizes reckless foulers
            
    fit_score -= penalty
    
    return round(max(0.0, min(20.0, fit_score)), 2)

def process_player_data(data):
    """Applies the new mathematical framework for Dynamic Rating and Synergy Score."""
    player_info = data.get('player_info')
    match_stats = data.get('match_stats')
    
    if not player_info or match_stats is None:
        return None # Skip files that don't match the individual player structure

    raw_stats = {}
    for stat in match_stats:
        total_stats = stat.get('total', {})
        for key, value in total_stats.items():
            if isinstance(value, (int, float)):
                raw_stats[key] = raw_stats.get(key, 0.0) + float(value)

    def safe_pct(won, total):
        t = raw_stats.get(total, 0)
        return (raw_stats.get(won, 0) / t) * 100.0 if t > 0 else 0.0

    def get_stat(key):
        return raw_stats.get(key, 0.0)

    stats_dict = {
        "Accurate Crosses": get_stat('successfulCrosses'),
        "Accurate Passes": get_stat('successfulPasses'),
        "Aerials": get_stat('aerialDuels'),
        "Aerials Lost": max(0.0, get_stat('aerialDuels') - get_stat('aerialDuelsWon')),
        "Aerials Won": get_stat('aerialDuelsWon'),
        "Appearances": len(match_stats),
        "Assists": get_stat('assists'),
        "Backward Passes": get_stat('backPasses'),
        "Ball Recovery": get_stat('recoveries'),
        "Big Chances Created": get_stat('smartPasses'),
        "Big Chances Missed": 0.0,
        "Blocked Shots": get_stat('shotsBlocked'),
        "Captain": 0.0,
        "Chances Created": get_stat('shotAssists'),
        "Cleansheets": get_stat('cleanSheets'),
        "Clearances": get_stat('clearances'),
        "Cumulative Minutes Played": 0.0,
        "Dispossessed": get_stat('losses'),
        "Dribble Attempts": get_stat('dribbles'),
        "Dribbled Past": 0.0,
        "Duels Lost": max(0.0, get_stat('duels') - get_stat('duelsWon')),
        "Duels Won": get_stat('duelsWon'),
        "Error Lead To Goal": get_stat('errors'),
        "Error Lead To Shot": get_stat('errors'),
        "Fouls": get_stat('fouls'),
        "Fouls Drawn": get_stat('foulsSuffered'),
        "Goalkeeper Goals Conceded": get_stat('goalsConceded'),
        "Goals": get_stat('goals'),
        "Goals Conceded": get_stat('goalsConceded'),
        "Good High Claim": 0.0,
        "Hit Woodwork": 0.0,
        "Interceptions": get_stat('interceptions'),
        "Key Passes": get_stat('keyPasses'),
        "Last Man Tackle": 0.0,
        "Lineups": 0.0,
        "Long Balls": get_stat('longPasses'),
        "Long Balls Won": get_stat('successfulLongPasses'),
        "Minutes Played": get_stat('minutesOnField'),
        "Offsides": get_stat('offsides'),
        "Own Goals": get_stat('ownGoals'),
        "Passes": get_stat('passes'),
        "Passes In Final Third": get_stat('passesToFinalThird'),
        "Penalties Committed": 0.0,
        "Penalties Missed": 0.0,
        "Penalties Saved": 0.0,
        "Penalties Scored": get_stat('penalties'),
        "Penalties Won": 0.0,
        "Possession Lost": get_stat('losses'),
        "Punches": 0.0,
        "Rating": 0.0,
        "Redcards": get_stat('redCards'),
        "Saves": get_stat('saves'),
        "Saves Insidebox": get_stat('saves'),
        "Shots Blocked": get_stat('shotsBlocked'),
        "Shots Off Target": max(0.0, get_stat('shots') - get_stat('shotsOnTarget')),
        "Shots On Target": get_stat('shotsOnTarget'),
        "Shots Total": get_stat('shots'),
        "Successful Dribbles": get_stat('successfulDribbles'),
        "Tackles": get_stat('slidingTackles'),
        "Tackles Won": get_stat('successfulSlidingTackles'),
        "Team Draws": get_stat('draws'),
        "Team Lost": get_stat('losses'),
        "Team Wins": get_stat('wins'),
        "Through Balls": get_stat('smartPasses'),
        "Through Balls Won": get_stat('successfulSmartPasses'),
        "Total Crosses": get_stat('crosses'),
        "Total Duels": get_stat('duels'),
        "Touches": get_stat('touches'),
        "Turn Over": get_stat('losses'),
        "Yellowcards": get_stat('yellowCards'),
        
        "Accurate Passes Percentage": safe_pct('successfulPasses', 'passes'),
        "Duels Won Percentage": safe_pct('duelsWon', 'duels'),
        "Long Balls Won Percentage": safe_pct('successfulLongPasses', 'longPasses'),
        "Successful Crosses Percentage": safe_pct('successfulCrosses', 'crosses'),
        "Tacles Won Percentage": safe_pct('successfulSlidingTackles', 'slidingTackles'),
        "Tackles Won Percentage": safe_pct('successfulSlidingTackles', 'slidingTackles'),
    }

    role_name = player_info.get('role', {}).get('name', 'Unknown')
    position_code = f"{role_name} {player_info.get('position', 'Unknown')} {player_info.get('role', {}).get('code2', '')}".upper()

    if position_code in ["COACH", "ASSISTANT_COACH", "UNKNOWN"]:
        return None 

    gen_pos = get_generalized_position(position_code)

    # --- 1. Calculate Base Performance: ∑(Stat_i × Weight_i) ---
    bpi = calculate_bpi(position_code, stats_dict)
    
    if bpi is None:
        print("BPI IS NONE!!")
        return None # Purge player due to incomplete data
    
    # --- 2. Simulating Agent A (News & Sentiment Δ) ---
    # Δnews (e.g., -15 to +15 points based on recent news/injuries)
    delta_news = 0.0
    
    # --- 3. Agent D: The Coach's Persona Fit ---
    # Analyzes discipline (cards/fouls) and work-rate/stamina (minutes played)
    fit_rating = calculate_fit_rating(stats_dict)
    
    # --- 4. NEW DYNAMIC RATING FORMULA ---
    # Dynamic Rating = (∑(Stat_i × Weight_i)) + Δnews + Fit Rating
    dynamic_rating = max(0.0, bpi + delta_news + fit_rating)
    
    # --- 5. Squad Deficit Intelligence (Agent B) ---
    squad_deficit = SQUAD_DEFICIT_MAP.get(gen_pos, 0.5)

    # --- 6. Tactical Matchmaker: Complementary Factor (Agent C) ---
    # Multiplier: 1.0 (No special synergy) up to 1.5x (Perfect fit for team weakness)
    complementary_factor = 1.0
    
    # Example logic: if the player is good at Aerials, and U Cluj needs Aerials
    #if TEAM_WORST_STATS.get("Aerials Won") and stats_dict.get("Aerials Won", 0) > 30:
    #    complementary_factor += 0.2
    # If the player is a good crosser/key passer, and U Cluj needs it
    #if TEAM_WORST_STATS.get("Total Crosses") and stats_dict.get("Key Passes", 0) > 20:
    #    complementary_factor += 0.15

    # --- 7. NEW SYNERGY SCORE FORMULA ---
    # Synergy Score = (Dynamic Rating × Squad Deficit_pos) × Complementary Factor
    synergy_score = (dynamic_rating * squad_deficit) * complementary_factor

    # --- Trend Indicator ---
    trend = "STABLE"
    if delta_news > 5.0:
        trend = "RISING"
    elif delta_news < -5.0:
        trend = "FALLING"

    first_name = player_info.get('firstName') or ''
    last_name = player_info.get('lastName') or ''
    name = f"{first_name} {last_name}".strip()
    if not name:
        name = player_info.get('shortName', 'Unknown')

    player_id = player_info.get('wyId') or player_info.get('id', '')

    minutes = stats_dict.get("Minutes Played", 0)
    p90 = minutes / 90.0 if minutes > 0 else 0.0

    stats_p90 = {}
    skip_p90 = {"Appearances", "Minutes Played", "Cumulative Minutes Played", "Lineups", "Captain", "Rating"}
    for key, val in stats_dict.items():
        if key in skip_p90 or "Percentage" in key:
            stats_p90[key] = round(val, 2) if isinstance(val, (int, float)) else val
        else:
            stats_p90[key] = round(val / p90, 2) if p90 > 0 else 0.0

    return {
        "player_id": f"U{player_id}",
        "name": name,
        "position": position_code,
        "base_bpi": round(bpi, 2),
        "delta_news": delta_news,
        "fit_rating": fit_rating,
        "dynamic_rating": round(dynamic_rating, 2),
        "squad_deficit_urgency": squad_deficit,
        "complementary_factor": round(complementary_factor, 2),
        "synergy_score": round(synergy_score, 2),
        "trend_indicator": trend,
        "key_stats_used": stats_p90
    }

# --- MAIN EXECUTION & FIREBASE UPLOAD ---

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "PLAYERS")
    
    if not os.path.exists(data_dir):
        print(f"Error: {data_dir} folder not found.")
        return

    results = []
    
    # Process all JSON files in the directory
    for filename in os.listdir(data_dir):
        if not filename.endswith(".json"):
            continue
            
        file_path = os.path.join(data_dir, filename)
        print(f"Processing {filename}...")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue
            
        processed = process_player_data(data)
        if processed:
            results.append(processed)
        else:
            print("NOT PROCESSED!")

    # Sort by Synergy Score since this is the true indicator of "Who should we buy right now?"
    #results.sort(key=lambda x: x["synergy_score"], reverse=True)
    
    print("\n--- Top 3 Prospects by SYNERGY SCORE ---")
    for r in results[:3]:
        print(f"[{r['trend_indicator']}] {r['name']} ({r['position']})")
        print(f"   Dynamic Rating: {r['dynamic_rating']} (BPI: {r['base_bpi']} | ΔNews: {r['delta_news']} | Fit: {r['fit_rating']})")
        print(f"   Synergy Score:  {r['synergy_score']} (Deficit: {r['squad_deficit_urgency']}x | Comp. Factor: {r['complementary_factor']}x)")
        print("-" * 50)

    try:
        print("\nConnecting to Firebase...")

        cred = credentials.Certificate(os.path.join(script_dir, 'firebase_cred.json'))

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        collection_ref = db.collection('u_players_calculated')
        
        # Firestore limits batches to 500 operations. We will upload in chunks.
        max_batch_size = 500
        uploaded_count = 0
        
        for i in range(0, len(results), max_batch_size):
            batch = db.batch()
            chunk = results[i:i + max_batch_size]
            for res in results:
                doc_ref = collection_ref.document(str(res['player_id']))
                batch.set(doc_ref, res)
            batch.commit()
            uploaded_count += len(results)
            print(f"Committed batch of {len(results)} players...")
            
        print(f"Successfully saved {uploaded_count} new structures to Firebase!")
    except Exception as e:
        print(f"\n[!] Firebase upload skipped. Error: {e}")

if __name__ == "__main__":
    main()