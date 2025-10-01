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
import requests
import yfinance as yf
import threading
import time

Config.set('graphics', 'fullscreen', 'auto')
Config.set('graphics', 'borderless', '1')
Config.set('graphics', 'resizable', '0')
Config.write()

class SignalScanApp(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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

        self.current_channel = "PreGap"
        self.nasdaq_last, self.nasdaq_pct = self.get_index_data("^IXIC")  # NASDAQ
        self.sp_last, self.sp_pct = self.get_index_data("^GSPC")  # S&P 500

        self.build_header()
        main_content = BoxLayout(orientation="vertical", spacing=0, padding=0)
        self.tabs_container = self.build_channel_tabs()
        main_content.add_widget(self.tabs_container)
        self.data_container = self.build_data_section()
        main_content.add_widget(self.data_container)
        self.add_widget(main_content)
        Clock.schedule_interval(self.update_times, 1)
        Clock.schedule_interval(self.refresh_live_data, 30)
        self.start_data_thread()

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def start_data_thread(self):
        #print("DEBUG: Starting data thread")
        # Force immediate fetch
        Clock.schedule_once(self.refresh_live_data, 0.1)  # Run in 0.1 seconds
        # Then schedule regular updates
        Clock.schedule_interval(self.refresh_live_data, 60)  # Every 60 seconds
        #print("DEBUG: Data thread scheduled")

    def fetch_live_data_loop(self):
        while True:
            try:
                self.fetch_live_market_data()
                time.sleep(60)
            except Exception as e:
                print(f"Data fetch error: {e}")
                time.sleep(30)

    def fetch_live_market_data(self):
        #print("DEBUG: fetch_live_market_data() STARTED")
        try:
            movers_symbols = self.get_all_us_stocks()[:500]
            #print(f"DEBUG: Got {len(movers_symbols)} symbols")
            live_stocks = []
        
            print(f"Downloading data for {len(movers_symbols)} stocks...")
        
            # Process in chunks of 100
            chunk_size = 100
            for i in range(0, len(movers_symbols), chunk_size):
                chunk = movers_symbols[i:i+chunk_size]
                try:
                    data = yf.download(chunk, period="2d", interval="1d", group_by='ticker', auto_adjust=True, threads=True)
                
                    for symbol in chunk:
                        try:
                            if len(chunk) == 1:
                                hist = data
                            else:
                                hist = data[symbol]
                            
                            if not hist.empty and len(hist) >= 2:
                                current_price = hist['Close'].iloc[-1]
                                prev_close = hist['Close'].iloc[-2]
                                volume = hist['Volume'].iloc[-1] if 'Volume' in hist.columns else 1000000
                                change_pct = ((current_price - prev_close) / prev_close) * 100
                            
                                formatted_data = [
                                    symbol,
                                    f"{current_price:.2f}",
                                    f"{change_pct:+.1f}%",
                                    self.format_volume(volume),
                                    "88.9M",
                                    "4.2x", 
                                    "📈"
                                ]
                                live_stocks.append((formatted_data, change_pct, volume))
                        except:
                            continue
                except:
                    continue
        
            self.categorize_stocks(live_stocks)
            print(f"Processed {len(live_stocks)} stocks successfully")
        
        except Exception as e:
            print(f"Market data fetch error: {e}")

    def get_index_data(self, symbol):
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if not hist.empty:
                current_price = hist['Close'][-1]
                prev_close = hist['Close'][-2]
                change_pct = ((current_price - prev_close) / prev_close) * 100
                return f"{current_price:.1f}", change_pct
        except:
            pass
        return "0.0", 0.0

    def get_all_us_stocks(self):
        """Fetch ALL US stock symbols from NASDAQ official data"""
        try:
            import pandas as pd
            import requests
        
            all_symbols = []
        
            # Get NASDAQ listed stocks (official source)
            nasdaq_url = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
            nasdaq_data = requests.get(nasdaq_url).text
            nasdaq_symbols = [line.split('|')[0] for line in nasdaq_data.split('\n')[1:] if '|' in line]
            all_symbols.extend(nasdaq_symbols)
        
            # Get NYSE + other exchanges (official source) 
            other_url = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"
            other_data = requests.get(other_url).text
            other_symbols = [line.split('|')[0] for line in other_data.split('\n')[1:] if '|' in line]
            all_symbols.extend(other_symbols)
        
            # Clean up symbols (remove test/invalid entries)
            clean_symbols = [s for s in all_symbols if s and len(s) <= 5 and s.isalpha()]
           
            print(f"Found {len(clean_symbols)} US stocks to scan")
            return clean_symbols
        
        except Exception as e:
            print(f"Error fetching stock list: {e}")
            # Fallback to basic list
            return ['AAPL', 'TSLA', 'NVDA', 'AMD', 'MSFT']

    def is_trading_hours(self):
        """Return True only between 06:00 and 19:00 EST on business days."""
        from datetime import datetime
        import pytz

        est = pytz.timezone("US/Eastern")
        now_est = datetime.now(est)

        # weekends
        if now_est.weekday() >= 5:        # 5 = Saturday, 6 = Sunday
            return False
        # pre-market cutoff
        if now_est.hour < 6:              # before 06:00
            return False
        # after-hours cutoff
        if now_est.hour >= 19:            # 19:00 (7 PM) or later
            return False
        return True

    def categorize_stocks(self, stocks):
        for channel in self.live_data:
            self.live_data[channel] = []
        stocks.sort(key=lambda x: x[1], reverse=True)
        for stock_data, change_pct, volume in stocks:
            if abs(change_pct) > 5:
                self.live_data["PreGap"].append(stock_data)
            if change_pct > 2:
                self.live_data["HOD"].append(stock_data)
            if change_pct > 0:
                self.live_data["RunUp"].append(stock_data)
            if change_pct < 0:
                self.live_data["RunDown"].append(stock_data)
            if volume > 1000000:
                self.live_data["Rvsl"].append(stock_data)

    def format_volume(self, volume):
        if volume >= 1000000:
            return f"{volume/1000000:.1f}M"
        elif volume >= 1000:
            return f"{volume/1000:.1f}K"
        return str(int(volume))

    def format_float(self, float_shares):
        if float_shares >= 1000000000:
            return f"{float_shares/1000000000:.1f}B"
        elif float_shares >= 1000000:
            return f"{float_shares/1000000:.1f}M"
        elif float_shares >= 1000:
            return f"{float_shares/1000:.1f}K"
        return str(int(float_shares))

    def refresh_live_data(self, dt=None):
        #print(f"DEBUG: refresh_live_data called at {datetime.datetime.now()}")
        #print(f"DEBUG: is_trading_hours() = {self.is_trading_hours()}")
    
        # ALWAYS FETCH DATA - REMOVE TRADING HOURS CHECK
        #print("DEBUG: FORCING fetch_live_market_data()")
        self.fetch_live_market_data()
        self.refresh_data_table()
        #print("DEBUG: Data refresh completed")

    def build_header(self):
        header = BoxLayout(orientation="horizontal", size_hint=(1, None), height=80, padding=[15, 10, 15, 10])
        with header.canvas.before:
            Color(0.12, 0.12, 0.12, 1)
            header.bg_rect = Rectangle(size=header.size, pos=header.pos)
        header.bind(size=lambda inst, val: setattr(header.bg_rect, "size", inst.size))
        header.bind(pos=lambda inst, val: setattr(header.bg_rect, "pos", inst.pos))
        title = Label(text="SignalScan", font_size=28, color=(1, 1, 1, 1), bold=True, size_hint=(None, 1), width=180)
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
        self.nasdaq_label = Label(text=f"NASDAQ  {self.nasdaq_pct:+.1f}%", font_size=13, color=(0, 1, 0, 1) if self.nasdaq_pct >= 0 else (1, 0, 0, 1), bold=True)
        self.sp_label = Label(text=f"S&P     {self.sp_pct:+.1f}%", font_size=13, color=(0, 1, 0, 1) if self.sp_pct >= 0 else (1, 0, 0, 1), bold=True)
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
    
        # Header
        header_layout = BoxLayout(orientation="horizontal", size_hint=(1, None), height=50)
        with header_layout.canvas.before:
            Color(0.15, 0.15, 0.15, 1)
            header_layout.bg_rect = Rectangle(size=header_layout.size, pos=header_layout.pos)
        header_layout.bind(size=lambda inst, val: setattr(header_layout.bg_rect, 'size', val))
        header_layout.bind(pos=lambda inst, val: setattr(header_layout.bg_rect, 'pos', val))
    
        headers = ["TICKER", "PRICE", "CHANGE%", "VOL", "FLOAT", "RVOL", "NEWS"]
        for header in headers:
            label = Label(text=header, font_size=15, color=(0.7, 0.7, 0.7, 1), bold=True)
            header_layout.add_widget(label)
        data_section.add_widget(header_layout)
    
        # SCROLLABLE DATA CONTAINER
        scroll = ScrollView()
        self.rows_container = BoxLayout(orientation="vertical", size_hint_y=None)
        self.rows_container.bind(minimum_height=self.rows_container.setter('height'))
    
        # Add rows to scroll view
        scroll.add_widget(self.rows_container)
        data_section.add_widget(scroll)
    
        self.refresh_data_table()
        return data_section

    def build_data_section(self):
        data_section = BoxLayout(orientation="vertical", spacing=0, padding=[15, 0, 15, 15])
        header_layout = BoxLayout(orientation="horizontal", size_hint=(1, None), height=35)
        with header_layout.canvas.before:
            Color(0.15, 0.15, 0.15, 1)
            header_layout.bg_rect = Rectangle(size=header_layout.size, pos=header_layout.pos)
        header_layout.bind(size=lambda inst, val: setattr(header_layout.bg_rect, "size", inst.size))
        header_layout.bind(pos=lambda inst, val: setattr(header_layout.bg_rect, "pos", inst.pos))
        headers = ["TICKER", "PRICE", "CHANGE%", "VOL", "FLOAT", "RVOL", "NEWS"]
        for header in headers:
            label = Label(text=header, font_size=15, color=(0.7, 0.7, 0.7, 1), bold=True)
            header_layout.add_widget(label)
        data_section.add_widget(header_layout)
        self.rows_container = BoxLayout(orientation="vertical", size_hint=(1, None), spacing=0)
        self.rows_container.bind(minimum_height=self.rows_container.setter('height'))
        data_section.add_widget(self.rows_container)
        spacer = Label(text="", size_hint=(1, 1))
        data_section.add_widget(spacer)
        self.refresh_data_table()
        return data_section

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

    def refresh_data_table(self):
        print("Refreshing data table...")

        # SAFETY CHECK - Don't run if scroll_view doesn't exist yet
        if not hasattr(self, 'scroll_view') or not self.scroll_view:
            print("ScrollView not created yet, skipping refresh")
            return

        # NUCLEAR OPTION - Recreate the entire container
        try:
            # Remove the old container completely
            if hasattr(self, 'rows_container') and self.rows_container:
                self.rows_container.parent.remove_widget(self.rows_container)
        except:
            pass

        # Create a brand new container
        from kivy.uix.boxlayout import BoxLayout
        self.rows_container = BoxLayout(orientation='vertical', size_hint_y=None)
        self.rows_container.bind(minimum_height=self.rows_container.setter('height'))

        # Add it back to the scroll view
        self.scroll_view.add_widget(self.rows_container)

        # Now add stock rows
        if hasattr(self, 'live_stocks') and self.live_stocks:
            count = 0
            for stock_data, change_pct, volume in self.live_stocks[:20]:  # Only 20 rows
                if count >= 20:
                    break
                try:
                    row = self.create_stock_row(stock_data, change_pct, volume)
                    if row:
                        self.rows_container.add_widget(row)
                        count += 1
                except:
                    continue
            print(f"Added {count} fresh stock rows")
        else:
            print("No stock data to display")

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
                days = 2
                monday = now_est + datetime.timedelta(days=days)
                times.append(monday.replace(hour=7, minute=0, second=0, microsecond=0))
            elif weekday == 6:
                days = 1
                monday = now_est + datetime.timedelta(days=days)
                times.append(monday.replace(hour=7, minute=0, second=0, microsecond=0))
            elif weekday == 4 and now_est.hour >= 16:
                monday = now_est + datetime.timedelta(days=3)
                times.append(monday.replace(hour=7, minute=0, second=0, microsecond=0))
        else:
            times.append(now_est.replace(hour=7, minute=0, second=0, microsecond=0))
        times = [t for t in times if t > now_est]
        return times[0] if times else None

    def exit_app(self, instance):
        App.get_running_app().stop()

class SignalScanMainApp(App):
    def build(self):
        return SignalScanApp()

if __name__ == '__main__':
    SignalScanMainApp().run()

