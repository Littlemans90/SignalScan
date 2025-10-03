"""
SignalScan - DEBUG VERSION - Windowed Mode
Version 4.0 DEBUG - 24/7 Ready + Glowing Colored News Buttons
VOL/RVOL FIXED - Smart on-demand company news - Yahoo Finance indices
FINAL FIX: Volume seeding with yfinance fallback
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.config import Config
import datetime
import pytz
import os
from dotenv import load_dotenv
import threading
import time
import requests
import json
import websocket
import ssl
import yfinance as yf

load_dotenv()

# DEBUG MODE: Windowed, resizable, with borders
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'borderless', '0')
Config.set('graphics', 'resizable', '1')
Config.set('graphics', 'width', '1400')
Config.set('graphics', 'height', '900')
Config.write()

print("DEBUG MODE: Window should appear on main screen")


class NewsManager:
    """Manages breaking news: Finnhub ONLY (24/7 unlimited) - SMART ON-DEMAND"""

    def __init__(self, callback, watchlist=None):
        self.callback = callback
        self.watchlist = set([x.upper() for x in (watchlist or [])])
        self.finnhub_key = os.getenv('FINNHUB_API_KEY')
        self.running = False
        self.news_cache = {}
        self.company_news_fetched = set()
        self.breaking_keywords = [
            'breaking', 'just announced', 'unconfirmed', 'exclusive',
            'soars', 'record', 'beat', 'expands', 'strong demand',
            'plunges', 'recall', 'layoffs', 'bankruptcy', 'downgrade',
            'fda approval', 'phase 3 results', 'patent granted', 'new product launch',
            'breakthrough technology', 'ai integration',
            'acquisition', 'merger', 'buyout', 'takeover offer', 'partnership',
            'strategic investment',
            'ceo resignation', 'ceo appointment', 'insider buying', 'insider selling',
            'board shakeup',
            'earnings beat', 'earnings miss', 'revenue up', 'revenue down',
            'guidance raised', 'guidance cut', 'eps above expectations',
            'eps below expectations', 'record profit', 'record loss', 'upgrade',
            'sec investigation', 'lawsuit settlement', 'antitrust', 'sanctions',
            'rate hike', 'rate cut',
            'jumps', 'drops', 'hits new 52-week', 'unusual volume'
        ]

    def start_news_stream(self):
        self.running = True
        threading.Thread(target=self._finnhub_news_loop, daemon=True).start()
        print("Starting Finnhub news monitoring (24/7)...")

    def _finnhub_news_loop(self):
        while self.running:
            try:
                self.fetch_finnhub_news()
                time.sleep(10)
            except Exception as e:
                print(f"Finnhub news error: {e}")
                time.sleep(15)

    def fetch_finnhub_news(self):
        """Fetch general market news"""
        try:
            url = f"https://finnhub.io/api/v1/news?category=general&token={self.finnhub_key}"
            response = requests.get(url, timeout=5)
            data = response.json()

            if isinstance(data, list):
                print(f"[DEBUG] Fetched {len(data)} general news articles")
                for article in data[:20]:
                    self.process_news_article(article)

        except Exception as e:
            print(f"Finnhub general news fetch error: {e}")

    def fetch_company_news_on_demand(self, symbol):
        """SMART: Fetch company-specific news when stock becomes channel candidate"""
        symbol = symbol.upper()
        if symbol in self.company_news_fetched:
            return

        print(f"[SMART NEWS] Fetching company-specific news for {symbol}")

        try:
            to_date = datetime.datetime.now().strftime('%Y-%m-%d')
            from_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')

            url = f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={from_date}&to={to_date}&token={self.finnhub_key}"
            response = requests.get(url, timeout=5)
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                for article in data[:3]:
                    if 'related' not in article or not article['related']:
                        article['related'] = symbol
                    elif symbol not in article['related']:
                        article['related'] = f"{article['related']},{symbol}"

                    self.process_news_article(article, source='company')

                print(f"[SMART NEWS] Found {min(3, len(data))} articles for {symbol}")
            else:
                print(f"[SMART NEWS] No recent news for {symbol}")

            self.company_news_fetched.add(symbol)

        except Exception as e:
            print(f"Company news error for {symbol}: {e}")

    def process_news_article(self, article, source='general'):
        """Process and allocate news ONLY to related symbols"""
        try:
            title = article.get('headline', '') or article.get('title', '')
            content = article.get('summary', '') or article.get('description', '')
            related_str = article.get('related', '') or article.get('symbols', '')
            article_id = article.get('id') or article.get('url') or ''
            timestamp = article.get('datetime', 0)

            if not article_id:
                article_id = f"{title[:80]}::{timestamp}"

            if article_id in self.news_cache:
                return
            self.news_cache[article_id] = True

            headline_content = (title + " " + content).lower()
            is_breaking = any(keyword.lower() in headline_content for keyword in self.breaking_keywords)

            if related_str:
                symbols = [s.strip().upper() for s in related_str.split(',') if s.strip()]
            else:
                symbols = []

            matched_symbols = [s for s in symbols if s in self.watchlist]

            if not matched_symbols:
                is_crypto_news = "crypto" in headline_content or "cryptocurrency" in headline_content

                if is_breaking and is_crypto_news:
                    # broadcast to first 3 watchlist items as fallback
                    for symbol in list(self.watchlist)[:3]:
                        news_data = {
                            'symbol': symbol,
                            'title': f"[CRYPTO] {title}",
                            'content': content,
                            'is_breaking': True,
                            'timestamp': timestamp
                        }
                        Clock.schedule_once(lambda dt, nd=news_data: self.callback(nd), 0)
                    print(f"[DEBUG] Crypto breaking news broadcast to top 3 stocks")
                return

            for symbol in matched_symbols:
                if symbol.startswith("CRYPTO:") or symbol.startswith("FOREX:"):
                    continue

                news_data = {
                    'symbol': symbol,
                    'title': title,
                    'content': content,
                    'is_breaking': is_breaking,
                    'timestamp': timestamp
                }
                Clock.schedule_once(lambda dt, nd=news_data: self.callback(nd), 0)

                if is_breaking:
                    print(f"[BREAKING] {symbol}: {title[:60]}...")
                else:
                    print(f"[NEWS] {symbol}: {title[:60]}...")

        except Exception as e:
            print(f"Error processing article: {e}")

    def stop(self):
        self.running = False


class MarketDataManager:
    """Manages Finnhub WebSocket + Yahoo Finance Indices"""

    def __init__(self, callback, news_manager_ref=None):
        self.callback = callback
        self.news_manager_ref = news_manager_ref
        self.finnhub_key = os.getenv('FINNHUB_API_KEY')
        self.ws = None
        self.running = False
        self.stock_data = {}
        self.watchlist = []
        self.stock_metrics = {}
        self.seeding_complete = False
        self.market_open_time = None

    def fetch_all_tradable_stocks(self):
        """Fetch top 100 US stocks"""
        print("Using top 100 US stocks...")
        self.watchlist = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B', 'UNH', 'JNJ',
            'V', 'XOM', 'WMT', 'LLY', 'JPM', 'PG', 'MA', 'HD', 'CVX', 'ABBV',
            'MRK', 'AVGO', 'KO', 'PEP', 'COST', 'ADBE', 'MCD', 'CSCO', 'CRM', 'ACN',
            'TMO', 'NFLX', 'ABT', 'DHR', 'LIN', 'VZ', 'TXN', 'INTC', 'NKE', 'AMD',
            'QCOM', 'PM', 'WFC', 'UPS', 'RTX', 'NEE', 'ORCL', 'HON', 'SPGI', 'INTU',
            'LOW', 'IBM', 'CAT', 'BA', 'GE', 'ELV', 'AMGN', 'NOW', 'GS', 'ISRG',
            'DE', 'BLK', 'SYK', 'AXP', 'BKNG', 'GILD', 'ADI', 'MDLZ', 'TJX', 'MMC',
            'VRTX', 'PLD', 'CB', 'SCHW', 'LRCX', 'SBUX', 'CI', 'AMT', 'SLB', 'TMUS',
            'ZTS', 'MO', 'REGN', 'PYPL', 'CVS', 'BMY', 'DUK', 'FI', 'SO', 'EQIX',
            'PGR', 'BDX', 'ITW', 'AON', 'APD', 'CL', 'ETN', 'MU', 'BSX', 'SHW'
        ]
        print(f"Loaded {len(self.watchlist)} stocks")

    def load_stock_metrics_batch(self):
        """Load stock metrics + seed volume BEFORE WebSocket connects"""
        print("Loading stock metrics + seeding volume (2 min)...")

        # Capture self references in local scope for thread safety
        watchlist = self.watchlist
        finnhub_key = self.finnhub_key
        stock_data = self.stock_data
        stock_metrics = self.stock_metrics
        parent_self = self

        def batch_load():
            for i, symbol in enumerate(watchlist):
                try:
                    # Get quote data from Finnhub
                    quote_url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={finnhub_key}"
                    quote_response = requests.get(quote_url, timeout=5)
                    quote_data = quote_response.json()

                    # Get profile data from Finnhub
                    profile_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={finnhub_key}"
                    profile_response = requests.get(profile_url, timeout=5)
                    profile_data = profile_response.json()

                    # CRITICAL FIX: Finnhub returns 0 volume during live hours, use yfinance fallback
                    todays_volume = float(quote_data.get('v', 0)) if quote_data.get('v') else 0

                    if todays_volume == 0:
                        # Fallback to yfinance for current volume
                        try:
                            ticker = yf.Ticker(symbol)
                            info = ticker.info or {}
                            todays_volume = float(info.get('volume', info.get('regularMarketVolume', 0) or 0))
                        except Exception as yf_error:
                            print(f"[WARN] yfinance fallback failed for {symbol}: {yf_error}")
                            todays_volume = 0

                    prev_close = float(quote_data.get('pc', 0) or 0)
                    current_price = float(quote_data.get('c', prev_close) or prev_close)

                    # Seed volume BEFORE WebSocket starts
                    stock_data[symbol] = {
                        'volume': todays_volume,
                        'price': current_price,
                        'timestamp': time.time()
                    }

                    if i < 3:
                        print(f"[DEBUG] Seeded {symbol}: {todays_volume:,.0f} volume")

                    # Use market cap to estimate average volume
                    market_cap = float(profile_data.get('marketCapitalization', 0) or 0)

                    # For average volume, try to get from yfinance since it's more reliable
                    avg_volume_estimate = None
                    try:
                        ticker = yf.Ticker(symbol)
                        info = ticker.info or {}
                        avg_volume_estimate = float(info.get('averageVolume', info.get('averageDailyVolume10Day', 0) or 0))
                    except Exception:
                        avg_volume_estimate = None

                    # Fallback: use today's volume or market cap estimation
                    if not avg_volume_estimate or avg_volume_estimate == 0:
                        if todays_volume > 0:
                            avg_volume_estimate = max(int(todays_volume * 1.5), 1)
                        elif market_cap > 0:
                            if market_cap > 1000:
                                avg_volume_estimate = 80_000_000
                            elif market_cap > 100:
                                avg_volume_estimate = 50_000_000
                            elif market_cap > 10:
                                avg_volume_estimate = 10_000_000
                            else:
                                avg_volume_estimate = 5_000_000
                        else:
                            avg_volume_estimate = 50_000_000

                    stock_metrics[symbol] = {
                        'prev_close': prev_close,
                        'avg_volume': avg_volume_estimate,
                        'float': float(profile_data.get('shareOutstanding', 0) or 0)
                    }

                    if (i + 1) % 10 == 0:
                        print(f"Loaded {i + 1}/{len(watchlist)} stocks...")

                    time.sleep(1.2)

                except Exception as e:
                    print(f"Error loading {symbol}: {e}")
                    stock_metrics[symbol] = {
                        'prev_close': None,
                        'avg_volume': 50_000_000,
                        'float': None
                    }

            parent_self.seeding_complete = True
            print("[DEBUG] All stock metrics loaded + volume seeded!")

        threading.Thread(target=batch_load, daemon=True).start()

    def start_websocket(self):
        """Start Finnhub WebSocket connection"""
        self.fetch_all_tradable_stocks()
        self.load_stock_metrics_batch()
        self.running = True

        est = pytz.timezone('US/Eastern')
        now_est = datetime.datetime.now(est)
        self.market_open_time = now_est.replace(hour=9, minute=30, second=0, microsecond=0)

        thread = threading.Thread(target=self._run_websocket, daemon=True)
        thread.start()

        print("Starting Finnhub WebSocket...")

    def _run_websocket(self):
        """Run Finnhub WebSocket connection"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if data.get('type') == 'trade':
                    for trade in data.get('data', []):
                        symbol = trade.get('s', '')
                        price = trade.get('p', 0)
                        volume = trade.get('v', 0)
                        timestamp = trade.get('t', 0)

                        if not self.seeding_complete:
                            continue

                        if symbol not in self.stock_data:
                            self.stock_data[symbol] = {'volume': 0, 'price': price, 'timestamp': timestamp}

                        current_volume = self.stock_data[symbol].get('volume', 0)
                        self.stock_data[symbol]['volume'] = current_volume + volume
                        self.stock_data[symbol]['price'] = price
                        self.stock_data[symbol]['timestamp'] = timestamp

                        if self.callback:
                            Clock.schedule_once(
                                lambda dt, s=symbol, d=self.stock_data[symbol]: self.callback(s, d),
                                0
                            )
            except Exception as e:
                print(f"WebSocket message error: {e}")

        def on_error(ws, error):
            print(f"WebSocket error: {error}")

        def on_close(ws, close_status_code, close_msg):
            print(f"WebSocket closed: {close_status_code} - {close_msg}")
            if self.running:
                print("Reconnecting WebSocket in 5 seconds...")
                time.sleep(5)
                self._run_websocket()

        def on_open(ws):
            print("[DEBUG] Finnhub WebSocket connected")
            for symbol in self.watchlist:
                try:
                    ws.send(json.dumps({'type': 'subscribe', 'symbol': symbol}))
                except Exception as err:
                    print(f"Error subscribing to {symbol}: {err}")

        websocket.enableTrace(False)
        ws_url = f"wss://ws.finnhub.io?token={self.finnhub_key}"
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )

        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def get_stock_metrics(self, symbol):
        """Get cached stock metrics"""
        return self.stock_metrics.get(symbol, {
            'prev_close': None,
            'avg_volume': 50_000_000,
            'float': None
        })

    def calculate_rvol(self, symbol, current_volume):
        """Calculate time-adjusted RVOL"""
        try:
            metrics = self.get_stock_metrics(symbol)
            avg_daily_volume = metrics.get('avg_volume', 50_000_000)

            if avg_daily_volume <= 0 or current_volume <= 0:
                return 0.0

            est = pytz.timezone('US/Eastern')
            now_est = datetime.datetime.now(est)

            if self.market_open_time and now_est >= self.market_open_time:
                elapsed_minutes = (now_est - self.market_open_time).total_seconds() / 60

                if elapsed_minutes < 60:
                    expected_ratio = 0.40 * (elapsed_minutes / 60)
                elif elapsed_minutes < 120:
                    expected_ratio = 0.40 + 0.25 * ((elapsed_minutes - 60) / 60)
                else:
                    expected_ratio = min(elapsed_minutes / 390, 1.0)

                expected_volume = avg_daily_volume * expected_ratio

                if expected_volume > 0:
                    rvol = current_volume / expected_volume
                    return rvol

            return current_volume / avg_daily_volume

        except Exception as e:
            print(f"RVOL calc error for {symbol}: {e}")
            return 0.0

    def is_strong_channel_candidate(self, symbol, change_pct, rvol):
        """SMART: Determine if stock is strong channel candidate worthy of company news"""
        if abs(change_pct) > 5:
            return True
        if change_pct > 2:
            return True
        if rvol > 3.0:
            return True
        return False

    def get_index_data(self, symbol):
        """Get index data using Yahoo Finance (free, unlimited, reliable)"""
        try:
            yahoo_symbol_map = {
                ".IXIC": "^IXIC",
                ".SPX": "^GSPC"
            }
            yahoo_symbol = yahoo_symbol_map.get(symbol, symbol)

            ticker = yf.Ticker(yahoo_symbol)
            hist = ticker.history(period="1d", interval="1m")

            if hist is not None and not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
                info = ticker.info or {}
                prev_close = float(info.get('previousClose', info.get('regularMarketPreviousClose', current_price) or current_price))

                if prev_close > 0:
                    change_pct = ((current_price - prev_close) / prev_close) * 100
                    print(f"[DEBUG] {yahoo_symbol} = ${current_price:.2f} ({change_pct:+.2f}%)")
                    return current_price, change_pct
                else:
                    return current_price, 0.0
            else:
                print(f"[DEBUG] No history data for {yahoo_symbol}")

        except Exception as e:
            print(f"Yahoo Finance error for {symbol}: {e}")
            import traceback
            traceback.print_exc()

        return 0.0, 0.0

    def stop(self):
        """Stop WebSocket connection"""
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass


