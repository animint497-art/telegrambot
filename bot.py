import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from telegram.constants import ParseMode
import asyncio
import json
import uuid
import threading
from flask import Flask, jsonify
import time
import sys

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ==================== ENVIRONMENT VARIABLES ====================

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN environment variable not set!")
    logger.error("Please set BOT_TOKEN in Render environment variables")
    # Don't crash - just warn, but bot won't work without token

# Flask Port Configuration
PORT = int(os.environ.get('PORT', 10000))

# External links
COMMUNITY_GROUP_LINK = os.getenv("COMMUNITY_GROUP_LINK", "https://t.me/YourCommunityGroup")
NFT_MINTING_GROUP_LINK = os.getenv("NFT_MINTING_GROUP_LINK", "https://t.me/YourNFTGroup")
PROMOTION_GROUP_LINK = os.getenv("PROMOTION_GROUP_LINK", "https://t.me/YourPromotionGroup")
VERIFY_TREND_LINK = os.getenv("VERIFY_TREND_LINK", "https://t.me/skeletontrend")
LOUNGE_GROUP_LINK = os.getenv("LOUNGE_GROUP_LINK", "https://t.me/skeletonlounge")
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@skeletondev")

# ==================== BOT CONFIGURATION ====================

# Conversation states
MAIN_MENU, SELECT_CHAIN, SELECT_DURATION, TOKEN_ADDRESS, TELEGRAM_LINK, TWITTER_LINK = range(6)

