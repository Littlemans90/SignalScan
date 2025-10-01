from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button  
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.config import Config
import datetime
import os
import pytz

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
        self.setup_channel_data()
        self.current_channel = "PreGap"
        self.build_header()
        main_content = BoxLayout(orientation="vertical", spacing=0, padding=0)
        self.tabs_container = self.build_channel_tabs()
        main_content.add_widget(self.tabs_container)
        self.data_container = self.build_data_section()
        main_content.add_widget(self.data_container)
        self.add_widget(main_content)
        Clock.schedule_interval(self.update_times, 1)

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def setup_channel_data(self):
        self.channel_data = {
            "PreGap": [["AAPL", "185.32", "+12.4", "45.2M", "15B", "4.8x", "BREAKING: iPhone sales surge"], ["TSLA", "267.89", "+8.9", "38.7M", "847B", "3.2x", "Model Y production up"], ["NVDA", "432.17", "+15.2", "67.3M", "1.1T", "5.1x", "AI chip demand soars"]],
            "HOD": [["AMD", "145.67", "+22.8", "89.4M", "235B", "6.7x", "New GPU announcement"], ["MSFT", "378.45", "+7.3", "28.9M", "2.8T", "2.1x", "Azure growth accelerates"]],
            "RunUp": [["META", "298.76", "+9.8", "31.2M", "759B", "3.4x", "Metaverse partnerships"], ["GOOGL", "134.21", "+5.7", "24.8M", "1.7T", "1.9x", "Search revenue beats"]],
            "RunDown": [["NFLX", "428.93", "-4.2", "19.3M", "185B", "2.3x", "Subscriber miss"], ["PYPL", "67.84", "-6.8", "42.1M", "76B", "4.1x", "Competition concerns"]],
            "Rvsl": [["UBER", "58.42", "+18.7", "78.5M", "115B", "8.2x", "Profitability milestone"], ["SNAP", "11.23", "-12.4", "156M", "17B", "9.8x", "User decline reported"]],
            "Halts": [["SPCE", "2.45", "+127", "234M", "640M", "47x", "BREAKING: Successful launch"], ["GME", "18.67", "+89", "189M", "5.7B", "23x", "Meme stock surge"]]
        }

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
        self.market_state_label = Label(text="Weekend", font_size=16, color=(1.0, 0.5, 0.0, 1), bold=True)
        self.countdown_label = Label(text="34:23:12", font_size=14, color=(1.0, 0.5, 0.0, 1))
        center_section.add_widget(self.market_state_label)
        center_section.add_widget(self.countdown_label)
        header.add_widget(center_section)
        
        indicators_section = BoxLayout(orientation="vertical", spacing=5, size_hint=(None, 1), width=140)
        self.nasdaq_label = Label(text="NASDAQ  +0.8%", font_size=13, color=(0.2, 0.8, 0.2, 1), bold=True)
        self.sp_label = Label(text="S&P     +0.4%", font_size=13, color=(0.2, 0.8, 0.2, 1), bold=True)
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
                btn.background_color = (0.3, 0.5, 0.8, 1)
                btn.color = (1, 1, 1, 1)
            else:
                btn.background_color = (0.25, 0.25, 0.25, 1)
                btn.color = (0.7, 0.7, 0.7, 1)
            btn.bind(on_release=lambda x, ch=channel: self.select_channel(ch))
            self.channel_buttons[channel] = btn
            tabs_container.add_widget(btn)
        return tabs_container

    def build_data_section(self):
        data_section = BoxLayout(orientation="vertical", spacing=0, padding=[15, 0, 15, 15])
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
        
        self.rows_container = BoxLayout(orientation="vertical", size_hint=(1, None), spacing=0)
        self.rows_container.bind(minimum_height=self.rows_container.setter('height'))
        data_section.add_widget(self.rows_container)
        
        spacer = Label(text="", size_hint=(1, 1))
        data_section.add_widget(spacer)
        
        self.refresh_data_table()
        return data_section

    def show_news_popup(self, ticker, news_text):
        content = BoxLayout(orientation="vertical", padding=20, spacing=15)
        title_label = Label(text=f"{ticker} - News Alert", font_size=18, bold=True, 
                           size_hint=(1, None), height=40, color=(1, 1, 1, 1))
        content.add_widget(title_label)
        
        news_label = Label(text=news_text, font_size=14, text_size=(400, None), 
                          halign="left", valign="middle", color=(0.9, 0.9, 0.9, 1))
        content.add_widget(news_label)
        
        close_btn = Button(text="Close", size_hint=(1, None), height=40, 
                          background_color=(0.3, 0.5, 0.8, 1))
        popup = Popup(title="", content=content, size_hint=(None, None), size=(450, 250), 
                     background_color=(0.15, 0.15, 0.15, 1))
        close_btn.bind(on_release=popup.dismiss)
        content.add_widget(close_btn)
        popup.open()

    def select_channel(self, channel):
        for ch, btn in self.channel_buttons.items():
            btn.background_color = (0.25, 0.25, 0.25, 1)
            btn.color = (0.7, 0.7, 0.7, 1)
            
        self.channel_buttons[channel].background_color = (0.3, 0.5, 0.8, 1)
        self.channel_buttons[channel].color = (1, 1, 1, 1)
        self.current_channel = channel
        self.refresh_data_table()

    def refresh_data_table(self):
        self.rows_container.clear_widgets()
        current_data = self.channel_data.get(self.current_channel, [])
        
        for i, row_data in enumerate(current_data):
            row_layout = BoxLayout(orientation="horizontal", size_hint=(1, None), height=32)
            with row_layout.canvas.before:
                if i % 2 == 0:
                    Color(0.1, 0.1, 0.1, 1)
                else:
                    Color(0.13, 0.13, 0.13, 1)
                row_layout.bg_rect = Rectangle(size=row_layout.size, pos=row_layout.pos)
            row_layout.bind(size=lambda inst, val: setattr(inst.bg_rect, "size", inst.size))
            row_layout.bind(pos=lambda inst, val: setattr(inst.bg_rect, "pos", inst.pos))
            
            ticker_label = Label(text=row_data[0], font_size=14, color=(1, 1, 1, 1), bold=True)
            row_layout.add_widget(ticker_label)
            
            price_label = Label(text="$" + row_data[1], font_size=14, color=(1, 1, 1, 1))
            row_layout.add_widget(price_label)
            
            try:
                gap_value = float(row_data[2].replace("+", "").replace("-", ""))
                gap_positive = "+" in row_data[2]
                gap_color = (0.2, 0.8, 0.2, 1) if gap_positive else (0.9, 0.2, 0.2, 1)
                gap_text = ("+" if gap_positive else "-") + f"{gap_value:.1f}%"
            except:
                gap_color = (0.8, 0.8, 0.8, 1)
                gap_text = row_data[2] + "%"
            gap_label = Label(text=gap_text, font_size=14, color=gap_color, bold=True)
            row_layout.add_widget(gap_label)
            
            vol_color = (0.4, 0.7, 1, 1) if "M" in row_data[3] else (0.8, 0.8, 0.8, 1)
            vol_label = Label(text=row_data[3], font_size=14, color=vol_color)
            row_layout.add_widget(vol_label)
            
            float_label = Label(text=row_data[4], font_size=14, color=(0.8, 0.8, 0.8, 1))
            row_layout.add_widget(float_label)
            
            try:
                rvol_val = float(row_data[5].replace("x", ""))
                rvol_color = (0.2, 0.8, 0.2, 1) if rvol_val > 2 else (0.8, 0.8, 0.8, 1)
                rvol_bold = True if rvol_val > 2 else False
            except:
                rvol_color = (0.8, 0.8, 0.8, 1)
                rvol_bold = False
            rvol_label = Label(text=row_data[5], font_size=14, color=rvol_color, bold=rvol_bold)
            row_layout.add_widget(rvol_label)
            
            news_color = (1, 1, 0, 1) if "BREAKING" in row_data[6] else (0.4, 0.7, 1, 1)
            news_btn = Button(text="📰", font_size=16, background_color=(0, 0, 0, 0), color=news_color)
            news_btn.bind(on_release=lambda x, ticker=row_data[0], news=row_data[6]: self.show_news_popup(ticker, news))
            row_layout.add_widget(news_btn)
            
            self.rows_container.add_widget(row_layout)

    def update_times(self, dt):
        now = datetime.datetime.now()
        self.local_time_label.text = "Local Time    " + now.strftime("%I:%M %p")
        nyc_time = now + datetime.timedelta(hours=3)
        self.nyc_time_label.text = "NYC Time     " + nyc_time.strftime("%I:%M %p")

    def exit_app(self, instance):
        App.get_running_app().stop()

class SignalScanMainApp(App):
    def build(self):
        return SignalScanApp()

if __name__ == '__main__':
    SignalScanMainApp().run()

