"""Rockstar Character Hub - web edition (English / Arabic).

A Streamlit front end for the "Which character are you?" quiz and the character
browser. It reuses the same logic modules as the CLI app (hub/), so both versions
always agree on how a match is calculated.

All user-facing text lives in TEXT_EN below and in data/ar.json, so the interface,
the quiz questions and every character bio exist in both languages. English is
always the internal key: only what is shown on screen is translated, never the
values the scoring works with.

The AI interview, ratings, tier lists and the admin area are CLI-only features:
they need a local Ollama model and per-user files that a shared web app cannot
keep. Run `python main.py` for the full experience.
"""

import streamlit as st
import plotly.graph_objects as go

from hub import characters as characters_module
from hub import quiz as quiz_logic
from hub.config import (
    BASE_DIR,
    CHARACTERS_FILE,
    QUESTIONS_FILE,
    SERIES,
    TOP_MATCHES,
    TRAITS,
    WEAK_MATCH_PERCENT,
)
from hub.storage import load_json

REPO_URL = "https://github.com/itsdevruba/rockstar-character-hub"
ARABIC_FILE = BASE_DIR / "data" / "ar.json"

# ---------- Theme tokens (kept in one place so the whole page stays consistent) ----------
SURFACE = "#14140f"  # page background
CARD = "#1c1c16"  # card background
INK = "#f2f1ea"  # primary text
INK_MUTED = "#a8a79c"  # secondary text
HAIRLINE = "rgba(242, 241, 234, 0.12)"
ACCENT = "#e0a336"  # gold, used for chrome only (buttons, badges) - never for data
SERIES_YOU = "#3987e5"  # blue - "You" in the trait chart
SERIES_CHARACTER = "#d95926"  # orange - the matched character

# ---------- English text (the Arabic side of this lives in data/ar.json) ----------

TEXT_EN = {
    "subtitle": "Find out which Rockstar Games character you are, and browse the cast of "
                "GTA, Red Dead Redemption and Bully.",
    "tab_quiz": "Which character are you?",
    "tab_browse": "Browse characters",
    "tab_about": "About",
    "language": "Language",

    "series_question": "Which series should you be matched against?",
    "all_series": "All series",
    "question_counter": "Question {n} of {total}",
    "pick_answer": "Pick the answer closest to you",
    "next": "Next",
    "back": "Back",
    "see_result": "See my result",
    "retake": "Take the quiz again",

    "closest_match": "Closest match",
    "weak_match": "No character fits you perfectly — the closest is {name} at {match}%. "
                  "Your answers sit between the personalities in this series.",
    "you_vs": "You vs {name}",
    "you": "You",
    "view_table": "View as table",
    "trait": "Trait",
    "also_close": "Also close to you",
    "share_title": "Share your result",
    "share_text": "I took the Rockstar Character Hub quiz and got {name} "
                  "({match}% match). Which one are you?\n{url}",

    "traits_details": "Traits & details",
    "spoilers_heading": "Story notes (spoilers)",
    "show_spoilers": "Show story notes (spoilers)",
    "read_wiki": "Read more on the wiki",
    "match_badge": "{match}% match",

    "search_label": "Search by name",
    "search_placeholder": "e.g. arthur",
    "series_label": "Series",
    "game_label": "Game",
    "role_label": "Role",
    "all_games": "All games",
    "all_roles": "All roles",
    "count_caption": "{shown} of {total} characters",
    "no_results": "No characters match these filters.",
    "data_error": "Character or question data could not be loaded.",
}