class SkeletonTrendingBot:
    def __init__(self):
        self.orders = {}
        self.user_data = {}
        
        # Chain configurations
        self.chains = {
            'bsc': {
                'name': 'Binance Smart Chain',
                'currency': 'BNB',
                'symbol': '🔗',
                'network': 'BEP20',
                'conversion_rate': 0.45
            },
            'eth': {
                'name': 'Ethereum',
                'currency': 'ETH',
                'symbol': '🟦',
                'network': 'ERC20',
                'conversion_rate': 0.05
            },
            'sol': {
                'name': 'Solana',
                'currency': 'SOL',
                'symbol': '🟪',
                'network': 'Solana',
                'conversion_rate': 1.0
            },
            'base': {
                'name': 'Base',
                'currency': 'ETH',
                'symbol': '⚪',
                'network': 'Base',
                'conversion_rate': 0.05
            },
            'pumpfun': {
                'name': 'PumpFun Trending',
                'currency': 'SOL',
                'symbol': '🔥',
                'network': 'Solana',
                'conversion_rate': 1.0
            },
            'possum': {
                'name': 'Possumlabs Trending',
                'currency': 'SOL',
                'symbol': '🦝',
                'network': 'Solana',
                'conversion_rate': 1.0
            },
            'fourmeme': {
                'name': 'FourMeme Trending',
                'currency': 'BNB',
                'symbol': '🎭',
                'network': 'BEP20',
                'conversion_rate': 0.45
            }
        }
        
        # Base prices in SOL
        self.base_prices = {
            '4_hours': 1.8,
            '8_hours': 2.7,
            '12_hours': 3.75,
            '24_hours': 5.25
        }
        
        # Calculate all prices
        self.prices = self.calculate_prices()
        logger.info("✅ Bot initialized successfully")
    
    def calculate_prices(self):
        """Calculate prices for all chains"""
        prices = {}
        for duration, sol_price in self.base_prices.items():
            prices[duration] = {}
            for chain_id, chain_info in self.chains.items():
                price = sol_price * chain_info['conversion_rate']
                prices[duration][chain_id] = round(price, 3)
        return prices
    
    def initialize_user(self, user_id: int):
        """Initialize user data"""
        if user_id not in self.orders:
            self.orders[user_id] = {
                'chain': None,
                'duration': None,
                'token_address': None,
                'telegram_link': None,
                'twitter_link': None,
                'order_date': None,
                'status': 'pending',
                'order_id': None
            }
        
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                'username': '',
                'orders': 0,
                'total_spent': 0,
                'join_date': datetime.now().isoformat()
            }
    
    def create_welcome_message(self) -> str:
        """Create welcome message"""
        current_date = datetime.now().strftime("%B %d")
        current_time = datetime.now().strftime("%H:%M")
        
        return f"""
<b># Skeleton Trending Boost Bot</b>

@SkeletonTrendingBot  
Always verify on {VERIFY_TREND_LINK} and in {LOUNGE_GROUP_LINK}  

<code>────────────────────</code>

<b>{current_date}</b>

/start  {current_time} ✅

<code>────────────────────</code>

<b>WELCOME TO</b>
<b>FASTTRACK TRENDING BOOST</b>
<b>SERVICE</b>

<b>BOOST YOUR TOKEN ON TRENDING IN SECONDS</b>

Welcome to Skeleton Fasttrack Trending listing service!
This Agent helps you to list your token on {VERIFY_TREND_LINK} fast and secure.

<b>FREE MASS DM promotion</b> sending to 112k users + 1 SolidSkull NFT free for 24Hours trending orders!
To avail contact {SUPPORT_CONTACT}

<i>Let's start and Choose an Option:</i>
"""
    
    def create_main_menu(self) -> InlineKeyboardMarkup:
        """Create main menu"""
        keyboard = [
            [InlineKeyboardButton("🚀 Main Trending Boost", callback_data="main_boost")],
            [InlineKeyboardButton("👥 Community Trending", callback_data="community_boost")],
            [InlineKeyboardButton("📊 Check All Promotion Options", callback_data="all_promotions")],
            [InlineKeyboardButton("💀 Mint SolidSkull NFT", callback_data="mint_nft")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_chain_selection(self) -> tuple:
        """Create chain selection menu"""
        text = f"""
<b># Skeleton Trending Boost Bot</b>

@SkeletonTrendingBot  
Always verify on {VERIFY_TREND_LINK} and in {LOUNGE_GROUP_LINK}  

<code>────────────────────</code>

<b>{datetime.now().strftime("%B %d")}</b>

/start  {datetime.now().strftime("%H:%M")} ▼

<code>────────────────────</code>

@SkeletonTrendingBot  
Select the chain your token is on: {datetime.now().strftime("%H:%M")}

<b>Each chain uses its native currency:</b>
• BSC → BNB
• Ethereum → ETH
• Solana → SOL
• Base → ETH
• PumpFun → SOL
• Possumlabs → SOL
• FourMeme → BNB
"""
        
        keyboard = [
            [InlineKeyboardButton(f"{self.chains['bsc']['symbol']} BSC (BNB)", callback_data="chain_bsc")],
            [InlineKeyboardButton(f"{self.chains['eth']['symbol']} Ethereum (ETH)", callback_data="chain_eth")],
            [InlineKeyboardButton(f"{self.chains['sol']['symbol']} Solana (SOL)", callback_data="chain_sol")],
            [InlineKeyboardButton(f"{self.chains['base']['symbol']} Base (ETH)", callback_data="chain_base")],
            [InlineKeyboardButton(f"{self.chains['pumpfun']['symbol']} PumpFun (SOL)", callback_data="chain_pumpfun")],
            [InlineKeyboardButton(f"{self.chains['possum']['symbol']} Possumlabs (SOL)", callback_data="chain_possum")],
            [InlineKeyboardButton(f"{self.chains['fourmeme']['symbol']} FourMeme (BNB)", callback_data="chain_fourmeme")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
        ]
        
        return text, InlineKeyboardMarkup(keyboard)
    
    def create_order_summary(self, user_id: int) -> tuple:
        """Create order summary"""
        user_data = self.orders[user_id]
        chain_info = self.chains.get(user_data['chain'], self.chains['sol'])
        duration = user_data['duration'].replace('_', ' ')
        price = self.prices[user_data['duration']][user_data['chain']]
        
        # Generate order ID
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        user_data['order_id'] = order_id
        
        # Format price
        if chain_info['currency'] in ['ETH', 'BNB']:
            price_str = f"{price:.3f}"
        else:
            price_str = f"{price:.2f}"
        
        # Get wallet based on chain
        wallet_info = self.get_wallet_info(user_data['chain'])
        
        text = f"""
<b>✅ ORDER SUMMARY</b>

<code>────────────────────</code>

<b>📋 Order Details:</b>
• Order ID: <code>{order_id}</code>
• Chain: {chain_info['name']}
• Duration: {duration}
• Currency: {chain_info['currency']}
• Amount: {price_str} {chain_info['currency']}

<b>📝 Token Info:</b>
• Address: <code>{user_data['token_address'][:30]}...</code>
• Telegram: {user_data['telegram_link']}
• Twitter: {user_data['twitter_link'] or 'Not provided'}

<code>────────────────────</code>

<b>💰 Payment Information:</b>
• Send: {price_str} {chain_info['currency']}
• To: <code>{wallet_info['address']}</code>
• Network: {wallet_info['network']}
• Memo: <code>{order_id}</code>

<code>────────────────────</code>

<b>🎁 Free Bonus:</b>
• SolidSkull NFT (all orders)
• Mass DM to 112k users (24h orders)

<code>────────────────────</code>

<b>📞 After Payment:</b>
1. Send payment screenshot
2. Contact: {SUPPORT_CONTACT}
3. Include Order ID: <code>{order_id}</code>
4. Go live within 15 minutes!

<b>Support:</b> {SUPPORT_CONTACT}
"""
        
        keyboard = [
            [InlineKeyboardButton("💳 I've Sent Payment", callback_data="payment_sent")],
            [InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{SUPPORT_CONTACT.replace('@', '')}")],
            [InlineKeyboardButton("🔄 New Order", callback_data="new_order")]
        ]
        
        return text, InlineKeyboardMarkup(keyboard)
    
    def get_wallet_info(self, chain_id: str) -> dict:
        """Get wallet information for chain"""
        wallets = {
            'bsc': {
                'address': os.getenv("BSC_WALLET", "0xYourBNBWalletAddress"),
                'network': 'Binance Smart Chain (BEP20)'
            },
            'eth': {
                'address': os.getenv("ETH_WALLET", "0xYourETHWalletAddress"),
                'network': 'Ethereum (ERC20)'
            },
            'sol': {
                'address': os.getenv("SOL_WALLET", "YourSolanaWalletAddress"),
                'network': 'Solana'
            },
            'base': {
                'address': os.getenv("BASE_WALLET", "0xYourBaseWalletAddress"),
                'network': 'Base Network'
            },
            'pumpfun': {
                'address': os.getenv("PUMPFUN_WALLET", "YourSolanaWalletAddress"),
                'network': 'Solana'
            },
            'possum': {
                'address': os.getenv("POSSUM_WALLET", "YourSolanaWalletAddress"),
                'network': 'Solana'
            },
            'fourmeme': {
                'address': os.getenv("FOURMEME_WALLET", "0xYourBNBWalletAddress"),
                'network': 'Binance Smart Chain (BEP20)'
            }
        }
        return wallets.get(chain_id, wallets['sol'])

# Initialize bot
bot = SkeletonTrendingBot()

# ==================== TELEGRAM BOT HANDLERS ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    user = update.effective_user
    
    logger.info(f"👤 User {user_id} ({user.username}) started bot")
    
    bot.initialize_user(user_id)
    bot.user_data[user_id]['username'] = user.username or user.first_name
    
    welcome_text = bot.create_welcome_message()
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=bot.create_main_menu()
    )
    
    return MAIN_MENU

async def handle_button_press(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button presses"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    bot.initialize_user(user_id)
    
    # ===== MAIN MENU ACTIONS =====
    if query.data == "main_boost":
        text, keyboard = bot.create_chain_selection()
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        return SELECT_CHAIN
    
    elif query.data == "community_boost":
        # Community trending - Solana only
        text = f"""
<b>👥 COMMUNITY TRENDING</b>

<code>────────────────────</code>

<i>Community Trending only supports Solana tokens</i>

<b>Pricing (in SOL):</b>
• 4 Hours: {bot.base_prices['4_hours']} SOL
• 8 Hours: {bot.base_prices['8_hours']} SOL
• 12 Hours: {bot.base_prices['12_hours']} SOL
• 24 Hours: {bot.base_prices['24_hours']} SOL

<code>────────────────────</code>

<b>Community benefits:</b>
• Promotion in community groups
• Still includes free NFT

<code>────────────────────</code>

<i>Select duration for Solana:</i>
"""
        keyboard = [
            [InlineKeyboardButton(f"⏱️ 4 Hours - {bot.prices['4_hours']['sol']:.2f} SOL [+ Free NFT]", callback_data="duration_4_hours_community")],
            [InlineKeyboardButton(f"⏱️ 8 Hours - {bot.prices['8_hours']['sol']:.2f} SOL [+ Free NFT]", callback_data="duration_8_hours_community")],
            [InlineKeyboardButton(f"⏱️ 12 Hours - {bot.prices['12_hours']['sol']:.2f} SOL [+ Free NFT]", callback_data="duration_12_hours_community")],
            [InlineKeyboardButton(f"⏱️ 24 Hours - {bot.prices['24_hours']['sol']:.2f} SOL [+Mass Dm & NFT]", callback_data="duration_24_hours_community")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECT_DURATION
    
    # ===== CHAIN SELECTION =====
    elif query.data.startswith("chain_"):
        chain = query.data.replace("chain_", "")
        bot.orders[user_id]['chain'] = chain
        
        # Create duration selection
        chain_info = bot.chains.get(chain, bot.chains['sol'])
        text = f"""
<b># TRENDING BOOST SERVICE</b>

<code>────────────────────</code>

<b>Chain:</b> {chain_info['name']}
<b>Currency:</b> {chain_info['currency']}
<b>Network:</b> {chain_info['network']}

<code>────────────────────</code>

<b>Free Mass DM promotion</b> sending to 112k users + 1 SolidSkull NFT free for 24Hours trending orders!
To avail contact {SUPPORT_CONTACT}

<b>Select duration:</b>
"""
        
        keyboard = []
        for duration_key, duration_name in [('4_hours', '4 Hours'), ('8_hours', '8 Hours'), 
                                           ('12_hours', '12 Hours'), ('24_hours', '24 Hours')]:
            price = bot.prices[duration_key][chain]
            currency = chain_info['currency']
            
            # Format price
            if currency in ['ETH', 'BNB']:
                price_str = f"{price:.3f}"
            else:
                price_str = f"{price:.2f}"
            
            if duration_key == '24_hours':
                button_text = f"⏱️ {duration_name} - {price_str} {currency} [+Mass Dm & NFT]"
            else:
                button_text = f"⏱️ {duration_name} - {price_str} {currency} [+ Free NFT]"
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"duration_{duration_key}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_chains")])
        
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECT_DURATION
    
    # ===== DURATION SELECTION =====
    elif query.data.startswith("duration_"):
        if "_community" in query.data:
            duration = query.data.replace("duration_", "").replace("_community", "")
            bot.orders[user_id]['chain'] = 'sol'  # Community is Solana only
        else:
            duration = query.data.replace("duration_", "")
        
        bot.orders[user_id]['duration'] = duration
        
        # Ask for token address
        chain_info = bot.chains.get(bot.orders[user_id]['chain'], bot.chains['sol'])
        price = bot.prices[duration][bot.orders[user_id]['chain']]
        currency = chain_info['currency']
        
        text = f"""
<b># Skeleton Trending Boost Bot</b>

<code>────────────────────</code>

<b>Please send your token address:</b> {datetime.now().strftime("%H:%M")}

<code>────────────────────</code>

<b>Chain:</b> {chain_info['name']}
<b>Duration:</b> {duration.replace('_', ' ')}
<b>Payment:</b> {price:.3f if currency in ['ETH', 'BNB'] else price:.2f} {currency}

<code>────────────────────</code>

<i>Send your token contract address:</i>
"""
        await query.edit_message_text(text, parse_mode=ParseMode.HTML)
        return TOKEN_ADDRESS
    
    # ===== ORDER COMPLETION =====
    elif query.data == "payment_sent":
        order_id = bot.orders[user_id].get('order_id', 'N/A')
        await query.answer(f"✅ Payment confirmed! Order ID: {order_id}\nContact {SUPPORT_CONTACT} with screenshot.", show_alert=True)
        
        text = f"""
<b>📞 CONTACT SUPPORT</b>

<code>────────────────────</code>

<b>Order ID:</b> <code>{order_id}</code>
<b>Contact:</b> {SUPPORT_CONTACT}

<code>────────────────────</code>

<i>Send payment screenshot and order ID to go live!</i>
"""
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📱 Message Support", url=f"https://t.me/{SUPPORT_CONTACT.replace('@', '')}")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_menu")]
            ])
        )
    
    # ===== NAVIGATION =====
    elif query.data == "back_to_menu":
        welcome_text = bot.create_welcome_message()
        await query.edit_message_text(welcome_text, parse_mode=ParseMode.HTML, reply_markup=bot.create_main_menu())
        return MAIN_MENU
    
    elif query.data == "back_to_chains":
        text, keyboard = bot.create_chain_selection()
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        return SELECT_CHAIN
    
    elif query.data == "new_order":
        # Reset user order
        bot.orders[user_id] = {
            'chain': None,
            'duration': None,
            'token_address': None,
            'telegram_link': None,
            'twitter_link': None,
            'order_date': None,
            'status': 'pending',
            'order_id': None
        }
        
        text, keyboard = bot.create_chain_selection()
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        return SELECT_CHAIN
    
    # ===== OTHER MENUS =====
    elif query.data == "all_promotions":
        text = f"""
<b>📊 ALL PROMOTION OPTIONS</b>

<code>────────────────────</code>

Join our official promotion group to see:
• All trending services
• Community promotions
• NFT minting info
• Special offers
• Live updates

<code>────────────────────</code>

<b>Click below to join:</b>
"""
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎯 Join Promotion Group", url=PROMOTION_GROUP_LINK)],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
            ])
        )
    
    elif query.data == "mint_nft":
        text = f"""
<b>💀 MINT SOLIDSKULL NFT</b>

<code>────────────────────</code>

<b>SolidSkull NFT Benefits:</b>
• Exclusive access to premium channels
• Priority support
• Voting rights in ecosystem
• Royalty sharing (5%)
• Free with all trending orders!

<code>────────────────────</code>

<b>To mint or learn more:</b>
Join our NFT community group:
"""
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💀 Join NFT Group", url=NFT_MINTING_GROUP_LINK)],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
            ])
        )
    
    return MAIN_MENU

