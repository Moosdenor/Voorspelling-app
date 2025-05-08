import streamlit as st
from finvizfinance.screener.overview import Overview
from finvizfinance.insider import Insider
from finvizfinance.news import News
import pandas as pd
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import mplfinance as mpf
from datetime import datetime
import ccxt
import plotly.graph_objects as go  # Importeer Plotly


# Functie voor het berekenen van technische indicatoren
def bereken_technische_indicatoren(df):
    # Simple Moving Average (SMA)
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()

    # Exponential Moving Average (EMA)
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()

    # Relative Strength Index (RSI)
    delta = df['Close'].diff()
    up, down = delta.clip(lower=0), -delta.clip(upper=0)
    ma_up = up.rolling(window=14).mean()
    ma_down = down.rolling(window=14).mean()
    rs = ma_up / ma_down
    df['RSI'] = 100 - (100 / (1 + rs))

    # Moving Average Convergence Divergence (MACD)
    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    df.dropna(inplace=True)
    return df


st.set_page_config(page_title="📊 Gokken Dashboard", layout="wide")

st.title("📈 Gokken Dashboard")
st.markdown("""
Deze applicatie helpt je bij het identificeren van potentiële aandelen en crypto om te kopen of verkopen, gebaseerd op fundamentele filters, insider trading-gegevens en nieuws.
""")

# Initialiseer sessiestatus voor watchlist
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []

# Maak keuze tussen aandelen en crypto
type_selectie = st.sidebar.radio("Selecteer type:", ["Aandelen Gokken", "Crypto Gokken"])

