import requests
from datetime import datetime
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

nltk.download("vader_lexicon", quiet=True)
sia = SentimentIntensityAnalyzer()

def fetch_reddit_posts(
    query: str,
    limit: int = 50,
    subreddits: list[str] = ["Bitcoin","CryptoCurrency"]
) -> list[dict]:
    
    headers = {
       "User-Agent": "crypto-sentiment-dashboard/0.1 (by u/your_reddit_username)"
    }
    
    all_posts: list[dict]=[]
    
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/search.json"
        
        params={
            "q":query,
            "sort": "new",
            "restrict_sr":1,
            "limit": limit
        }
        resp = requests.get(url, params = params, headers = headers, timeout=10)
        resp.raise_for_status()
        
        for child in resp.json()["data"]["children"]:
            item=child["data"]
            all_posts.append({
                "time": datetime.fromtimestamp(item["created_utc"]),
                "title": item.get("title",""),
                "body": item.get("selftext",""),
                "permalink": f"https://reddit.com{item.get('permalink','')}"
            })
            
    all_posts.sort(key=lambda x: x["time"])
    return all_posts[-limit:]
app=dash.Dash(__name__)


dark_colors = {
    'background': '#0f1419',
    'card': '#1a1f2e',
    'accent': '#00d4aa',
    'text': '#ffffff',
    'text_secondary': '#8892b0',
    'border': '#233554',
    'positive': '#00ff88',
    'negative': '#ff6b6b',
    'neutral': '#64748b'
}

app.layout = html.Div(
    style={
        "background": f"linear-gradient(135deg, {dark_colors['background']} 0%, #1a1f2e 100%)",
        "minHeight": "100vh",
        "fontFamily": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        "color": dark_colors['text'],
        "padding": "0",
        "margin": "0"
    },
    children=[
        html.Div([
            html.H1("📈 Crypto Sentiment Tracker",
                    style={
                        "fontSize": "2.5rem",
                        "fontWeight": "700",
                        "margin": "0",
                        "background": f"linear-gradient(45deg, {dark_colors['accent']}, #00b4d8)",
                        "WebkitBackgroundClip": "text",
                        "WebkitTextFillColor": "transparent",
                    }),
            html.P("Real-time Reddit sentiment analysis for crypto markets",
                   style={
                       "fontSize": "1.1rem",
                       "color": dark_colors['text_secondary'],
                       "margin": "8px 0 0 0",
                       "fontWeight": "400"
                   })
        ], style={"textAlign": "center", "padding": "40px 20px"}),
        
        html.Div([
            html.Div([
                html.Label("Search Term",
                           style={
                               "fontSize": "1rem",
                               "fontWeight": "600",
                               "color": dark_colors['text'],
                               "marginBottom": "8px",
                               "display": "block"
                           }),
                dcc.Input(
                    id="query-input",
                    type="text",
                    value="bitcoin",  # default term
                    style={
                        "width": "100%",
                        "padding": "12px 16px",
                        "border": f"2px solid {dark_colors['border']}",
                        "borderRadius": "8px",
                        "backgroundColor": dark_colors['card'],
                        "color": dark_colors['text'],
                        "fontSize": "1rem",
                        "outline": "none",
                        "transition": "all 0.3s ease"
                    }
                ),
            ], style={
                "backgroundColor": dark_colors['card'],
                "padding": "24px",
                "borderRadius": "12px",
                "border": f"1px solid {dark_colors['border']}",
                "marginBottom": "24px",
                "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.3)"
            }),

            html.Div([
                dcc.Graph(id="sentiment-graph", style={"height": "400px"}, config={'displayModeBar': False})
            ], style={
                "backgroundColor": dark_colors['card'],
                "borderRadius": "12px",
                "border": f"1px solid {dark_colors['border']}",
                "marginBottom": "24px",
                "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.3)",
                "overflow": "hidden"
            }),

            html.Div([
                html.H3("🔍 Recent Reddit Posts",
                       style={
                           "fontSize": "1.5rem",
                           "fontWeight": "600",
                           "margin": "0 0 20px 0",
                           "color": dark_colors['text']
                       }),
                html.Div(id="recent-posts")
            ], style={
                "backgroundColor": dark_colors['card'],
                "padding": "24px",
                "borderRadius": "12px",
                "border": f"1px solid {dark_colors['border']}",
                "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.3)"
            }),

        ], style={
            "maxWidth": "1000px",
            "margin": "0 auto",
            "padding": "24px"
        }),

        html.Div([
            html.Span("🔄 Auto-refreshing every 60 seconds",
                      style={
                          "fontSize": "0.9rem",
                          "color": dark_colors['text_secondary'],
                          "fontStyle": "italic"
                      })
        ], style={
            "textAlign": "center",
            "padding": "20px",
            "borderTop": f"1px solid {dark_colors['border']}"
        }),

        dcc.Interval(id="interval", interval=60*1000, n_intervals=0)
    ]
)