async def handle_token_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle token address input"""
    user_id = update.effective_user.id
    token_address = update.message.text.strip()
    
    if len(token_address) < 10:
        await update.message.reply_text("❌ Invalid token address. Please send a valid contract address:")
        return TOKEN_ADDRESS
    
    bot.orders[user_id]['token_address'] = token_address
    
    # Ask for Telegram link
    text = f"""
<b># Skeleton Trending Boost Bot</b>

<code>────────────────────</code>

<b>Token address received ✅</b>
<code>{token_address[:50]}...</code>

<code>────────────────────</code>

<b>Please send the Telegram link:</b> {datetime.now().strftime("%H:%M")}

<i>Format: https://t.me/yourchannel</i>
<i>Example: https://t.me/pandagenerate</i>
"""
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    return TELEGRAM_LINK

async def handle_telegram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Telegram link input"""
    user_id = update.effective_user.id
    telegram_link = update.message.text.strip()
    
    if not (telegram_link.startswith('https://t.me/') or telegram_link.startswith('t.me/')):
        await update.message.reply_text("❌ Invalid Telegram link. Must start with https://t.me/\nPlease send a valid link:")
        return TELEGRAM_LINK
    
    bot.orders[user_id]['telegram_link'] = telegram_link
    
    # Ask for Twitter link (optional)
    text = f"""
<b># Skeleton Trending Boost Bot</b>

<code>────────────────────</code>

<b>Telegram link received ✅</b>
{telegram_link}

<code>────────────────────</code>

<b>Add your token Twitter [X] Link (optional):</b> {datetime.now().strftime("%H:%M")}

Tokens with X link get posted on Skeletonecosys X Trending!

<i>Send X link or type "skip" to skip:</i>
<i>Format: @username or full URL</i>
"""
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    return TWITTER_LINK

