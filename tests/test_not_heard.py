"""Not heard yet — the T1 fix (founder ruling, Oct 31, 2026,
evening; finding T1 of the external design review).

The review's gravest finding, verified in the shipped
code: the submit handler cleared the composer BEFORE the
send resolved, and send() drew the storyteller's turn as
if settled; on any failure Liv said "please try again"
while the words were gone from the box, present in the
thread, and absent from the server — a chapter arranged
later (built server-side from received tellings) silently
omitted them while the storyteller believed them kept.

The fix pinned here:

- The composer keeps its text until the server confirms
  the turn; confirmation clears it only if the box still
  holds exactly the telling that was sent.
- An unconfirmed storyteller turn carries a visible,
  word-carried "Not heard yet" state from the moment it
  is drawn until confirmation; on failure the mark STAYS
  and a resend button on the turn offers to send the same
  text + media through the same send path. A resend never
  double-draws the turn.
- Media staged via the pending tray return to the tray
  on a failed composer send, and leave it again when the
  resend settles; pressing Send again with the same words
  and media routes to the failed turn's own resend.
- Voice takes (finding R1): a take whose UPLOAD fails is
  held in memory, announced truthfully in the voice-status
  line, and offered the same one-tap resend; a take too
  large ever to send is named impossible rather than
  offered a fake recovery. A take that uploads but whose
  message send fails rides the turn machinery like text.
"""
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"


class _WebCase(unittest.TestCase):
    def setUp(self):
        self.html = (WEB / "index.html").read_text(encoding="utf-8")
        self.js = (WEB / "app.js").read_text(encoding="utf-8")
        self.css = (WEB / "styles.css").read_text(encoding="utf-8")

    def section(self, start, end):
        part = self.js.split(start, 1)[1]
        return part.split(end, 1)[0]


class TestComposerKeepsItsWords(_WebCase):
    def test_submit_no_longer_clears_the_composer_up_front(self):
        handler = self.section(
            'form.addEventListener("submit"',
            "// Finish for today")
        self.assertNotIn('input.value = "";', handler)
        # The old order — drain, clear, send — is gone; the
        # handler sends with the composer as the source and
        # marks the send as composer-born.
        self.assertIn('{ fromComposer: true }', handler)

    def test_confirmation_clears_only_the_exact_telling(self):
        heal = self.section("function healComposer",
                            "function restoreMedia")
        self.assertIn("input.value === state.message", heal)
        self.assertIn('input.value = "";', heal)
        # Only composer-born turns may heal the box — the
        # Finish flow's words are never the composer's.
        self.assertIn("state.fromComposer", heal)

    def test_add_message_returns_the_turn_it_drew(self):
        add = self.section("function addMessage",
                           "// ---- Heard, or not heard yet")
        self.assertIn("return div;", add)


class TestNotHeardMark(_WebCase):
    def test_turn_state_builds_the_words_and_the_button(self):
        state = self.section("function turnState",
                             "function settleTurn")
        self.assertIn('"not-heard-note"', state)
        self.assertIn('textContent = "Not heard yet"', state)
        self.assertIn('"secondary not-heard-resend"', state)
        self.assertIn('textContent = "Try sending again"',
                      state)
        # The button starts hidden — it is offered when a
        # send has failed, not while one is travelling.
        self.assertIn("resend.hidden = true", state)

    def test_attempt_marks_the_turn_from_the_moment_it_flies(self):
        send = self.section("function send(message",
                            "beginBtn.addEventListener")
        self.assertIn('classList.add("not-heard")', send)
        # Confirmation — and only confirmation — settles.
        self.assertIn("if (data.reply) {", send)
        self.assertIn("settleTurn(state)", send)

    def test_settle_removes_mark_note_and_button(self):
        settle = self.section("function settleTurn",
                              "function failTurn")
        self.assertIn('classList.remove("not-heard")', settle)
        self.assertIn("removeChild(state.note)", settle)
        self.assertIn("removeChild(state.resend)", settle)

    def test_failure_keeps_the_mark_and_stands_the_resend(self):
        fail = self.section("function failTurn",
                            "function healComposer")
        self.assertIn("state.resend.hidden = false", fail)
        self.assertNotIn("removeChild", fail)
        self.assertNotIn("settleTurn", fail)

    def test_resend_button_calls_the_turns_own_attempt(self):
        state = self.section("function turnState",
                             "function settleTurn")
        self.assertIn('addEventListener("click"', state)
        self.assertIn("state.attempt()", state)
        # Guarded: never while settled, never while flying.
        self.assertIn("state.settled || state.flying", state)
        send = self.section("function send(message",
                            "beginBtn.addEventListener")
        self.assertIn("state.attempt = attempt", send)

    def test_mark_styles_are_words_in_house_tokens(self):
        note = self.css.split(".msg .not-heard-note {", 1)[1]
        note = note.split("}", 1)[0]
        self.assertIn("var(--ink-2)", note)
        self.assertIn("text-transform: uppercase", note)
        # The resend is the house secondary — a full-size
        # target — and its hidden state truly hides.
        self.assertIn(".not-heard-resend[hidden]", self.css)
        # No new warm fill anywhere in the T1 styles: the
        # one warm fill stays the Talk to Liv key.
        block = self.css.split("/* Not heard yet (T1 fix", 1)[1]
        block = block.split("/* The held voice take", 1)[0]
        self.assertNotIn("var(--action)", block)
        self.assertNotIn("var(--flame)", block)