ABOUT_EN = """
### About this project

**Rockstar Character Hub** started as my final individual project in a Python
program: an interactive command-line app for fans of Rockstar Games. This page is
the web edition of two of its features — the personality quiz and the character
browser.

**The data** — {characters} characters across {games} games — was written by hand
from the community wikis. No external API is involved.

**How the match is calculated.** Every answer adds or subtracts points across five
traits: loyalty, morality, temper, humor and ambition. Those points are scaled to a
0–10 range where 5 is neutral, then each character is ranked by Euclidean distance
from your profile. The web version imports the exact same functions as the CLI app,
so both always give the same answer.

**Only in the command-line version**
- *Interview with AI* — a local language model (Ollama) asks five open questions and
  matches you from your own words
- Rating characters on writing, growth, charisma, combat and memorability
- Personal tier lists (S–D) and side-by-side comparison
- User accounts and an admin area for managing characters and results

Those features need a local AI model and per-user files, which a shared web app
can't provide — so they live in the terminal.

**Built with** Python, Streamlit and Plotly on the web; `questionary`, `rich`,
`pyfiglet` and `ollama` in the terminal.

[View the source on GitHub]({url})

---

*Unofficial student project. All characters belong to Rockstar Games. Character
information is summarized from the GTA, Red Dead and Bully wikis (CC BY-SA).*
"""


# ---------- Data ----------


@st.cache_data
def load_characters() -> list[dict]:
    """Load the character list once per session."""
    return load_json(CHARACTERS_FILE, [])


@st.cache_data
def load_questions() -> list[dict]:
    """Load the quiz questions once per session."""
    return load_json(QUESTIONS_FILE, [])


@st.cache_data
def load_arabic() -> dict:
    """Load the Arabic strings. Returns an empty dict if the file is missing."""
    return load_json(ARABIC_FILE, {})


# ---------- Page setup ----------

st.set_page_config(
    page_title="Rockstar Character Hub",
    page_icon="🎮",
    layout="centered",
    initial_sidebar_state="collapsed",
)

if "lang" not in st.session_state:
    st.session_state.lang = "en"

arabic = load_arabic()
is_arabic = st.session_state.lang == "ar" and bool(arabic)


def t(key: str, **values) -> str:
    """Return the interface string for `key` in the current language."""
    if is_arabic:
        text = arabic.get("ui", {}).get(key) or TEXT_EN.get(key, key)
    else:
        text = TEXT_EN.get(key, key)
    return text.format(**values) if values else text


def trait_label(trait: str) -> str:
    """The display name of a trait."""
    if is_arabic:
        return arabic.get("traits", {}).get(trait, trait.capitalize())
    return trait.capitalize()


def role_label(role: str) -> str:
    """The display name of a role."""
    return arabic.get("roles", {}).get(role, role) if is_arabic else role


def affiliation_label(affiliation: str) -> str:
    """The display name of an affiliation."""
    if is_arabic:
        return arabic.get("affiliations", {}).get(affiliation, affiliation)
    return affiliation


def character_text(character: dict, field: str) -> str:
    """A character's bio or spoiler notes in the current language."""
    if is_arabic:
        translated = arabic.get("characters", {}).get(character["id"], {}).get(field)
        if translated:
            return translated
    return character.get(field, "")


def question_text(question: dict) -> str:
    """The question wording in the current language."""
    if is_arabic:
        return arabic.get("questions", {}).get(question["text"], {}).get("text", question["text"])
    return question["text"]


def option_label(question: dict, option: str) -> str:
    """One answer's wording in the current language (the English text stays the key)."""
    if is_arabic:
        options = arabic.get("questions", {}).get(question["text"], {}).get("options", {})
        return options.get(option, option)
    return option


# The Arabic web font goes in its own <style> block: an @import is only valid at the
# top of a stylesheet, so it cannot sit at the end of the main block below.
if is_arabic:
    st.markdown(
        "<style>@import url('https://fonts.googleapis.com/css2"
        "?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap');</style>",
        unsafe_allow_html=True,
    )