async def handle_twitter_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Twitter link input"""
    user_id = update.effective_user.id
    twitter_link = update.message.text.strip()
    
    if twitter_link.lower() == 'skip':
        bot.orders[user_id]['twitter_link'] = None
    else:
        bot.orders[user_id]['twitter_link'] = twitter_link
    
    bot.orders[user_id]['order_date'] = datetime.now().isoformat()
    
    # Show order summary
    summary_text, keyboard = bot.create_order_summary(user_id)
    await update.message.reply_text(summary_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    text = update.message.text.lower()
    
    if text in ['/start', 'start']:
        await start_command(update, context)
        return MAIN_MENU
    
    # Default response
    welcome_text = bot.create_welcome_message()
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML, reply_markup=bot.create_main_menu())
    return MAIN_MENU

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Error: {context.error}")
    
    if update and update.effective_user:
        try:
            welcome_text = bot.create_welcome_message()
            await update.effective_user.send_message(
                welcome_text,
                parse_mode=ParseMode.HTML,
                reply_markup=bot.create_main_menu()
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

# ==================== FLASK APP FOR HEALTH CHECKS ====================

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Skeleton Trending Boost Bot is running!", 200

@flask_app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'Skeleton Trending Boost Bot',
        'timestamp': datetime.now().isoformat(),
        'orders_processed': len(bot.orders),
        'bot_token_set': bool(BOT_TOKEN),
        'environment': 'production' if os.getenv('RENDER') else 'development'
    }), 200

@flask_app.route('/info')
def info():
    return jsonify({
        'bot': 'Skeleton Trending Boost Bot',
        'version': '2.0',
        'deployment': 'Render',
        'port': PORT,
        'external_links': {
            'community_group': COMMUNITY_GROUP_LINK,
            'nft_group': NFT_MINTING_GROUP_LINK,
            'promotion_group': PROMOTION_GROUP_LINK,
            'support': SUPPORT_CONTACT
        }
    }), 200

def run_flask_app():
    """Run Flask app for health checks"""
    logger.info(f"Starting Flask app on port {PORT}")
    
    # Check if running with gunicorn (production)
    if "gunicorn" in sys.modules:
        logger.info("Running with gunicorn - skipping manual run")
        return
    
    # Development mode
    flask_app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

# ==================== TELEGRAM BOT RUNNER ====================

def run_telegram_bot():
    """Run the Telegram bot with retry logic"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN not set! Bot cannot start.")
        logger.error("Please set BOT_TOKEN in Render environment variables")
        return
    
    max_retries = 5
    retry_delay = 30
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🚀 Starting Telegram bot (Attempt {attempt + 1}/{max_retries})")
            
            # Create Application
            application = Application.builder().token(BOT_TOKEN).build()
            
            # Create conversation handler
            conv_handler = ConversationHandler(
                entry_points=[CommandHandler('start', start_command)],
                states={
                    MAIN_MENU: [
                        CallbackQueryHandler(handle_button_press),
                        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
                    ],
                    SELECT_CHAIN: [CallbackQueryHandler(handle_button_press)],
                    SELECT_DURATION: [CallbackQueryHandler(handle_button_press)],
                    TOKEN_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_token_address)],
                    TELEGRAM_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_link)],
                    TWITTER_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_twitter_link)]
                },
                fallbacks=[CommandHandler('start', start_command)]
            )
            
            # Add handlers
            application.add_handler(conv_handler)
            application.add_handler(CommandHandler("help", start_command))
            application.add_error_handler(error_handler)
            
            # Log startup info
            logger.info("✅ Bot application created successfully")
            logger.info(f"🌐 Health check: http://localhost:{PORT}/health")
            logger.info(f"📊 Info: http://localhost:{PORT}/info")
            logger.info(f"🤖 Bot username: @{(application.bot.username or 'Unknown')}")
            
            # Start bot polling
            logger.info("🤖 Starting bot polling...")
            await application.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES,
                close_loop=False
            )
            
        except Exception as e:
            logger.error(f"❌ Bot crashed on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                logger.info(f"⏱️ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("🚨 Max retries reached. Bot stopped.")
                raise

async def main_async():
    """Async main function to run both bot and Flask"""
    # Start bot in background task
    bot_task = asyncio.create_task(run_telegram_bot())
    
    # Run Flask in separate thread
    import threading
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    # Wait for bot task (it will run until stopped)
    await bot_task

def main():
    """Main entry point"""
    print("🚀 Initializing Skeleton Trending Boost Bot...")
    print(f"📝 BOT_TOKEN: {'✅ Set' if BOT_TOKEN else '❌ NOT SET - Bot will not work!'}")
    print(f"🔧 PORT: {PORT}")
    print(f"🌍 Environment: {'Render' if os.getenv('RENDER') else 'Local'}")
    
    if not BOT_TOKEN:
        print("\n❌ CRITICAL ERROR: BOT_TOKEN environment variable is required!")
        print("💡 Set it in Render: Environment → Add Environment Variable")
        print("📋 Get token from @BotFather on Telegram")
        return
    
    # Run the async main function
    asyncio.run(main_async())

if __name__ == '__main__':
    main()
