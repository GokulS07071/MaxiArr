import logging
from functools import wraps

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.agent import MediaAgent
from bot.config import ALLOWED_USER_IDS
from bot.helpers import (
    download_image_bytes,
    escape,
    format_timeleft,
    get_poster_url,
    make_progress_bar,
)

logger = logging.getLogger("telegram_bot.handlers")


def get_agent(context: ContextTypes.DEFAULT_TYPE) -> MediaAgent:
    """Helper to safely retrieve the MediaAgent instance from context.bot_data."""
    agent = context.bot_data.get("agent")
    if not agent:
        raise ValueError("MediaAgent is not initialized in bot_data.")
    return agent


def restricted(func):
    """Decorator to restrict access to handlers based on ALLOWED_USER_IDS."""

    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        user_id = user.id

        # If whitelist is configured, check if user is authorized
        if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
            logger.warning(
                f"Unauthorized access attempt: user_id={user_id}, "
                f"username=@{user.username or 'none'}, "
                f"name='{user.first_name} {user.last_name or ''}'"
            )
            if update.message:
                await update.message.reply_text("⛔️ You are not authorized to use this bot.")
            elif update.callback_query:
                await update.callback_query.answer("⛔️ You are not authorized to use this bot.", show_alert=True)
            return

        return await func(update, context, *args, **kwargs)

    return wrapped