class SignalScanApp(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print("[DEBUG] Initializing SignalScanApp...")
        self.orientation = "vertical"
        self.spacing = 0
        self.padding = 0

        with self.canvas.before:
            Color(0.08, 0.08, 0.08, 1)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_bg, pos=self._update_bg)

        self.live_data = {
            "PreGap": [],
            "HOD": [],
            "RunUp": [],
            "RunDown": [],
            "Rvsl": [],
            "Halts": []
        }

        self.stock_news = {}
        self.current_channel = "RunUp"
        self.nasdaq_last, self.nasdaq_pct = 0.0, 0.0
        self.sp_last, self.sp_pct = 0.0, 0.0

        self.news_manager = None
        self.market_data = MarketDataManager(callback=self.on_websocket_update, news_manager_ref=None)

        self.build_header()
        main_content = BoxLayout(orientation="vertical", spacing=0, padding=0)
        self.tabs_container = self.build_channel_tabs()
        main_content.add_widget(self.tabs_container)
        self.data_container = self.build_data_section()
        main_content.add_widget(self.data_container)
        self.add_widget(main_content)

        Clock.schedule_interval(self.update_times, 1)
        Clock.schedule_once(self.start_market_data, 2)
        Clock.schedule_once(self.start_news_feed, 3)
        Clock.schedule_once(self.update_indices, 5)

        print("[DEBUG] SignalScanApp initialized successfully")

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def start_market_data(self, dt=None):
        """Initialize market data streams"""
        print("Starting market data streams...")
        self.market_data.start_websocket()

    def start_news_feed(self, dt=None):
        """Initialize news feed"""
        wl = [s.upper() for s in self.market_data.watchlist] if self.market_data.watchlist else []
        self.news_manager = NewsManager(callback=self.on_news_update, watchlist=wl)
        self.market_data.news_manager_ref = self.news_manager
        self.news_manager.start_news_stream()

    def on_websocket_update(self, symbol, data):
        """Callback when WebSocket receives new data"""
        self.process_stock_update(symbol, data)

    def on_news_update(self, news_data):
        """Callback when breaking news arrives"""
        symbol = news_data['symbol']
        title = news_data['title']
        is_breaking = news_data.get('is_breaking', False)

        if symbol not in self.stock_news:
            self.stock_news[symbol] = {'title': title, 'is_breaking': is_breaking}

        if is_breaking:
            self.stock_news[symbol]['tier'] = 2
        else:
            self.stock_news[symbol]['tier'] = 3

        Clock.schedule_once(lambda dt: self.refresh_data_table(), 0)

    def process_stock_update(self, symbol, data):
        """Process stock data update and categorize"""
        try:
            price = data.get('price', 0)
            volume = data.get('volume', 0)

            if price == 0:
                return

            metrics = self.market_data.get_stock_metrics(symbol)
            prev_close = metrics.get('prev_close')
            float_shares = metrics.get('float')
            
            if symbol in ['UNH', 'NEE', 'LLY', 'DHR']:
                print(f"[DEBUG FLOAT] {symbol}: raw float_shares={float_shares} (type: {type(float_shares)})")
            
            if prev_close and prev_close > 0:
                change_pct = ((price - prev_close) / prev_close * 100)
            else:
                change_pct = 0.0

            if float_shares and float_shares > 0:
                # Finnhub returns shareOutstanding ALREADY IN MILLIONS
                if float_shares >= 1000:  # 1000 million = 1 billion
                    float_str = f"{float_shares/1000:.1f}B"
                else:  # Less than 1000 million = show as millions
                    float_str = f"{float_shares:.1f}M"
    
                # Debug verification
                if symbol in ['UNH', 'NEE', 'LLY', 'DHR']:
                    print(f"[DEBUG FLOAT] {symbol}: formatted as {float_str}")
            else:
                float_str = "N/A"

                if symbol in ['UNH', 'NEE', 'LLY', 'DHR']:
                    print(f"[DEBUG FLOAT] {symbol}: formatted as {float_str}")
            
            rvol = self.market_data.calculate_rvol(symbol, volume)
            rvol_str = f"{rvol:.2f}x" if rvol > 0 else "0.00x"

            if self.market_data.is_strong_channel_candidate(symbol, change_pct, rvol):
                if self.news_manager and symbol not in self.news_manager.company_news_fetched:
                    threading.Thread(
                        target=self.news_manager.fetch_company_news_on_demand,
                        args=(symbol,),
                        daemon=True
                    ).start()

            formatted_data = [
                symbol,
                f"${price:.2f}",
                f"{change_pct:+.1f}%",
                self.format_volume(volume),
                float_str,
                rvol_str,
                ""
            ]

            self.categorize_stock(formatted_data, change_pct, volume)
            Clock.schedule_once(lambda dt: self.refresh_data_table(), 0)

        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    def categorize_stock(self, stock_data, change_pct, volume):
        """Categorize stock into scanner channels"""
        ticker = stock_data[0]

        # remove existing entries for ticker across channels
        for channel in self.live_data:
            self.live_data[channel] = [s for s in self.live_data[channel] if s[0] != ticker]

        # Categorize into channels (these are additive)
        if abs(change_pct) > 5:
            self.live_data["PreGap"].append(stock_data)
        if change_pct > 2:
            self.live_data["HOD"].append(stock_data)
        if change_pct > 0:
            self.live_data["RunUp"].append(stock_data)
        if change_pct < 0:
            self.live_data["RunDown"].append(stock_data)
        if volume > 1_000_000:
            self.live_data["Rvsl"].append(stock_data)

    def update_indices(self, dt=None):
        """Update NASDAQ and S&P 500 data via Yahoo Finance with smart scheduling"""
        print("Fetching index data from Yahoo Finance...")
        self.nasdaq_last, self.nasdaq_pct = self.market_data.get_index_data(".IXIC")
        self.sp_last, self.sp_pct = self.market_data.get_index_data(".SPX")

        self.nasdaq_label.text = f"NASDAQ  {self.nasdaq_pct:+.1f}%"
        self.nasdaq_label.color = (0, 1, 0, 1) if self.nasdaq_pct > 0 else (1, 0, 0, 1)

        self.sp_label.text = f"S&P     {self.sp_pct:+.1f}%"
        self.sp_label.color = (0, 1, 0, 1) if self.sp_pct > 0 else (1, 0, 0, 1)

        est = pytz.timezone('US/Eastern')
        now_est = datetime.datetime.now(est)
        state, _ = self.get_market_state_and_color(now_est)

        if state == "Market Open":
            next_interval = 300
        elif state in ["PreMarket", "After Hours"]:
            next_interval = 900
        else:
            next_interval = 1800

        Clock.unschedule(self.update_indices)
        Clock.schedule_once(self.update_indices, next_interval)

    def format_volume(self, volume):
        """Format volume in millions/billions"""
        try:
            volume = int(volume)
        except Exception:
            return str(volume)

        if volume >= 1_000_000_000:
            return f"{volume/1_000_000_000:.1f}B"
        elif volume >= 1_000_000:
            return f"{volume/1_000_000:.1f}M"
        elif volume >= 1_000:
            return f"{volume/1_000:.1f}K"
        return str(int(volume))

    def build_header(self):
        header = BoxLayout(orientation="horizontal", size_hint=(1, None), height=80, padding=[15, 10, 15, 10])
        with header.canvas.before:
            Color(0.12, 0.12, 0.12, 1)
            header.bg_rect = Rectangle(size=header.size, pos=header.pos)
        header.bind(size=lambda inst, val: setattr(header.bg_rect, "size", inst.size))
        header.bind(pos=lambda inst, val: setattr(header.bg_rect, "pos", inst.pos))

        title = Label(text="SignalScan [DEBUG]", font_size=28, color=(1, 1, 0, 1), bold=True, size_hint=(None, 1), width=250)
        header.add_widget(title)

        times_section = BoxLayout(orientation="vertical", spacing=5, size_hint=(None, 1), width=160)
        self.local_time_label = Label(text="Local Time    7:00 PM", font_size=14, color=(0.8, 0.8, 0.8, 1))
        self.nyc_time_label = Label(text="NYC Time     10:00 PM", font_size=14, color=(0.8, 0.8, 0.8, 1))
        times_section.add_widget(self.local_time_label)
        times_section.add_widget(self.nyc_time_label)
        header.add_widget(times_section)

        center_section = BoxLayout(orientation="vertical", spacing=5, size_hint=(None, 1), width=160)
        self.market_state_label = Label(text="Weekend", font_size=16, color=(1, 0.6, 0, 1), bold=True)
        self.countdown_label = Label(text="00:00:00", font_size=14, color=(1, 0.6, 0, 1))
        center_section.add_widget(self.market_state_label)
        center_section.add_widget(self.countdown_label)
        header.add_widget(center_section)

        indicators_section = BoxLayout(orientation="vertical", spacing=5, size_hint=(None, 1), width=140)
        self.nasdaq_label = Label(text=f"NASDAQ  +0.0%", font_size=13, color=(0, 1, 0, 1), bold=True)
        self.sp_label = Label(text=f"S&P     +0.0%", font_size=13, color=(0, 1, 0, 1), bold=True)
        indicators_section.add_widget(self.nasdaq_label)
        indicators_section.add_widget(self.sp_label)
        header.add_widget(indicators_section)

        header.add_widget(Label(text="", size_hint=(1, 1)))

        exit_btn = Button(text="✖", font_size=18, size_hint=(None, None), size=(35, 35),
                          background_color=(0.6, 0.2, 0.2, 1), color=(1, 1, 1, 1))
        exit_btn.bind(on_release=self.exit_app)
        header.add_widget(exit_btn)

        self.add_widget(header)

    def build_channel_tabs(self):
        tabs_container = BoxLayout(orientation="horizontal", size_hint=(1, None), height=45, spacing=0, padding=0)
        with tabs_container.canvas.before:
            Color(0.1, 0.1, 0.1, 1)
            tabs_container.bg_rect = Rectangle(size=tabs_container.size, pos=tabs_container.pos)
        tabs_container.bind(size=lambda inst, val: setattr(tabs_container.bg_rect, "size", inst.size))
        tabs_container.bind(pos=lambda inst, val: setattr(tabs_container.bg_rect, "pos", inst.pos))

        channels = ["PreGap", "HOD", "RunUp", "RunDown", "Rvsl", "Halts"]
        self.channel_buttons = {}

        for channel in channels:
            btn = Button(text=channel, font_size=16, size_hint=(1, 1), bold=True)
            if channel == self.current_channel:
                btn.background_color = (0, 0.8, 0, 1)
                btn.color = (1, 1, 1, 1)
            else:
                btn.background_color = (0.25, 0.25, 0.25, 1)
                btn.color = (0.7, 0.7, 0.7, 1)
            btn.bind(on_release=lambda x, ch=channel: self.select_channel(ch))
            self.channel_buttons[channel] = btn
            tabs_container.add_widget(btn)

        return tabs_container

    def build_data_section(self):
        data_section = BoxLayout(orientation="vertical", spacing=0, padding=[15, 10, 15, 10])

        header_layout = BoxLayout(orientation="horizontal", size_hint=(1, None), height=35)
        with header_layout.canvas.before:
            Color(0.15, 0.15, 0.15, 1)
            header_layout.bg_rect = Rectangle(size=header_layout.size, pos=header_layout.pos)
        header_layout.bind(size=lambda inst, val: setattr(header_layout.bg_rect, "size", inst.size))
        header_layout.bind(pos=lambda inst, val: setattr(header_layout.bg_rect, "pos", inst.pos))

        headers = ["TICKER", "PRICE", "GAP%", "VOL", "FLOAT", "RVOL", "NEWS"]
        for header in headers:
            label = Label(text=header, font_size=15, color=(0.7, 0.7, 0.7, 1), bold=True)
            header_layout.add_widget(label)
        data_section.add_widget(header_layout)

        self.scroll_view = ScrollView(size_hint=(1, 1))
        self.rows_container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=2)
        self.rows_container.bind(minimum_height=self.rows_container.setter('height'))

        self.scroll_view.add_widget(self.rows_container)
        data_section.add_widget(self.scroll_view)

        return data_section

    def refresh_data_table(self):
        """Refresh the data table with current channel stocks"""
        self.rows_container.clear_widgets()

        stocks = self.live_data.get(self.current_channel, [])

        for stock_data in stocks[:50]:
            row = self.create_stock_row(stock_data)
            if row:
                self.rows_container.add_widget(row)

    def create_stock_row(self, stock_data):
        """Create a single stock row with GLOWING COLORED NEWS BUTTONS"""
        row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=40)

        try:
            change_str = stock_data[2].replace('%', '').replace('+', '')
            change_pct = float(change_str)
            text_color = (0, 1, 0, 1) if change_pct >= 0 else (1, 0, 0, 1)
        except Exception:
            text_color = (0.9, 0.9, 0.9, 1)

        for i, value in enumerate(stock_data):
            if i == 6:
                ticker = stock_data[0]

                if ticker in self.stock_news:
                    tier = self.stock_news[ticker].get('tier', 3)
                    if tier == 2:
                        btn_color = (1, 1, 0, 1)
                        btn_text = "BREAKING"
                        text_color_btn = (0, 0, 0, 1)
                    else:
                        btn_color = (0, 0.8, 1, 1)
                        btn_text = "NEWS"
                        text_color_btn = (0, 0, 0, 1)
                else:
                    btn_color = (1, 0.3, 0.3, 1)
                    btn_text = "NO NEWS"
                    text_color_btn = (1, 1, 1, 1)

                btn = Button(text=btn_text, font_size=12, size_hint=(1, 1),
                             background_color=btn_color, bold=True,
                             color=text_color_btn)

                news_content = self.stock_news.get(ticker, {}).get('title', 'No news available')
                btn.bind(on_release=lambda x, t=ticker, n=news_content: self.show_news_popup(t, n))
                row.add_widget(btn)
            else:
                label = Label(text=str(value), font_size=14, color=text_color if i > 0 else (1, 1, 1, 1))
                row.add_widget(label)

        return row

    def show_news_popup(self, ticker, news_text):
        content = BoxLayout(orientation="vertical", padding=20, spacing=15)
        title_label = Label(text=f"{ticker} - NEWS", font_size=18, bold=True,
                            size_hint=(1, None), height=40, color=(0, 1, 0, 1))
        content.add_widget(title_label)

        news_label = Label(text=news_text, font_size=14, text_size=(400, None),
                           halign="left", valign="middle", color=(0.9, 0.9, 0.9, 1))
        content.add_widget(news_label)

        close_btn = Button(text="Close", size_hint=(1, None), height=40,
                           background_color=(0, 0.8, 0, 1))
        popup = Popup(title="", content=content, size_hint=(None, None), size=(450, 250),
                      background_color=(0.15, 0.15, 0.15, 1))
        close_btn.bind(on_release=popup.dismiss)
        content.add_widget(close_btn)
        popup.open()

    def select_channel(self, channel):
        for ch, btn in self.channel_buttons.items():
            btn.background_color = (0.25, 0.25, 0.25, 1)
            btn.color = (0.7, 0.7, 0.7, 1)
        self.channel_buttons[channel].background_color = (0, 0.8, 0, 1)
        self.channel_buttons[channel].color = (1, 1, 1, 1)
        self.current_channel = channel
        self.refresh_data_table()

    def update_times(self, dt):
        now = datetime.datetime.now()
        self.local_time_label.text = "Local Time    " + now.strftime("%I:%M %p")

        est = pytz.timezone('US/Eastern')
        now_est = datetime.datetime.now(est)
        self.nyc_time_label.text = "NYC Time     " + now_est.strftime("%I:%M %p")

        state, color = self.get_market_state_and_color(now_est)
        self.market_state_label.text = state
        self.market_state_label.color = color
        self.countdown_label.color = color

        next_time = self.get_next_change(now_est, state)
        if next_time:
            remaining = next_time - now_est
            seconds = int(remaining.total_seconds())
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = seconds % 60
            self.countdown_label.text = f"{h:02d}:{m:02d}:{s:02d}"
        else:
            self.countdown_label.text = "00:00:00"

    def get_market_state_and_color(self, now_est):
        market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
        premkt_start = now_est.replace(hour=7, minute=0, second=0, microsecond=0)
        close_start = now_est.replace(hour=14, minute=0, second=0, microsecond=0)
        after_end = now_est.replace(hour=19, minute=0, second=0, microsecond=0)

        weekday = now_est.weekday()
        state = "Closed"
        color = (1, 0, 0, 1)

        if weekday == 5 or weekday == 6 or (weekday == 4 and now_est >= market_close):
            state = "Weekend"
            color = (1, 0.6, 0, 1)
        elif now_est >= premkt_start and now_est < market_open:
            state = "PreMarket"
            color = (0.2, 0.5, 1, 1)
        elif now_est >= market_open and now_est < close_start:
            state = "Market Open"
            color = (0, 1, 0, 1)
        elif now_est >= close_start and now_est < market_close:
            state = "Market Closes"
            color = (1, 1, 0, 1)
        elif now_est >= market_close and now_est < after_end:
            state = "After Hours"
            color = (0.2, 0.5, 1, 1)

        return state, color

    def get_next_change(self, now_est, state):
        times = []
        weekday = now_est.weekday()

        if state == "PreMarket":
            times.append(now_est.replace(hour=9, minute=30, second=0, microsecond=0))
        elif state == "Market Open":
            times.append(now_est.replace(hour=14, minute=0, second=0, microsecond=0))
        elif state == "Market Closes":
            times.append(now_est.replace(hour=16, minute=0, second=0, microsecond=0))
        elif state == "After Hours":
            times.append(now_est.replace(hour=19, minute=0, second=0, microsecond=0))
        elif state == "Weekend":
            if weekday == 5:
                monday = now_est + datetime.timedelta(days=2)
                times.append(monday.replace(hour=7, minute=0, second=0, microsecond=0))
            elif weekday == 6:
                monday = now_est + datetime.timedelta(days=1)
                times.append(monday.replace(hour=7, minute=0, second=0, microsecond=0))
            elif weekday == 4 and now_est.hour >= 16:
                monday = now_est + datetime.timedelta(days=3)
                times.append(monday.replace(hour=7, minute=0, second=0, microsecond=0))
        else:
            if now_est.hour >= 19:
                next_day = now_est + datetime.timedelta(days=1)
                while next_day.weekday() >= 5:
                    next_day = next_day + datetime.timedelta(days=1)
                times.append(next_day.replace(hour=7, minute=0, second=0, microsecond=0))
            else:
                times.append(now_est.replace(hour=7, minute=0, second=0, microsecond=0))

        times = [t for t in times if t > now_est]
        return times[0] if times else None

    def exit_app(self, instance):
        self.market_data.stop()
        if self.news_manager:
            self.news_manager.stop()
        App.get_running_app().stop()


class SignalScanMainApp(App):
    def build(self):
        print("[DEBUG] Building app...")
        return SignalScanApp()


if __name__ == '__main__':
    print("[DEBUG] Starting SignalScan in DEBUG mode...")
    SignalScanMainApp().run()