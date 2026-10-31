"""Liv-only + greeting contracts (founder rulings, Oct 29, 2026).

Three rulings pinned here:

- LIV-ONLY: the companion is Liv — only Liv. The Livio/Livia
  variants mapped to voices, but TTS was cut from this build, so
  the consent-screen choice changed nothing real. A client may
  still SEND a companion/companion_name value; it is accepted and
  ignored, and a session's name can never vary from Liv.
- GREETING: Liv introduces herself in the founder's words —
  "Hi, I'm Liv!" — keeping the pace and skip beats, and the
  name ask now carries its own skip ("…or no name at all — and
  you can skip this too; whatever feels right.").
- ONE-ASK GUARANTEE: the name question is asked exactly once.
  A clear name answer is captured; an explicit skip/decline is
  honoured with no name stored and no re-ask; a substantive
  telling launched straight past the question is received as
  the story — never mined for a name, never circled back to.
- MIC BUTTON (UI/UX ruling, same day): an inline SVG microphone
  (never the emoji glyph), an always-visible "Talk to Liv"
  label, and a distinct recording state in CSS.
- CONVERSATION LAYOUT (founder rulings, Oct 29, 2026, in
  three acts: his layout ruling, his hand sketch, his own
  vetted mockup — then CASANOVA Direction B "Sheet",
  chosen by the founder over Direction A the same night):
  the app is ONE calm sheet centred on a quiet desk. The
  header is the wordmark as he drew it — "FireSide" in
  ExtraBold italic near-black with a terracotta flame
  glyph after the word — over the sub-line "Talking To
  Liv" (title case as drawn; his phrasing: to, not
  with), Montserrat bold, ink, left-aligned. TYPE
  (founder ruling, Oct 29, 2026): Montserrat throughout,
  in varying weights and styles — 800 italic wordmark,
  700 headings, 700 labels, 400 body, 500 italic cameos;
  Atkinson Hyperlegible rides second in the stack as
  the fallback face. PALETTE (founder ruling, same
  night): his own "Earth & Oak" palette — Desert Sand
  #D5C2B1, Eucalyptus Sage #839788, Raw Linen #E6E1DA,
  Terracotta Earth #A75D3F, Volcanic Stone #3C3B3A — in
  its QUIET NEUTRALS use (use #9 of ten drawn): the
  stone neutrals carry the sheet, and exactly ONE warm
  event remains — the flame (var(--flame), declared
  Terracotta) and the Talk to Liv pill (var(--action),
  Terracotta Deep). ONE paper tone (--sheet, Linen
  Light) and ONE card tone (--card, Warm White): the
  cream stack is collapsed and the old ember/blue
  tokens are deleted. Speaker labels ride above each
  turn, small — LIV left in Volcanic Stone (var(--liv)),
  YOU right in a warm gray (var(--you) #6E675C), in
  capitals set by CSS with NO marker glyphs; the DOM
  text stays "Liv" / "You" for assistive technology.
  Both speakers' turns live in the SAME square box at
  the SAME size (parity is deliberate), differentiated
  by 3px rules — volcanic at Liv's LEFT, warm gray at
  the storyteller's RIGHT — and the label colours.
  Dialogue boxes are RECTANGULAR (border-radius 0);
  the sheet, the field, and the buttons keep their
  curves. The 4px seam is DELETED (condition 3). The
  reply section is a dark band exactly as wide as the
  SHEET, never 100vw: label "Reply", a white field at
  20px radius, one action row (Talk to Liv — the row's
  sole WARM fill · + Add · Send as a full pill at the
  right end with a NON-warm ink fill, condition 2),
  the session actions inside the band as ghost outline
  buttons at 52px with borders in the tokenised
  --ghost-line (#BCB8B2), and "Take your time" beneath
  them in its Montserrat Medium italic cameo — nothing
  of the session area remains on the sheet below the
  band. Standing UI principle, in his words:
  minimalist but very functional, conversational,
  intuitive, effective.
- THE MARRIAGE (founder ruling, Oct 31, 2026; spec:
  design-vet/marriage/marriage.html) supersedes the
  Direction B shell where they differ: each screen is
  an ink CHASSIS at 100dvh (header pinned, one scroll
  region, foot pinned; the desk shows around the
  console on wide screens; consent and chapter capped
  at a 760px letter measure). The Sheet's manners
  survive inside it — the wordmark large, the same
  turn boxes and labels, the token set unchanged. The
  sub-line moved INTO the ink titlebar (20px; tint on
  ink 8.6:1; phrasing and casing unchanged). The reply
  band became the SWITCHBOARD: the meter asleep
  (segments only — nothing claims LISTENING at rest),
  one write line (+ Add key · card field at radius
  2px · Send as a control-brown key, never the warm
  fill), then the Talk key — a square machine key now
  (radius 2px, 56px), no longer a pill. The session
  actions LEFT the band: Finish, Arrange and the
  hold-to-delete guard live on the desktop guard
  RAIL (from 1024px) and, below that width, behind
  the header's "This sitting" control in a sheet of
  the same words. Deleting is a HOLD (~2s, flame
  track, live-region announcements), never a tap;
  completing it runs the unchanged end-session flow.
  The recording band's meter lights from the REAL
  microphone level (an AnalyserNode on the recorder's
  own stream). The chapter gained the ribbon graft:
  checklist and outline rows, and the draft's section
  headings, hang on a flame spine with a node
  generated per row.
"""
import unittest
from pathlib import Path