@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Greet the user and explain how to use the bot."""
    user = update.effective_user
    welcome_text = (
        f"👋 Hi <b>{escape(user.first_name)}</b>!\n\n"
        "Welcome to your <b>MaxiArr Media Assistant</b>. 🎬\n\n"
        "To search and download media, simply send me a movie or show name (e.g. <code>Inception</code> or <code>Breaking Bad</code>).\n\n"
        "Try using /status to monitor your downloads!"
    )
    await update.message.reply_text(welcome_text, parse_mode="HTML")


@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the help guide."""
    help_text = (
        "💡 <b>Media Assistant Help Menu</b>\n\n"
        "• Send any title text to search (e.g. <code>Narcos</code>).\n"
        "• Select the media type (Movie or TV Show).\n"
        "• Apply <b>Year Filters</b> if there are many matches.\n"
        "• View rich description cards including high-res posters.\n"
        "• Pick your preferred download quality profile.\n"
        "• Choose the specific release candidate (showing size, seeders, and peers).\n"
        "• Run /status to check active downloads in real-time."
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


@restricted
async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text input from user (as search queries)."""
    query_text = update.message.text.strip()
    if not query_text:
        return

    # Clear prior user context data
    context.user_data.clear()
    context.user_data["current_query"] = query_text

    keyboard = [
        [
            InlineKeyboardButton("🎬 Movie (Radarr)", callback_data="type_movie"),
            InlineKeyboardButton("📺 TV Show (Sonarr)", callback_data="type_series"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_search")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"What type of media is <b>{escape(query_text)}</b>?",
        reply_markup=reply_markup,
        parse_mode="HTML",
    )


async def render_matches_list(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_to_edit=None) -> None:
    """Render the matches inline keyboard with optional year filter buttons."""
    results = context.user_data.get("lookup_results", [])
    selected_year = context.user_data.get("year_filter")
    query_text = context.user_data.get("current_query")

    # Filter matches by year if requested
    filtered_results = results
    if selected_year:
        filtered_results = [r for r in results if str(r.get("year")) == str(selected_year)]

    # Find all unique years available in lookup results
    unique_years = sorted(list(set(str(r.get("year")) for r in results if r.get("year"))))

    keyboard = []

    # Render year filter row if there are multiple matches and multiple years
    if len(results) > 3 and len(unique_years) > 1:
        filter_row = []
        for y in unique_years[:4]:  # Display up to 4 year filters to fit screen width
            label = f"• {y} •" if str(selected_year) == str(y) else str(y)
            filter_row.append(InlineKeyboardButton(label, callback_data=f"filter_year_{y}"))
        keyboard.append(filter_row)

        if selected_year:
            keyboard.append([InlineKeyboardButton("🔄 Clear Year Filter", callback_data="filter_clear")])

    # Add matches (display up to 5)
    for idx, item in enumerate(filtered_results[:5]):
        # Map back to the original index in `results`
        original_idx = results.index(item)
        title = item.get("title", "Unknown")
        year = item.get("year", "N/A")
        keyboard.append([InlineKeyboardButton(f"{title} ({year})", callback_data=f"select_media_{original_idx}")])

    keyboard.append([InlineKeyboardButton("❌ Cancel Search", callback_data="cancel_search")])

    text = f"Select the correct match for <b>{escape(query_text)}</b>:"
    if selected_year:
        text += f"\n<i>(Filtered by Year: {selected_year})</i>"

    markup = InlineKeyboardMarkup(keyboard)

    if message_to_edit:
        try:
            await message_to_edit.edit_text(text=text, reply_markup=markup, parse_mode="HTML")
            return
        except Exception as e:
            logger.debug(f"Could not edit message, falling back to send new: {e}")

    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, parse_mode="HTML")


@restricted
async def handle_media_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Perform lookup query to Radarr or Sonarr based on media type."""
    query = update.callback_query
    await query.answer()

    choice = query.data
    query_text = context.user_data.get("current_query")
    agent = get_agent(context)

    if not query_text:
        await query.edit_message_text("No search query found. Please search again.")
        return

    if choice == "type_movie":
        context.user_data["media_type"] = "movie"
        await query.edit_message_text(f"🔍 Searching Radarr for '{escape(query_text)}'...")
        results = await agent.search_movie(query_text)
    else:
        context.user_data["media_type"] = "series"
        await query.edit_message_text(f"🔍 Searching Sonarr for '{escape(query_text)}'...")
        results = await agent.search_series(query_text)

    if not results:
        await query.edit_message_text(f"❌ No results found matching '{escape(query_text)}'.")
        return

    context.user_data["lookup_results"] = results
    context.user_data["year_filter"] = None

    await render_matches_list(context, query.message.chat_id, message_to_edit=query.message)


@restricted
async def handle_year_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set or clear the year filter and update results list."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "filter_clear":
        context.user_data["year_filter"] = None
    else:
        year = data.split("_")[-1]
        context.user_data["year_filter"] = year

    await render_matches_list(context, query.message.chat_id, message_to_edit=query.message)


@restricted
async def handle_media_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete the text list message and send a photo message card containing the poster and details."""
    query = update.callback_query
    await query.answer()

    idx = int(query.data.split("_")[-1])
    results = context.user_data.get("lookup_results", [])
    if idx >= len(results):
        await query.edit_message_text("Media details not found. Please search again.")
        return

    item = results[idx]
    context.user_data["selected_idx"] = idx
    media_type = context.user_data.get("media_type")

    # Extract metadata
    title = item.get("title", "Unknown")
    year = item.get("year", "N/A")
    overview = item.get("overview", "No overview description available.")
    genres = ", ".join(item.get("genres", [])) or "N/A"

    rating = (
        item.get("ratings", {}).get("value", "N/A")
        if isinstance(item.get("ratings"), dict)
        else item.get("ratings", "N/A")
    )
    runtime = item.get("runtime", "N/A")
    poster_url = get_poster_url(item)

    # Caption layout (strict HTML)
    caption = (
        f"🎬 <b>{escape(title)} ({year})</b>\n\n"
        f"⭐️ <b>Rating:</b> {rating} | ⏱ <b>Runtime:</b> {runtime} mins\n"
        f"🎭 <b>Genres:</b> {escape(genres)}\n\n"
        f"<i>{escape(overview)}</i>"
    )

    keyboard = [
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_to_list"),
            InlineKeyboardButton("➕ Add to Library", callback_data="add_confirm"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_search")],
    ]

    # Delete the matches text list message
    try:
        await query.message.delete()
    except Exception as e:
        logger.debug(f"Could not delete matches list message: {e}")

    # Attempt to download image bytes first
    photo_data = await download_image_bytes(poster_url, media_type)

    # Send the poster cover as a photo message, with fallbacks if download or send fails
    try:
        if photo_data:
            # Reset pointer before sending
            photo_data.seek(0)
            photo_msg = await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=photo_data,
                caption=caption,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            context.user_data["photo_message_id"] = photo_msg.message_id
        else:
            raise ValueError("No downloaded photo bytes available.")
    except Exception as e:
        logger.warning(f"Failed to send poster photo bytes ({poster_url}), trying fallback: {e}")
        try:
            fallback_poster = "https://images.unsplash.com/photo-1594909122845-11baa439b7bf?q=80&w=500"
            photo_msg = await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=fallback_poster,
                caption=caption + "\n\n<i>(Note: Poster image load failed)</i>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            context.user_data["photo_message_id"] = photo_msg.message_id
        except Exception as ex:
            logger.error(f"Failed to send fallback photo: {ex}")
            # Final fallback to standard text message
            text_msg = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=caption + "\n\n<i>(Note: Poster image load failed)</i>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            context.user_data["photo_message_id"] = text_msg.message_id


@restricted
async def handle_back_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete the photo poster message and return back to the list of matches."""
    query = update.callback_query
    await query.answer()

    photo_msg_id = context.user_data.get("photo_message_id")
    if photo_msg_id:
        try:
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=photo_msg_id)
        except Exception as e:
            logger.debug(f"Failed to delete photo message: {e}")
        context.user_data["photo_message_id"] = None

    await render_matches_list(context, query.message.chat_id)


