"""Voice deck contracts (Rehearsal Finding #1, Oct 30, 2026 —
revised the same evening on the founder's phone-test ruling).

The dress rehearsal found the recorder a maze at both ends:
no timer, no discoverable pause/stop on the way in, and a
blind auto-send on the way out. The morning build answered
"one tap in, one decision out" — a recording bar plus a
review bar (hear the take, then Send or Re-record).

The founder's phone test that evening superseded the
second half, in his own terms:

- "Too many Record buttons" — the mic pill row AND the
  deck bars read as two competing voice surfaces. Now
  there is ONE: while a recording runs, the pill parks
  itself (disabled, label "Recording…" — state only,
  never a second stop/send control) and the recording
  bar is the only voice control: rec dot, live timer,
  Pause/Resume (feature-detected, never faked), Discard,
  Stop.
- "The button stopping the recording should also
  automatically send the message… The recordings are not
  ABSOLUTE records or perfect records. The end user is
  just telling their story as they know it." The review
  step is RETIRED. Stop = send, through the unchanged
  listening-track + /api/media pipeline, with the
  heard-you announcement in the same beat. Corrections
  happen in conversation — the app's standing doctrine.
  A deliberate Discard still sends nothing, and a take
  killed silently (panels closing, session ending) is
  marked for discard so its stop event can never send it.

Ride-alongs pinned here too (unchanged from the morning):

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

    def test_discard_lives_inside_the_recording_bar(self):
        # One surface: while recording, Discard sits in the
        # bar between Pause and Stop — not up in the
        # composer row competing with the pill.
        bar = self.html.index('id="mic-recbar"')
        discard = self.html.index('id="mic-discard"')
        status = self.html.index('id="voice-status"')
        self.assertLess(bar, discard)
        self.assertLess(discard, status)
        self.assertIn('id="mic-discard" class="secondary" '
                      'type="button">Discard</button>', self.html)

    def test_review_deck_is_retired_from_the_dom(self):
        # The founder retired the review step: no review
        # bar, no playback element, no Re-record/Send pair.
        for frag in ('id="mic-review"', 'id="mic-play"',
                     'id="mic-duration"', 'id="mic-rerecord"',
                     'id="mic-send"', 'id="mic-playback"'):
            self.assertNotIn(frag, self.html)

    def test_deck_lives_inside_the_reply_band(self):
        form_open = self.html.index('<form id="chat-form"')
        form_close = self.html.index("</form>")
        where = self.html.index('id="mic-recbar"')
        self.assertLess(form_open, where)
        self.assertLess(where, form_close)

    def test_dead_audio_use_button_is_gone_video_keeps_his(self):
        # "Use this recording" could never be reached for a
        # recorded take, and a chosen file stages directly —
        # dead furniture, removed. Video's preview/Use flow
        # is untouched.
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

    def test_stop_sends_the_take_through_the_pipeline(self):
        # Stop = send: the recorder's stop event hands the
        # take to sendVoiceTake, which fires the heard-you
        # line in the same beat and runs the unchanged
        # listening-track + /api/media pipeline as a
        # standalone message.
        self.assertIn("function sendVoiceTake(blob, type, "
                      "cutShort)", self.js)
        self.assertIn("sendVoiceTake(audioBlob, type, "
                      "cutShort)", self.js)
        self.assertIn('stageWithListening("audio", blob,',
                      self.js)
        self.assertIn("Heard you — Liv is listening to your "
                      "words.", self.js)
        self.assertIn('send("", true, [item])', self.js)
        # The retired review machinery is gone, not parked.
        self.assertNotIn("enterVoiceReview", self.js)
        self.assertNotIn("micReviewReset", self.js)
        self.assertNotIn("mic-review", self.js)

    def test_panel_take_closes_the_panel_as_it_sends(self):
        # A take begun in the + Add panel follows the same
        # stop → send; the panel closes as the send fires.
        self.assertIn("if (!wasMic) { closePanels(); }",
                      self.js)
        closed = self.js.index("if (!wasMic) { closePanels(); }")
        sent = self.js.index("sendVoiceTake(audioBlob, type, "
                             "cutShort)")
        self.assertLess(closed, sent)

    def test_pill_parks_while_recording(self):
        # Disabled, state label only — never a second
        # stop/send control beside the recording bar.
        self.assertIn("micBtn.disabled = true", self.js)
        self.assertIn("micBtn.disabled = false", self.js)
        self.assertIn('micLabel.textContent = "Recording…"',
                      self.js)
        self.assertNotIn('micLabel.textContent = "Tap to stop"',
                         self.js)
        self.assertNotIn('micLabel.textContent = "Tap to send"',
                         self.js)
        # The pill's click handler no longer stops a take.
        self.assertNotIn("if (R.viaMic) { R.rec.stop(); }",
                         self.js)

    def test_discard_and_kills_send_nothing(self):
        self.assertIn("R.discardNext", self.js)
        self.assertIn("Recording discarded — nothing was "
                      "sent.", self.js)
        # A recorder killed through stopRecorder (panels
        # closing, session ending) is marked for discard
        # BEFORE it is stopped, so its stop event throws
        # the take away instead of sending it.
        stopper = self.js.split("function stopRecorder", 1)[1]
        stopper = stopper.split("function startRecorder", 1)[0]
        self.assertIn("R.discardNext = true", stopper)

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
    def test_bar_exists_and_can_actually_hide(self):
        self.assertIn(".mic-recbar {", self.css)
        # A flex row would beat the [hidden] default — the
        # explicit rule is what lets the bar hide at all.
        self.assertIn(".mic-recbar[hidden] { display: none; }",
                      self.css)
        # The retired review bar leaves no styles behind.
        self.assertNotIn(".mic-review", self.css)

    def test_recording_dot_pulses_and_rests(self):
        self.assertIn(".rec-dot {", self.css)
        self.assertIn(".mic-recbar.paused .rec-dot", self.css)
        reduce = self.css.split(
            "@media (prefers-reduced-motion: reduce)", 1)[1]
        self.assertIn(".rec-dot { animation: none; }", reduce)

    def test_timer_uses_tabular_figures(self):
        self.assertIn("font-variant-numeric: tabular-nums",
                      self.css)


class TestWakeLockSessionScope(_WebCase):
    """Fix 1 (Oct 30, evening): the founder's screen slept
    on Safari mid-telling and the recording was cut. His
    refinement: the interaction with Liv is continuous,
    so the wake lock is SESSION-scoped — acquired at the
    Begin transition past consent, at home on every
    post-consent screen, released only by the end-session
    wipe, pagehide, or WAKE_IDLE_MS (30 min) untouched.
    Recording paths merely ensure it is held."""

    def test_lock_is_feature_detected_and_requested(self):
        self.assertIn('"wakeLock" in navigator', self.js)
        self.assertIn('navigator.wakeLock.request("screen")',
                      self.js)
        # Enhancement only: acquisition refuses cleanly
        # when unsupported or outside a sitting, and the
        # request's rejection is swallowed.
        acquire = self.js.split("function acquireWakeLock",
                                1)[1]
        acquire = acquire.split("function releaseWakeLock",
                                1)[0]
        self.assertIn("if (!wakeLockSupported() || "
                      "!inSitting()) { return; }", acquire)
        self.assertIn(".catch(function () {", acquire)

    def test_lock_acquired_at_begin_not_on_consent(self):
        # The Begin transition acquires; the guard means
        # the consent screen itself can never hold it.
        begin = self.js.split(
            'beginBtn.addEventListener("click"', 1)[1]
        begin = begin.split('send("", false)', 1)[0]
        self.assertIn("acquireWakeLock();", begin)
        self.assertIn("return consented;", self.js)

    def test_lock_released_on_end_session_and_pagehide(self):
        end = self.js.split(
            'getElementById("end-session-btn")', 1)[1]
        end = end.split("chapterCall", 1)[0]
        self.assertIn("releaseWakeLock();", end)
        self.assertIn('addEventListener("pagehide"', self.js)
        hide = self.js.split('addEventListener("pagehide"',
                             1)[1]
        hide = hide.split("visibilitychange", 1)[0]
        self.assertIn("releaseWakeLock();", hide)

    def test_idle_release_on_the_named_constant(self):
        self.assertIn("var WAKE_IDLE_MS = 30 * 60 * 1000;",
                      self.js)
        arm = self.js.split("function armWakeIdle", 1)[1]
        arm = arm.split("function dropWakeSentinel", 1)[0]
        self.assertIn("setTimeout(function ()", arm)
        self.assertIn("}, WAKE_IDLE_MS);", arm)
        self.assertIn("releaseWakeLock();", arm)

    def test_interaction_rearms_and_reacquires(self):
        self.assertIn('document.addEventListener('
                      '"pointerdown", noteWakeInteraction);',
                      self.js)
        self.assertIn('document.addEventListener('
                      '"keydown", noteWakeInteraction);',
                      self.js)
        # A message sent counts as interaction.
        send = self.js.split("function send(message", 1)[1]
        send = send.split("beginBtn", 1)[0]
        self.assertIn("noteWakeInteraction();", send)
        # Returning to the tab counts as interaction too.
        vis = self.js.split(
            'addEventListener("visibilitychange"', 1)[1]
        self.assertIn("noteWakeInteraction();", vis)

    def test_recording_start_ensures_the_lock(self):
        start = self.js.split("function startRecorder",
                              1)[1]
        start = start.split("function wireRecorder", 1)[0]
        self.assertIn("noteWakeInteraction();", start)
        self.assertIn("maybeWakeHint();", start)


class TestInterruptionTruthfulness(_WebCase):
    """Fix 2 (Oct 30, evening): stop causes are told
    apart — a deliberate Stop (stopInitiated), a Discard
    or kill (discardNext), and an UNEXPECTED stop (the
    recorder died under a slept screen). A cut take still
    sends — the partial telling is preserved, per the
    founder's doctrine — but its announcement tells the
    truth about the cut."""

    def test_stop_causes_are_marked(self):
        # Both deliberate Stop controls mark the cause.
        self.assertGreaterEqual(
            self.js.count("R.stopInitiated = true;"), 2)
        # The page hiding mid-telling marks interrupted.
        vis = self.js.split(
            'addEventListener("visibilitychange"', 1)[1]
        self.assertIn("R.interrupted = true;", vis)
        # A fresh take starts with no cause marked.
        start = self.js.split("function startRecorder",
                              1)[1]
        start = start.split("function wireRecorder", 1)[0]
        self.assertIn("R.interrupted = false;", start)
        self.assertIn("R.stopInitiated = false;", start)

    def test_cut_takes_send_with_truthful_copy(self):
        self.assertIn("var cutShort = R.interrupted || "
                      "!R.stopInitiated;", self.js)
        self.assertIn("setVoiceStatus(cutShort", self.js)
        self.assertIn("The screen slept and cut that "
                      "short — what you ", self.js)
        self.assertIn("said up to then went to Liv.",
                      self.js)

    def test_normal_stop_keeps_the_normal_line(self):
        # The heard-you line survives as the non-cut
        # branch; a deliberate, uninterrupted stop never
        # sees the cut copy.
        self.assertIn(': "Heard you — Liv is listening '
                      'to your words.");', self.js)

    def test_dead_recorder_resyncs_on_return(self):
        # Recorder dead while the mic chrome still shows
        # recording: resync to the truth and say so.
        self.assertIn("if (R.viaMic && !micRecbar.hidden)",
                      self.js)
        self.assertIn("The screen slept, and the "
                      "recording stopped.", self.js)

    def test_hint_once_only_and_only_when_unsupported(self):
        hint = self.js.split("function maybeWakeHint",
                             1)[1]
        hint = hint.split("pointerdown", 1)[0]
        self.assertIn("if (wakeLockSupported() || "
                      "wakeHintShown) { return; }", hint)
        self.assertIn("wakeHintShown = true;", hint)
        self.assertIn("Keeping the screen awake helps "
                      "here — ", self.js)
        self.assertIn("if the screen sleeps, the "
                      "recording stops.", self.js)


if __name__ == "__main__":
    unittest.main()