from server import app
from server.canned import CannedCompanion, normalize_companion_name

WEB = Path(__file__).resolve().parent.parent / "web"

NAME_ASK = ("Before we begin — what would you like me to call "
            "you? A name, a nickname, or no name at all — and "
            "you can skip this too; whatever feels right.")
STORY = ("I grew up in Bamenda, in Cameroon, and the house I "
         "remember most is the one behind the old market, where "
         "my grandmother kept chickens and the rain on the zinc "
         "roof sounded like drumming.")


class TestLivOnlyNames(unittest.TestCase):
    def test_normalize_always_returns_liv(self):
        for value in ("Liv", "Livio", "Livia", "livia", "Bob",
                      "", None, 42):
            self.assertEqual(normalize_companion_name(value), "Liv")

    def test_companion_cannot_be_constructed_with_a_variant(self):
        self.assertEqual(CannedCompanion("Livia").name, "Liv")
        self.assertEqual(CannedCompanion("Livio").name, "Liv")
        self.assertEqual(CannedCompanion().name, "Liv")


class TestGreeting(unittest.TestCase):
    def test_greeting_opens_with_the_founders_words(self):
        self.assertTrue(
            CannedCompanion().greeting().startswith("Hi, I’m Liv!"))

    def test_greeting_keeps_pace_skip_and_the_ask_with_its_skip(self):
        greeting = CannedCompanion().greeting()
        self.assertIn("we can go at your pace", greeting)
        self.assertIn("And we can skip anything — just say so.",
                      greeting)
        self.assertIn(NAME_ASK, greeting)


class _EmptyChatClient:
    """Live-shaped stub whose chat returns empty, so handle_chat
    lands on the canned companion (the parity path)."""

    def chat(self, messages, model=None, **kwargs):
        return "", {}

    def transcribe_wav(self, wav_bytes, model=None):
        raise RuntimeError("not used here")


class TestHandlerLivOnly(unittest.TestCase):
    def setUp(self):
        app._sessions.clear()
        self._saved_client = app._live_client
        app._live_client = _EmptyChatClient()

    def tearDown(self):
        app._live_client = self._saved_client
        app._sessions.clear()

    def chat(self, session_id, message, **extra):
        payload = {"session_id": session_id, "consent": True,
                   "age_confirmed": True, "message": message}
        payload.update(extra)
        status, body = app.handle_chat(payload)
        self.assertEqual(status, 200, body)
        return body

    def test_variant_request_still_greets_as_liv(self):
        body = self.chat("s-variant", "", companion="Livia")
        self.assertEqual(body["companion"], "Liv")
        self.assertTrue(body["reply"].startswith("Hi, I’m Liv!"))

    def test_variant_sent_mid_session_changes_nothing(self):
        self.chat("s-mid", "", companion_name="Livio")
        self.chat("s-mid", "Call me Petro.")
        body = self.chat("s-mid", "Petro is fine.",
                         companion="Livia")
        self.assertEqual(body["companion"], "Liv")
        self.assertEqual(
            app._sessions["s-mid"]["companion_name"], "Liv")

    def test_sessions_never_vary(self):
        for i, asked in enumerate(("Livio", "Livia", "Liv", None)):
            sid = "s-%d" % i
            extra = {} if asked is None else {"companion": asked}
            body = self.chat(sid, "", **extra)
            self.assertEqual(body["companion"], "Liv")