@restricted
async def handle_add_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete the poster photo and ask the user to choose the quality profile."""
    query = update.callback_query
    await query.answer()

    photo_msg_id = context.user_data.get("photo_message_id")
    agent = get_agent(context)

    if photo_msg_id:
        try:
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=photo_msg_id)
        except Exception as e:
            logger.debug(f"Failed to delete photo message: {e}")
        context.user_data["photo_message_id"] = None

    profile_msg = await context.bot.send_message(
        chat_id=query.message.chat_id, text="⏳ Fetching available quality profiles..."
    )

    media_type = context.user_data.get("media_type")
    if media_type == "movie":
        profiles = await agent.get_radarr_quality_profiles()
    else:
        profiles = await agent.get_sonarr_quality_profiles()

    if not profiles:
        await profile_msg.edit_text("❌ Could not load quality profiles. Please try again.")
        return

    keyboard = []
    for p in profiles:
        keyboard.append([InlineKeyboardButton(p["name"], callback_data=f"profile_{p['id']}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_search")])

    await profile_msg.edit_text(
        text="Choose the desired <b>Quality Profile</b> to monitor:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


@restricted
async def handle_quality_profile_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add item, query releases from indexers, and display release candidates with sizes."""
    query = update.callback_query
    await query.answer()

    profile_id = int(query.data.split("_")[-1])
    media_type = context.user_data.get("media_type")
    idx = context.user_data.get("selected_idx")
    results = context.user_data.get("lookup_results", [])
    agent = get_agent(context)

    if idx is None or idx >= len(results):
        await query.edit_message_text("No selected item found. Please start over.")
        return

    item = results[idx]
    await query.edit_message_text(f"⏳ Adding '{escape(item.get('title'))}' to database...")

    if media_type == "movie":
        success, media_id, message = await agent.add_movie(item, profile_id)
    else:
        success, media_id, message = await agent.add_series(item, profile_id)

    if not success or not media_id:
        await query.edit_message_text(f"❌ Failed to add: {message}")
        return

    await query.edit_message_text(
        text="🔍 <b>Searching indexers for releases...</b>\n<i>Please wait (typically takes 5-15 seconds)...</i>",
        parse_mode="HTML",
    )

    if media_type == "movie":
        releases = await agent.get_movie_releases(media_id)
    else:
        releases = await agent.get_series_releases(media_id)

    if not releases:
        await query.edit_message_text("❌ No release candidates found on indexers. Added to library.")
        return

    # Sort releases by seeders
    releases = sorted(releases, key=lambda r: r.get("seeders", 0), reverse=True)
    top_releases = releases[:10]

    keyboard = []
    releases_list = []

    for r_idx, r in enumerate(top_releases):
        title = r.get("title", "Unknown Release")
        size = r.get("size", 0)
        seeders = r.get("seeders", 0)
        peers = r.get("peers", 0)

        size_gb = size / (1024**3)
        size_str = f"{size_gb:.1f} GB" if size_gb >= 1.0 else f"{size / (1024**2):.0f} MB"

        btn_text = f"💾 [{size_str}] S:{seeders} P:{peers} | {title}"
        if len(btn_text) > 48:
            btn_text = btn_text[:45] + "..."

        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"dl_release_{r_idx}")])
        releases_list.append(r)

    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_search")])

    context.user_data["releases_list"] = releases_list
    context.user_data["app_type"] = media_type

    await query.edit_message_text(
        text="📦 <b>Release Candidates Found:</b>\nSelect a release below to begin downloading:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


@restricted
async def handle_release_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send download release command."""
    query = update.callback_query
    await query.answer()

    r_idx = int(query.data.split("_")[-1])
    releases_list = context.user_data.get("releases_list", [])
    app_type = context.user_data.get("app_type")
    agent = get_agent(context)

    if r_idx >= len(releases_list) or not app_type:
        await query.edit_message_text("Release details not found. Please search again.")
        return

    release_payload = releases_list[r_idx]
    await query.edit_message_text(f"⏳ Sending download command for '{escape(release_payload.get('title'))}'...")

    success, message = await agent.download_release(app_type, release_payload)
    if success:
        await query.edit_message_text(f"✅ <b>Success:</b> {escape(message)}", parse_mode="HTML")
    else:
        await query.edit_message_text(f"❌ <b>Error:</b> {escape(message)}", parse_mode="HTML")

    context.user_data.clear()


@restricted
async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel operation, deleting the photo cover card if displayed."""
    query = update.callback_query
    await query.answer()

    photo_msg_id = context.user_data.get("photo_message_id")
    if photo_msg_id:
        try:
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=photo_msg_id)
        except Exception as e:
            logger.debug(f"Failed to delete photo message: {e}")
        context.user_data["photo_message_id"] = None
        await context.bot.send_message(chat_id=query.message.chat_id, text="❌ Search cancelled.")
    else:
        await query.edit_message_text("❌ Action cancelled.")

    context.user_data.clear()


