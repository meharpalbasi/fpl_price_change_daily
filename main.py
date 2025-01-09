import requests
import pandas as pd
import os

from datetime import datetime

# --- Constants & Mappings ---
BASE_URL = "https://fantasy.premierleague.com/api/"
GENERAL = "bootstrap-static/"

type_mapping = {
    1: "GK",
    2: "DEF",
    3: "MID",
    4: "FWD",
    'u': "Unavailable",
    'a': "Available",
    'd': "Doubtful",
    'NaN': "Info unavailable"
}

YESTERDAY_FILE = "yesterday_costs.csv"

def fetch_fpl_data():
    """Fetch the latest FPL data and return it as a pandas DataFrame."""
    url = BASE_URL + GENERAL
    r = requests.get(url).json()
    players_df = pd.DataFrame(r['elements'])
    return players_df

def load_previous_day_costs(filename=YESTERDAY_FILE):
    """Load costs from a CSV if it exists; otherwise return None."""
    if os.path.exists(filename):
        return pd.read_csv(filename)
    else:
        return None

def save_today_costs(df_today, filename=YESTERDAY_FILE):
    """Save today's cost data to a CSV for future comparison."""
    # We only need 'id' and 'now_cost' to compare day-to-day
    df_today[['id','now_cost']].to_csv(filename, index=False)

def format_price_changes(df, change_type):
    arrow = '🔽' if change_type == 'Price Falls' else '🔼'
    message = f"{change_type} {arrow}\n\n"
    message += "Player   New Price   Old Price\n"
    
    for _, player in df.iterrows():
        message += (
            f"{player['web_name']}   "
            f"£{player['now_cost']/10:.1f}   "
            f"£{player['prev_cost']/10:.1f}\n"
        )
    return message.strip()

def main():
    # 1. Fetch today's data from the FPL API
    players_df = fetch_fpl_data()

    # 2. Create a cleaned DataFrame (just like you do now)
    players_clean_df = players_df[['id','web_name','cost_change_event','now_cost']].assign(
        position=players_df['element_type'].map(type_mapping),
        availability=players_df['status'].map(type_mapping)
    )

    # 3. Load yesterday's costs (if exists)
    df_yesterday = load_previous_day_costs()

    if df_yesterday is None:
        # First run: no file found, so create one with today's data
        save_today_costs(players_clean_df)
        print("Initialized yesterday_costs.csv with today's data. No price changes for today.")
        return
    else:
        # 4. Merge today's data with yesterday's
        merged_df = players_clean_df.merge(
            df_yesterday, 
            on='id', 
            how='left', 
            suffixes=("", "_yest")
        )

        # 5. If we have no 'yesterday' cost, fill it with today's to avoid NaN
        merged_df["now_cost_yest"] = merged_df["now_cost_yest"].fillna(merged_df["now_cost"])

        # 6. Compute daily change
        merged_df["daily_change"] = merged_df["now_cost"] - merged_df["now_cost_yest"]

        # 7. Add a 'prev_cost' column for clarity
        merged_df["prev_cost"] = merged_df["now_cost_yest"]

        # 8. Filter rows where there is an actual change
        price_changed_players = merged_df[merged_df["daily_change"] != 0].copy()

        # 9. Identify up vs down
        price_changed_players["arrow"] = price_changed_players["daily_change"].apply(
            lambda x: "up" if x > 0 else ("down" if x < 0 else "no_change")
        )

        # 10. Separate rises and falls
        price_rises = price_changed_players[price_changed_players["arrow"] == "up"]
        price_falls = price_changed_players[price_changed_players["arrow"] == "down"]

        # 11. Sort them if desired (by new price ascending)
        price_rises = price_rises.sort_values(by='now_cost', ascending=True)
        price_falls = price_falls.sort_values(by='now_cost', ascending=True)

        # 12. Format messages
        rises_message = format_price_changes(price_rises, 'Price Rises')
        falls_message = format_price_changes(price_falls, 'Price Falls')

        # 13. Print or do something with these messages
        if not price_rises.empty:
            print(rises_message)
        if not price_falls.empty:
            print("\n" + falls_message)

        if price_rises.empty and price_falls.empty:
            print("No price changes today.")

        # 14. Save today's data for tomorrow's comparison
        save_today_costs(players_clean_df)

if __name__ == "__main__":
    main()