class TestOneAskGuarantee(unittest.TestCase):
    """The three first-reply shapes (founder catch, Oct 29)."""

    def companion_after(self, first_reply):
        c = CannedCompanion()
        c.greeting()
        reply = c.reply(first_reply)
        return c, reply

    def test_clear_name_is_captured_and_used_sparingly(self):
        c, reply = self.companion_after("Call me Petro.")
        self.assertEqual(c.preferred_name, "Petro")
        self.assertEqual(c.name_state, "set")
        self.assertIn("Petro", reply)

    def test_explicit_skip_stores_no_name(self):
        for decline in ("Skip.", "I'd rather not say.",
                        "No name at all, thanks."):
            c, reply = self.companion_after(decline)
            self.assertIsNone(c.preferred_name, decline)
            self.assertEqual(c.name_state, "declined", decline)
            self.assertIn("no name at all is perfectly fine", reply)

    def test_decline_is_never_reasked(self):
        c, _ = self.companion_after("Skip.")
        follow = c.reply("Judith was like a second mother to me.")
        self.assertNotIn("what would you like me to call", follow)
        self.assertIsNone(c.preferred_name)

    def test_story_first_reply_is_a_telling_not_a_name(self):
        c, reply = self.companion_after(STORY)
        self.assertIsNone(c.preferred_name)
        self.assertEqual(c.name_state, "missed")
        # The story was heard as a story: a detail was gathered
        # and the reply follows up on the telling itself.
        self.assertTrue(c.details)
        self.assertIn("Bamenda", reply)

    def test_story_first_reply_is_never_reasked(self):
        c, _ = self.companion_after(STORY)
        follow = c.reply("The roof leaked every rainy season.")
        self.assertNotIn("what would you like me to call", follow)
        self.assertIsNone(c.preferred_name)

    def test_im_from_is_a_telling_not_a_name(self):
        c, _ = self.companion_after("I'm from Bamenda.")
        self.assertIsNone(c.preferred_name)
        self.assertEqual(c.name_state, "missed")


class TestFrontendContract(unittest.TestCase):
    def setUp(self):
        self.html = (WEB / "index.html").read_text(encoding="utf-8")
        self.js = (WEB / "app.js").read_text(encoding="utf-8")
        self.css = (WEB / "styles.css").read_text(encoding="utf-8")

    def test_no_variants_no_choice_in_the_page(self):
        self.assertNotIn("Livio", self.html)
        self.assertNotIn("Livia", self.html)
        self.assertNotIn('name="companion"', self.html)
        self.assertIn('class="companion-intro"', self.html)

    def test_no_companion_choice_sent_or_wired(self):
        self.assertNotIn("Livio", self.js)
        self.assertNotIn("Livia", self.js)
        self.assertNotIn('input[name="companion"]', self.js)
        self.assertNotIn("companion:", self.js)

    def test_mic_icon_is_svg_never_emoji(self):
        self.assertNotIn("\U0001F399", self.html)  # 🎙 emoji
        self.assertIn('<span class="mic-icon" aria-hidden="true">'
                      "<svg", self.html)
        self.assertIn('id="mic-label">Talk to Liv<', self.html)

    def test_mic_button_styles_two_colour_and_recording_state(self):
        resting = self.css.split(".mic-btn {", 1)[1].split("}", 1)[0]
        self.assertIn("background: var(--action)", resting)
        self.assertIn("color: #FFFFFF", resting)
        # The Marriage (Oct 31, 2026): the pill became a
        # machine key — square corners, the board's 56px
        # key height. The warm fill and the white label
        # (6.1:1) are unchanged.
        self.assertIn("border-radius: 2px", resting)
        self.assertIn("min-height: 3.5rem", resting)
        recording = self.css.split(".mic-btn.recording {", 1)[1]
        recording = recording.split("}", 1)[0]
        self.assertIn("background: var(--ink)", recording)
        self.assertIn(".mic-btn.recording::after", self.css)


