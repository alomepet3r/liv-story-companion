"""Voice deck contracts (Rehearsal Finding #1 rebuild, Oct 30, 2026).

The dress rehearsal found the recorder a maze at both ends:
no timer, no discoverable pause/stop on the way in, and a
blind auto-send — no way to hear a take — on the way out.
The founder's spec, and this build: ONE TAP IN, ONE
DECISION OUT.

- IN: tapping Talk to Liv starts recording immediately
  (the first-use notice is inline, once, as before). The
  recording bar is in plain sight while recording: an
  elapsed timer that counts, a Stop button, and a Pause
  button shown ONLY where the browser truly supports
  MediaRecorder.pause()/resume() — never faked. Every
  transition is announced in #voice-status; no state
  rides on colour alone.
- OUT: Stop lands the take in exactly one review bar —
  Play/Pause to hear it, its duration, Re-record
  (discards, back to idle), Send. Send runs the unchanged
  listening-track + /api/media pipeline and fires the
  heard-you state in the same beat. Takes recorded from
  the + Add panel land in the same deck.

Ride-alongs pinned here too:

- Finding #2: the session buttons route through named,
  in-flight-guarded handlers (finishForToday /
  endInFlight), so a landed tap can never queue a second
  close or a second wipe behind a slow first one.
- Finding #4: the end-session confirmation line sits at
  the TOP of the consent screen, where the storyteller
  lands after a wipe, as a polite status region.
"""
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"


class _WebCase(unittest.TestCase):
    def setUp(self):
        self.html = (WEB / "index.html").read_text(encoding="utf-8")
        self.js = (WEB / "app.js").read_text(encoding="utf-8")
        self.css = (WEB / "styles.css").read_text(encoding="utf-8")


class TestVoiceDeckDom(_WebCase):
    def test_recording_bar_present_hidden_and_labelled(self):
        self.assertIn('id="mic-recbar" class="mic-recbar" hidden',
                      self.html)
        self.assertIn('aria-label="Recording controls"', self.html)
        self.assertIn('id="mic-timer"', self.html)
        self.assertIn('id="mic-pause" class="secondary" '
                      'type="button"', self.html)
        self.assertIn('id="mic-stop" class="secondary" '
                      'type="button"', self.html)
        # The timer is visual; the live region carries state,
        # so the ticking numbers stay out of the AT stream.
        self.assertIn('id="mic-timer" class="mic-timer" '
                      'aria-hidden="true"', self.html)

    def test_review_bar_present_hidden_and_labelled(self):
        self.assertIn('id="mic-review" class="mic-review" hidden',
                      self.html)
        self.assertIn('aria-label="Review your recording"',
                      self.html)
        for frag in ('id="mic-play"', 'id="mic-duration"',
                     'id="mic-rerecord"', 'id="mic-send"',
                     'id="mic-playback"'):
            self.assertIn(frag, self.html)
        self.assertIn('id="mic-send" class="primary small" '
                      'type="button"', self.html)

    def test_deck_lives_inside_the_reply_band(self):
        form_open = self.html.index('<form id="chat-form"')
        form_close = self.html.index("</form>")
        for frag in ('id="mic-recbar"', 'id="mic-review"'):
            where = self.html.index(frag)
            self.assertLess(form_open, where, frag)
            self.assertLess(where, form_close, frag)

    def test_dead_audio_use_button_is_gone_video_keeps_his(self):
        # "Use this recording" could never be reached for a
        # recorded take (the stop branch always hid it), and
        # a chosen file stages directly — dead furniture,
        # removed. Video's preview/Use flow is untouched.
        self.assertNotIn('id="audio-use"', self.html)
        self.assertIn('id="audio-discard"', self.html)
        self.assertIn('id="video-use"', self.html)


class TestVoiceDeckJs(_WebCase):
    def test_pause_is_feature_detected_never_faked(self):
        self.assertIn("MediaRecorder.prototype.pause", self.js)
        self.assertIn("typeof MediaRecorder.prototype.pause "
                      "=== \"function\"", self.js)
        self.assertIn("micPause.hidden = !micCanPause", self.js)
        self.assertIn("R.rec.pause()", self.js)
        self.assertIn("R.rec.resume()", self.js)

    def test_stop_lands_in_the_review_deck(self):
        self.assertIn("function enterVoiceReview(blob, type)",
                      self.js)
        self.assertIn("enterVoiceReview(audioBlob, type)",
                      self.js)
        # The deck's Send runs the unchanged pipeline and
        # announces the heard-you state in the same beat.
        self.assertIn('stageWithListening("audio", take.blob',
                      self.js)
        self.assertIn("Heard you — Liv is listening to your "
                      "words.", self.js)
        # A deliberate discard still skips the deck entirely.
        self.assertIn("R.discardNext", self.js)
        self.assertIn("Recording discarded — nothing was "
                      "sent.", self.js)

    def test_pill_speaks_the_new_truth(self):
        # Stop no longer sends, so the recording label says
        # what the tap now does.
        self.assertIn('micLabel.textContent = "Tap to stop"',
                      self.js)
        self.assertNotIn('micLabel.textContent = "Tap to send"',
                         self.js)

    def test_timer_ticks_on_the_recording_bar(self):
        self.assertIn("deckTickStart", self.js)
        self.assertIn("micTimer.textContent = "
                      "fmtTime(deckElapsed())", self.js)


class TestSessionButtonGuards(_WebCase):
    def test_finish_routes_through_a_guarded_named_function(self):
        self.assertIn("function finishForToday()", self.js)
        self.assertIn("finishInFlight", self.js)
        self.assertIn('addEventListener("click",\n    '
                      'finishForToday)', self.js)

    def test_end_session_is_in_flight_guarded(self):
        self.assertIn("endInFlight", self.js)
        self.assertIn("if (!consented || endInFlight)",
                      self.js)


class TestEndSessionNote(_WebCase):
    def test_confirmation_sits_at_the_top_of_consent(self):
        note = self.html.index('id="session-ended-msg"')
        checks = self.html.index('class="consent-checks"')
        begin = self.html.index('id="begin-btn"')
        self.assertLess(note, checks)
        self.assertLess(note, begin)
        self.assertIn("Session ended — everything from that "
                      "sitting has been deleted", self.html)
        self.assertIn('id="session-ended-msg" class="quiet" '
                      'role="status" hidden', self.html)


class TestVoiceDeckCss(_WebCase):
    def test_bars_exist_and_can_actually_hide(self):
        self.assertIn(".mic-recbar, .mic-review {", self.css)
        # A flex row would beat the [hidden] default — the
        # explicit rule is what lets the bars hide at all.
        self.assertIn(".mic-recbar[hidden], "
                      ".mic-review[hidden] { display: none; }",
                      self.css)

    def test_recording_dot_pulses_and_rests(self):
        self.assertIn(".rec-dot {", self.css)
        self.assertIn(".mic-recbar.paused .rec-dot", self.css)
        reduce = self.css.split(
            "@media (prefers-reduced-motion: reduce)", 1)[1]
        self.assertIn(".rec-dot { animation: none; }", reduce)

    def test_timer_uses_tabular_figures(self):
        self.assertIn("font-variant-numeric: tabular-nums",
                      self.css)


if __name__ == "__main__":
    unittest.main()