# Right-to-left layout and the Arabic UI font, applied only in Arabic.
RTL_CSS = """
      .block-container, .block-container p, .block-container div, .block-container label,
      .block-container h1, .block-container h2, .block-container h3,
      .block-container h4, .block-container h5, .block-container li {
        font-family: 'IBM Plex Sans Arabic', system-ui, sans-serif !important;
      }
      .block-container { direction: rtl; text-align: right; }
      /* Streamlit sets text-align:left on its own markdown/alert wrappers, which beats
         the inherited alignment above - so the alignment is restated on them here. */
      .block-container [data-testid="stMarkdownContainer"],
      .block-container .stMarkdown,
      .block-container [data-testid="stCaptionContainer"],
      .block-container [data-testid="stAlertContentInfo"],
      .block-container [data-testid="stAlert"],
      .block-container [data-testid="stExpander"] summary,
      .block-container [data-testid="stWidgetLabel"] {
        text-align: right;
      }
      /* the only code block on the page is the shareable result sentence */
      .block-container pre, .block-container code {
        direction: rtl; text-align: right; white-space: pre-wrap !important;
        word-break: break-word !important; overflow-wrap: anywhere !important;
        font-family: 'IBM Plex Sans Arabic', system-ui, sans-serif !important;
      }
      div[data-testid="stExpander"] summary { flex-direction: row-reverse; }
"""

st.markdown(
    f"""
    <style>
      .stApp {{ background: {SURFACE}; }}
      .block-container {{ padding-top: 2.6rem; max-width: 52rem; }}

      .hub-title {{
        font-size: 2.1rem; font-weight: 700; letter-spacing: -0.02em;
        color: {INK}; margin: 0 0 0.25rem 0; line-height: 1.15; direction: ltr;
        text-align: {"right" if is_arabic else "left"};
      }}
      .hub-subtitle {{ color: {INK_MUTED}; font-size: 0.95rem; margin: 0 0 0.4rem 0; }}

      .hub-card {{
        background: {CARD}; border: 1px solid {HAIRLINE}; border-radius: 12px;
        padding: 1.1rem 1.2rem; margin-bottom: 0.75rem;
      }}
      .hub-card-name {{ font-size: 1.15rem; font-weight: 650; color: {INK}; margin-bottom: 0.15rem; }}
      .hub-card-meta {{ font-size: 0.82rem; color: {INK_MUTED}; margin-bottom: 0.55rem; }}
      .hub-card-bio {{ font-size: 0.9rem; color: {INK}; opacity: 0.88; line-height: 1.65; }}

      .hub-badge {{
        display: inline-block; font-size: 0.72rem; font-weight: 600;
        padding: 0.15rem 0.5rem; border-radius: 999px; margin: 0 0.3rem;
        border: 1px solid {HAIRLINE}; color: {INK_MUTED};
      }}
      .hub-badge-match {{
        background: rgba(224, 163, 54, 0.14); border-color: rgba(224, 163, 54, 0.45);
        color: {ACCENT};
      }}

      .hub-hero-match {{ font-size: 3.1rem; font-weight: 700; color: {ACCENT}; line-height: 1;
        direction: ltr; }}
      .hub-hero-label {{ font-size: 0.8rem; color: {INK_MUTED}; text-transform: uppercase;
        letter-spacing: 0.08em; }}

      .hub-question {{ font-size: 1.15rem; font-weight: 600; color: {INK}; margin-bottom: 0.2rem; }}
      .hub-step {{ font-size: 0.78rem; color: {INK_MUTED}; letter-spacing: 0.06em;
        text-transform: uppercase; }}

      .hub-note {{
        font-size: 0.85rem; color: {INK_MUTED}; border-inline-start: 2px solid {HAIRLINE};
        padding-inline-start: 0.7rem; line-height: 1.65;
      }}

      div[data-testid="stExpander"] details {{
        background: {CARD}; border: 1px solid {HAIRLINE}; border-radius: 10px;
      }}
      .stButton > button {{ border-radius: 8px; font-weight: 600; }}
      footer, #MainMenu {{ visibility: hidden; }}
      {RTL_CSS if is_arabic else ""}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Small helpers ----------


def character_by_name(all_characters: list[dict], name: str) -> dict | None:
    """Find a character by its exact display name."""
    for character in all_characters:
        if character["name"] == name:
            return character
    return None


def meta_line(character: dict) -> str:
    """One line of context under a character's name."""
    parts = [character["game"]]
    if character.get("year"):
        parts.append(str(character["year"]))
    parts.append(role_label(character["role"]))
    if character.get("affiliation") and character["affiliation"] != "None":
        parts.append(affiliation_label(character["affiliation"]))
    return " · ".join(parts)


def trait_chart(character: dict, user_traits: dict[str, float] | None = None) -> go.Figure:
    """Horizontal bars for the five traits.

    With `user_traits` it compares you against the character (two series, legend +
    value labels); without it, it shows the character's traits alone.
    """
    labels = [trait_label(trait) for trait in TRAITS]
    figure = go.Figure()

    if user_traits is not None:
        figure.add_bar(
            y=labels,
            x=[user_traits[trait] for trait in TRAITS],
            name=t("you"),
            orientation="h",
            marker=dict(color=SERIES_YOU, cornerradius=4),
            text=[f"{user_traits[trait]:g}" for trait in TRAITS],
            textposition="outside",
            textfont=dict(color=INK_MUTED, size=11),
            hovertemplate=t("you") + " · %{y}: %{x}<extra></extra>",
        )

    figure.add_bar(
        y=labels,
        x=[character["traits"][trait] for trait in TRAITS],
        name=character["name"],
        orientation="h",
        marker=dict(color=SERIES_CHARACTER, cornerradius=4),
        text=[f"{character['traits'][trait]:g}" for trait in TRAITS],
        textposition="outside",
        textfont=dict(color=INK_MUTED, size=11),
        hovertemplate=character["name"] + " · %{y}: %{x}<extra></extra>",
    )

    figure.update_layout(
        barmode="group",
        bargap=0.34,
        bargroupgap=0.12,
        height=64 * len(TRAITS) if user_traits is not None else 46 * len(TRAITS),
        margin=dict(l=0, r=28, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="'IBM Plex Sans Arabic', system-ui, sans-serif"
            if is_arabic
            else 'system-ui, -apple-system, "Segoe UI", sans-serif',
            color=INK_MUTED,
            size=12,
        ),
        showlegend=user_traits is not None,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            font=dict(color=INK_MUTED, size=11),
        ),
        hoverlabel=dict(bgcolor=CARD, bordercolor=HAIRLINE, font=dict(color=INK)),
    )
    # In Arabic the bars grow from the right edge leftwards, so the chart reads
    # in the same direction as the page.
    figure.update_xaxes(
        range=[11.4, 0] if is_arabic else [0, 11.4],
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        fixedrange=True,
    )
    figure.update_yaxes(
        showgrid=False,
        zeroline=False,
        autorange="reversed",
        side="right" if is_arabic else "left",
        ticksuffix="  ",
        fixedrange=True,
    )
    figure.update_layout(margin=dict(l=28, r=0, t=8, b=8) if is_arabic else dict(l=0, r=28, t=8, b=8))
    return figure


