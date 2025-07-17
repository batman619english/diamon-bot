    # ---------------- Admin + Public Commands ---------------- #
    # Re-check role here in case /mod was just used
    is_owner = user_id == OWNER_ID or user_id == "U75fd18c523f2254bb7f1553ee39454fb"
    is_mod = roles.get("mods", {}).get(user_id, False)
    authorized = is_owner or is_mod

    # /help - list commands
    if text == "/help":
        help_text = (
            "**Admin Commands:**\n"
            "/addban <word>\n"
            "/removeban <word>\n"
            "/mod @<user>\n"
            "/ban @<user>\n"
            "/unban @<user>\n"
            "/announce <message>\n"
            "/kick @<user>\n"
            "/botname <newname>\n"
            "/purge\n\n"
            "**Public Commands:**\n"
            "/time\n"
            ".lurkmsg"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=help_text))
        return

    # /time - UTC time
    if text == "/time":
        utc_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🕒 Current UTC time:\n{utc_time}"))
        return

    # /botname <newname> - simulated
    if text.startswith("/botname"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            bot_name = parts[1]
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🤖 My new name is now: {bot_name} (simulated)"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /botname NewBotName"))
        return

    # /purge - simulated
    if text == "/purge":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🧹 Purging recent messages... (simulated)"))
        return

    if not authorized:
        return  # Don't process admin commands for regular users

    # /addban <word>
    if text.startswith("/addban"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            word = parts[1].strip().lower()
            if word not in banned_words:
                banned_words.append(word)
                save_json(BANNED_WORDS_FILE, banned_words)
                msg = f"✅ Added banned word: {word}"
            else:
                msg = f"⚠️ Word already in ban list: {word}"
        else:
            msg = "Usage: /addban <word>"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    # /removeban <word>
    if text.startswith("/removeban"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            word = parts[1].strip().lower()
            if word in banned_words:
                banned_words.remove(word)
                save_json(BANNED_WORDS_FILE, banned_words)
                msg = f"✅ Removed banned word: {word}"
            else:
                msg = f"⚠️ Word not found: {word}"
        else:
            msg = "Usage: /removeban <word>"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    # /mod @user
    if text.startswith("/mod"):
        parts = text.split()
        if len(parts) >= 2:
            target_id = mention_to_user_id(parts[1], names, event)
            if target_id:
                roles.setdefault("mods", {})[target_id] = True
                save_json(ROLES_FILE, roles)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🛡️ User promoted to moderator."))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /mod @username"))
        return

    # /ban @user
    if text.startswith("/ban"):
        parts = text.split()
        if len(parts) >= 2:
            target_id = mention_to_user_id(parts[1], names, event)
            if target_id:
                roles.setdefault("banned", {})[target_id] = True
                save_json(ROLES_FILE, roles)
                if group_id:
                    kick_user_from_group(group_id, target_id, event)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /ban @username"))
        return

    # /unban @user
    if text.startswith("/unban"):
        parts = text.split()
        if len(parts) >= 2:
            target_id = mention_to_user_id(parts[1], names, event)
            if target_id and target_id in roles.get("banned", {}):
                del roles["banned"][target_id]
                save_json(ROLES_FILE, roles)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ User has been unbanned."))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /unban @username"))
        return

    # /announce <message>
    if text.startswith("/announce"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            msg = parts[1]
            if group_id:
                line_bot_api.push_message(group_id, TextSendMessage(text=f"📢 Announcement:\n{msg}"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: /announce <message>"))
        return
