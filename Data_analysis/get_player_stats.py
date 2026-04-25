import json
import os

def get_player_statistics(target_id):
    # Resolve the path to the raw_data_sportmonks directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "raw_data_sportmonks")
    
    if not os.path.exists(data_dir):
        print(f"Error: Directory not found at {data_dir}")
        return

    print(f"Searching for player ID: {target_id} in {data_dir}...\n")

    # Iterate through the JSON files
    for filename in os.listdir(data_dir):
        if not filename.endswith(".json"):
            continue
            
        file_path = os.path.join(data_dir, filename)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue
            
        players = data.get("data", data) if isinstance(data, dict) else data
        
        for player in players:
            if str(player.get("id")) == str(target_id):
                name = player.get("display_name") or player.get("name", "Unknown")
                print(f"Found Player: {name} (ID: {target_id}) in file: {filename}")
                print("-" * 50)
                
                # 1. Extract Season Statistics (pre-aggregated totals from the provider)
                season_stats = {}
                for stat_season in player.get("statistics", []):
                    for detail in stat_season.get("details", []):
                        stat_name = detail.get("type", {}).get("name", "Unknown Stat")
                        val_obj = detail.get("value")
                        val = val_obj.get("total") if isinstance(val_obj, dict) else val_obj
                        
                        if val is not None:
                            try:
                                season_stats[stat_name] = season_stats.get(stat_name, 0.0) + float(val)
                            except (ValueError, TypeError):
                                pass
                
                # 2. Extract Lineups Statistics (granular match-by-match stats)
                match_stats_raw = {}
                for lineup in player.get("lineups", []):
                    for detail in lineup.get("details", []):
                        stat_name = detail.get("type", {}).get("name", "Unknown Stat")
                        data_obj = detail.get("data")
                        val = data_obj.get("value") if isinstance(data_obj, dict) else data_obj
                        
                        if val is not None:
                            try:
                                match_stats_raw.setdefault(stat_name, []).append(float(val))
                            except (ValueError, TypeError):
                                pass

                # 3. Aggregate Match-by-Match Statistics intelligently
                match_stats_agg = {}
                for stat_name, values in match_stats_raw.items():
                    if not values:
                        continue
                    # Averages for rates/percentages/ratings, otherwise sum the values
                    if "Percentage" in stat_name or "Rating" in stat_name:
                        match_stats_agg[stat_name] = sum(values) / len(values)
                    else:
                        match_stats_agg[stat_name] = sum(values)

                # Formatting helper to print integers cleanly, or floats to 2 decimals
                def format_val(v):
                    return int(v) if isinstance(v, float) and v.is_integer() else round(v, 2)

                # Output Results
                if season_stats:
                    print("Season Statistics (Pre-Aggregated):")
                    for stat, value in sorted(season_stats.items()):
                        print(f"  - {stat}: {format_val(value)}")
                else:
                    print("No season statistics found.")

                if match_stats_agg:
                    print("\nMatch-by-Match Aggregated Statistics:")
                    for stat, value in sorted(match_stats_agg.items()):
                        avg_marker = " (Avg)" if "Percentage" in stat or "Rating" in stat else ""
                        print(f"  - {stat}{avg_marker}: {format_val(value)}")
                else:
                    print("\nNo match-by-match statistics found in lineups.")
                
                return  # Exit after finding the target player

    print(f"Player with ID {target_id} was not found in any JSON files.")

if __name__ == "__main__":
    # Replace 10683 with any ID you want to look up
    get_player_statistics(13355)