def trait_table(character: dict, user_traits: dict[str, float] | None = None) -> None:
    """The chart's data as a table, so identity is never carried by color alone."""
    rows = {t("trait"): [trait_label(trait) for trait in TRAITS]}
    if user_traits is not None:
        rows[t("you")] = [user_traits[trait] for trait in TRAITS]
    rows[character["name"]] = [character["traits"][trait] for trait in TRAITS]
    st.dataframe(rows, hide_index=True, use_container_width=True)


def character_card(character: dict, show_spoilers: bool, match: int | None = None) -> None:
    """Render one character as a card, with the details behind an expander."""
    badge = (
        f'<span class="hub-badge hub-badge-match">{t("match_badge", match=match)}</span>'
        if match is not None
        else ""
    )
    st.markdown(
        f"""
        <div class="hub-card">
          <div class="hub-card-name">{character["name"]} {badge}</div>
          <div class="hub-card-meta">{meta_line(character)}</div>
          <div class="hub-card-bio">{character_text(character, "bio")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander(t("traits_details")):
        st.plotly_chart(
            trait_chart(character),
            use_container_width=True,
            config={"displayModeBar": False},
            key=f"chart-{character['id']}-{match}",
        )
        with st.popover(t("view_table")):
            trait_table(character)
        if show_spoilers and character.get("spoiler_notes"):
            st.markdown(f"**{t('spoilers_heading')}**")
            st.markdown(
                f'<div class="hub-note">{character_text(character, "spoiler_notes")}</div>',
                unsafe_allow_html=True,
            )
        if character.get("source"):
            st.markdown(f"[{t('read_wiki')}]({character['source']})")


# ---------- Header ----------

title_column, language_column = st.columns([3, 1], vertical_alignment="center")
with title_column:
    st.markdown('<div class="hub-title">Rockstar Character Hub</div>', unsafe_allow_html=True)
with language_column:
    choice = st.radio(
        t("language"),
        ["English", "العربية"],
        index=1 if is_arabic else 0,
        horizontal=True,
        label_visibility="collapsed",
        key="language_choice",
    )
    new_lang = "ar" if choice == "العربية" else "en"
    if new_lang != st.session_state.lang:
        st.session_state.lang = new_lang
        st.rerun()

st.markdown(f'<div class="hub-subtitle">{t("subtitle")}</div>', unsafe_allow_html=True)

all_characters = load_characters()
questions = load_questions()

if not all_characters or not questions:
    st.error(t("data_error"))
    st.stop()

quiz_tab, browse_tab, about_tab = st.tabs([t("tab_quiz"), t("tab_browse"), t("tab_about")])


# ---------- Tab 1: the quiz ----------

with quiz_tab:
    if "answers" not in st.session_state:
        st.session_state.answers = []
    if "quiz_series" not in st.session_state:
        st.session_state.quiz_series = None
    if "result" not in st.session_state:
        st.session_state.result = None

    def reset_quiz() -> None:
        """Clear the answers and the result so the quiz starts from question 1."""
        st.session_state.answers = []
        st.session_state.result = None

    # --- Results screen ---
    if st.session_state.result is not None:
        result = st.session_state.result
        top_name, top_match = result["matches"][0]
        top_character = character_by_name(all_characters, top_name)

        left, right = st.columns([1, 2.4], vertical_alignment="center")
        with left:
            st.markdown(
                f'<div class="hub-hero-label">{t("closest_match")}</div>'
                f'<div class="hub-hero-match">{top_match}%</div>',
                unsafe_allow_html=True,
            )
        with right:
            st.markdown(
                f'<div class="hub-card-name" style="font-size:1.5rem">{top_name}</div>'
                f'<div class="hub-card-meta">{meta_line(top_character)}</div>',
                unsafe_allow_html=True,
            )

        if top_match < WEAK_MATCH_PERCENT:
            st.info(t("weak_match", name=top_name, match=top_match))

        st.markdown(
            f'<div class="hub-card"><div class="hub-card-bio">'
            f'{character_text(top_character, "bio")}</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown("##### " + t("you_vs", name=top_name))
        st.plotly_chart(
            trait_chart(top_character, result["traits"]),
            use_container_width=True,
            config={"displayModeBar": False},
            key="chart-result",
        )
        with st.popover(t("view_table")):
            trait_table(top_character, result["traits"])

        if top_character.get("spoiler_notes"):
            with st.expander(t("spoilers_heading")):
                st.markdown(
                    f'<div class="hub-note">{character_text(top_character, "spoiler_notes")}</div>',
                    unsafe_allow_html=True,
                )

        others = result["matches"][1:]
        if others:
            st.markdown("##### " + t("also_close"))
            for name, match in others:
                character = character_by_name(all_characters, name)
                if character is not None:
                    character_card(character, show_spoilers=False, match=match)

        st.markdown("##### " + t("share_title"))
        st.code(
            t("share_text", name=top_name, match=top_match, url=REPO_URL),
            language=None,
        )

        st.button(t("retake"), on_click=reset_quiz, type="primary")

    # --- Question screen ---
    else:
        step = len(st.session_state.answers)

        if step == 0:
            series_options = [None, *SERIES]
            st.session_state.quiz_series = st.radio(
                t("series_question"),
                series_options,
                format_func=lambda s: t("all_series") if s is None else s,
                horizontal=True,
                key="series_choice",
            )

        question = questions[step]
        options = list(question["options"])

        st.progress((step + 1) / len(questions))
        st.markdown(
            f'<div class="hub-step">{t("question_counter", n=step + 1, total=len(questions))}</div>'
            f'<div class="hub-question">{question_text(question)}</div>',
            unsafe_allow_html=True,
        )

        choice = st.radio(
            t("pick_answer"),
            options,
            index=None,
            format_func=lambda option: option_label(question, option),
            key=f"question-{step}-{st.session_state.lang}",
            label_visibility="collapsed",
        )

        st.write("")
        next_column, back_column, _ = st.columns([1.4, 1, 2.6])
        with back_column:
            if step > 0 and st.button(t("back"), use_container_width=True):
                st.session_state.answers.pop()
                st.rerun()
        with next_column:
            last = step == len(questions) - 1
            if st.button(
                t("see_result") if last else t("next"),
                use_container_width=True,
                type="primary",
                disabled=choice is None,
            ):
                st.session_state.answers.append(choice)
                if last:
                    # Same calculation the CLI uses: add up trait points, scale them
                    # to 0-10, then rank characters by distance.
                    totals = dict.fromkeys(TRAITS, 0)
                    for index, answer in enumerate(st.session_state.answers):
                        quiz_logic.add_points(totals, questions[index]["options"][answer])
                    traits = quiz_logic.to_scale(totals, quiz_logic.max_points(questions))

                    series = st.session_state.quiz_series
                    pool = (
                        all_characters
                        if series is None
                        else characters_module.filter_by(all_characters, "series", series)
                    )
                    st.session_state.result = {
                        "series": series,
                        "traits": traits,
                        "matches": quiz_logic.best_matches(traits, pool, TOP_MATCHES),
                    }
                st.rerun()


# ---------- Tab 2: browse ----------

with browse_tab:
    show_spoilers = st.toggle(t("show_spoilers"), value=False)

    search_column, series_column = st.columns([2, 1])
    with search_column:
        query = st.text_input(t("search_label"), placeholder=t("search_placeholder"))
    with series_column:
        series_filter = st.selectbox(
            t("series_label"),
            [None, *SERIES],
            format_func=lambda s: t("all_series") if s is None else s,
        )

    if series_filter is None:
        game_names = characters_module.get_games_by_year(all_characters)
    else:
        in_series = characters_module.filter_by(all_characters, "series", series_filter)
        game_names = characters_module.get_games_by_year(in_series)

    game_column, role_column = st.columns(2)
    with game_column:
        game_filter = st.selectbox(
            t("game_label"),
            [None, *game_names],
            format_func=lambda g: t("all_games") if g is None else g,
        )
    with role_column:
        role_filter = st.selectbox(
            t("role_label"),
            [None, *characters_module.ROLES],
            format_func=lambda r: t("all_roles") if r is None else role_label(r),
        )

    results = all_characters
    if query.strip():
        results = characters_module.search(results, query)
    if series_filter is not None:
        results = characters_module.filter_by(results, "series", series_filter)
    if game_filter is not None:
        results = characters_module.filter_by(results, "game", game_filter)
    if role_filter is not None:
        results = characters_module.filter_by(results, "role", role_filter)

    results = characters_module.sort_by_name(results)

    st.caption(t("count_caption", shown=len(results), total=len(all_characters)))
    if not results:
        st.info(t("no_results"))
    for character in results:
        character_card(character, show_spoilers)


# ---------- Tab 3: about ----------

with about_tab:
    about_template = arabic.get("about", ABOUT_EN) if is_arabic else ABOUT_EN
    st.markdown(
        about_template.format(
            characters=len(all_characters),
            games=len(characters_module.get_games_by_year(all_characters)),
            url=REPO_URL,
        )
    )
