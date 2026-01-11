import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from telethon import TelegramClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telethon.tl.functions.account import UpdateProfileRequest

# Log konfiguratsiyasi
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Konfiguratsiya fayli
class Config:
    # Telegram Client (User Account) ma'lumotlari
    API_ID = '38362737'  # my.telegram.org dan oling
    API_HASH = 'c23cb05729322fda13cd21ac57edf6be'  # my.telegram.org dan oling
    PHONE_NUMBER = '+998994829824'  # Telefon raqamingiz
    
    # Bot Token
    BOT_TOKEN = '8263929871:AAGrNR_x-9xuAWZQk7qq0a4mPVPnDFUjmes'  # @BotFather dan oling
    
    # Admin ID (Sizning ID'ingiz)
    ADMIN_ID = 6582564319   # O'zingizning ID'ingizni kiriting
    
    # Soat formati
    TIME_FORMAT = "%H:%M:%S %d.%m.%Y"

# Stats fayl
STATS_FILE = 'stats.json'

class StatsManager:
    def __init__(self, stats_file=STATS_FILE):
        self.stats_file = Path(stats_file)
        self.stats = self.load_stats()
    
    def load_stats(self):
        """Statistikani fayldan yuklash"""
        if self.stats_file.exists():
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        else:
            return {
                'clock_on_count': 0,
                'clock_off_count': 0,
                'total_updates': 0,
                'last_update': None,
                'is_running': False
            }
    
    def save_stats(self):
        """Statistikani faylga saqlash"""
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=4)
    
    def increment_on_count(self):
        """Soat yoqish sonini oshirish"""
        self.stats['clock_on_count'] += 1
        self.stats['total_updates'] += 1
        self.stats['last_update'] = datetime.now().isoformat()
        self.save_stats()
    
    def increment_off_count(self):
        """Soat o'chirish sonini oshirish"""
        self.stats['clock_off_count'] += 1
        self.stats['total_updates'] += 1
        self.stats['last_update'] = datetime.now().isoformat()
        self.save_stats()
    
    def set_running(self, status: bool):
        """Ish holatini o'zgartirish"""
        self.stats['is_running'] = status
        self.save_stats()
    
    def get_stats_text(self):
        """Statistika matni"""
        return (
            f"📊 **Bot Statistikasi:**\n"
            f"• Soat yoqilgan: {self.stats['clock_on_count']} marta\n"
            f"• Soat o'chirilgan: {self.stats['clock_off_count']} marta\n"
            f"• Jami yangilanishlar: {self.stats['total_updates']}\n"
            f"• So'nggi yangilanish: {self.stats['last_update'] or 'Hali yo\'q'}\n"
            f"• Holati: {'✅ Ishlamoqda' if self.stats['is_running'] else '❌ To\'xtatilgan'}"
        )

