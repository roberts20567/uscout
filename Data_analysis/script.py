import json
import os
import random
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. CONFIGURATION & U CLUJ TACTICAL PROFILES ---

# Deficit Map: G_gap (Squad Deficit Urgency by Position)
# Simulates Agent B: The "General Manager" output
SQUAD_DEFICIT_MAP = {
    "GOALKEEPER": 0.3,
    "FULLBACK": 0.6,
    "CENTER_BACK": 0.9,     # Urgent need! e.g., lost 3-0, bad aerial duels
    "MIDFIELDER": 0.5,
    "WINGER": 0.7,
    "ATTACKER": 0.8
}

# Team Weaknesses for Complementary Factor calculation
# Simulates Agent C's logic mapping prospect strengths to U Cluj weaknesses
TEAM_WORST_STATS = {
    "AERIALS_WON": True,
    "CROSSES": True,
    "KEY_PASSES": False
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
    bpi = 0.0
    
    goals = stats_dict.get("GOALS", 0)
    assists = stats_dict.get("ASSISTS", 0)
    saves = stats_dict.get("SAVES", 0)
    clean_sheets = stats_dict.get("CLEAN_SHEETS", 0)
    interceptions = stats_dict.get("INTERCEPTIONS", 0)
    tackles = stats_dict.get("TACKLES", 0)
    aerials_won = stats_dict.get("AERIALS_WON", 0)
    key_passes = stats_dict.get("KEY_PASSES", 0)
    passes_accuracy = stats_dict.get("PASSES_ACCURACY", 70) 
    dribbles = stats_dict.get("DRIBBLES_SUCCESSFUL", 0)
    shots_on_target = stats_dict.get("SHOTS_ON_TARGET", 0)

    n_goals = normalize_stat(goals, 20)
    n_assists = normalize_stat(assists, 15)
    n_saves = normalize_stat(saves, 100)
    n_clean_sheets = normalize_stat(clean_sheets, 15)
    n_interceptions = normalize_stat(interceptions, 50)
    n_tackles = normalize_stat(tackles, 80)
    n_aerials_won = normalize_stat(aerials_won, 100)
    n_key_passes = normalize_stat(key_passes, 50)
    n_passes_accuracy = passes_accuracy 
    n_dribbles = normalize_stat(dribbles, 60)
    n_shots_on_target = normalize_stat(shots_on_target, 40)

    position_code = position_code.upper()
    
    if "GOALKEEPER" in position_code:
        bpi = (0.35 * n_saves) + (0.25 * n_passes_accuracy) + (0.20 * n_clean_sheets) + (0.20 * 80)
    elif "FULLBACK" in position_code or "WINGBACK" in position_code:
        bpi = (0.25 * 75) + (0.25 * n_key_passes) + (0.30 * n_tackles) + (0.20 * n_interceptions)
    elif "CENTER_BACK" in position_code or "DEFENDER" in position_code:
        bpi = (0.35 * n_aerials_won) + (0.25 * n_interceptions) + (0.20 * n_passes_accuracy) + (0.20 * n_tackles)
    elif "MIDFIELDER" in position_code:
        bpi = (0.30 * n_key_passes) + (0.25 * n_interceptions) + (0.25 * n_dribbles) + (0.20 * n_passes_accuracy)
    elif "WINGER" in position_code:
        bpi = (0.30 * n_dribbles) + (0.25 * ((n_goals + n_assists) / 2)) + (0.25 * 80) + (0.20 * n_tackles)
    elif "ATTACKER" in position_code or "STRIKER" in position_code:
        bpi = (0.40 * n_goals) + (0.20 * n_shots_on_target) + (0.20 * n_aerials_won) + (0.20 * n_passes_accuracy)
    else:
        bpi = (n_goals + n_assists + n_interceptions + n_tackles) / 4

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

def process_player_data(player):
    """Applies the new mathematical framework for Dynamic Rating and Synergy Score."""
    # --- Data Extraction ---
    stats_dict = {}
    if player.get("statistics"):
        for stat_season in player["statistics"]:
            if stat_season.get("details"):
                for detail in stat_season["details"]:
                    dev_name = detail.get("type", {}).get("developer_name")
                    val = detail.get("value", {}).get("total")
                    if dev_name and val is not None:
                        stats_dict[dev_name] = stats_dict.get(dev_name, 0) + val

    pos_info = player.get("detailedposition") or player.get("position") or {}
    position_code = pos_info.get("developer_name", "UNKNOWN")
    
    if position_code in ["COACH", "ASSISTANT_COACH", "UNKNOWN"]:
        return None 

    gen_pos = get_generalized_position(position_code)

    # --- 1. Calculate Base Performance: ∑(Stat_i × Weight_i) ---
    bpi = calculate_bpi(position_code, stats_dict)
    
    # --- 2. Simulating Agent A (News & Sentiment Δ) ---
    # Δnews (e.g., -15 to +15 points based on recent news/injuries)
    delta_news = round(random.uniform(-15.0, 15.0), 2)
    
    # --- 3. Simulating Fit Rating (Style-to-Coach match) ---
    # Score from 0 to 20 based on Sabău's preferred playstyle
    fit_rating = round(random.uniform(5.0, 20.0), 2)
    
    # --- 4. NEW DYNAMIC RATING FORMULA ---
    # Dynamic Rating = (∑(Stat_i × Weight_i)) + Δnews + Fit Rating
    dynamic_rating = max(0.0, bpi + delta_news + fit_rating)
    
    # --- 5. Squad Deficit Intelligence (Agent B) ---
    squad_deficit = SQUAD_DEFICIT_MAP.get(gen_pos, 0.5)

    # --- 6. Tactical Matchmaker: Complementary Factor (Agent C) ---
    # Multiplier: 1.0 (No special synergy) up to 1.5x (Perfect fit for team weakness)
    complementary_factor = 1.0
    
    # Example logic: if the player is good at Aerials, and U Cluj needs Aerials
    if TEAM_WORST_STATS.get("AERIALS_WON") and stats_dict.get("AERIALS_WON", 0) > 30:
        complementary_factor += 0.2
    # If the player is a good crosser/key passer, and U Cluj needs it
    if TEAM_WORST_STATS.get("CROSSES") and stats_dict.get("KEY_PASSES", 0) > 20:
        complementary_factor += 0.15

    # --- 7. NEW SYNERGY SCORE FORMULA ---
    # Synergy Score = (Dynamic Rating × Squad Deficit_pos) × Complementary Factor
    synergy_score = (dynamic_rating * squad_deficit) * complementary_factor

    # --- Trend Indicator ---
    trend = "STABLE"
    if delta_news > 5.0:
        trend = "RISING"
    elif delta_news < -5.0:
        trend = "FALLING"

    return {
        "player_id": player.get("id"),
        "name": player.get("display_name") or player.get("name"),
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
    

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "raw_data_sportmonks")
    
    if not os.path.exists(data_dir):
        print("Error: raw_data_sportmonks folder not found.")
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
            
        players = data.get("data", data) if isinstance(data, dict) else data
        
        for player in players:
            processed = process_player_data(player)
            if processed:
                results.append(processed)

    # Sort by Synergy Score since this is the true indicator of "Who should we buy right now?"
    results.sort(key=lambda x: x["synergy_score"], reverse=True)
    
    print("\n--- Top 3 Prospects by SYNERGY SCORE ---")
    for r in results[:3]:
        print(f"[{r['trend_indicator']}] {r['name']} ({r['position']})")
        print(f"   Dynamic Rating: {r['dynamic_rating']} (BPI: {r['base_bpi']} | ΔNews: {r['delta_news']} | Fit: {r['fit_rating']})")
        print(f"   Synergy Score:  {r['synergy_score']} (Deficit: {r['squad_deficit_urgency']}x | Comp. Factor: {r['complementary_factor']}x)")
        print("-" * 50)

    try:
        print("\nConnecting to Firebase...")

        cred = credentials.Certificate('../firebase_cred.json')
  
  
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        batch = db.batch()
        collection_ref = db.collection('u_dynamic_shadow_prospects')
        
        for res in results[:2000]:
            doc_ref = collection_ref.document(str(res['player_id']))
            batch.set(doc_ref, res)
            
        batch.commit()
        print("Successfully saved new structures to Firebase!")
    except Exception as e:
        print(f"\n[!] Firebase upload skipped. Error: {e}")

if __name__ == "__main__":
    main()