@app.callback(
    [Output("sentiment-graph","figure"),
     Output("recent-posts","children")],
    [Input("query-input","value"),
     Input("interval","n_intervals")]
)
def update_graph_and_list(query:str, n: int):
    
    posts = fetch_reddit_posts(query=query, limit=50)
    
    if not posts:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="No data available",
            paper_bgcolor=dark_colors['card'],
            plot_bgcolor=dark_colors['card'],
            font_color=dark_colors['text']
        )
        return empty_fig, html.Div([
            html.P("No recent posts found.",
                   style={
                       "textAlign": "center",
                       "color": dark_colors['text_secondary'],
                       "fontSize": "1.1rem",
                       "padding": "40px"
                   })
        ])

    scored = []
    for p in posts:
        text = f"{p['title']}\n\n{p['body']}"
        comp = sia.polarity_scores(text)["compound"]
        scored.append({"time": p["time"], "score": comp})

    df = pd.DataFrame(scored).sort_values("time")
    df["rolling"] = df["score"].rolling(window=5, min_periods=1).mean()

    line_color = dark_colors['accent']
    fill_color = f"rgba(0, 212, 170, 0.1)"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["rolling"],
        fill='tonexty', fillcolor=fill_color,
        line=dict(color=line_color, width=3), mode="lines",
        hovertemplate="<b>%{y:.3f}</b><br>%{x}<extra></extra>"
    ))
    fig.add_hline(y=0, line_dash="dash", line_color=dark_colors['text_secondary'], opacity=0.5)
    fig.update_layout(
        title={
            'text': f"Sentiment Trend: {query.title()}",
            'x': 0.5, 'xanchor': 'center',
            'font': {'size': 20, 'color': dark_colors['text']}
        },
        xaxis_title="Time (UTC)", yaxis_title="Sentiment Score",
        yaxis=dict(range=[-1, 1], gridcolor=dark_colors['border'], zerolinecolor=dark_colors['border']),
        xaxis=dict(gridcolor=dark_colors['border']),
        paper_bgcolor=dark_colors['card'], plot_bgcolor=dark_colors['card'],
        font=dict(color=dark_colors['text']), margin={"l":60,"r":30,"t":60,"b":50},
        hovermode="x unified", showlegend=False
    )

    recent_elems = []
    for p in posts[-20:][::-1]:
        time_str = p["time"].strftime("%m/%d %H:%M")
        sentiment_score = sia.polarity_scores(f"{p['title']}\n\n{p['body']}")["compound"]

        if sentiment_score > 0.1:
            border_color = dark_colors['positive']
            sentiment_emoji = "📈"
        elif sentiment_score < -0.1:
            border_color = dark_colors['negative']
            sentiment_emoji = "📉"
        else:
            border_color = dark_colors['neutral']
            sentiment_emoji = "➖"

        recent_elems.append(html.Div([
            html.Div([
                html.Span(sentiment_emoji, style={"marginRight":"8px","fontSize":"1.1rem"}),
                html.A(p["title"], href=p["permalink"], target="_blank",
                       style={"color": dark_colors['text'],"fontWeight":"500"})
            ], style={"marginBottom":"8px"}),
            html.Div([
                html.Span(f"{time_str} UTC", style={"color": dark_colors['text_secondary']}),
                html.Span(f"Score: {sentiment_score:.2f}",
                          style={"color": border_color,"fontWeight":"500","marginLeft":"12px"})
            ]),
            html.P(p["body"][:150] + ("..." if len(p["body"])>150 else ""),
                   style={"margin":"8px 0 0 0","fontSize":"0.9rem",
                          "lineHeight":"1.4","color": dark_colors['text_secondary']})
        ], style={
            "padding":"16px","marginBottom":"12px","backgroundColor": dark_colors['background'],
            "borderRadius":"8px","border":f"1px solid {dark_colors['border']}",
            "borderLeft":f"4px solid {border_color}","transition":"all 0.2s ease"
        }))

    return fig, recent_elems

if __name__ == "__main__":
    print("Starting Crypto Reddit Sentiment Dashboard")
    app.run(debug=True)