class TestConversationLayout(unittest.TestCase):
    """Founder layout rulings (Oct 29, 2026; the Marriage,
    Oct 31, 2026) — see module docstring."""

    def setUp(self):
        self.html = (WEB / "index.html").read_text(encoding="utf-8")
        self.js = (WEB / "app.js").read_text(encoding="utf-8")
        self.css = (WEB / "styles.css").read_text(encoding="utf-8")

    def test_page_title_begins_with_the_brand(self):
        self.assertIn(
            "<title>Fireside — Your stories, in your own voice"
            "</title>", self.html)

    def test_brand_lockup_wordmark_and_flame(self):
        # The vetted mockup's wordmark: ExtraBold italic
        # "FireSide" (capital F, capital S) in Montserrat,
        # with the terracotta flame glyph AFTER the word —
        # the flame-in-ring medallion is gone.
        self.assertIn('class="brand-lockup"', self.html)
        self.assertIn('<span class="brand-name">FireSide</span>',
                      self.html)
        self.assertIn('class="brand-flame"', self.html)
        self.assertLess(self.html.index('class="brand-name"'),
                        self.html.index('class="brand-flame"'))
        self.assertNotIn('class="brand-mark"', self.html)
        name = self.css.split(".brand-name {", 1)[1].split("}", 1)[0]
        self.assertIn("font-style: italic", name)
        self.assertIn("font-weight: 800", name)
        # Direction B type scale: the wordmark at 32px.
        self.assertIn("font-size: 2rem", name)
        flame = self.css.split(".brand-flame {", 1)[1]
        flame = flame.split("}", 1)[0]
        self.assertIn("color: var(--flame)", flame)

    def test_sub_line_is_the_founders_phrasing(self):
        # His phrasing ("to", not "with"), presented title
        # case as drawn in the vetted mockup — Montserrat
        # bold, left-aligned, never italic.
        self.assertIn(
            '<h1 id="chat-heading" class="chat-subtitle">'
            "Talking To Liv</h1>", self.html)
        self.assertNotIn("Talking with", self.html)
        sub = self.css.split(".chat-subtitle {", 1)[1].split("}", 1)[0]
        self.assertIn("font-weight: 700", sub)
        self.assertIn("text-align: left", sub)
        self.assertNotIn("italic", sub)
        # The Marriage (Oct 31, 2026): the sub-line moved
        # into the ink titlebar, under the wordmark — the
        # board's 20px, in tint on the ink (8.6:1). The
        # phrasing and title casing above are untouched.
        self.assertIn("font-size: 1.25rem", sub)
        self.assertIn("color: var(--tint)", sub)

    def test_conversation_lives_in_the_chassis(self):
        # The Marriage (Oct 31, 2026): the Sheet's single
        # centred page is superseded by the chassis — each
        # screen an ink machine at 100dvh, header pinned,
        # one scroll region, foot pinned; her manners and
        # the whole token set live on inside it.
        consent = self.html.index('id="consent-screen"')
        chat = self.html.index('id="chat-screen"')
        chapter = self.html.index('id="chapter-screen"')
        self.assertLess(consent, chat)
        self.assertLess(chat, chapter)
        self.assertIn(
            'id="consent-screen" class="chassis chassis-narrow"',
            self.html)
        self.assertIn('id="chat-screen" class="chassis"',
                      self.html)
        self.assertIn(
            'id="chapter-screen" class="chassis chassis-narrow"',
            self.html)
        # The declared tokens of the Sheet world — unchanged
        # by the Marriage (Quiet Neutrals only).
        for token in ("--desk: #D5C2B1", "--sheet: #F1EDE6",
                      "--card: #FBF9F5", "--ink: #3C3B3A",
                      "--liv: #3C3B3A", "--you: #6E675C",
                      "--action: #93502F", "--flame: #A75D3F",
                      "--tint: #E6E1DA", "--control: #655C4E",
                      "--ink-2: #68635B",
                      "--ghost-line: #BCB8B2"):
            self.assertIn(token, self.css)
        # The cream stack and the old colour tokens are
        # gone, and the quiet ink is a solid token now,
        # not an rgba.
        for gone in ("--paper:", "--paper-2:", "--paper-3:",
                     "--box:", "--gold:", "--sage:",
                     "--ember:", "var(--ember)",
                     "--ember-deep:", "var(--ember-deep)",
                     "--ember-tint:", "--user-blue:",
                     "var(--user-blue)", "#1458B4", "#9D2224",
                     "Cormorant",
                     "var(--ink-soft)"):
            self.assertNotIn(gone, self.css)
        body = self.css.split("body {", 1)[1].split("}", 1)[0]
        self.assertIn("background: var(--desk)", body)
        chassis = self.css.split(".chassis {", 1)[1]
        chassis = chassis.split("}", 1)[0]
        self.assertIn("background: var(--ink)", chassis)
        self.assertIn("display: flex", chassis)
        # A hidden screen stays hidden under the flex
        # shell (an author display would defeat it).
        hidden = self.css.split(".chassis[hidden] {", 1)[1]
        hidden = hidden.split("}", 1)[0]
        self.assertIn("display: none", hidden)
        # The shell is viewport-tall; the page itself does
        # not carry the scroll.
        app = self.css.split(".app {", 1)[1].split("}", 1)[0]
        self.assertIn("height: 100dvh", app)
        # The turns still group inside the panel wrapper,
        # and the composer still follows — the panel is now
        # the sheet FACE inside the chassis and the app's
        # one scroll region on this screen.
        panel = self.html.index('class="conversation-panel"')
        messages = self.html.index('id="messages"')
        listening = self.html.index('id="listening"')
        composer = self.html.index('class="composer"')
        self.assertLess(panel, messages)
        self.assertLess(messages, listening)
        self.assertLess(listening, composer)
        block = self.css.split(".conversation-panel {", 1)[1]
        block = block.split("}", 1)[0]
        self.assertIn("background: var(--sheet)", block)
        self.assertIn("overflow-y: auto", block)

    def test_speaker_labels_small_caps_and_marker_free(self):
        # The founder's sketch restored the labels; his review
        # of the deployed build then removed the marker glyphs
        # (refinement, Oct 29, 2026): the name alone, in
        # capitals set by CSS, at the same small size. The DOM
        # text app.js writes stays "Liv" / "You", so AT reads
        # the speaker as before.
        self.assertIn('label.className = "who"', self.js)
        block = self.css.split(".msg .who {", 1)[1].split("}", 1)[0]
        self.assertIn("display: block", block)
        # Direction B type scale: 13px, bold, tracked out.
        self.assertIn("font-size: 0.8125rem", block)
        self.assertIn("font-weight: 700", block)
        self.assertIn("letter-spacing: 0.08em", block)
        self.assertIn("text-transform: uppercase", block)
        # The visually-hidden recipe stays gone.
        self.assertNotIn("clip-path: inset(50%)", block)
        self.assertNotIn("position: absolute", block)
        # No markers anywhere: no ::before content on the
        # labels, and neither glyph survives in the stylesheet.
        self.assertNotIn(".who::before", self.css)
        self.assertNotIn("◆", self.css)
        self.assertNotIn("●", self.css)
        # The storyteller's label still aligns right, over
        # his boxes.
        you = self.css.split(".msg.storyteller .who {", 1)[1]
        you = you.split("}", 1)[0]
        self.assertIn("text-align: right", you)

    def test_turn_boxes_unified_with_mirrored_rules(self):
        # Direction B (Oct 29, 2026) in Quiet Neutrals:
        # both speakers' turns live in the SAME square box
        # (--card, Warm White) on the sheet. The
        # differentiators are the 3px rules (a margin mark,
        # not a flag: volcanic at Liv's LEFT, the
        # storyteller's warm gray at his RIGHT) and the
        # label colours. Dialogue boxes stay RECTANGULAR
        # (founder amendment: radius 0, rules flush); the
        # sheet, the field, and the buttons keep their
        # curves. Parity is deliberate (reconciliation
        # D16): both turns set at the same 19px / 1.65.
        # Ink on the card is 10.6:1.
        self.assertIn("--you: #6E675C", self.css)
        liv = self.css.split(".msg.companion {", 1)[1].split("}", 1)[0]
        self.assertIn("border-left: 3px solid var(--liv)", liv)
        self.assertIn("background: var(--card)", liv)
        self.assertIn("border-radius: 0", liv)
        you = self.css.split(".msg.storyteller {", 1)[1]
        you = you.split("}", 1)[0]
        self.assertIn("border-right: 3px solid var(--you)",
                      you)
        self.assertIn("background: var(--card)", you)
        self.assertIn("border-radius: 0", you)
        # Same shape: the padding declaration is identical.
        liv_pad = [ln.strip() for ln in liv.splitlines()
                   if "padding:" in ln]
        you_pad = [ln.strip() for ln in you.splitlines()
                   if "padding:" in ln]
        self.assertEqual(liv_pad, you_pad)
        self.assertEqual(liv_pad,
                         ["padding: 1.125rem 1.375rem;"])
        # Deliberate size parity: identical font-size and
        # line-height on both speakers' turns.
        for block in (liv, you):
            self.assertIn("font-size: 1.19rem", block)
            self.assertIn("line-height: 1.65", block)
        # The label colours ride with the speakers: LIV in
        # Volcanic Stone (9.6:1 on the sheet, AAA), YOU in
        # his warm gray (5.1:1 on the sheet).
        liv_who = self.css.split(".msg.companion .who {", 1)[1]
        liv_who = liv_who.split("}", 1)[0]
        self.assertIn("color: var(--liv)", liv_who)
        you_who = self.css.split(".msg.storyteller .who {", 1)[1]
        you_who = you_who.split("}", 1)[0]
        self.assertIn("color: var(--you)", you_who)
        self.assertIn("text-align: right", you_who)

    def test_composer_follows_the_marriage_board(self):
        # The Marriage foot (Oct 31, 2026): one plain write
        # line — + Add (a machine key now, in the line, not
        # above it), the field, Send — then the Talk key on
        # its own row (phone) or at 300px in the same row
        # (desktop console, board 2).
        field = self.html.index('id="chat-input"')
        mic = self.html.index('id="mic-btn"')
        attach = self.html.index('id="btn-attach"')
        send = self.html.index('class="primary small send-btn"')
        self.assertLess(attach, field)
        self.assertLess(field, send)
        self.assertLess(send, mic)
        self.assertIn('class="attach-btn key-add"', self.html)
        # The button lives in the write line; the picker it
        # controls stayed in place above the form.
        row = self.html.split('class="attach-row"', 1)[1]
        row = row.split("</div>", 1)[0]
        self.assertNotIn('id="btn-attach"', row)
        self.assertIn('id="attach-picker"', row)
        # The console row: the Talk key at the board's
        # 300px, the write line taking the rest.
        self.assertIn(".writeline {", self.css)
        self.assertIn("flex: 0 0 300px", self.css)

    def test_reply_section_is_the_switchboard(self):
        # The Marriage (Oct 31, 2026): the reply form is the
        # chassis's switchboard foot — ink, the board's own
        # padding, pinned under the conversation. The Sheet
        # band's negative-margin reach is gone with the
        # sheet. The session actions LEFT the foot: they
        # live on the guard rail (and its narrow twin, the
        # sitting sheet); "Take your time" stays.
        self.assertIn('<form id="chat-form" class="reply-band">',
                      self.html)
        self.assertIn('<label for="chat-input">Reply</label>',
                      self.html)
        band = self.css.split(".reply-band {", 1)[1].split("}", 1)[0]
        self.assertIn("background: var(--ink)", band)
        self.assertIn("padding: 0.875rem 1rem 1rem", band)
        self.assertNotIn("calc(-1", band)
        self.assertNotIn("100vw", band)
        # The seam stays gone — element and rule both.
        self.assertNotIn('class="seam"', self.html)
        self.assertNotIn(".seam {", self.css)
        form_open = self.html.index('<form id="chat-form"')
        form_close = self.html.index("</form>")
        # The session actions are NOT in the foot any more…
        for frag in ('id="finish-btn"', 'id="chapter-btn"',
                     'id="end-session-btn"'):
            self.assertNotIn(frag,
                             self.html[form_open:form_close])
        # …they live on the rail, in the board's words…
        rail = self.html.index('<aside class="rail"')
        for frag in ('id="finish-btn"', 'id="chapter-btn"',
                     'id="end-session-btn"'):
            self.assertLess(rail, self.html.index(frag), frag)
        self.assertIn("Hold to delete everything", self.html)
        # …and behind the header's one control on narrow
        # widths, as the sheet of the same words.
        for frag in ('id="sitting-btn"', 'id="sitting-sheet"',
                     'id="finish-btn-sheet"',
                     'id="chapter-btn-sheet"',
                     'id="end-session-btn-sheet"'):
            self.assertIn(frag, self.html)
        # "Take your time" still closes the foot.
        calm_where = self.html.index(
            "Take your time. There is no hurry here.")
        self.assertLess(form_open, calm_where)
        self.assertLess(calm_where, form_close)
        # On the dark ground the status words are sheet
        # (9.6:1)…
        self.assertIn(".reply-band .voice-status", self.css)
        # …the field is the card at the machine's radius,
        # its text at the heritage floor line-height…
        field = self.css.split("#chat-input {", 1)[1]
        field = field.split("}", 1)[0]
        self.assertIn("background: var(--card)", field)
        self.assertIn("border-radius: 2px", field)
        self.assertIn("line-height: 1.65", field)
        # …and Send is NOT the warm fill: a control-brown
        # key (card words on control, 6.3:1) — the Talk
        # key is the foot's sole warm fill.
        send = self.css.split(".reply-band .send-btn {", 1)[1]
        send = send.split("}", 1)[0]
        self.assertIn("background: var(--control)", send)
        self.assertNotIn("var(--action)", send)
        # "Take your time" closes the foot in its cameo —
        # Montserrat Medium italic (founder type ruling).
        calm = self.css.split(".reply-band .quiet {", 1)[1]
        calm = calm.split("}", 1)[0]
        self.assertIn("Montserrat", calm)
        self.assertIn("font-style: italic", calm)
        self.assertIn("font-weight: 500", calm)
        self.assertIn("color: var(--sheet)", calm)

    def test_hold_guard_replaces_the_end_button(self):
        # Deleting is a hold, never a tap (board 8): the
        # guard's own words ride in the page, the mechanics
        # are a ~2s press (pointer and keyboard) with the
        # flame track filling, and completion runs the SAME
        # end-session flow the plain button used to fire.
        self.assertIn("Hold to delete everything", self.html)
        self.assertIn("it is a hold, never a tap", self.html)
        self.assertIn('class="track"', self.html)
        self.assertIn("function wireHold", self.js)
        self.assertIn("var HOLD_MS = 2000;", self.js)
        self.assertIn("function endSessionNow()", self.js)
        self.assertIn('"/api/session/end"', self.js)
        # Progress and cancellation are announced in the
        # live region, never carried by the track alone.
        self.assertIn("Deleting — keep holding", self.js)
        self.assertIn("Delete cancelled — nothing was "
                      "deleted.", self.js)
        # The rail appears at the console breakpoint; below
        # it, the sitting control carries the same actions.
        self.assertIn("@media (min-width: 1024px)", self.css)
        rail = self.css.split(".rail {", 1)[1].split("}", 1)[0]
        self.assertIn("display: none", rail)

    def test_the_meter_claims_nothing_at_rest(self):
        # The founder's honesty flag: at rest the meter is
        # segments only — no LISTENING word is claimed
        # anywhere in the page — and while recording the
        # band's segments light from the REAL microphone
        # level, measured off the recorder's own stream.
        self.assertNotIn("LISTENING", self.html)
        self.assertIn('id="mic-level"', self.html)
        self.assertIn('class="meter-rest"', self.html)
        self.assertIn("function startMeter", self.js)
        self.assertIn("createAnalyser", self.js)
        self.assertIn("getByteTimeDomainData", self.js)
        # While a recording runs, the whole foot is the
        # recording: the calm rows step away (board 5).
        self.assertIn('form.classList.add("is-recording")',
                      self.js)
        self.assertIn(".reply-band.is-recording .writeline",
                      self.css)

    def test_chapter_wears_the_ribbon(self):
        # The ribbon graft (board 6/7): the checklist and
        # the outline hang on a flame spine, and the set
        # chapter's section headings carry filled nodes —
        # every node generated per row by CSS, never a
        # hand-placed offset in markup.
        for sel in (".chapter-checklist::before",
                    ".chapter-checklist li::before",
                    ".chapter-checklist li.done::before",
                    ".chapter-sections::before",
                    ".chapter-sections li::before",
                    ".chapter-draft-body::before",
                    ".chapter-draft-body .chapter-h3::before"):
            self.assertIn(sel, self.css)
        self.assertIn("background: var(--flame)",
                      self.css.split(
                          ".chapter-draft-body .chapter-h3"
                          "::before {", 1)[1].split("}", 1)[0])


if __name__ == "__main__":
    unittest.main()
