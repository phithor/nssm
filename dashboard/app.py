"""
NSSM - Norwegian/Swedish Stock Market Monitor Dashboard
Interactive dashboard showing Top Buzzing Stocks, sentiment charts, and news overlay.
"""

import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import data layer functions
from .data import (
    get_available_tickers,
    get_buzzing_heatmap_data,
    get_dashboard_stats,
    get_news_overlay,
    get_sentiment_price_series,
)

# Page configuration
st.set_page_config(
    page_title="NSSM Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 0.25rem solid #1f77b4;
    }
    .sidebar-header {
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


def main():
    """Main dashboard function"""
    st.markdown(
        '<h1 class="main-header">📈 NSSM Dashboard</h1>', unsafe_allow_html=True
    )
    st.markdown("*Norwegian/Swedish Stock Market Monitor*")
    st.markdown("---")

    # Sidebar filters with state management
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-header">🔧 Dashboard Filters</div>',
            unsafe_allow_html=True,
        )

        # Initialize session state for filters
        if "start_date" not in st.session_state:
            st.session_state.start_date = datetime.now() - timedelta(days=7)
        if "end_date" not in st.session_state:
            st.session_state.end_date = datetime.now()
        if "selected_tickers" not in st.session_state:
            st.session_state.selected_tickers = []
        if "anomaly_threshold" not in st.session_state:
            st.session_state.anomaly_threshold = 2.0
        if "sentiment_filter" not in st.session_state:
            st.session_state.sentiment_filter = (-1.0, 1.0)
        if "news_sources" not in st.session_state:
            st.session_state.news_sources = ["openbb", "oslobors", "nasdaq"]

        # Time Range Section
        st.markdown("### 📅 Time Range")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=st.session_state.start_date,
                help="Select start date for analysis",
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=st.session_state.end_date,
                help="Select end date for analysis",
            )

        # Update session state
        st.session_state.start_date = start_date
        st.session_state.end_date = end_date

        # Ticker Selection Section
        st.markdown("### 📊 Tickers")
        available_tickers = get_available_tickers()

        if available_tickers:
            # Quick select buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Select All", help="Select all available tickers"):
                    st.session_state.selected_tickers = available_tickers
                    st.rerun()
            with col2:
                if st.button("Clear All", help="Clear all ticker selections"):
                    st.session_state.selected_tickers = []
                    st.rerun()
            with col3:
                if st.button("Top 5", help="Select top 5 tickers by activity"):
                    st.session_state.selected_tickers = available_tickers[:5]
                    st.rerun()

            selected_tickers = st.multiselect(
                "Select Tickers",
                available_tickers,
                default=st.session_state.selected_tickers,
                help=f"Select tickers to analyze ({len(available_tickers)} available)",
                label_visibility="collapsed",
            )
            st.session_state.selected_tickers = selected_tickers
        else:
            st.warning(
                "⚠️ No tickers available in database. Please run data ingestion first."
            )
            selected_tickers = []

        # Analysis Filters Section
        st.markdown("### 🎯 Analysis Filters")

        # Anomaly threshold
        anomaly_threshold = st.slider(
            "Anomaly Threshold (σ)",
            min_value=1.0,
            max_value=5.0,
            value=st.session_state.anomaly_threshold,
            step=0.5,
            help="Z-score threshold for anomaly detection",
        )
        st.session_state.anomaly_threshold = anomaly_threshold

        # Sentiment range filter
        sentiment_filter = st.slider(
            "Sentiment Range",
            min_value=-1.0,
            max_value=1.0,
            value=st.session_state.sentiment_filter,
            step=0.1,
            help="Filter sentiment data within this range",
        )
        st.session_state.sentiment_filter = sentiment_filter

        # News sources filter
        st.markdown("### 📰 News Sources")
        news_sources = st.multiselect(
            "News Sources",
            ["openbb", "oslobors", "nasdaq"],
            default=st.session_state.news_sources,
            help="Select news sources to include",
        )
        st.session_state.news_sources = news_sources

        # Actions Section
        st.markdown("### ⚡ Actions")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Data", type="primary", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with col2:
            if st.button("🔧 Reset Filters", use_container_width=True):
                # Reset all filters to defaults
                st.session_state.start_date = datetime.now() - timedelta(days=7)
                st.session_state.end_date = datetime.now()
                st.session_state.selected_tickers = (
                    available_tickers[:2] if available_tickers else []
                )
                st.session_state.anomaly_threshold = 2.0
                st.session_state.sentiment_filter = (-1.0, 1.0)
                st.session_state.news_sources = ["openbb", "oslobors", "nasdaq"]
                st.cache_data.clear()
                st.rerun()

        # Filter Summary
        st.markdown("### 📋 Active Filters")
        with st.expander("Filter Summary", expanded=False):
            st.write(
                f"**Date Range:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            )
            st.write(
                f"**Selected Tickers:** {len(selected_tickers)} ({', '.join(selected_tickers[:3])}{'...' if len(selected_tickers) > 3 else ''})"
            )
            st.write(f"**Anomaly Threshold:** {anomaly_threshold}σ")
            st.write(
                f"**Sentiment Range:** {sentiment_filter[0]:.1f} to {sentiment_filter[1]:.1f}"
            )
            st.write(f"**News Sources:** {', '.join(news_sources)}")

            # Data freshness indicator
            last_update = datetime.now()
            st.write(f"**Last Update:** {last_update.strftime('%H:%M:%S')}")

        # Performance metrics
        st.markdown("### 📈 Performance")
        st.metric(
            "Session Active",
            f"{(datetime.now() - st.session_state.start_date).days} days",
        )
        st.metric("Data Freshness", "Real-time")

    # Main content area
    if not selected_tickers:
        st.warning("Please select at least one ticker to display data.")
        return

    # Get dashboard statistics
    dashboard_stats = get_dashboard_stats(start_date, end_date)

    # Metrics overview
    st.subheader("📊 Market Overview")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Active Tickers", dashboard_stats["unique_tickers"])

    with col2:
        st.metric("Time Period", f"{(end_date - start_date).days} days")

    with col3:
        st.metric("Total Posts", f"{dashboard_stats['total_posts']:,}")

    with col4:
        st.metric("Avg Sentiment", f"{dashboard_stats['avg_sentiment']:.3f}")

    # Charts section (placeholders for subtasks 8.3 and 8.4)
    st.markdown("---")
    st.subheader("📈 Market Sentiment Analysis")

    # Heatmap for Top Buzzing Stocks
    st.subheader("🔥 Top Buzzing Stocks Heatmap")

    # Get anomaly data for heatmap
    heatmap_data = get_buzzing_heatmap_data(start_date, end_date)

    if not heatmap_data.empty:
        # Process data for heatmap
        heatmap_data["date"] = heatmap_data["window_start"].dt.date
        heatmap_data["hour"] = heatmap_data["window_start"].dt.hour

        # Pivot data for heatmap (ticker vs time)
        heatmap_pivot = heatmap_data.pivot_table(
            values="zscore",
            index="ticker",
            columns="date",
            aggfunc="mean",
            fill_value=0,
        )

        if not heatmap_pivot.empty:
            # Create heatmap
            fig = px.imshow(
                heatmap_pivot.values,
                x=heatmap_pivot.columns,
                y=heatmap_pivot.index,
                color_continuous_scale="RdYlGn_r",  # Red for negative, Green for positive
                labels=dict(x="Date", y="Ticker", color="Z-Score"),
                title="Stock Sentiment Anomalies (Z-Score)",
                aspect="auto",
            )

            # Update layout
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Ticker",
                coloraxis_colorbar=dict(
                    title="Z-Score",
                    tickvals=[-3, -2, -1, 0, 1, 2, 3],
                    ticktext=["-3σ", "-2σ", "-1σ", "0", "+1σ", "+2σ", "+3σ"],
                ),
            )

            # Add annotations for extreme values
            max_z = heatmap_data["zscore"].max()
            min_z = heatmap_data["zscore"].min()

            if abs(max_z) >= 2 or abs(min_z) >= 2:
                st.info(
                    "💡 Anomalies with |Z-Score| ≥ 2σ indicate unusual sentiment activity"
                )

            st.plotly_chart(fig, use_container_width=True)

            # Show top anomalies table
            st.subheader("📊 Top Sentiment Anomalies")
            top_anomalies = heatmap_data.nlargest(10, "zscore")[
                ["ticker", "window_start", "zscore", "direction", "post_count"]
            ]
            top_anomalies["window_start"] = top_anomalies["window_start"].dt.strftime(
                "%Y-%m-%d %H:%M"
            )
            st.dataframe(
                top_anomalies,
                column_config={
                    "ticker": "Ticker",
                    "window_start": "Time",
                    "zscore": st.column_config.NumberColumn("Z-Score", format="%.2f"),
                    "direction": "Direction",
                    "post_count": "Posts",
                },
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No anomaly data available for the selected time period.")
    else:
        st.info(
            "No anomaly data available for the selected time period. Anomalies are detected when sentiment activity significantly deviates from normal patterns."
        )

    # Sentiment vs Price Analysis with News Overlay
    st.subheader("📊 Sentiment vs Price Analysis")

    # Select ticker for detailed analysis
    if len(selected_tickers) > 1:
        analysis_ticker = st.selectbox(
            "Select ticker for detailed analysis:",
            selected_tickers,
            help="Choose one ticker to see detailed sentiment vs price analysis",
        )
    else:
        analysis_ticker = selected_tickers[0] if selected_tickers else None

    if analysis_ticker:
        # Get data for the selected ticker
        sentiment_df, price_df = get_sentiment_price_series(
            analysis_ticker, start_date, end_date
        )
        news_df = get_news_overlay(analysis_ticker, start_date, end_date)

        # Create the dual-axis chart
        fig = go.Figure()

        # Add price line (primary y-axis)
        if not price_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=price_df["timestamp"],
                    y=price_df["price"],
                    name=f"{analysis_ticker} Price",
                    line=dict(color="#1f77b4", width=2),
                    mode="lines",
                    hovertemplate="Price: %{y:.2f}<br>%{x}<extra></extra>",
                )
            )

            # Add price range if available
            if "high" in price_df.columns and "low" in price_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=price_df["timestamp"],
                        y=price_df["high"],
                        fill=None,
                        mode="lines",
                        line=dict(color="rgba(31, 119, 180, 0.3)", width=1),
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=price_df["timestamp"],
                        y=price_df["low"],
                        fill="tonexty",
                        mode="lines",
                        line=dict(color="rgba(31, 119, 180, 0.3)", width=1),
                        fillcolor="rgba(31, 119, 180, 0.1)",
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )

        # Add sentiment line (secondary y-axis)
        if not sentiment_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=sentiment_df["timestamp"],
                    y=sentiment_df["sentiment"],
                    name="Sentiment",
                    line=dict(color="#ff7f0e", width=2),
                    mode="lines+markers",
                    yaxis="y2",
                    hovertemplate="Sentiment: %{y:.3f}<br>Posts: %{customdata}<br>%{x}<extra></extra>",
                    customdata=sentiment_df["post_count"],
                )
            )

        # Add news events as markers
        if not news_df.empty:
            # Filter news by importance (show only high importance or all if few)
            if len(news_df) > 20:
                news_df = news_df[news_df["importance"] >= 0.7]

            for _, news_item in news_df.iterrows():
                # Determine marker color based on category
                marker_color = (
                    "#2ca02c" if news_item["category"] == "news" else "#d62728"
                )

                fig.add_trace(
                    go.Scatter(
                        x=[news_item["published_at"]],
                        y=[0],  # Position at y=0 for visibility
                        mode="markers",
                        marker=dict(
                            symbol="diamond",
                            size=10,
                            color=marker_color,
                            line=dict(width=2, color="white"),
                        ),
                        name=f"News: {news_item['headline'][:30]}...",
                        hovertemplate="<b>%{text}</b><br>Source: %{customdata}<br>Time: %{x|%Y-%m-%d %H:%M}<extra></extra>",
                        showlegend=False,
                    )
                )

        # Update layout for dual axes
        fig.update_layout(
            title=f"{analysis_ticker} - Sentiment vs Price Analysis",
            xaxis=dict(title="Time", type="date", tickformat="%Y-%m-%d %H:%M"),
            yaxis=dict(
                title="Price",
                titlefont=dict(color="#1f77b4"),
                tickfont=dict(color="#1f77b4"),
                showgrid=False,
            ),
            yaxis2=dict(
                title="Sentiment Score",
                titlefont=dict(color="#ff7f0e"),
                tickfont=dict(color="#ff7f0e"),
                overlaying="y",
                side="right",
                range=[-1, 1],
                tickvals=[-1, -0.5, 0, 0.5, 1],
                ticktext=["-1.0", "-0.5", "0.0", "0.5", "1.0"],
            ),
            hovermode="x unified",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            height=500,
        )

        # Add correlation analysis
        if not sentiment_df.empty and not price_df.empty:
            # Simple correlation calculation
            try:
                # Merge dataframes on timestamp (simplified)
                merged_df = pd.merge_asof(
                    sentiment_df.sort_values("timestamp"),
                    price_df.sort_values("timestamp"),
                    on="timestamp",
                    direction="nearest",
                ).dropna()

                if len(merged_df) > 5:
                    correlation = merged_df["sentiment"].corr(merged_df["price"])
                    st.metric("Sentiment-Price Correlation", f"{correlation:.3f}")

                    if abs(correlation) > 0.3:
                        st.info(
                            f"📈 {'Strong positive' if correlation > 0 else 'Strong negative'} correlation between sentiment and price ({correlation:.3f})"
                        )
                    elif abs(correlation) > 0.1:
                        st.info(
                            f"📊 Moderate correlation between sentiment and price ({correlation:.3f})"
                        )
            except Exception as e:
                st.warning(
                    "Could not calculate correlation due to data alignment issues."
                )

        st.plotly_chart(fig, use_container_width=True)

        # Show recent news
        if not news_df.empty:
            st.subheader("📰 Recent News & Events")
            recent_news = news_df.nlargest(5, "importance")[
                ["published_at", "headline", "source", "importance"]
            ]
            recent_news["published_at"] = recent_news["published_at"].dt.strftime(
                "%Y-%m-%d %H:%M"
            )

            st.dataframe(
                recent_news,
                column_config={
                    "published_at": "Time",
                    "headline": st.column_config.TextColumn("Headline", width="large"),
                    "source": "Source",
                    "importance": st.column_config.NumberColumn(
                        "Importance", format="%.2f"
                    ),
                },
                hide_index=True,
                use_container_width=True,
            )
    else:
        st.info(
            "Please select at least one ticker to view sentiment vs price analysis."
        )

    # Footer
    st.markdown("---")
    st.markdown(
        "*Dashboard automatically refreshes every 5 minutes. Last updated: {}*".format(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )


if __name__ == "__main__":
    main()