async def build_status_message(agent: MediaAgent) -> tuple[str, InlineKeyboardMarkup]:
    """Helper to retrieve active queue and build status text and reply markup."""
    queue = await agent.get_download_queue()
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if not queue:
        return "✅ No active downloads in queue.", reply_markup

    html_lines = ["📥 <b>Active Downloads</b>\n"]
    for idx, item in enumerate(queue):
        title = escape(item["title"])
        status = escape(item["status"])
        app = escape(item["app"])
        size = item["size"]
        sizeleft = item["sizeleft"]

        progress = 0.0
        if size > 0:
            progress = ((size - sizeleft) / size) * 100.0

        progress_bar = make_progress_bar(progress, width=10)

        size_gb = size / (1024**3)
        sizeleft_gb = sizeleft / (1024**3)
        downloaded_gb = size_gb - sizeleft_gb

        timeleft = format_timeleft(item.get("timeleft"))

        html_lines.append(
            f"🎬 <b>{app}</b>\n"
            f"<code>{title}</code>\n"
            f"[{progress_bar}] {progress:.1f}%\n"
            f"📂 {downloaded_gb:.2f} GB / {size_gb:.2f} GB | ⏱ {timeleft}\n"
            f"⚙️ Status: <i>{status}</i>\n"
        )
    return "\n".join(html_lines), reply_markup


@restricted
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Query and display active downloads in Sonarr and Radarr queues."""
    progress_message = await update.message.reply_text("⏳ Fetching download queue status...")
    agent = get_agent(context)
    text, reply_markup = await build_status_message(agent)
    await progress_message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")


@restricted
async def handle_refresh_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback query handler to refresh the status message."""
    query = update.callback_query
    agent = get_agent(context)

    try:
        await query.answer("Refreshing status...")
    except Exception as e:
        logger.debug(f"Failed to answer callback query: {e}")

    text, reply_markup = await build_status_message(agent)

    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        if "Message is not modified" in str(e):
            logger.debug("Status message not modified during refresh.")
        else:
            logger.error(f"Error editing status message: {e}")