class ProfileClockBot:
    def __init__(self, config: Config):
        self.config = config
        self.stats_manager = StatsManager()
        
        # Telegram Client (User Account)
        self.client = TelegramClient(
            'user_session',
            config.API_ID,
            config.API_HASH
        )
        
        # Bot Application
        self.bot_app = Application.builder().token(config.BOT_TOKEN).build()
        
        # Ish holati
        self.is_clock_running = False
        self.clock_task = None
        
    async def start_telegram_client(self):
        """Telegram clientni ishga tushirish"""
        await self.client.start(phone=self.config.PHONE_NUMBER)
        logger.info("Telegram client muvaffaqiyatli ishga tushirildi")
    
    async def update_profile(self):
        """Profil bio'sini yangilash"""
        try:
            current_time = datetime.now().strftime(self.config.TIME_FORMAT)
            online_status = "🟢 Online" if self.is_clock_running else "⚪️ Offline"
            
            bio = f"⏰ Soat: {current_time} | {online_status}"
            
            await self.client(UpdateProfileRequest(
                about=bio
            ))
            
            logger.info(f"Profil yangilandi: {bio}")
            return True
        except Exception as e:
            logger.error(f"Profil yangilashda xatolik: {e}")
            return False
    
    async def clock_loop(self):
        """Soat yangilash tsikli"""
        while self.is_clock_running:
            await self.update_profile()
            await asyncio.sleep(30)  # Har 30 soniyada yangilash
    
    async def start_clock(self):
        """Soatni ishga tushirish"""
        if not self.is_clock_running:
            self.is_clock_running = True
            self.stats_manager.set_running(True)
            self.stats_manager.increment_on_count()
            
            # Soat tsiklini ishga tushirish
            self.clock_task = asyncio.create_task(self.clock_loop())
            logger.info("Soat ishga tushirildi")
            return True
        return False
    
    async def stop_clock(self):
        """Soatni to'xtatish"""
        if self.is_clock_running:
            self.is_clock_running = False
            self.stats_manager.set_running(False)
            self.stats_manager.increment_off_count()
            
            # Soat tsiklini to'xtatish
            if self.clock_task:
                self.clock_task.cancel()
                try:
                    await self.clock_task
                except asyncio.CancelledError:
                    pass
            
            # Profilni sozsiz holatga o'tkazish
            await self.update_profile()
            logger.info("Soat to'xtatildi")
            return True
        return False
    
    async def auto_message_loop(self):
        """Avtomatik xabar tsikli"""
        while True:
            try:
                if self.is_clock_running:
                    message = "✅ Bot normal ishlamoqda"
                    await self.bot_app.bot.send_message(
                        chat_id=self.config.ADMIN_ID,
                        text=message
                    )
                await asyncio.sleep(3600)  # Har 1 soatda
            except Exception as e:
                logger.error(f"Avtomatik xabar yuborishda xatolik: {e}")
                await asyncio.sleep(300)  # 5 daqiqa kutish
    
    # Bot komandalari
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/start komandasi"""
        user = update.effective_user
        
        # Faqat admin uchun
        if user.id != self.config.ADMIN_ID:
            await update.message.reply_text("❌ Sizga ruxsat yo'q!")
            return
        
        keyboard = [
            [
                InlineKeyboardButton("⏰ Soatni Yoqish", callback_data='clock_on'),
                InlineKeyboardButton("🛑 Soatni O'chirish", callback_data='clock_off')
            ],
            [
                InlineKeyboardButton("📊 Statistika", callback_data='stats'),
                InlineKeyboardButton("🔄 Yangilash", callback_data='refresh')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        status = "✅ Ishlamoqda" if self.is_clock_running else "❌ To'xtatilgan"
        
        await update.message.reply_text(
            f"👋 Assalomu alaykum {user.first_name}!\n"
            f"📝 **Profil Soati Botiga xush kelibsiz!**\n\n"
            f"📍 **Holat:** {status}\n"
            f"🔧 Quyidagi tugmalar orqali botni boshqaring:",
            reply_markup=reply_markup
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inline tugmalar uchun callback"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        # Faqat admin uchun
        if user.id != self.config.ADMIN_ID:
            await query.edit_message_text("❌ Sizga ruxsat yo'q!")
            return
        
        if query.data == 'clock_on':
            success = await self.start_clock()
            if success:
                message = "✅ Soat yoqildi! Profil bio'si har 30 soniyada yangilanadi."
            else:
                message = "⚠️ Soat allaqachon yoqilgan!"
            
            await query.edit_message_text(message)
            
        elif query.data == 'clock_off':
            success = await self.stop_clock()
            if success:
                message = "🛑 Soat o'chirildi! Profil bio'si yangilanmaydi."
            else:
                message = "⚠️ Soat allaqachon o'chirilgan!"
            
            await query.edit_message_text(message)
            
        elif query.data == 'stats':
            stats_text = self.stats_manager.get_stats_text()
            await query.edit_message_text(stats_text)
            
        elif query.data == 'refresh':
            current_status = "✅ Ishlamoqda" if self.is_clock_running else "❌ To'xtatilgan"
            await query.edit_message_text(
                f"🔄 Yangilandi!\n📍 **Joriy holat:** {current_status}"
            )
        
        # Tugmalarni qayta ko'rsatish
        keyboard = [
            [
                InlineKeyboardButton("⏰ Soatni Yoqish", callback_data='clock_on'),
                InlineKeyboardButton("🛑 Soatni O'chirish", callback_data='clock_off')
            ],
            [
                InlineKeyboardButton("📊 Statistika", callback_data='stats'),
                InlineKeyboardButton("🔄 Yangilash", callback_data='refresh')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Statistika komandasi"""
        user = update.effective_user
        
        if user.id != self.config.ADMIN_ID:
            await update.message.reply_text("❌ Sizga ruxsat yo'q!")
            return
        
        stats_text = self.stats_manager.get_stats_text()
        await update.message.reply_text(stats_text)
    
    def setup_bot_handlers(self):
        """Bot handler'larini sozlash"""
        self.bot_app.add_handler(CommandHandler("start", self.start_command))
        self.bot_app.add_handler(CommandHandler("stats", self.stats_command))
        self.bot_app.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def run(self):
        """Botni ishga tushirish"""
        try:
            # Telegram clientni ishga tushirish
            await self.start_telegram_client()
            
            # Bot handler'larini sozlash
            self.setup_bot_handlers()
            
            # Avtomatik xabar tsiklini ishga tushirish
            auto_message_task = asyncio.create_task(self.auto_message_loop())
            
            # Botni ishga tushirish
            await self.bot_app.initialize()
            await self.bot_app.start()
            await self.bot_app.updater.start_polling()
            
            logger.info("Bot muvaffaqiyatli ishga tushirildi")
            
            # Dasturni ishlashini saqlash
            await asyncio.Event().wait()
            
        except Exception as e:
            logger.error(f"Bot ishga tushirishda xatolik: {e}")
        finally:
            # Tozalash ishlari
            if self.is_clock_running:
                await self.stop_clock()
            
            await self.bot_app.stop()
            await self.client.disconnect()

async def main():
    """Asosiy funksiya"""
    config = Config()
    bot = ProfileClockBot(config)
    
    await bot.run()

if __name__ == '__main__':
    # Requirements fayli uchun kerakli kutubxonalar
    requirements = [
        "telethon==1.34.0",
        "python-telegram-bot==20.7",
        "python-dotenv==1.0.0"
    ]
    
    print("Telegram Profil Soati Bot")
    print("=" * 40)
    print("\nKerakli kutubxonalar:")
    for req in requirements:
        print(f"  - {req}")
    
    print("\nSozlamalar:")
    print("1. my.telegram.org saytidan API_ID va API_HASH oling")
    print("2. @BotFather dan yangi bot yarating va token oling")
    print("3. Konfiguratsiya ma'lumotlarini Config klassiga kiriting")
    print("4. admin_id ni o'zingizning Telegram ID'ingizga o'zgartiring")
    
    # .env fayli yaratish tavsiyasi
    env_example = """
# .env fayli
API_ID=1234567
API_HASH=your_api_hash_here
PHONE_NUMBER=+998901234567
BOT_TOKEN=1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ
ADMIN_ID=123456789
"""
    
    print("\n.env fayli misoli:")
    print(env_example)
    
    # Botni ishga tushirish
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nBot to'xtatildi.")
