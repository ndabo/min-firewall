import re
import pathlib
import pandas as pd
import streamlit as st

LOG_PATH = pathlib.Path(__file__).resolve().parent.parent / "logs" / "mif-firewall.log"


@st.cache_data(ttl=60)  # Cache for 60 seconds so you’re not re-reading the file on every widget interaction
def load_logs(log_path: pathlib.Path) -> pd.DataFrame:
    """
    Reads the mif-firewall.log (plain-text) and returns a DataFrame with:
      - timestamp (datetime)
      - is_blocked  (True if level==WARNING)
      - user_id     (we’ll treat the IP address as “user_id” here)
    Args:
        path (str): Path to the CSV file containing logs.
    Returns:
        pd.DataFrame: DataFrame containing the logs with correct data types.
    """
    pattern = re.compile(
        r"(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - "
        r"mif_firewall - (?P<level>INFO|WARNING) - "
        r"(Allowed|Blocked) request from IP (?P<ip>[\d\.]+):"
    )

    logs = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.match(line)
            if not m:
                continue
            ts_str = m.group("ts")
            level = m.group("level")           # “INFO” or “WARNING”
            ip = m.group("ip")                 # e.g. “127.0.0.1”

            # Convert timestamp to Python datetime
            ts = pd.to_datetime(ts_str, format="%Y-%m-%d %H:%M:%S")

            is_blocked = True if level == "WARNING" else False

            logs.append({
                "timestamp": ts,
                "user_id": ip,
                "is_blocked": is_blocked,
                # Note: we don’t yet log token usage in this file; see step 4 below
                "tokens_used": None
            })

    df = pd.DataFrame(logs)
    return df

def main():
    st.set_page_config(page_title="MIF Admin Dashboard", layout="wide")
    st.title("🔐 Model Inference Firewall: Admin Dashboard")
    st.markdown("This dashboard provides an overview of the Model Inference Firewall (MIF) logs.")

    # Load & optionally filter by date range
    df = load_logs(LOG_PATH)

    st.sidebar.header("Date Range Filter")
    min_date = df["timestamp"].dt.date.min()
    max_date = df["timestamp"].dt.date.max()
    start_date = st.sidebar.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
    end_date   = st.sidebar.date_input("End Date",   value=max_date, min_value=min_date, max_value=max_date)

    mask = (df["timestamp"].dt.date >= start_date) & (df["timestamp"].dt.date <= end_date)
    filtered_df = df.loc[mask] #create a filtered DataFrame

    # Compute key metrics
    total_requests  = len(filtered_df)
    threats_blocked = filtered_df["is_blocked"].sum()

    # We haven’t yet captured tokens in the log, so for now just show “N/A” or prompt how to add it.
    total_tokens = "N/A"

    # Token usage per user: placeholder until you log tokens in your proxy
    st.subheader("Key Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Requests", f"{total_requests:,}")
    col2.metric("Threats Blocked", f"{int(threats_blocked):,}")
    col3.metric("Total Tokens Used", total_tokens)

    st.markdown("---")

    # Show “requests per user” (blocked vs. allowed) as a table
    st.subheader("Requests by User (IP address)")

    # Group by user_id and compute counts
    summary = (
        filtered_df
        .groupby("user_id")
        .agg(
            total_requests=("user_id", "count"),
            threats_blocked=("is_blocked", "sum")
        )
        .reset_index() #turns the grouped "user_id" back into a regular column, rather than keeping it as the DataFrame index.
        .sort_values("total_requests", ascending=False)
    )
    st.dataframe(summary, use_container_width=True)

    # If you want a simple bar chart of top IPs by request volume:
    #this code snippet adds an interactive bar chart to the Streamlit dashboard n\
    # allowing users to visualize the most active users by request count.
    top_n = st.sidebar.slider("Show top N users by request count", 5, 20, 10)
    top_users = summary.head(top_n).set_index("user_id")
    st.subheader(f"Top {top_n} Users by Request Count")
    st.bar_chart(top_users["total_requests"])


if __name__ == "__main__":
    main()