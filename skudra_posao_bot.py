import requests
from bs4 import BeautifulSoup
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

FUNNY_RESPONSES = [
    "Stigli su hladni dani",
    "Kopaćeš kurac",
    "Nemoj da me zezaš!",
    "Sunce ti jebem žarko!"
]

# Синонимы профессий
SEARCH_TERMS = {
    "radnik": ["radnik", "radni", "radnice", "radnika", "radnici", "pomoćni radnik", "pomocni radnik"],
    "vozač": ["vozač", "vozac", "vozači", "šofer"],
    "konobar": ["konobar", "konobari", "ugostitelj", "ugostiteljstvo"],
    "operater": ["operater", "operateri", "operatera", "operater mašina"],
    "menadžer": ["menadžer", "menager", "manager", "rukovodilac"]
}


async def parse_jobs(city="", profession="", attempt=0):
    """Парсер вакансий с oglasi.rs с реальными селекторами и фильтрацией"""

    SEARCH_TERMS = {
        "radnik": ["radnik", "radni", "radnice", "radnika", "radnici", "pomoćni radnik", "vozac", "vozač"],
        "konobar": ["konobar", "konobari", "ugostitelj", "ugostiteljstvo"],
        "vozač": ["vozač", "vozac", "vozači", "šofer"],
        "operater": ["operater", "operateri", "operater mašina"],
        "menadžer": ["menadžer", "menager", "manager", "rukovodilac"]
    }

    base_url = "https://www.oglasi.rs/posao/"
    query = profession.lower()
    location = f"u {city.capitalize()}" if city else "u Srbiji"
    url = f"{base_url}{city.lower().replace(' ', '-') if city else ''}?q={query}"

    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code == 404:
        return ["Ma opusti se, bre! Samo polako"]

    soup = BeautifulSoup(resp.text, 'html.parser')
    jobs = []
    terms = SEARCH_TERMS.get(query, [query])

    for el in soup.select('.fpogl-holder:not(.advert_list_item_top_oglas)'):
        title_a = el.select_one('a.fpogl-list-title')
        if not title_a: continue

        title = title_a.get_text(strip=True)
        if not any(term in title.lower() for term in terms):
            continue

        link = "https://www.oglasi.rs" + title_a['href']
        company = None
        for strong in el.select('strong'):
            if "Naziv kompanije" in strong.parent.text:
                company = strong.get_text(strip=True)
                break

        date = el.select_one('time').get_text(strip=True) if el.select_one('time') else ''

        jobs.append(f"🔹 {title}\n🏢 {company or 'Nepoznata kompanija'}\n📅 {date}\n🔗 {link}")
        if len(jobs) >= 15:
            break

    if jobs:
        return jobs
    elif 3 <= attempt < 3 + len(FUNNY_RESPONSES):
        return [FUNNY_RESPONSES[attempt - 3]]
    return [f"Nema aktuelnih oglasa za '{profession}' {location}"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    context.user_data.clear()
    keyboard = ReplyKeyboardMarkup([["Svi gradovi"]], resize_keyboard=True)
    await update.message.reply_text(
        "Izaberite grad ili kliknite 'Svi gradovi':",
        reply_markup=keyboard
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик сообщений"""
    user_input = update.message.text.strip()

    if 'city' not in context.user_data:
        if user_input == "Svi gradovi":
            context.user_data['city'] = ""
            reply = "🏙 Izabran grad: Srbija\n✍️ Unesite naziv posla koji tražite:\n(ili /start za promenu grada)"
        else:
            context.user_data['city'] = user_input.lower().replace(' ', '-')
            reply = f"🏙 Izabrana lokacija: {user_input}\n✍️ Unesite naziv posla koji tražite:"

        context.user_data['attempt'] = 0
        await update.message.reply_text(reply)

    else:
        profession = user_input
        city = context.user_data['city']
        attempt = context.user_data['attempt'] = context.user_data.get('attempt', 0) + 1

        jobs = await parse_jobs(city, profession, attempt)
        response = "\n\n".join(jobs)

        await update.message.reply_text(
            f"{response}\n\n"
            "✍️ Možete uneti još jednu profesiju za pretragu\n"
            "(ili /start za promenu lokacije)"
        )


def main():
    """Запуск бота"""
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot je pokrenut! Zaustavi ga pomoću Ctrl+C")
    app.run_polling()


if __name__ == "__main__":
    main()