if type_selectie == "Aandelen Gokken":
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📋 Aandelenlijst", "🕵️ Insider Trading", "📰 Nieuws", "📈 Sector & Insider Analyse"])

    with tab1:
        st.subheader("📋 Gefilterde Aandelenlijst")
        # Stap 1: Definieer aankoopfilters
        filters = {
            'Market Cap.': '+Small (over $300mln)',
            'Average Volume': 'Over 500K',
            'Price': 'Over $10',
            '50-Day Simple Moving Average': 'Price above SMA50',
            '200-Day Simple Moving Average': 'Price above SMA200',
            'EPS growththis year': 'Over 20%'
        }

        # Stap 2: Haal aandelen op die aan de filters voldoen
        overview = Overview()
        overview.set_filter(filters_dict=filters)
        screener_df = overview.screener_view()

        # Toon aantal aandelen en timestamp
        st.write(f"Aantal aandelen gevonden: {len(screener_df)}")
        st.write(f"Laatst bijgewerkt op: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Voeg checkboxen toe om aandelen aan watchlist toe te voegen
        selected_tickers = st.multiselect("Selecteer aandelen om toe te voegen aan je watchlist:",
                                            screener_df['Ticker'])
        if st.button("Toevoegen aan watchlist"):
            st.session_state.watchlist.extend(selected_tickers)
            st.success(f"{', '.join(selected_tickers)} toegevoegd aan watchlist.")

        st.dataframe(screener_df)

    with tab2:
        st.subheader("🕵️ Insider Trading Activiteit")
        try:
            insider = Insider(option='latest')
            insider_df = insider.get_insider()
            st.dataframe(insider_df)
        except Exception as e:
            st.error(f"Fout bij het ophalen van insider data: {e}")

    with tab3:
        st.subheader("📰 Laatste Nieuws met Sentimentanalyse")
        news = News()
        news_data = news.get_news()
        news_df = pd.DataFrame(news_data['news'])

        analyzer = SentimentIntensityAnalyzer()
        news_df['Sentiment'] = news_df['Title'].apply(lambda x: analyzer.polarity_scores(x)['compound'])
        news_df['Sentiment Label'] = news_df['Sentiment'].apply(
            lambda x: 'Positief' if x > 0.05 else ('Negatief' if x < -0.05 else 'Neutraal')
        )
        st.dataframe(news_df[['Date', 'Title', 'Sentiment', 'Sentiment Label']])

    with tab4:
        st.subheader("📈 Beste en Slechtst Presterende Sectoren in 2025")

        # Geactualiseerde sectorprestaties voor 2025
        sector_data = {
            'Sector': [
                'Industrials',
                'Energy',
                'Basic Materials',
                'Telecommunications Services',
                'Financials',
                'Healthcare',
                'Consumer Discretionary',
                'Utilities',
                'Technology',
                'Real Estate',
                'Consumer Staples'
            ],
            'Rendement (%)': [
                18.0,
                15.0,
                12.0,
                10.0,
                8.0,
                6.0,
                4.0,
                2.0,
                -1.0,
                -3.0,
                -5.0
            ]
        }
        sector_df = pd.DataFrame(sector_data)
        st.dataframe(sector_df)

        # Visualisatie van sectorprestaties
        st.bar_chart(sector_df.set_index('Sector'))

        # Beste en slechtst presterende sectoren
        best_sector = sector_df.loc[sector_df['Rendement (%)'].idxmax()]
        worst_sector = sector_df.loc[sector_df['Rendement (%)'].idxmin()]
        st.markdown(f"**Beste sector:** {best_sector['Sector']} ({best_sector['Rendement (%)']}%)")
        st.markdown(f"**Slechtste sector:** {worst_sector['Sector']} ({worst_sector['Rendement (%)']}%)")

        st.subheader("🕵️ Meest en Minst Actieve Insider Traders")
        try:
            # Analyseer insider trading-gegevens
            insider = Insider(option='latest')
            insider_df = insider.get_insider()

            # Groepeer op 'Insider' en tel het aantal transacties
            insider_counts = insider_df['Insider'].value_counts().reset_index()
            insider_counts.columns = ['Insider', 'Aantal Transacties']

            # Meest actieve insiders
            top_insiders = insider_counts.head(5)
            st.markdown("**Meest actieve insiders:**")
            st.dataframe(top_insiders)

            # Minst actieve insiders (met meer dan 1 transactie)
            least_active_insiders = insider_counts[insider_counts['Aantal Transacties'] > 1].tail(5)
            st.markdown("**Minst actieve insiders (met meer dan 1 transactie):**")
            st.dataframe(least_active_insiders)
        except Exception as e:
            st.error(f"Fout bij het analyseren van insider data: {e}")

elif type_selectie == "Crypto Gokken":
    tab5, tab6, tab7, tab8 = st.tabs(
        ["🪙 Crypto Screener", "🐳 Crypto Insider", "🔮 Crypto Voorspelling", "🚀 Top 10 Stijgers/Dalers"])

    with tab5:
        st.subheader("🪙 Crypto Screener")
        try:
            exchange = ccxt.binance()
            markets = exchange.load_markets()
            tickers = exchange.fetch_tickers()

            data = []
            for k, v in tickers.items():
                if '/USDT' in k:
                    data.append({
                        'Symbol': k,
                        'Last Price': v['last'],
                        '24h Change': v['percentage'],
                        'Volume': v['baseVolume']
                    })

            df = pd.DataFrame(data)
            st.dataframe(df)
        except Exception as e:
            st.error(f"Fout bij het ophalen van crypto data: {e}")

    with tab6:
        st.subheader("🐳 Crypto Insider Analyse")
        st.write("Analyseert grote transacties (walvissen) op de blockchain om potentiële insider-activiteit te detecteren.")

        crypto_symbol_insider = st.text_input("Voer de crypto ticker in (bijv: BTC/USDT):", "BTC/USDT",
                                                key="crypto_insider")
        try:
            exchange = ccxt.binance()
            trades = exchange.fetch_trades(crypto_symbol_insider, limit=20)
            trades_df = pd.DataFrame(trades)
            st.dataframe(trades_df)
        except Exception as e:
            st.error(f"Fout bij het ophalen van transactie data: {e}")

    with tab7:
        st.subheader("🔮 Crypto Voorspelling")
        crypto_symbol_voorspelling = st.text_input("Voer de crypto ticker in (bijv: BTC/USDT):", "BTC/USDT",
                                                    key="crypto_voorspelling")
        try:
            exchange = ccxt.binance()
            data = exchange.fetch_ohlcv(crypto_symbol_voorspelling, timeframe='1d', limit=100)
            df = pd.DataFrame(data, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
            df.set_index('Timestamp', inplace=True)

            # Bereken technische indicatoren
            df = bereken_technische_indicatoren(df)

            # Plot candlestick chart met technische indicatoren
            fig = go.Figure(go.Candlestick(x=df.index,
                                            open=df['Open'],
                                            high=df['High'],
                                            low=df['Low'],
                                            close=df['Close'],
                                            name='Candlestick'))

            # Voeg SMA lijnen toe
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='blue'), name='SMA 20'))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='red'), name='SMA 50'))

            st.plotly_chart(fig, use_container_width=True)

            # Display RSI and MACD
            st.subheader("RSI")
            st.line_chart(df['RSI'])
            st.subheader("MACD")
            st.line_chart(df[['MACD', 'Signal_Line']])

            # Eenvoudige trading signalen (voorbeeld)
            if df['RSI'].iloc[-1] < 30:
                st.success("Koop Signaal (RSI < 30)")
            elif df['RSI'].iloc[-1] > 70:
                st.warning("Verkoop Signaal (RSI > 70)")

        except Exception as e:
            st.error(f"Fout bij het ophalen van crypto data of berekeningen: {e}")

    with tab8:
        st.subheader("🚀 Top 10 Stijgers en Dalers")
        try:
            exchange = ccxt.binance()
            tickers = exchange.fetch_tickers()

            data = []
            for k, v in tickers.items():
                if '/USDT' in k and v['percentage'] is not None:
                    data.append({
                        'Symbol': k,
                        '24h Change': v['percentage']
                    })

            df = pd.DataFrame(data)

            # Sorteer op stijging en daling
            df_stijgers = df.sort_values(by='24h Change', ascending=False).head(10)
            df_dalers = df.sort_values(by='24h Change', ascending=True).head(10)

            st.subheader("Top 10 Stijgers")
            st.dataframe(df_stijgers)

            st.subheader("Top 10 Dalers")
            st.dataframe(df_dalers)

        except Exception as e:
            st.error(f"Fout bij het ophalen van crypto data: {e}")

# Stap 5: Toon watchlist met realtime gegevens en technische analyse
st.subheader("📌 Watchlist Analyse")
for ticker in st.session_state.watchlist:
    st.markdown(f"### {ticker}")
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Toon KPI's
        kpis = {
            'P/E Ratio': info.get('trailingPE'),
            'ROE': info.get('returnOnEquity'),
            'Debt/Equity': info.get('debtToEquity')
        }
        st.write("**Kerncijfers:**")
        st.write(kpis)

        # Haal historische gegevens op voor technische analyse
        hist = stock.history(period='3mo')
        if not hist.empty:
            mpf.plot(hist, type='candle', mav=(20, 50), volume=True, style='yahoo',
                     title=f'{ticker} Candlestick Chart')
        else:
            st.write("Geen historische gegevens beschikbaar voor technische analyse.")
    except Exception as e:
        st.error(f"Fout bij het ophalen van ticker info: {e}")
