import json
import os
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. CONFIGURATION & U CLUJ TACTICAL PROFILES ---

# Deficit Map: G_gap (Squad Deficit Urgency by Position)
SQUAD_DEFICIT_MAP = {
    "GOALKEEPER": 0.5,
    "FULLBACK": 0.5,
    "CENTER_BACK": 0.5,
    "MIDFIELDER": 0.5,
    "WINGER": 0.5,
    "ATTACKER": 0.5
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
    elif "CENTER_BACK" in position_code or "DEFENDER" in position_code:
        required_stats = ["Duels Won Percentage", "Aerials Won Percentage", "Clearances", "Interceptions", "Shots Blocked", "Accurate Passes Percentage", "Long Balls Won"]
    elif "MIDFIELDER" in position_code:
        required_stats = ["Accurate Passes Percentage", "Passes In Final Third", "Duels Won Percentage", "Ball Recovery", "Interceptions", "Key Passes", "Chances Created", "Successful Dribbles"]
    elif "WINGER" in position_code:
        required_stats = ["Successful Dribbles", "Chances Created", "Accurate Passes Percentage", "Successful Crosses Percentage", "Accurate Crosses", "Ball Recovery"]
    elif "ATTACKER" in position_code or "STRIKER" in position_code or "FORWARD" in position_code:
        required_stats = ["Shots On Target", "Aerials Won Percentage", "Duels Won Percentage", "Accurate Passes Percentage", "Key Passes"]
    else:
        required_stats = ["Accurate Passes Percentage", "Interceptions"]

    for stat in required_stats:
        if stat not in stats_dict:
            return None

    bpi = 0.0
    
    # Advanced Tactical Percentages (Default to 50 if missing)
    pass_acc = stats_dict.get("Accurate Passes Percentage", 50.0)
    tackle_win_pct = stats_dict.get("Tacles Won Percentage", stats_dict.get("Tackles Won Percentage", 50.0))
    duel_win_pct = stats_dict.get("Duels Won Percentage", 50.0)
    aerial_win_pct = stats_dict.get("Aerials Won Percentage", 50.0)
    cross_acc = stats_dict.get("Successful Crosses Percentage", 30.0)
    
    # Calculate 'Per 90' factor. Force minimum 3 full matches (270 mins)
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
        shot_stopping = (n_saves * 0.4) + (n_saves_insidebox * 0.3) + (n_clean_sheets * 0.3)
        distribution = (pass_acc * 0.5) + (n_dist_volume * 0.3) + (n_long_balls * 0.2)
        box_control = (n_box_control * 0.7) + (n_clearances * 0.3)
        penalty = min(errors * 100.0, 15.0)
        bpi = (shot_stopping * 0.40) + (distribution * 0.40) + (box_control * 0.20) - penalty
        
    elif "FULLBACK" in position_code or "WINGBACK" in position_code:
        defensive = (tackle_win_pct * 0.3) + (duel_win_pct * 0.3) + (n_interceptions * 0.2) + (n_ball_recovery * 0.2)
        buildup = (pass_acc * 0.3) + (n_final_third * 0.3) + (cross_acc * 0.2) + (n_acc_crosses * 0.2)
        offensive = (n_dribbles * 0.4) + (n_key_passes * 0.3) + (n_assists * 0.2) + (n_goals * 0.1)
        bpi = (defensive * 0.35) + (buildup * 0.40) + (offensive * 0.25)
        
    elif "CENTER_BACK" in position_code or "DEFENDER" in position_code:
        defensive = (duel_win_pct * 0.25) + (aerial_win_pct * 0.25) + (n_clearances * 0.2) + (n_interceptions * 0.15) + (n_blocked_shots * 0.15)
        buildup = (pass_acc * 0.6) + (n_long_balls * 0.4)
        bpi = (defensive * 0.70) + (buildup * 0.30)
        
    elif "MIDFIELDER" in position_code:
        buildup = (pass_acc * 0.5) + (n_final_third * 0.5)
        defensive = (duel_win_pct * 0.4) + (n_ball_recovery * 0.3) + (n_interceptions * 0.3)
        offensive = (n_key_passes * 0.4) + (n_chances_created * 0.3) + (n_dribbles * 0.3)
        bpi = (buildup * 0.40) + (defensive * 0.30) + (offensive * 0.30)
        
    elif "WINGER" in position_code:
        offensive = (n_dribbles * 0.3) + (n_chances_created * 0.2) + (n_goals * 0.25) + (n_assists * 0.25)
        buildup = (pass_acc * 0.4) + (cross_acc * 0.3) + (n_acc_crosses * 0.3)
        defensive = n_ball_recovery
        bpi = (offensive * 0.60) + (buildup * 0.30) + (defensive * 0.10)
        
    elif "ATTACKER" in position_code or "STRIKER" in position_code or "FORWARD" in position_code:
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
    if "ATTACKER" in pos or "STRIKER" in pos or "FORWARD" in pos: return "ATTACKER"
    return "UNKNOWN"

def calculate_fit_rating(stats_dict):
    """
    Evaluates discipline, stamina, work-rate, and reliability.
    Returns a score bounded between 0.0 and 20.0.
    """
    fit_score = 10.0
    
    minutes = stats_dict.get("Minutes Played", 0)
    appearances = stats_dict.get("Appearances", 0)
    yellows = stats_dict.get("Yellowcards", 0)
    reds = stats_dict.get("Redcards", 0)
    fouls = stats_dict.get("Fouls", 0)

    if minutes > 2000:
        fit_score += 10.0
    elif minutes > 1000:
        fit_score += 6.0
    elif minutes > 500:
        fit_score += 3.0
        
    penalty = (reds * 4.0) + (yellows * 0.5)
    
    if appearances > 0:
        fouls_per_game = fouls / appearances
        if fouls_per_game > 1.5:
            penalty += 3.0
            
    fit_score -= penalty
    
    return round(max(0.0, min(20.0, fit_score)), 2)

def process_player_data(player_data):
    """Applies the mathematical framework to Wyscout JSON formatted data."""
    stats_dict = {}
    
    match_stats = player_data.get("match_stats", [])
    
    # 1. Map Wyscout metrics to the existing BPI requirements
    t_minutes = sum(m.get("total", {}).get("minutesOnField", 0) for m in match_stats)
    t_goals = sum(m.get("total", {}).get("goals", 0) for m in match_stats)
    t_assists = sum(m.get("total", {}).get("assists", 0) for m in match_stats)
    t_interceptions = sum(m.get("total", {}).get("interceptions", 0) for m in match_stats)
    t_clearances = sum(m.get("total", {}).get("clearances", 0) for m in match_stats)
    t_recoveries = sum(m.get("total", {}).get("recoveries", 0) for m in match_stats)
    t_key_passes = sum(m.get("total", {}).get("keyPasses", 0) for m in match_stats)
    t_shot_assists = sum(m.get("total", {}).get("shotAssists", 0) for m in match_stats) # Proxies Chances Created
    t_dribbles = sum(m.get("total", {}).get("successfulDribbles", 0) for m in match_stats)
    t_shots_blocked = sum(m.get("total", {}).get("shotsBlocked", 0) for m in match_stats)
    t_passes_final_third = sum(m.get("total", {}).get("passesToFinalThird", 0) for m in match_stats)
    t_acc_crosses = sum(m.get("total", {}).get("successfulCrosses", 0) for m in match_stats)
    t_long_balls = sum(m.get("total", {}).get("successfulLongPasses", 0) for m in match_stats)
    t_saves = sum(m.get("total", {}).get("gkSaves", 0) for m in match_stats)
    t_cleansheets = sum(m.get("total", {}).get("gkCleanSheets", 0) for m in match_stats)
    t_shots_on_target = sum(m.get("total", {}).get("shotsOnTarget", 0) for m in match_stats)
    t_saves_inbox = t_saves * 0.6 # Approximation since explicit stat varies
    t_exits = sum(m.get("total", {}).get("gkSuccessfulExits", 0) for m in match_stats)
    t_punches = 0
    t_errors = 0
    t_acc_passes = sum(m.get("total", {}).get("successfulPasses", 0) for m in match_stats)
    
    t_yellow = sum(m.get("total", {}).get("yellowCards", 0) for m in match_stats)
    t_red = sum(m.get("total", {}).get("redCards", 0) for m in match_stats)
    t_fouls = sum(m.get("total", {}).get("fouls", 0) for m in match_stats)
    
    # Extract total attempts for percentage calculations
    t_passes = sum(m.get("total", {}).get("passes", 0) for m in match_stats)
    t_duels = sum(m.get("total", {}).get("duels", 0) for m in match_stats)
    t_duels_won = sum(m.get("total", {}).get("duelsWon", 0) for m in match_stats)
    t_aerials = sum(m.get("total", {}).get("aerialDuels", 0) for m in match_stats)
    t_aerials_won = sum(m.get("total", {}).get("aerialDuelsWon", 0) for m in match_stats)
    t_crosses = sum(m.get("total", {}).get("crosses", 0) for m in match_stats)
    t_def_duels = sum(m.get("total", {}).get("defensiveDuels", 0) for m in match_stats)
    t_def_duels_won = sum(m.get("total", {}).get("defensiveDuelsWon", 0) for m in match_stats)

    stats_dict = {
        "Minutes Played": t_minutes,
        "Goals": t_goals,
        "Assists": t_assists,
        "Interceptions": t_interceptions,
        "Clearances": t_clearances,
        "Ball Recovery": t_recoveries,
        "Key Passes": t_key_passes,
        "Chances Created": t_shot_assists,
        "Successful Dribbles": t_dribbles,
        "Shots Blocked": t_shots_blocked,
        "Passes In Final Third": t_passes_final_third,
        "Accurate Crosses": t_acc_crosses,
        "Long Balls Won": t_long_balls,
        "Saves": t_saves,
        "Cleansheets": t_cleansheets,
        "Shots On Target": t_shots_on_target,
        "Saves Insidebox": t_saves_inbox,
        "Good High Claim": t_exits,
        "Punches": t_punches,
        "Error Lead To Goal": t_errors,
        "Accurate Passes": t_acc_passes,
        "Appearances": len(match_stats),
        "Yellowcards": t_yellow,
        "Redcards": t_red,
        "Fouls": t_fouls,
        "Accurate Passes Percentage": (t_acc_passes / t_passes * 100) if t_passes > 0 else 0,
        "Duels Won Percentage": (t_duels_won / t_duels * 100) if t_duels > 0 else 0,
        "Aerials Won Percentage": (t_aerials_won / t_aerials * 100) if t_aerials > 0 else 0,
        "Successful Crosses Percentage": (t_acc_crosses / t_crosses * 100) if t_crosses > 0 else 0,
        "Tackles Won Percentage": (t_def_duels_won / t_def_duels * 100) if t_def_duels > 0 else 0
    }
    stats_dict["Tacles Won Percentage"] = stats_dict["Tackles Won Percentage"]

    player_info = player_data.get("player_info", {})
    position_code = player_info.get("role", {}).get("name", "UNKNOWN")
    
    if position_code in ["COACH", "ASSISTANT_COACH", "UNKNOWN"]:
        return None 

    gen_pos = get_generalized_position(position_code)

    # --- Calculate BPI ---
    bpi = calculate_bpi(position_code, stats_dict)
    
    if bpi is None:
        return None # Purge player due to incomplete data
    
    delta_news = 0.0
    fit_rating = calculate_fit_rating(stats_dict)
    
    dynamic_rating = max(0.0, bpi + delta_news + fit_rating)
    squad_deficit = SQUAD_DEFICIT_MAP.get(gen_pos, 0.5)

    complementary_factor = 1.0
    
    synergy_score = (dynamic_rating * squad_deficit) * complementary_factor

    trend = "STABLE"
    if delta_news > 5.0:
        trend = "RISING"
    elif delta_news < -5.0:
        trend = "FALLING"

    return {
        "player_id": player_info.get("wyId"),
        "name": player_info.get("shortName") or f"{player_info.get('firstName', '')} {player_info.get('lastName', '')}",
        "position": position_code,
        "base_bpi": round(bpi, 2),
        "delta_news": delta_news,
        "fit_rating": fit_rating,
        "dynamic_rating": round(dynamic_rating, 2),
        "squad_deficit_urgency": squad_deficit,
        "complementary_factor": round(complementary_factor, 2),
        "synergy_score": round(synergy_score, 2),
        "trend_indicator": trend,
        "key_stats_used": stats_dict
    }

# --- MAIN EXECUTION & FIREBASE UPLOAD ---

def main():
    # Adjusted path to "PLAYERS/Players" as requested
    data_dir = os.path.join(os.path.dirname(__file__), "PLAYERS", "Players")
    
    if not os.path.exists(data_dir):
        print(f"Error: {data_dir} folder not found.")
        return

    results = []
    
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

    # Sort by Synergy Score
    results.sort(key=lambda x: x["synergy_score"], reverse=True)
    
    print("\n--- Top 3 Prospects by SYNERGY SCORE ---")
    for r in results[:3]:
        print(f"[{r['trend_indicator']}] {r['name']} ({r['position']})")
        print(f"   Dynamic Rating: {r['dynamic_rating']} (BPI: {r['base_bpi']} | ΔNews: {r['delta_news']} | Fit: {r['fit_rating']})")
        print(f"   Synergy Score:  {r['synergy_score']} (Deficit: {r['squad_deficit_urgency']}x | Comp. Factor: {r['complementary_factor']}x)")
        print("-" * 50)

    try:
        print("\nConnecting to Firebase...")

        cred_path = os.path.join(os.path.dirname(__file__), 'firebase_cred.json')
        cred = credentials.Certificate(cred_path)
  
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        # Different collection name
        collection_ref = db.collection('u_wyscout_shadow_prospects')
        
        max_batch_size = 500
        uploaded_count = 0
        
        for i in range(0, len(results), max_batch_size):
            batch = db.batch()
            chunk = results[i:i + max_batch_size]
            for res in chunk:
                # Add 'U' prefix to the document ID as requested
                doc_ref = collection_ref.document("U" + str(res['player_id']))
                batch.set(doc_ref, res)
            batch.commit()
            uploaded_count += len(chunk)
            print(f"Committed batch of {len(chunk)} players...")
            
        print(f"Successfully saved {uploaded_count} new structures to Firebase!")
    except Exception as e:
        print(f"\n[!] Firebase upload skipped. Error: {e}")

if __name__ == "__main__":
    main()