class TestMediaAndRetryRouting(_WebCase):
    def test_failure_restores_staged_media_to_the_tray(self):
        fail = self.section("function failTurn",
                            "function healComposer")
        self.assertIn("restoreMedia(state.mediaItems)", fail)
        restore = self.section("function restoreMedia",
                               "function dropPendingByIds")
        self.assertIn("restored.concat(pendingMedia)", restore)
        self.assertIn("renderPending()", restore)

    def test_settling_takes_its_media_back_out_of_the_tray(self):
        settle = self.section("function settleTurn",
                              "function failTurn")
        self.assertIn("dropPendingByIds(state.mediaIds)",
                      settle)

    def test_send_again_routes_to_the_failed_twin(self):
        handler = self.section(
            'form.addEventListener("submit"',
            "// Finish for today")
        self.assertIn("findFailedTurn(text, media)", handler)
        self.assertIn("twin.attempt()", handler)
        # The twin route runs before any new send is drawn.
        self.assertLess(handler.index("findFailedTurn"),
                        handler.index("send(text, true, media"))

    def test_duplicate_press_while_travelling_is_ignored(self):
        handler = self.section(
            'form.addEventListener("submit"',
            "// Finish for today")
        self.assertIn("inflightSigs[sendSignature(text, "
                      "stagedIds)]", handler)

    def test_session_wipe_forgets_unsettled_turns(self):
        wipe = self.section("function endSessionNow",
                            "sitting sheet")
        self.assertIn("liveTurns = [];", wipe)
        self.assertIn("inflightSigs = {};", wipe)


class TestVoiceTakes(_WebCase):
    def test_failed_upload_holds_the_take_and_offers_resend(self):
        take = self.section("function sendVoiceTake",
                            "micPause.addEventListener")
        self.assertIn("else { holdTake(blob, type, cutShort); }",
                      take)
        # The successful path is the unchanged pipeline.
        self.assertIn('send("", true, [item])', take)

    def test_hold_announces_the_truth_in_the_status_line(self):
        hold = self.section("function holdTake",
                            "function dropHeldTake")
        self.assertIn("didn't reach Liv", hold)
        self.assertIn("takeResendBtn.hidden = false", hold)

    def test_oversize_take_is_named_not_offered(self):
        hold = self.section("function holdTake",
                            "function dropHeldTake")
        self.assertIn("blob.size > MEDIA_CAPS.audio", hold)
        self.assertIn("too large to send", hold)

    def test_resend_button_exists_hidden_and_wired(self):
        self.assertIn('id="take-resend"', self.html)
        self.assertIn(">Try sending again</button>", self.html)
        self.assertIn('document.getElementById("take-resend")',
                      self.js)
        click = self.section(
            'takeResendBtn.addEventListener("click"',
            "function sendVoiceTake")
        self.assertIn("sendVoiceTake(take.blob, take.type, "
                      "take.cutShort)", click)

    def test_session_wipe_drops_a_held_take(self):
        wipe = self.section("function endSessionNow",
                            "sitting sheet")
        self.assertIn("dropHeldTake();", wipe)


if __name__ == "__main__":
    unittest.main()
