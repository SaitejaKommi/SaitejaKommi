import os
import sys
import json
import re
from datetime import datetime, timezone
import urllib.request
import urllib.error

USERNAME = "SaitejaKommi"
DATA_FILE = os.path.join("assets", "generated", "contribution-data.json")

WEEKDAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

def fetch_via_graphql(token):
    url = "https://api.github.com/graphql"
    query = """
    query($user: String!) {
      user(login: $user) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                color
                weekday
              }
            }
          }
        }
      }
    }
    """
    req = urllib.request.Request(
        url,
        data=json.dumps({"query": query, "variables": {"user": USERNAME}}).encode("utf-8"),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "SaitejaKommi-Mario-Profile"
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        
    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    total = calendar["totalContributions"]
    all_days = []
    for w_idx, week in enumerate(calendar["weeks"]):
        for day in week["contributionDays"]:
            # GitHub GraphQL weekday: 0=Sunday, 1=Monday, ..., 6=Saturday
            cnt = int(day["contributionCount"])
            level = 0
            if cnt > 0:
                if cnt <= 2:
                    level = 1
                elif cnt <= 5:
                    level = 2
                elif cnt <= 8:
                    level = 3
                else:
                    level = 4
            all_days.append({
                "date": day["date"],
                "contributions": cnt,
                "level": level,
                "weekday": day.get("weekday", 0),
                "week_idx": w_idx
            })
    return total, all_days

def fetch_via_html():
    url = f"https://github.com/users/{USERNAME}/contributions"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8")
        
    # Match td elements with id, date, level
    td_pattern = re.compile(
        r'<td[^>]*id="(contribution-day-component-[^"]+)"[^>]*data-date="([^"]+)"[^>]*data-level="([^"]+)"',
        re.DOTALL
    )
    td_matches = td_pattern.findall(html)
    if not td_matches:
        td_pattern = re.compile(
            r'<td[^>]*data-date="([^"]+)"[^>]*id="(contribution-day-component-[^"]+)"[^>]*data-level="([^"]+)"',
            re.DOTALL
        )
        td_matches = [(cid, dt, lvl) for dt, cid, lvl in td_pattern.findall(html)]

    tip_pattern = re.compile(r'<tool-tip[^>]*for="(contribution-day-component-[^"]+)"[^>]*>([^<]+)</tool-tip>')
    tips = dict(tip_pattern.findall(html))

    if not td_matches:
        raise ValueError("Could not parse contribution TD elements from GitHub HTML")

    all_days = []
    for cid, dt, lvl in td_matches:
        tip_text = tips.get(cid, "")
        m = re.search(r'(\d+)\s+contribution', tip_text)
        cnt = int(m.group(1)) if m else 0
        
        # Calculate weekday: Sun=0, Mon=1, ..., Sat=6
        d_obj = datetime.strptime(dt, "%Y-%m-%d")
        w_sun = (d_obj.weekday() + 1) % 7
        
        all_days.append({
            "date": dt,
            "contributions": cnt,
            "level": int(lvl) if lvl.isdigit() else (1 if cnt > 0 else 0),
            "weekday": w_sun
        })

    # Sort chronologically
    all_days.sort(key=lambda x: x["date"])
    
    # Calculate week indices based on Sunday starts
    w_idx = 0
    for i, d in enumerate(all_days):
        if i > 0 and d["weekday"] == 0:
            w_idx += 1
        d["week_idx"] = w_idx

    total = sum(d["contributions"] for d in all_days)
    return total, all_days

def calculate_streaks(all_days):
    if not all_days:
        return 0, 0
    
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    
    for d in all_days:
        if d["contributions"] > 0:
            temp_streak += 1
            if temp_streak > longest_streak:
                longest_streak = temp_streak
        else:
            temp_streak = 0
            
    # Calculate current streak up to latest day
    idx = len(all_days) - 1
    if idx >= 0 and all_days[idx]["contributions"] == 0:
        # Check if today has 0, maybe yesterday was active
        idx -= 1
        
    while idx >= 0 and all_days[idx]["contributions"] > 0:
        current_streak += 1
        idx -= 1
        
    return current_streak, longest_streak

def organize_into_calendar_grid(all_days):
    # Total weeks
    num_weeks = max(d["week_idx"] for d in all_days) + 1
    
    # Grid: 7 rows x num_weeks columns
    # grid[weekday_row][week_col]
    grid = [[None for _ in range(num_weeks)] for _ in range(7)]
    
    for d in all_days:
        r = d["weekday"]
        c = d["week_idx"]
        grid[r][c] = d

    # Also build month headers: detect which week columns start a new month
    month_labels = []
    prev_month = None
    for c in range(num_weeks):
        # find first valid day in column
        col_days = [grid[r][c] for r in range(7) if grid[r][c] is not None]
        if col_days:
            dt = datetime.strptime(col_days[0]["date"], "%Y-%m-%d")
            m_str = dt.strftime("%b")
            if m_str != prev_month:
                month_labels.append({"week_idx": c, "month": m_str})
                prev_month = m_str

    # Build per-row summary
    row_summaries = []
    for r in range(7):
        row_days = [grid[r][c] for c in range(num_weeks) if grid[r][c] is not None]
        total_row_contrib = sum(d["contributions"] for d in row_days)
        active_days = sum(1 for d in row_days if d["contributions"] > 0)
        row_summaries.append({
            "weekday": r,
            "name": WEEKDAY_NAMES[r],
            "total_contributions": total_row_contrib,
            "active_days": active_days,
            "total_days": len(row_days)
        })

    return grid, num_weeks, month_labels, row_summaries

def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    total_contributions = 0
    all_days = []
    
    if token:
        try:
            print("Fetching contributions via GitHub GraphQL API...")
            total_contributions, all_days = fetch_via_graphql(token)
            print(f"GraphQL succeeded: {len(all_days)} days, {total_contributions} contributions.")
        except Exception as e:
            print(f"GraphQL fetch failed: {e}. Trying HTML fallback...")
            
    if not all_days:
        try:
            print("Fetching contributions via HTML fallback...")
            total_contributions, all_days = fetch_via_html()
            print(f"HTML fallback succeeded: {len(all_days)} days, {total_contributions} contributions.")
        except Exception as e:
            print(f"HTML fetch failed: {e}.")
            sys.exit(1)

    all_days.sort(key=lambda x: x["date"])
    
    # Calculate streaks
    current_streak, longest_streak = calculate_streaks(all_days)
    
    # Organize into 7-row calendar grid
    grid, num_weeks, month_labels, row_summaries = organize_into_calendar_grid(all_days)
    
    active_days_total = sum(1 for d in all_days if d["contributions"] > 0)
    
    result = {
        "username": USERNAME,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_contributions": total_contributions,
        "active_days": active_days_total,
        "total_calendar_days": len(all_days),
        "num_weeks": num_weeks,
        "start_date": all_days[0]["date"],
        "end_date": all_days[-1]["date"],
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "weekday_names": WEEKDAY_NAMES,
        "month_labels": month_labels,
        "row_summaries": row_summaries,
        "grid": grid,
        "all_days": all_days
    }
    
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        
    print(f"\n==================== DATA SUMMARY ====================")
    print(f"User: {USERNAME}")
    print(f"Calendar Period: {all_days[0]['date']} to {all_days[-1]['date']} ({num_weeks} weeks, 7 weekday rows)")
    print(f"Total Contributions: {total_contributions} (Active Days: {active_days_total}/{len(all_days)})")
    print(f"Current Streak: {current_streak} days | Longest Streak: {longest_streak} days")
    print("\nWeekday Corridors:")
    for rs in row_summaries:
        print(f"  Row {rs['weekday']} ({rs['name']}): {rs['total_contributions']:3d} contributions across {rs['active_days']:2d} active days")
    print(f"Data saved to {DATA_FILE}")
    print(f"======================================================\n")

if __name__ == "__main__":
    main()
