import requests
import pandas as pd
import os

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

def fetch_fpl_data():
    """Fetch the latest FPL data and return it as a pandas DataFrame."""
    url = BASE_URL + GENERAL
    r = requests.get(url).json()
    players_df = pd.DataFrame(r['elements'])
    return players_df

def load_yesterday_costs(filename="yesterday_costs.csv"):
    """
    Load yesterday's cost data from a CSV.
    Return an empty DataFrame if the file does not exist.
    """
    if os.path.exists(filename):
        return pd.read_csv(filename)
    else:
        return pd.DataFrame()

def save_today_costs(df, filename="yesterday_costs.csv"):
    """
    Save today's cost data (player ID + now_cost) to a CSV
    so we can compare tomorrow.
    """
    df[['id','now_cost']].to_csv(filename, index=False)

def format_price_changes(df, change_type):
    """
    Return a formatted string listing the players who have
    changed price (up or down).
    """
    arrow = '🔽' if change_type == 'Price Falls' else '🔼'
    message = f"{change_type} {arrow}\n\n"
    message += "Player   New Price   Old Price\n"
    
    for _, player in df.iterrows():
        message += (f"{player['web_name']}   "
                    f"£{player['now_cost']/10:.1f}   "
                    f"£{player['prev_cost']/10:.1f}\n")
    return message.strip()

def main():
    # 1. Fetch today's data
    players_df = fetch_fpl_data()
    
    # 2. Load yesterday's data
    yesterday_df = load_yesterday_costs()

    # 3. Clean up today's data with your typical approach:
    players_clean_df = players_df[["id", "web_name", "now_cost", "cost_change_event"]].assign(
        position=players_df['element_type'].map(type_mapping),
        availability=players_df['status'].map(type_mapping)
    )

    # 4. Merge with yesterday's data to get "yesterday's now_cost"
    #    so we can compare directly day-to-day.
    merged_df = players_clean_df.merge(
        yesterday_df, 
        on="id", 
        how="left", 
        suffixes=("", "_yest")
    )
    # If there's no yesterday data, fill with today's cost to avoid NaN
    merged_df["now_cost_yest"] = merged_df["now_cost_yest"].fillna(merged_df["now_cost"])

    # 5. Compute the daily change by comparing now_cost to yesterday's now_cost
    merged_df["daily_change"] = merged_df["now_cost"] - merged_df["now_cost_yest"]

    # 6. Create columns for new/previous cost for display
    merged_df["prev_cost"] = merged_df["now_cost_yest"]
    
    # 7. Filter out players who changed price
    price_changed_players = merged_df[merged_df["daily_change"] != 0].copy()
    
    # 8. Add an arrow column (up/down) based on daily_change
    price_changed_players["arrow"] = price_changed_players["daily_change"].apply(
        lambda x: "up" if x > 0 else ("down" if x < 0 else "no_change")
    )

    # 9. Separate rises and falls
    price_rises = price_changed_players[price_changed_players["arrow"] == "up"]
    price_falls = price_changed_players[price_changed_players["arrow"] == "down"]

    # 10. Sort them (optional: e.g., by now_cost ascending)
    price_rises = price_rises.sort_values(by='now_cost', ascending=True)
    price_falls = price_falls.sort_values(by='now_cost', ascending=True)

    # 11. Format messages
    falls_message = format_price_changes(price_falls, 'Price Falls')
    rises_message = format_price_changes(price_rises, 'Price Rises')

    # 12. Print or send the messages
    print(falls_message)
    print("\n" + "-"*40 + "\n")
    print(rises_message)

    # 13. Save today's costs for tomorrow's comparison
    save_today_costs(players_clean_df)

if __name__ == "__main__":
    main()
