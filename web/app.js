// Day 1 shell behaviour.
// Screen 1 (consent) gates Screen 2 (conversation): the chat UI is not
// shown until the storyteller agrees, and every /api/chat call carries
// the consent flag, which the server also enforces. The companion is
// Liv — only Liv (founder ruling, Oct 29, 2026): no name is chosen on
// Screen 1 and none is sent; the name spans in the page already say
// "Liv", and the server keeps every session's companion as Liv.
// Age posture (Petro, Oct 26): lone users are adults only. The Begin
// button stays disabled until BOTH the consent checkbox and the
// "I confirm I am 18 or older" attestation are checked, and every
// call carries age_confirmed, which the server enforces the same way.
// Sharing (Day 2 capture; Day 3 conversation-first composer):
// the conversation is the interface — one "+" attach button opens
// a small picker (photo/camera, voice recording, video, document
// or archive), used only when the storyteller chooses. Sharing is
// staged: pick or record → uploaded to /api/media for THIS
// session → shown in a pending tray with a remove option → sent
// with the next message. Media is in-memory on the server and
// dies with the tab session, exactly like the conversation. The
// first media use in a session shows a short notice before
// anything opens.
// Day 3 listening: for audio and video, the browser ALSO makes a
// "listening track" — the item's sound transcoded with Web Audio
// to a 16 kHz mono WAV, the only form the transcription model
// accepts — and uploads it alongside the original. The server
// transcribes it and Liv answers the storyteller's actual words.

(function () {
  "use strict";

  var sessionId = "s-" + Date.now().toString(36) + "-" +
    Math.random().toString(36).slice(2, 8);
  var consented = false;
  var ageConfirmed = false;
  var companionName = "Liv";  // Liv's display name; it never varies.

  var beginBtn = document.getElementById("begin-btn");
  var consentCheck = document.getElementById("consent-check");
  var ageCheck = document.getElementById("age-check");

  function refreshBegin() {
    beginBtn.disabled = !(consentCheck.checked && ageCheck.checked);
  }
  consentCheck.addEventListener("change", refreshBegin);
  ageCheck.addEventListener("change", refreshBegin);
  refreshBegin();

  var consentScreen = document.getElementById("consent-screen");
  var chatScreen = document.getElementById("chat-screen");
  var messages = document.getElementById("messages");
  var listening = document.getElementById("listening");
  var form = document.getElementById("chat-form");
  var input = document.getElementById("chat-input");

  // Smooth scrolling only for people who have not asked their
  // system for reduced motion (the CSS media query cannot reach
  // JS-driven scrolling, so it is honoured here instead).
  function scrollBehavior() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ? "auto" : "smooth";
  }

  function setListening(on) {
    if (listening) { listening.hidden = !on; }
  }

  function mediaUrl(item) {
    return "/api/media/" + item.id + "?session_id=" +
      encodeURIComponent(sessionId);
  }

  function mediaElement(item, inThread) {
    var el;
    if (item.kind === "photo") {
      el = document.createElement("img");
      el.src = mediaUrl(item);
      if (item.source === "archive") {
        el.alt = inThread
          ? "A photo from your archive shared in this conversation"
          : "A photo from your archive ready to share";
      } else {
        el.alt = inThread ? "A photo shared in this conversation"
                          : "A photo ready to share";
      }
      el.className = inThread ? "shared-media" : "pending-thumb";
    } else if (item.kind === "audio") {
      el = document.createElement("audio");
      el.controls = true;
      el.src = mediaUrl(item);
      el.setAttribute("aria-label", "Voice recording shared in this conversation");
      el.className = inThread ? "shared-media-audio" : "pending-audio";
    } else {
      el = document.createElement("video");
      el.src = mediaUrl(item);
      el.setAttribute("aria-label", "Video shared in this conversation");
      el.playsInline = true;
      if (inThread) { el.controls = true; }
      else { el.muted = true; el.preload = "metadata"; }
      el.className = inThread ? "shared-media" : "pending-thumb";
    }
    return el;
  }

  function addMessage(who, text, cls, mediaItems) {
    var div = document.createElement("div");
    // The session's closing message is set in the typography of a
    // letter's end (presentation only; text and flow unchanged).
    if (cls === "companion" && text &&
        text.indexOf("Thank you for sitting with me") === 0) {
      cls += " closing";
    }
    div.className = "msg " + cls;
    var label = document.createElement("span");
    label.className = "who";
    label.textContent = who;
    div.appendChild(label);
    if (mediaItems) {
      for (var i = 0; i < mediaItems.length; i++) {
        div.appendChild(mediaElement(mediaItems[i], true));
        if (mediaItems[i].transcript) {
          // The storyteller's spoken words, as Liv heard them —
          // shown with the recording they belong to, so the
          // thread reads as what was actually said.
          var heard = document.createElement("span");
          heard.className = "media-transcript";
          heard.textContent = "\u201c" + mediaItems[i].transcript +
            "\u201d";
          div.appendChild(heard);
        }
        if (mediaItems[i].source === "archive") {
          var origin = document.createElement("span");
          origin.className = "archive-origin";
          var originText = "From your archive";
          if (mediaItems[i].date) {
            originText += " · " + mediaItems[i].date;
          }
          if (mediaItems[i].caption) {
            originText += " — \u201c" + mediaItems[i].caption + "\u201d";
          }
          origin.textContent = originText;
          div.appendChild(origin);
        }
      }
    }
    if (text) {
      var body = document.createElement("span");
      body.textContent = text;
      div.appendChild(body);
    }
    messages.appendChild(div);
    div.scrollIntoView({ block: "end", behavior: scrollBehavior() });
  }

  function send(message, showMine, mediaItems) {
    // A message sent is interaction: it re-arms the
    // session wake lock's idle clock (Fix 1).
    noteWakeInteraction();
    var ids = [];
    if (mediaItems) {
      for (var i = 0; i < mediaItems.length; i++) { ids.push(mediaItems[i].id); }
    }
    if (showMine && (message.trim() !== "" || ids.length > 0)) {
      addMessage("You", message, "storyteller", mediaItems);
    }
    setListening(true);
    return fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        message: message,
        consent: consented,
        age_confirmed: ageConfirmed,
        media_ids: ids
      })
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        setListening(false);
        var name = data.companion || companionName;
        if (data.reply) {
          addMessage(name, data.reply, "companion");
        } else if (data.error) {
          addMessage(name,
            "Something went wrong on my side. Please try again.",
            "companion");
        }
      })
      .catch(function () {
        setListening(false);
        addMessage(companionName,
          "I could not be reached just now. Please try again in a moment.",
          "companion");
      });
  }

  beginBtn.addEventListener("click", function () {
    if (!(consentCheck.checked && ageCheck.checked)) { return; }
    consented = true;
    ageConfirmed = true;
    consentScreen.hidden = true;
    chatScreen.hidden = false;
    // The sitting begins: take the screen wake lock for
    // it (Fix 1 — session-scoped; see the wake lock
    // section). Enhancement only — acquireWakeLock
    // swallows its own failures, so nothing here can be
    // broken by it.
    acquireWakeLock();
    send("", false).then(function () { input.focus(); });
  });

  document.getElementById("not-now").addEventListener("click", function (ev) {
    ev.preventDefault();
    document.getElementById("not-now-msg").hidden = false;
  });

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var text = input.value;
    var media = takePendingMedia();
    if (text.trim() === "" && media.length === 0) { return; }
    input.value = "";
    send(text, true, media).then(function () { input.focus(); });
  });

  // Finish for today (Rehearsal Finding #2, Oct 30, 2026):
  // reported inert on tap at the dress rehearsal. The wiring
  // was forensically verified sound — this same handler, on
  // a type="button" control, calling the same send() the
  // typed phrase used successfully moments later, in BOTH
  // the rehearsal build and this one; app.js is byte-
  // identical between them. So the tap never landed as a
  // click (a first tap with the phone keyboard up is the
  // classic eater of taps). What the code can own is fixed
  // here: the tap routes through a named function with an
  // in-flight guard, so a landed tap can never queue a
  // second close behind a slow first one, and a double-tap
  // is harmless.
  var finishInFlight = false;
  function finishForToday() {
    if (finishInFlight) { return; }
    finishInFlight = true;
    send("Finish for today", true).then(function () {
      finishInFlight = false;
    });
  }
  document.getElementById("finish-btn").addEventListener("click",
    finishForToday);

  // ---- Media sharing ------------------------------------------------
  var MEDIA_CAPS = { photo: 10 * 1024 * 1024, audio: 50 * 1024 * 1024,
                     video: 50 * 1024 * 1024 };
  var MEDIA_NOUN = { photo: "photo", audio: "recording", video: "video" };

  var pendingMedia = [];   // [{id, kind}] staged for the next message
  var pendingBox = document.getElementById("pending-media");
  var pendingItems = document.getElementById("pending-items");
  var mediaError = document.getElementById("media-error");

  function showMediaError(text) {
    mediaError.textContent = text;
    mediaError.hidden = !text;
  }

  function renderPending() {
    pendingItems.innerHTML = "";
    for (var i = 0; i < pendingMedia.length; i++) {
      (function (item, position) {
        var row = document.createElement("div");
        row.className = "pending-item";
        row.appendChild(mediaElement(item, false));
        var label = document.createElement("span");
        label.className = "pending-kind";
        label.textContent = item.source === "archive"
          ? "Archive photo"
          : { photo: "Photo", audio: "Voice recording",
              video: "Video" }[item.kind];
        if (item.transcript) {
          label.textContent += " — Liv heard your words";
        } else if (item.transcript_status === "failed") {
          label.textContent += " — Liv could not hear this one";
        }
        row.appendChild(label);
        var remove = document.createElement("button");
        remove.type = "button";
        remove.className = "secondary pending-remove";
        remove.textContent = "Remove";
        remove.setAttribute("aria-label",
          "Remove " + label.textContent.toLowerCase() + " " + position);
        remove.addEventListener("click", function () {
          pendingMedia = pendingMedia.filter(function (m) {
            return m.id !== item.id;
          });
          renderPending();
        });
        row.appendChild(remove);
        pendingItems.appendChild(row);
      })(pendingMedia[i], i + 1);
    }
    pendingBox.hidden = pendingMedia.length === 0;
  }

  function takePendingMedia() {
    var media = pendingMedia;
    pendingMedia = [];
    renderPending();
    return media;
  }

  function stageMedia(kind, blob, filename, listenBlob, onStaged) {
    showMediaError("");
    if (blob.size > MEDIA_CAPS[kind]) {
      showMediaError("That " + MEDIA_NOUN[kind] + " is too large — " +
        "photos can be up to 10 MB, recordings and videos up to 50 MB.");
      if (onStaged) { onStaged(null); }
      return;
    }
    var fd = new FormData();
    fd.append("session_id", sessionId);
    fd.append("consent", consented ? "true" : "false");
    fd.append("age_confirmed", ageConfirmed ? "true" : "false");
    fd.append("kind", kind);
    fd.append("file", blob, filename || ("shared-" + kind));
    if (listenBlob) {
      // The listening track (Day 3): this item's sound as a
      // 16 kHz mono WAV, for the transcription model only.
      fd.append("listen", listenBlob, "listening.wav");
    }
    fetch("/api/media", { method: "POST", body: fd })
      .then(function (res) {
        return res.json().then(function (data) {
          return { status: res.status, data: data };
        });
      })
      .then(function (out) {
        if (out.status === 200 && out.data.media_id) {
          var item = {
            id: out.data.media_id, kind: kind,
            transcript: out.data.transcript || null,
            transcript_status: out.data.transcript_status || null
          };
          if (onStaged) { onStaged(item); return; }
          pendingMedia.push(item);
          renderPending();
          input.focus();
        } else {
          showMediaError(out.data.error ||
            "That did not arrive. Please try again.");
          if (onStaged) { onStaged(null); }
        }
      })
      .catch(function () {
        showMediaError("That did not arrive. Please try again.");
        if (onStaged) { onStaged(null); }
      });
  }

  // ---- The listening track (Day 3) --------------------------------
  // Browsers record WebM/Opus; the transcription model accepts
  // mono PCM WAV at 16/24 kHz only. So the sound of every audio
  // and video item is decoded with Web Audio, downmixed and
  // resampled to 16 kHz mono in an OfflineAudioContext, and
  // encoded as a plain PCM16 WAV. Any failure along the way
  // yields null — the item is still shared, honestly unheard.
  var _listenCtx = null;
  function listenContext() {
    if (_listenCtx) { return _listenCtx; }
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) { return null; }
    _listenCtx = new AC();
    return _listenCtx;
  }

  function encodeListeningWav(samples, rate) {
    var buffer = new ArrayBuffer(44 + samples.length * 2);
    var view = new DataView(buffer);
    function writeStr(offset, text) {
      for (var i = 0; i < text.length; i++) {
        view.setUint8(offset + i, text.charCodeAt(i));
      }
    }
    writeStr(0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    writeStr(8, "WAVE");
    writeStr(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);          // PCM
    view.setUint16(22, 1, true);          // mono
    view.setUint32(24, rate, true);
    view.setUint32(28, rate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeStr(36, "data");
    view.setUint32(40, samples.length * 2, true);
    for (var i = 0; i < samples.length; i++) {
      var s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF,
                    true);
    }
    return new Blob([view], { type: "audio/wav" });
  }

  function makeListeningTrack(blob) {
    var ctx = listenContext();
    if (!ctx || !window.OfflineAudioContext) {
      return Promise.resolve(null);
    }
    if (ctx.state === "suspended") { ctx.resume(); }
    return blob.arrayBuffer()
      .then(function (buf) { return ctx.decodeAudioData(buf); })
      .then(function (decoded) {
        var rate = 16000;
        var frames = Math.max(1, Math.ceil(decoded.duration * rate));
        var off = new OfflineAudioContext(1, frames, rate);
        var src = off.createBufferSource();
        src.buffer = decoded;
        src.connect(off.destination);
        src.start();
        return off.startRendering();
      })
      .then(function (rendered) {
        return encodeListeningWav(rendered.getChannelData(0), 16000);
      })
      .catch(function () { return null; });
  }

  function stageWithListening(kind, blob, filename, onStaged) {
    if (kind === "photo") {
      stageMedia(kind, blob, filename, null, onStaged);
      return;
    }
    makeListeningTrack(blob).then(function (listenBlob) {
      stageMedia(kind, blob, filename, listenBlob, onStaged);
    });
  }

  // First-use notice: shown ONCE per session, before any panel opens.
  // Focus management: when the notice appears, focus moves to its
  // heading so keyboard and screen-reader users actually encounter
  // it (it renders above the button that summoned it, so without
  // this it is silently skipped). "Continue" lands focus on the
  // first control of the panel it opens; "Not now" returns focus
  // to the media button that asked.
  var notice = document.getElementById("media-notice");
  var noticeTitle = document.getElementById("media-notice-title");
  var noticeDone = false;
  var noticeAction = null;
  var noticeInvoker = null;
  var noticePanel = null;

  function guardFirstUse(action, invoker, panel) {
    if (noticeDone) { action(); return; }
    noticeAction = action;
    noticeInvoker = invoker || null;
    noticePanel = panel || null;
    notice.hidden = false;
    notice.scrollIntoView({ block: "nearest", behavior: scrollBehavior() });
    noticeTitle.focus();
  }
  document.getElementById("media-notice-ok").addEventListener("click",
    function () {
      noticeDone = true;
      notice.hidden = true;
      var action = noticeAction;
      var panel = noticePanel;
      noticeAction = null;
      noticeInvoker = null;
      noticePanel = null;
      if (action) { action(); }
      if (panel) {
        var first = panel.querySelector("button");
        if (first) { first.focus(); }
      }
    });
  document.getElementById("media-notice-cancel").addEventListener("click",
    function () {
      notice.hidden = true;
      var invoker = noticeInvoker;
      noticeAction = null;
      noticeInvoker = null;
      noticePanel = null;
      if (invoker) {
        // The invoker may be a picker choice that has since
        // closed with its picker; then the attach button — the
        // control that is always there — takes the focus.
        if (typeof attachPicker !== "undefined" && attachPicker &&
            attachPicker.hidden && attachBtn &&
            invoker !== attachBtn) {
          attachBtn.focus();
        } else {
          invoker.focus();
        }
      }
    });

  // Panels: one open at a time; opening goes through the notice.
  var panels = {
    photo: document.getElementById("panel-photo"),
    audio: document.getElementById("panel-audio"),
    video: document.getElementById("panel-video"),
    archive: document.getElementById("panel-archive")
  };
  var barButtons = {
    photo: document.getElementById("btn-photo"),
    audio: document.getElementById("btn-audio"),
    video: document.getElementById("btn-video"),
    archive: document.getElementById("btn-archive")
  };

  // The attach affordance (Day 3 conversation-first composer):
  // one "+" button; the picker is a quiet row of choices that
  // exists only while it is open. Choosing a kind closes the
  // picker and opens that kind's panel, through the same
  // first-use notice as before.
  var attachBtn = document.getElementById("btn-attach");
  var attachPicker = document.getElementById("attach-picker");

  function hidePicker() {
    attachPicker.hidden = true;
    attachBtn.setAttribute("aria-expanded", "false");
  }

  attachBtn.addEventListener("click", function () {
    var willOpen = attachPicker.hidden;
    closePanels();
    if (!willOpen) { return; }
    attachPicker.hidden = false;
    attachBtn.setAttribute("aria-expanded", "true");
    var first = attachPicker.querySelector("button");
    if (first) { first.focus(); }
  });

  function closePanels() {
    hidePicker();
    for (var k in panels) {
      panels[k].hidden = true;
      barButtons[k].setAttribute("aria-expanded", "false");
    }
    // If a Talk to Liv recording is live, closing the panels
    // kills it WITHOUT sending (stopRecorder marks the take
    // for discard, so the stop event throws it away).
    // Resync the mic chrome and SAY so — the pill used to
    // be left showing its recording state over a dead
    // recorder.
    var RA = (typeof recorders !== "undefined")
      ? recorders.audio : null;
    var micWasLive = !!(RA && RA.viaMic && RA.rec &&
      RA.rec.state !== "inactive");
    stopRecorder("audio", true);
    stopRecorder("video", true);
    if (micWasLive) {
      micUiReset();
      setVoiceStatus("Recording stopped — nothing was sent.");
    }
  }

  function togglePanel(kind) {
    var willOpen = panels[kind].hidden;
    closePanels();
    if (!willOpen) { return; }
    guardFirstUse(function () {
      panels[kind].hidden = false;
      barButtons[kind].setAttribute("aria-expanded", "true");
    }, barButtons[kind], panels[kind]);
  }
  barButtons.photo.addEventListener("click", function () { togglePanel("photo"); });
  barButtons.audio.addEventListener("click", function () { togglePanel("audio"); });
  barButtons.video.addEventListener("click", function () { togglePanel("video"); });

  // ---- Bring your archive ------------------------------------------
  // The archive panel has its OWN first-use notice (a bigger
  // handing-over than one photo deserves its own plain word), with
  // the same focus discipline as the media notice: focus to the
  // heading on open; Continue lands on the panel's first control;
  // Not now returns focus to the archive button.
  var archiveNotice = document.getElementById("archive-notice");
  var archiveNoticeTitle = document.getElementById("archive-notice-title");
  var archiveNoticeDone = false;
  var archiveNoticePending = null;

  function guardArchiveFirstUse(action) {
    if (archiveNoticeDone) { action(); return; }
    archiveNoticePending = action;
    archiveNotice.hidden = false;
    archiveNotice.scrollIntoView({ block: "nearest",
                                   behavior: scrollBehavior() });
    archiveNoticeTitle.focus();
  }
  document.getElementById("archive-notice-ok").addEventListener("click",
    function () {
      archiveNoticeDone = true;
      archiveNotice.hidden = true;
      var action = archiveNoticePending;
      archiveNoticePending = null;
      if (action) { action(); }
      var first = panels.archive.querySelector("button");
      if (first && !panels.archive.hidden) { first.focus(); }
    });
  document.getElementById("archive-notice-cancel").addEventListener(
    "click", function () {
      archiveNotice.hidden = true;
      archiveNoticePending = null;
      barButtons.archive.focus();
    });

  barButtons.archive.addEventListener("click", function () {
    var willOpen = panels.archive.hidden;
    closePanels();
    if (!willOpen) { return; }
    guardArchiveFirstUse(function () {
      panels.archive.hidden = false;
      barButtons.archive.setAttribute("aria-expanded", "true");
    });
  });

  var ARCHIVE_ZIP_CAP = 200 * 1024 * 1024;
  var archiveStatus = document.getElementById("archive-status");
  var archiveTray = document.getElementById("archive-tray");
  var archiveTrayTitle = document.getElementById("archive-tray-title");
  var archiveItemsBox = document.getElementById("archive-items");
  var archiveShare = document.getElementById("archive-share");
  var archiveFileInput = document.getElementById("archive-file-input");
  var archiveListing = [];

  function archiveItemUrl(item) {
    return "/api/archive/item/" + item.id + "?session_id=" +
      encodeURIComponent(sessionId);
  }

  function refreshArchiveShare() {
    var boxes = archiveItemsBox.querySelectorAll(
      'input[type="checkbox"]:checked');
    var n = boxes.length;
    archiveShare.textContent = "Share selected (" + n + ")";
    archiveShare.disabled = n === 0;
    return n;
  }

  function renderArchiveTray(data) {
    archiveListing = data.items || [];
    archiveItemsBox.innerHTML = "";
    for (var i = 0; i < archiveListing.length; i++) {
      (function (item) {
        var label = document.createElement("label");
        label.className = "archive-item";
        var box = document.createElement("input");
        box.type = "checkbox";
        box.value = item.id;
        var description = item.caption || "A photo from your archive";
        if (item.date) { description += ", " + item.date; }
        box.setAttribute("aria-label", "Share this photo: " + description);
        box.addEventListener("change", refreshArchiveShare);
        label.appendChild(box);
        var thumb = document.createElement("img");
        thumb.className = "pending-thumb";
        thumb.src = archiveItemUrl(item);
        thumb.alt = "";
        label.appendChild(thumb);
        var text = document.createElement("span");
        text.className = "archive-item-text";
        var caption = document.createElement("span");
        caption.className = "archive-item-caption";
        caption.textContent = item.caption || "No caption";
        text.appendChild(caption);
        if (item.date || item.album) {
          var meta = document.createElement("span");
          meta.className = "archive-item-meta";
          meta.textContent = [item.date, item.album]
            .filter(Boolean).join(" · ");
          text.appendChild(meta);
        }
        label.appendChild(text);
        archiveItemsBox.appendChild(label);
      })(archiveListing[i]);
    }
    var summary = "I found " + data.found +
      (data.found === 1 ? " photo" : " photos") + " in your archive.";
    if (data.skipped > 0) {
      summary += " " + data.skipped +
        (data.skipped === 1 ? " item" : " items") +
        " could not be brought in (too large, or not a photo I " +
        "could read) and " +
        (data.skipped === 1 ? "was" : "were") + " left out.";
    }
    summary += " Tick the photos you would like to share.";
    archiveStatus.textContent = summary;
    archiveTray.hidden = false;
    refreshArchiveShare();
    archiveTrayTitle.focus();
  }

  function uploadArchive(file) {
    showMediaError("");
    if (file.size > ARCHIVE_ZIP_CAP) {
      showMediaError("That archive is larger than 200 MB. In " +
        "Download Your Information you can ask for photos only, " +
        "which makes a smaller file.");
      return;
    }
    archiveStatus.textContent = "Looking through your archive…";
    var fd = new FormData();
    fd.append("session_id", sessionId);
    fd.append("consent", consented ? "true" : "false");
    fd.append("age_confirmed", ageConfirmed ? "true" : "false");
    fd.append("file", file, file.name);
    fetch("/api/archive", { method: "POST", body: fd })
      .then(function (res) {
        return res.json().then(function (data) {
          return { status: res.status, data: data };
        });
      })
      .then(function (out) {
        if (out.status === 200 && out.data.items) {
          renderArchiveTray(out.data);
        } else {
          archiveStatus.textContent = "";
          showMediaError(out.data.error ||
            "That archive could not be read. Please try again.");
        }
      })
      .catch(function () {
        archiveStatus.textContent = "";
        showMediaError("That archive could not be read. " +
          "Please try again.");
      });
  }

  document.getElementById("archive-choose").addEventListener("click",
    function () { archiveFileInput.click(); });
  archiveFileInput.addEventListener("change", function () {
    if (archiveFileInput.files && archiveFileInput.files[0]) {
      uploadArchive(archiveFileInput.files[0]);
    }
    archiveFileInput.value = "";
  });

  archiveShare.addEventListener("click", function () {
    var boxes = archiveItemsBox.querySelectorAll(
      'input[type="checkbox"]:checked');
    var ids = [];
    for (var i = 0; i < boxes.length; i++) { ids.push(boxes[i].value); }
    if (ids.length === 0) { return; }
    showMediaError("");
    fetch("/api/archive/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        consent: consented,
        age_confirmed: ageConfirmed,
        item_ids: ids
      })
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { status: res.status, data: data };
        });
      })
      .then(function (out) {
        if (out.status === 200 && out.data.media) {
          for (var i = 0; i < out.data.media.length; i++) {
            pendingMedia.push(out.data.media[i]);
          }
          renderPending();
          for (var j = 0; j < boxes.length; j++) {
            boxes[j].checked = false;
          }
          refreshArchiveShare();
          archiveStatus.textContent = out.data.media.length +
            (out.data.media.length === 1 ? " photo is" :
             " photos are") +
            " ready — they will go with your next message.";
          closePanels();
          input.focus();
        } else {
          showMediaError(out.data.error ||
            "Those photos could not be shared. Please try again.");
        }
      })
      .catch(function () {
        showMediaError("Those photos could not be shared. " +
          "Please try again.");
      });
  });

  // File choices (take / choose for photos; choose for
  // audio/video — those also make their listening track first).
  function wireFileInput(id, kind) {
    var el = document.getElementById(id);
    el.addEventListener("change", function () {
      if (el.files && el.files[0]) {
        stageWithListening(kind, el.files[0], el.files[0].name);
      }
      el.value = "";
      closePanels();
    });
    return el;
  }
  var photoTakeInput = wireFileInput("photo-take-input", "photo");
  var photoChooseInput = wireFileInput("photo-choose-input", "photo");
  var audioFileInput = wireFileInput("audio-file-input", "audio");
  var videoFileInput = wireFileInput("video-file-input", "video");

  document.getElementById("photo-take").addEventListener("click",
    function () { photoTakeInput.click(); });
  document.getElementById("photo-choose").addEventListener("click",
    function () { photoChooseInput.click(); });
  document.getElementById("audio-upload").addEventListener("click",
    function () { audioFileInput.click(); });
  document.getElementById("video-upload").addEventListener("click",
    function () { videoFileInput.click(); });

  // Recording (audio + video share one small state machine).
  var recorders = {
    audio: { rec: null, stream: null, chunks: [], blob: null,
             timer: null, started: 0,
             status: document.getElementById("audio-status"),
             button: document.getElementById("audio-record"),
             preview: document.getElementById("audio-preview"),
             actions: document.getElementById("audio-rec-actions"),
             gum: { audio: true },
             idleText: "Record your voice here, or choose a recording you already have." },
    video: { rec: null, stream: null, chunks: [], blob: null,
             timer: null, started: 0,
             status: document.getElementById("video-status"),
             button: document.getElementById("video-record"),
             preview: document.getElementById("video-preview"),
             actions: document.getElementById("video-rec-actions"),
             gum: { audio: true, video: true },
             idleText: "Record a short video here, or choose one you already have." }
  };

  function pickMime(kind) {
    var candidates = kind === "audio"
      ? ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"]
      : ["video/webm;codecs=vp9,opus", "video/webm", "video/mp4"];
    if (!window.MediaRecorder) { return ""; }
    for (var i = 0; i < candidates.length; i++) {
      if (MediaRecorder.isTypeSupported(candidates[i])) {
        return candidates[i];
      }
    }
    return "";
  }

  function extFor(mime) {
    if (mime.indexOf("mp4") !== -1) { return "mp4"; }
    if (mime.indexOf("ogg") !== -1) { return "ogg"; }
    return "webm";
  }

  function fmtTime(ms) {
    var s = Math.floor(ms / 1000);
    return Math.floor(s / 60) + ":" + ("0" + (s % 60)).slice(-2);
  }

  function stopTracks(kind) {
    var R = recorders[kind];
    if (R.stream) {
      R.stream.getTracks().forEach(function (t) { t.stop(); });
      R.stream = null;
    }
  }

  function stopRecorder(kind, silent) {
    var R = recorders[kind];
    if (R.timer) { clearInterval(R.timer); R.timer = null; }
    if (R.rec && R.rec.state !== "inactive") {
      // A recorder stopped through here is KILLED, not
      // finished (panels closing, session ending): mark
      // the take for discard, so the stop event — which
      // still fires — throws it away instead of sending
      // it. (Video never reads the flag; its stop path
      // is unchanged.)
      R.discardNext = true;
      R.rec.onstop = null;
      try { R.rec.stop(); } catch (e) { /* already stopped */ }
    }
    R.rec = null;
    stopTracks(kind);
    stopMeter();
    if (!silent) {
      R.button.textContent = "Start recording";
      R.status.textContent = R.idleText;
    }
  }

  function startRecorder(kind) {
    var R = recorders[kind];
    showMediaError("");
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      showMediaError("Recording is not available in this browser — " +
        "you can choose a file you already have instead.");
      return;
    }
    navigator.mediaDevices.getUserMedia(R.gum)
      .then(function (stream) {
        R.stream = stream;
        R.chunks = [];
        R.blob = null;
        // Stop-cause flags for THIS take (Fix 2, Oct 30
        // evening): a fresh recording starts with no cause
        // marked. A deliberate Discard or a kill sets
        // discardNext; the deliberate Stop controls set
        // stopInitiated; the page hiding mid-telling sets
        // interrupted. The stop event reads them to tell a
        // finish from a cut.
        R.discardNext = false;
        R.stopInitiated = false;
        R.interrupted = false;
        var mime = pickMime(kind);
        R.rec = mime ? new MediaRecorder(stream, { mimeType: mime })
                     : new MediaRecorder(stream);
        R.rec.addEventListener("dataavailable", function (ev) {
          if (ev.data && ev.data.size > 0) { R.chunks.push(ev.data); }
        });
        R.rec.addEventListener("stop", function () {
          var type = (R.rec && R.rec.mimeType) || mime || "video/webm";
          R.blob = new Blob(R.chunks, { type: type });
          stopTracks(kind);
          stopMeter();
          if (R.timer) { clearInterval(R.timer); R.timer = null; }
          R.button.textContent = "Start recording";
          if (kind === "audio") {
            // Voice SENDS ITSELF on stop (founder's ruling,
            // Oct 30 evening — restoring the Day 4 behaviour
            // on top of the morning's deck): stop → the take
            // travels the listening-track + /api/media
            // pipeline at once, as its own message. The
            // review bar the morning build added is retired
            // the same day it shipped: a recording is a
            // telling, not an absolute record, and anything
            // said can be corrected in the conversation that
            // follows. A take begun in the + Add panel ends
            // the same way — the panel closes as the send
            // fires. Only a deliberate Discard (or a kill
            // through stopRecorder) skips the send, straight
            // to nothing-sent.
            var audioBlob = R.blob;
            R.blob = null;
            var wasMic = R.viaMic;
            R.actions.hidden = true;
            R.preview.hidden = true;
            R.status.textContent = R.idleText;
            if (R.discardNext) {
              R.discardNext = false;
              R.interrupted = false;
              R.stopInitiated = false;
              setVoiceStatus("Recording discarded — nothing was sent.");
              micUiReset();
              return;
            }
            // Stop causes (Fix 2): this stop was the
            // storyteller's own finish only if a Stop
            // control marked it (stopInitiated) AND the
            // page never hid mid-telling (interrupted).
            // Anything else — the screen slept, the OS
            // killed the recorder — is a CUT. The partial
            // telling still travels the normal send path
            // (a telling is not an absolute record, and
            // what was said up to the cut is worth keeping),
            // but its announcement must tell the truth
            // about the cut, never dress it as a full send.
            var cutShort = R.interrupted || !R.stopInitiated;
            R.interrupted = false;
            R.stopInitiated = false;
            micUiReset();
            if (!wasMic) { closePanels(); }
            noteWakeInteraction();
            sendVoiceTake(audioBlob, type, cutShort);
            return;
          }
          R.preview.src = URL.createObjectURL(R.blob);
          R.preview.hidden = false;
          if (kind === "video") {
            R.preview.muted = false;
            R.preview.controls = true;
          }
          R.actions.hidden = false;
          R.status.textContent = "Here it is — have a look or a " +
            "listen, then choose “Use this " +
            (kind === "audio" ? "recording" : "video") +
            "” to share it, or discard it.";
        });
        if (kind === "video") {
          R.preview.srcObject = stream;
          R.preview.muted = true;
          R.preview.controls = false;
          R.preview.hidden = false;
          R.preview.play();
        }
        R.actions.hidden = true;
        if (kind === "audio") {
          // While a voice recording runs, Discard stays
          // reachable in the panel (the recording state's own
          // control — throwing a take away must be possible
          // before it ever reaches the review deck).
          R.actions.hidden = false;
        }
        R.rec.start(250);
        // The honest meter (the Marriage): while a voice
        // take runs, the recording band's segments light
        // from this stream's real level.
        if (kind === "audio") { startMeter(stream); }
        R.started = Date.now();
        R.button.textContent = "Stop recording";
        R.status.textContent = "Recording… 0:00";
        if (kind === "audio" && R.viaMic) { micRecordingUi(); }
        R.timer = setInterval(function () {
          R.status.textContent = "Recording… " +
            fmtTime(Date.now() - R.started);
        }, 500);
        // Starting a recording is interaction: it re-arms
        // the session wake lock's idle clock and ensures
        // the lock is held while a telling is captured
        // (Fix 1). For voice, an unsupported browser gets
        // the one-line hint instead (maybeWakeHint).
        noteWakeInteraction();
        if (kind === "audio") { maybeWakeHint(); }
      })
      .catch(function () {
        if (kind === "audio") {
          recorders.audio.viaMic = false;
          micUiReset();
        }
        showMediaError("I could not reach the " +
          (kind === "audio" ? "microphone" : "camera") +
          ". You can allow it in your browser, or choose a file " +
          "you already have.");
      });
  }

  function wireRecorder(kind) {
    var R = recorders[kind];
    R.button.addEventListener("click", function () {
      if (R.rec && R.rec.state === "recording") {
        // A deliberate stop: mark the cause before the
        // stop event reads it (Fix 2).
        R.stopInitiated = true;
        R.rec.stop();
      } else {
        R.viaMic = false;
        R.preview.hidden = true;
        R.actions.hidden = true;
        startRecorder(kind);
      }
    });
    // The "Use this …" step survives for VIDEO only. For
    // audio it was dead furniture: every recorded take sends
    // itself on stop, and a chosen file stages directly —
    // the button could never be reached, so the element is
    // gone from the page and this binding is guarded to the
    // kind that still has one.
    var useBtn = document.getElementById(kind + "-use");
    if (useBtn) {
      useBtn.addEventListener("click", function () {
        if (R.blob) {
          var mime = R.blob.type || "video/webm";
          stageWithListening(kind, R.blob,
            "recorded-" + kind + "." + extFor(mime));
        }
        R.blob = null;
        R.preview.hidden = true;
        R.actions.hidden = true;
        R.status.textContent = R.idleText;
        closePanels();
      });
    }
    document.getElementById(kind + "-discard").addEventListener("click",
      function () {
        if (R.rec && R.rec.state === "recording") {
          // Discarding mid-recording: stop, and let the stop
          // handler throw the take away instead of sending it.
          R.discardNext = true;
          R.rec.stop();
          return;
        }
        R.blob = null;
        R.preview.hidden = true;
        R.actions.hidden = true;
        R.status.textContent = R.idleText;
      });
  }
  wireRecorder("audio");
  wireRecorder("video");

  // ---- Talk to Liv: the dedicated mic button (Day 4) -------------
  // The founder's directive (Oct 28): a first-class mic button
  // beside the composer, icon PLUS words, so speaking is visibly
  // an equal of typing — especially for storytellers not
  // comfortable with a keyboard. It drives the same audio
  // recorder as the panel. Day 5 flow (Rehearsal Finding #1
  // rebuild, revised the same evening on the founder's
  // phone-test ruling): ONE voice surface at a time — tap to
  // record and the pill PARKS itself (disabled, labelled
  // "Recording…", state only, never a second stop/send
  // control) while the recording bar below holds the only
  // controls: timer, Pause, Discard, Stop. Stop sends the
  // take at once (see sendVoiceTake) — the review step the
  // morning build added was retired by the founder within
  // the day. Recording state is visible (button label +
  // pressed state) AND announced in the #voice-status live
  // region, which is what closes accessibility item O2
  // (recording transitions were never announced).
  var micBtn = document.getElementById("mic-btn");
  var micLabel = document.getElementById("mic-label");
  var micDiscard = document.getElementById("mic-discard");
  var voiceStatus = document.getElementById("voice-status");

  function setVoiceStatus(text) {
    if (voiceStatus) { voiceStatus.textContent = text; }
  }

  function micRecordingUi() {
    micBtn.setAttribute("aria-pressed", "true");
    micBtn.classList.add("recording");
    // The pill parks while recording: disabled, its label
    // showing state only. It is NOT a second stop/send
    // control — the recording bar is the only voice
    // surface now (founder's ruling, Oct 30 evening).
    micBtn.disabled = true;
    micLabel.textContent = "Recording…";
    deckResetPause();
    micRecbar.hidden = false;
    // The whole foot becomes the recording (board 5):
    // the calm rows step away while the band is up.
    form.classList.add("is-recording");
    deckTickStart();
    setVoiceStatus("Recording — speak whenever you’re ready. " +
      "Tap Stop when you’re done and it goes straight to " +
      "Liv. Or Discard to throw it away.");
  }

  function micUiReset() {
    recorders.audio.viaMic = false;
    micBtn.setAttribute("aria-pressed", "false");
    micBtn.classList.remove("recording");
    micBtn.disabled = false;
    micLabel.textContent = "Talk to Liv";
    deckTickStop();
    deckResetPause();
    micRecbar.hidden = true;
    form.classList.remove("is-recording");
  }

  micBtn.addEventListener("click", function () {
    var R = recorders.audio;
    if (R.rec && R.rec.state !== "inactive") {
      // A recording is live — started by this pill (which
      // is parked disabled while so) or by the panel. The
      // pill never stops or sends a take: the recording
      // bar, or the panel, holds the only controls.
      return;
    }
    R.viaMic = true;
    guardFirstUse(function () {
      closePanels();
      recorders.audio.viaMic = true;
      startRecorder("audio");
    }, micBtn, null);
  });

  micDiscard.addEventListener("click", function () {
    var R = recorders.audio;
    if (R.rec && R.rec.state !== "inactive") {
      R.discardNext = true;
      R.rec.stop();
    }
  });

  // ---- The voice deck: the recording bar ----------
  // (Rehearsal Finding #1 rebuild, Oct 30, 2026; revised the
  // same evening on the founder's phone-test ruling — markup
  // in index.html.) While a Talk to Liv recording runs, the
  // bar shows the elapsed time as it counts, a Pause button,
  // Discard, and Stop — and it is the ONLY voice surface:
  // the mic pill is parked (disabled, state label only)
  // beside it. Pause is rendered ONLY where the browser
  // truly supports MediaRecorder.pause()/resume(); where it
  // does not (iOS Safari historically), the button is never
  // shown rather than faked. STOP SENDS — see sendVoiceTake.
  var micRecbar = document.getElementById("mic-recbar");
  var micTimer = document.getElementById("mic-timer");
  var micPause = document.getElementById("mic-pause");
  var micStop = document.getElementById("mic-stop");
  var micCanPause = !!(window.MediaRecorder &&
    MediaRecorder.prototype &&
    typeof MediaRecorder.prototype.pause === "function");
  micPause.hidden = !micCanPause;

  // ---- The honest meter (the Marriage, Oct 31, 2026) --------
  // The recording band's segments light from the REAL
  // microphone level: an AnalyserNode tapped into the
  // recorder's own stream while a voice take runs (started
  // in startRecorder, stopped wherever the take stops). At
  // rest no segment is lit and no word anywhere claims the
  // machine is listening. If a browser offers no Web Audio
  // analyser, the segments simply stay dark — the timer and
  // the #voice-status announcements still carry the state —
  // rather than animating a level that was never measured.
  var micLevelSegs = document.querySelectorAll("#mic-level .rseg");
  var meterCtx = null;
  var meterAnalyser = null;
  var meterData = null;
  var meterRaf = null;

  function meterPaint() {
    if (!meterAnalyser) { meterRaf = null; return; }
    meterAnalyser.getByteTimeDomainData(meterData);
    var peak = 0;
    for (var i = 0; i < meterData.length; i++) {
      var v = Math.abs(meterData[i] - 128) / 128;
      if (v > peak) { peak = v; }
    }
    var lit = Math.round(
      Math.min(1, peak * 1.8) * micLevelSegs.length);
    for (var j = 0; j < micLevelSegs.length; j++) {
      micLevelSegs[j].classList.toggle("lit", j < lit);
    }
    meterRaf = requestAnimationFrame(meterPaint);
  }

  function startMeter(stream) {
    stopMeter();
    try {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC || !stream) { return; }
      meterCtx = new AC();
      if (meterCtx.state === "suspended") { meterCtx.resume(); }
      var src = meterCtx.createMediaStreamSource(stream);
      meterAnalyser = meterCtx.createAnalyser();
      meterAnalyser.fftSize = 512;
      meterData = new Uint8Array(meterAnalyser.fftSize);
      src.connect(meterAnalyser);
      meterPaint();
    } catch (e) {
      meterCtx = null;
      meterAnalyser = null;
    }
  }

  function stopMeter() {
    if (meterRaf !== null) {
      cancelAnimationFrame(meterRaf);
      meterRaf = null;
    }
    meterAnalyser = null;
    if (meterCtx) {
      try { meterCtx.close(); } catch (e) { /* already closed */ }
      meterCtx = null;
    }
    for (var j = 0; j < micLevelSegs.length; j++) {
      micLevelSegs[j].classList.remove("lit");
    }
  }

  var deck = { tick: null,
               pausedMs: 0, pauseStart: 0, paused: false };

  function deckElapsed() {
    var R = recorders.audio;
    var ms = Date.now() - R.started - deck.pausedMs;
    if (deck.paused && deck.pauseStart) {
      ms -= Date.now() - deck.pauseStart;
    }
    return Math.max(0, ms);
  }

  function deckTickStart() {
    deckTickStop();
    micTimer.textContent = fmtTime(deckElapsed());
    deck.tick = setInterval(function () {
      micTimer.textContent = fmtTime(deckElapsed());
    }, 250);
  }

  function deckTickStop() {
    if (deck.tick) { clearInterval(deck.tick); deck.tick = null; }
  }

  function deckResetPause() {
    deck.pausedMs = 0;
    deck.pauseStart = 0;
    deck.paused = false;
    micPause.textContent = "Pause";
    micPause.setAttribute("aria-pressed", "false");
    micRecbar.classList.remove("paused");
  }

  function sendVoiceTake(blob, type, cutShort) {
    // Stop IS send (founder's ruling, Oct 30 evening): the
    // heard-you state fires in this same beat, and the take
    // travels the unchanged pipeline — listening track,
    // /api/media, and its own message when it lands. There
    // is no review step: a recording is a telling, not an
    // absolute record, and anything said can be corrected
    // in the conversation that follows. A CUT take (Fix 2 —
    // the screen slept, the recorder was killed) travels
    // the same path and the partial telling is preserved,
    // but its announcement tells the truth about the cut
    // instead of claiming a normal full send.
    setVoiceStatus(cutShort
      ? "The screen slept and cut that short — what you " +
        "said up to then went to Liv."
      : "Heard you — Liv is listening to your words.");
    stageWithListening("audio", blob,
      "recorded-audio." + extFor(type), function (item) {
        if (item) { send("", true, [item]); }
      });
  }

  micPause.addEventListener("click", function () {
    var R = recorders.audio;
    if (!R.rec || !micCanPause) { return; }
    if (R.rec.state === "recording") {
      R.rec.pause();
      deck.paused = true;
      deck.pauseStart = Date.now();
      micPause.textContent = "Resume";
      micPause.setAttribute("aria-pressed", "true");
      micRecbar.classList.add("paused");
      setVoiceStatus("Paused — Liv can’t hear you while " +
        "you’re paused. Tap Resume when you’re ready.");
    } else if (R.rec.state === "paused") {
      R.rec.resume();
      deck.pausedMs += Date.now() - deck.pauseStart;
      deck.paused = false;
      deck.pauseStart = 0;
      micPause.textContent = "Pause";
      micPause.setAttribute("aria-pressed", "false");
      micRecbar.classList.remove("paused");
      setVoiceStatus("Recording again — speak whenever " +
        "you’re ready.");
    }
  });

  micStop.addEventListener("click", function () {
    // Stop = stop-and-send: the recorder's stop event runs
    // the send (see the audio branch of startRecorder).
    // Mark the cause first — this stop is the storyteller's
    // own finish (Fix 2).
    var R = recorders.audio;
    if (R.rec && R.rec.state !== "inactive") {
      R.stopInitiated = true;
      R.rec.stop();
    }
  });

  // ---- Screen wake lock — SESSION-scoped (Fix 1, Oct 30
  // evening, as refined by the founder the same evening) --
  // The founder, testing on his phone: "My screen went to
  // sleep on safari and the recording was interrupted
  // while I was still talking." His refinement: the
  // interaction with Liv is continuous, so the lock is
  // held for the whole SITTING, not per recording. It is
  // acquired at the Begin transition past consent; its
  // home is every post-consent screen (conversation and
  // chapter alike); recording start merely ensures it is
  // held. The screen may sleep only after WAKE_IDLE_MS
  // with no interaction at all — the constant is named so
  // the founder can move it. Any interaction re-arms the
  // idle clock, and the first interaction after an idle
  // release re-acquires. Full release: the end-session
  // wipe and pagehide. The consent screen itself never
  // holds the lock.
  //
  // Enhancement only, held to the same standard as Pause:
  // feature-detected, and every failure — a rejected
  // request, an unsupported browser, a browser-initiated
  // release — is swallowed. Nothing may ever break or
  // block because the lock could not be held. Where the
  // API does not exist, nothing is faked; the first
  // recording of the session carries a plain hint instead
  // (maybeWakeHint).
  var WAKE_IDLE_MS = 30 * 60 * 1000;
  var wakeLockSentinel = null;
  var wakeRequestInFlight = false;
  var wakeIdleTimer = null;
  var wakeHintShown = false;

  function wakeLockSupported() {
    return "wakeLock" in navigator &&
      typeof navigator.wakeLock.request === "function";
  }

  function inSitting() {
    // Post-consent is the lock's home: Begin sets this;
    // the end-session wipe clears it.
    return consented;
  }

  function armWakeIdle() {
    if (wakeIdleTimer) { clearTimeout(wakeIdleTimer); }
    wakeIdleTimer = setTimeout(function () {
      // Untouched for the whole window: hand the screen
      // back to the device and let it sleep naturally.
      // The sitting itself continues — the next
      // interaction re-acquires (noteWakeInteraction).
      wakeIdleTimer = null;
      releaseWakeLock();
    }, WAKE_IDLE_MS);
  }

  function dropWakeSentinel(sentinel) {
    try {
      var p = sentinel.release();
      if (p && typeof p.catch === "function") {
        p.catch(function () { /* already released */ });
      }
    } catch (e) { /* already released */ }
  }

  function acquireWakeLock() {
    if (!wakeLockSupported() || !inSitting()) { return; }
    if (wakeLockSentinel || wakeRequestInFlight) {
      armWakeIdle();
      return;
    }
    if (document.visibilityState === "hidden") { return; }
    wakeRequestInFlight = true;
    try {
      navigator.wakeLock.request("screen")
        .then(function (sentinel) {
          wakeRequestInFlight = false;
          if (!inSitting()) {
            // The sitting ended while the request was in
            // flight — hand the lock straight back.
            dropWakeSentinel(sentinel);
            return;
          }
          wakeLockSentinel = sentinel;
          sentinel.addEventListener("release", function () {
            // The browser releases the lock on its own
            // whenever the page hides; note it here so a
            // return to visible knows to re-request.
            if (wakeLockSentinel === sentinel) {
              wakeLockSentinel = null;
            }
          });
          armWakeIdle();
        })
        .catch(function () {
          // Enhancement only: a rejection (page hidden,
          // power policy, anything) changes nothing.
          wakeRequestInFlight = false;
        });
    } catch (e) {
      wakeRequestInFlight = false;
    }
  }

  function releaseWakeLock() {
    if (wakeIdleTimer) {
      clearTimeout(wakeIdleTimer);
      wakeIdleTimer = null;
    }
    var sentinel = wakeLockSentinel;
    wakeLockSentinel = null;
    if (sentinel) { dropWakeSentinel(sentinel); }
  }

  function noteWakeInteraction() {
    // Pointer/key activity, a message sent, a recording
    // starting or stopping — each is proof the sitting is
    // alive: re-arm the idle clock, and re-acquire the
    // lock if it had lapsed (an idle release, or a
    // browser release not yet answered).
    if (!inSitting()) { return; }
    if (wakeLockSentinel) { armWakeIdle(); return; }
    acquireWakeLock();
  }

  function maybeWakeHint() {
    // No wake lock in this browser: nothing is faked.
    // Once per session, the first recording carries the
    // plain fact instead — sleep stops a recording, so a
    // screen kept awake is a telling kept whole.
    if (wakeLockSupported() || wakeHintShown) { return; }
    wakeHintShown = true;
    var hint = "Keeping the screen awake helps here — " +
      "if the screen sleeps, the recording stops.";
    if (voiceStatus && voiceStatus.textContent) {
      voiceStatus.textContent += " " + hint;
    } else {
      setVoiceStatus(hint);
    }
  }

  document.addEventListener("pointerdown", noteWakeInteraction);
  document.addEventListener("keydown", noteWakeInteraction);

  window.addEventListener("pagehide", function () {
    // The page is going away: the lock goes with it.
    releaseWakeLock();
  });

  document.addEventListener("visibilitychange", function () {
    var R = recorders.audio;
    var live = !!(R.rec && R.rec.state !== "inactive");
    if (document.visibilityState === "hidden") {
      if (live) {
        // The page going away mid-telling marks the take
        // interrupted (Fix 2): browsers stop the recorder
        // under a hidden page, so the stop that follows
        // is a cut, not a finish, and the send must say
        // so.
        R.interrupted = true;
      }
      return;
    }
    // Visible again. Returning to the tab counts as
    // interaction (founder refinement): re-arm the idle
    // clock and re-acquire the lock the browser dropped
    // when the page hid.
    noteWakeInteraction();
    if (live) { return; }
    // State mismatch: the recorder is dead but the mic
    // chrome still shows a recording in progress — its
    // stop event never landed (or is queued behind this
    // handler). Resync the UI to the truth, the way
    // closePanels does, and say what happened. If the
    // stop event IS merely queued, its send still runs
    // and the cut-short line speaks last.
    if (R.viaMic && !micRecbar.hidden) {
      micUiReset();
      setVoiceStatus("The screen slept, and the recording stopped.");
    }
  });

  // ---- End session & delete everything (Day 4 truth pass;
  // the Marriage, Oct 31, 2026) --------------------------------
  // The storyteller's own delete control: the server wipes the
  // session's whole in-memory state (conversation, media,
  // archive, chapter) and drops any keepsake links it minted;
  // the page then returns to the consent screen under a fresh
  // session id, with the ending stated plainly. The Marriage
  // changed the control's MECHANICS, not its effect: the plain
  // End button is now a hold-to-delete guard on the rail (and
  // in the narrow sitting sheet) — press and hold two seconds
  // and exactly this flow runs (wireHold, below).
  var endInFlight = false;
  var endSessionBtn = document.getElementById("end-session-btn");
  function endSessionNow() {
      // In-flight guard (Finding #2 hardening): a double
      // completion must not POST the wipe twice — the second
      // call would answer "not ended" and raise an error over
      // a wipe that already succeeded.
      if (!consented || endInFlight) { return; }
      endInFlight = true;
      fetch("/api/session/end", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          consent: consented,
          age_confirmed: ageConfirmed
        })
      })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          endInFlight = false;
          if (!data.ended) {
            showMediaError(data.error ||
              "That did not work just now. Please try again.");
            return;
          }
          consented = false;
          ageConfirmed = false;
          consentCheck.checked = false;
          ageCheck.checked = false;
          refreshBegin();
          sessionId = "s-" + Date.now().toString(36) + "-" +
            Math.random().toString(36).slice(2, 8);
          messages.innerHTML = "";
          pendingMedia = [];
          renderPending();
          // Kill any live recorder first: stopRecorder marks
          // the take for discard, so its stop event throws it
          // away rather than sending it into the new session.
          stopRecorder("audio", true);
          stopRecorder("video", true);
          deckTickStop();
          micUiReset();
          closePanels();
          setListening(false);
          setVoiceStatus("");
          // The sitting is over: the wake lock's home is
          // post-consent, so it is fully released here —
          // the consent screen the storyteller lands on
          // never holds it (Fix 1). The unsupported-browser
          // hint re-arms for the next sitting.
          releaseWakeLock();
          wakeHintShown = false;
          hideSittingSheet();
          chatScreen.hidden = true;
          chapterScreen.hidden = true;
          consentScreen.hidden = false;
          document.getElementById("session-ended-msg").hidden = false;
          window.scrollTo(0, 0);
        })
        .catch(function () {
          endInFlight = false;
          showMediaError("That did not work just now. " +
            "Please try again.");
        });
  }

  // ---- The sitting sheet + the hold guard (the Marriage) -----
  // On narrow widths the guard rail folds away and the SAME
  // three actions live behind the header's "This sitting"
  // control — Finish and Arrange never more than one tap from
  // the talking screen at any width. The sheet's Finish and
  // Arrange are the rail's own functions, wired twice.
  var sittingBtn = document.getElementById("sitting-btn");
  var sittingSheet = document.getElementById("sitting-sheet");
  function hideSittingSheet() {
    if (sittingSheet) { sittingSheet.hidden = true; }
    if (sittingBtn) {
      sittingBtn.setAttribute("aria-expanded", "false");
    }
  }
  if (sittingBtn && sittingSheet) {
    sittingBtn.addEventListener("click", function () {
      var open = sittingSheet.hidden;
      sittingSheet.hidden = !open;
      sittingBtn.setAttribute("aria-expanded",
        open ? "true" : "false");
    });
  }
  document.getElementById("finish-btn-sheet").addEventListener(
    "click", function () {
      hideSittingSheet();
      finishForToday();
    });
  document.getElementById("chapter-btn-sheet").addEventListener(
    "click", function () {
      hideSittingSheet();
      openChapter();
    });

  // Hold to delete: press-and-hold ~2s, pointer AND keyboard
  // (hold Space/Enter while focused). The flame track fills
  // as you hold; progress is announced in the #voice-status
  // live region and shown under the track ("Deleting… keep
  // holding."). Release early = cancelled, nothing deleted.
  // Completing the hold runs endSessionNow() — exactly the
  // shipped end-session flow: same POST, same wipe, same
  // reset. A plain click is swallowed: it is a hold, never
  // a tap.
  var HOLD_MS = 2000;
  function wireHold(btn) {
    if (!btn) { return; }
    var fill = btn.querySelector(".track i");
    var state = btn.querySelector(".hold-state");
    var raf = null;
    var startedAt = 0;
    var completed = false;
    function setProgress(p) {
      if (fill) { fill.style.width = (p * 100).toFixed(1) + "%"; }
    }
    function step() {
      var p = Math.min(1, (Date.now() - startedAt) / HOLD_MS);
      setProgress(p);
      if (p >= 1) { complete(); return; }
      raf = requestAnimationFrame(step);
    }
    function start(e) {
      if (!consented || endInFlight || raf !== null) { return; }
      if (e.type === "keydown") {
        if (e.key !== " " && e.key !== "Enter") { return; }
        e.preventDefault();
      }
      if (e.type === "pointerdown" &&
          e.button !== undefined && e.button !== 0) { return; }
      completed = false;
      startedAt = Date.now();
      if (state) { state.textContent = "Deleting… keep holding."; }
      setVoiceStatus("Deleting — keep holding to delete " +
        "everything.");
      raf = requestAnimationFrame(step);
    }
    function cancel() {
      if (raf === null) { return; }
      cancelAnimationFrame(raf);
      raf = null;
      if (completed) { return; }
      setProgress(0);
      if (state) { state.textContent = ""; }
      setVoiceStatus("Delete cancelled — nothing was deleted.");
    }
    function complete() {
      completed = true;
      if (raf !== null) {
        cancelAnimationFrame(raf);
        raf = null;
      }
      if (state) { state.textContent = ""; }
      endSessionNow();
      setProgress(0);
    }
    btn.addEventListener("pointerdown", start);
    btn.addEventListener("pointerup", cancel);
    btn.addEventListener("pointerleave", cancel);
    btn.addEventListener("pointercancel", cancel);
    btn.addEventListener("keydown", start);
    btn.addEventListener("keyup", cancel);
    btn.addEventListener("blur", cancel);
    btn.addEventListener("click", function (e) {
      e.preventDefault();
    });
  }
  wireHold(endSessionBtn);
  wireHold(document.getElementById("end-session-btn-sheet"));

  // ---- Chapter (talk -> chapter -> keepsake) --------------------
  // Plan before write: Liv proposes an outline (title, dedication,
  // materials); the storyteller edits and may ask for a re-plan;
  // only then is a draft written. The draft is an UNVERIFIED draft
  // until the storyteller approves it — and the share link exists
  // only after approval. Every step and checklist state rendered
  // here comes from the server, which records what it actually
  // did (see server/chapter.py).
  var chapterScreen = document.getElementById("chapter-screen");
  var chapterHeading = document.getElementById("chapter-heading");
  var chapterStatus = document.getElementById("chapter-status");
  var chapterError = document.getElementById("chapter-error");
  var chapterSteps = document.getElementById("chapter-steps");
  var chapterChecklist = document.getElementById("chapter-checklist");
  var chapterOutlineBox = document.getElementById("chapter-outline-box");
  var chapterTitle = document.getElementById("chapter-title");
  var chapterDedication = document.getElementById("chapter-dedication");
  var chapterMaterials = document.getElementById("chapter-materials");
  var chapterSections = document.getElementById("chapter-sections");
  var chapterDraftBox = document.getElementById("chapter-draft-box");
  var chapterDraftBody = document.getElementById("chapter-draft-body");
  var chapterFlags = document.getElementById("chapter-flags");
  var chapterFlagsList = document.getElementById("chapter-flags-list");
  var chapterKeepsakeBox = document.getElementById("chapter-keepsake-box");
  var chapterShareLink = document.getElementById("chapter-share-link");
  var chapterKeepsakeLink = document.getElementById("chapter-keepsake-link");
  var chapterIllustrateBtn = document.getElementById("chapter-illustrate");
  var chapterIllustrationBox = document.getElementById("chapter-illustration-box");
  var chapterIllustrationImg = document.getElementById("chapter-illustration-img");

  function showChapterError(text) {
    chapterError.textContent = text || "";
    chapterError.hidden = !text;
  }

  function chapterCall(path, extra) {
    var body = { session_id: sessionId, consent: consented,
                 age_confirmed: ageConfirmed };
    if (extra) {
      for (var k in extra) { body[k] = extra[k]; }
    }
    return fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (res) {
      return res.json().then(function (data) {
        return { status: res.status, data: data };
      });
    });
  }

  function renderSteps(steps) {
    chapterSteps.innerHTML = "";
    (steps || []).forEach(function (step) {
      var li = document.createElement("li");
      var strong = document.createElement("strong");
      strong.textContent = step.label;
      li.appendChild(strong);
      if (step.detail) {
        var detail = document.createElement("span");
        detail.className = "step-detail";
        detail.textContent = " — " + step.detail;
        li.appendChild(detail);
      }
      chapterSteps.appendChild(li);
    });
  }

  function renderChecklist(items) {
    chapterChecklist.innerHTML = "";
    (items || []).forEach(function (item) {
      var li = document.createElement("li");
      li.className = item.done ? "done" : "todo";
      li.textContent = (item.done ? "\u2713 " : "\u00b7 ") + item.label;
      chapterChecklist.appendChild(li);
    });
  }

  function renderOutline(view) {
    var ch = view.chapter;
    var outline = ch.outline;
    if (document.activeElement !== chapterTitle) {
      chapterTitle.value = outline.title || "";
    }
    if (document.activeElement !== chapterDedication) {
      chapterDedication.value = outline.dedication || "";
    }
    chapterMaterials.innerHTML = "";
    (ch.materials_all || []).forEach(function (mat) {
      var label = document.createElement("label");
      label.className = "archive-item";
      var box = document.createElement("input");
      box.type = "checkbox";
      box.value = mat.id;
      box.checked = mat.included;
      box.setAttribute("aria-label",
        "Include in the chapter: " + mat.label);
      label.appendChild(box);
      var text = document.createElement("span");
      text.className = "archive-item-text";
      text.textContent = mat.label;
      label.appendChild(text);
      chapterMaterials.appendChild(label);
    });
    chapterSections.innerHTML = "";
    (outline.sections || []).forEach(function (sec) {
      var li = document.createElement("li");
      li.textContent = sec.heading + " — " + sec.source_ids.length +
        (sec.source_ids.length === 1 ? " part" : " parts") +
        " of your telling";
      chapterSections.appendChild(li);
    });
    var atOutline = ch.stage === "outline";
    chapterTitle.disabled = !atOutline;
    chapterDedication.disabled = !atOutline;
    document.getElementById("chapter-replan").disabled = !atOutline;
    document.getElementById("chapter-draft").disabled = !atOutline;
    var boxes = chapterMaterials.querySelectorAll('input[type="checkbox"]');
    for (var i = 0; i < boxes.length; i++) { boxes[i].disabled = !atOutline; }
  }

  function evidenceFor(view, sectionIdx, textStart) {
    var found = [];
    (view.evidence || []).forEach(function (ev) {
      if (ev.section === sectionIdx && ev.text_start === textStart) {
        found = ev.sources || [];
      }
    });
    return found;
  }

  function renderDraft(view) {
    var ch = view.chapter;
    var draft = ch.draft;
    chapterDraftBox.hidden = !draft;
    if (!draft) { return; }
    var check = ch.check;
    if (check && check.flags && check.flags.length > 0) {
      chapterFlags.hidden = false;
      chapterFlagsList.innerHTML = "";
      check.flags.forEach(function (flag) {
        var li = document.createElement("li");
        li.textContent = "\u201c" + flag.text + "\u201d (" +
          flag.kind + ") — not in your words, please check";
        chapterFlagsList.appendChild(li);
      });
    } else {
      chapterFlags.hidden = true;
    }
    chapterDraftBody.innerHTML = "";
    var title = document.createElement("h3");
    title.className = "chapter-draft-title";
    title.textContent = draft.title;
    chapterDraftBody.appendChild(title);
    if (draft.dedication) {
      var forLine = document.createElement("p");
      forLine.className = "chapter-for";
      forLine.textContent = "For " + draft.dedication;
      chapterDraftBody.appendChild(forLine);
    }
    draft.sections.forEach(function (section, si) {
      var heading = document.createElement("h3");
      heading.className = "chapter-h3";
      heading.textContent = section.heading;
      chapterDraftBody.appendChild(heading);
      section.paragraphs.forEach(function (para) {
        var p = document.createElement("p");
        p.textContent = para.text;
        chapterDraftBody.appendChild(p);
        var sources = evidenceFor(view, si, para.text.slice(0, 80));
        var det = document.createElement("details");
        det.className = "chapter-evidence";
        var sum = document.createElement("summary");
        sum.textContent = "Where did this come from?";
        det.appendChild(sum);
        var ul = document.createElement("ul");
        if (sources.length > 0) {
          sources.forEach(function (src) {
            var li = document.createElement("li");
            li.textContent = src.label;
            ul.appendChild(li);
          });
        } else {
          var li2 = document.createElement("li");
          li2.textContent = "Arranged from your conversation as a " +
            "whole — no single part was marked for this paragraph.";
          ul.appendChild(li2);
        }
        det.appendChild(ul);
        chapterDraftBody.appendChild(det);
      });
      (section.media_ids || []).forEach(function (mediaId) {
        var img = document.createElement("img");
        img.className = "shared-media";
        img.src = mediaUrl({ id: mediaId });
        img.alt = "A photo kept with this chapter";
        chapterDraftBody.appendChild(img);
      });
    });
  }

  function renderChapter(view) {
    renderSteps(view.steps);
    renderChecklist(view.checklist);
    if (!view.chapter) { return; }
    renderOutline(view);
    renderDraft(view);
    var approved = view.chapter.stage === "approved" && view.share_url;
    chapterKeepsakeBox.hidden = !approved;
    if (approved) {
      var absolute = window.location.origin + view.share_url;
      chapterShareLink.value = absolute;
      chapterKeepsakeLink.href = view.share_url;
      document.getElementById("chapter-approve").disabled = true;
    }
    var illustrated = approved && view.chapter.illustration;
    chapterIllustrationBox.hidden = !illustrated;
    if (illustrated) {
      chapterIllustrationImg.src = "/api/chapter/illustration" +
        "?session_id=" + encodeURIComponent(sessionId) +
        "&v=" + (view.chapter.illustration_version || 1);
    }
  }

  function openChapter() {
    chatScreen.hidden = true;
    chapterScreen.hidden = false;
    chapterHeading.focus();
    showChapterError("");
    chapterStatus.textContent = "Liv is gathering what you shared\u2026";
    chapterCall("/api/chapter/outline")
      .then(function (out) {
        if (out.status === 200 && out.data.chapter) {
          chapterStatus.textContent = "Here is the plan, first — " +
            "nothing is written until you say it looks right.";
          renderChapter(out.data);
        } else {
          chapterStatus.textContent = "";
          showChapterError(out.data.error ||
            "A chapter could not be started just now.");
        }
      })
      .catch(function () {
        chapterStatus.textContent = "";
        showChapterError("Liv could not be reached just now. " +
          "Please try again in a moment.");
      });
  }

  document.getElementById("chapter-btn").addEventListener("click",
    openChapter);

  document.getElementById("chapter-back").addEventListener("click",
    function () {
      chapterScreen.hidden = true;
      chatScreen.hidden = false;
      input.focus();
    });

  function currentPlanEdits() {
    var excluded = [];
    var boxes = chapterMaterials.querySelectorAll(
      'input[type="checkbox"]');
    for (var i = 0; i < boxes.length; i++) {
      if (!boxes[i].checked) { excluded.push(boxes[i].value); }
    }
    return {
      title: chapterTitle.value,
      dedication: chapterDedication.value,
      exclude_source_ids: excluded
    };
  }

  document.getElementById("chapter-replan").addEventListener("click",
    function () {
      showChapterError("");
      chapterStatus.textContent = "Liv is re-planning the outline\u2026";
      chapterCall("/api/chapter/replan", currentPlanEdits())
        .then(function (out) {
          if (out.status === 200 && out.data.chapter) {
            chapterStatus.textContent = "Here is the new plan.";
            renderChapter(out.data);
          } else {
            chapterStatus.textContent = "";
            showChapterError(out.data.error ||
              "The plan could not be changed just now.");
          }
        })
        .catch(function () {
          chapterStatus.textContent = "";
          showChapterError("Liv could not be reached just now.");
        });
    });

  document.getElementById("chapter-draft").addEventListener("click",
    function () {
      showChapterError("");
      chapterStatus.textContent = "Saving your plan\u2026";
      // The plan on screen IS the plan approved: edits are saved
      // first (a re-plan), then the draft is written from it.
      chapterCall("/api/chapter/replan", currentPlanEdits())
        .then(function (out) {
          if (out.status !== 200) {
            chapterStatus.textContent = "";
            showChapterError((out.data && out.data.error) ||
              "The plan could not be saved just now.");
            return null;
          }
          chapterStatus.textContent = "Liv is arranging your " +
            "chapter\u2026";
          return chapterCall("/api/chapter/draft");
        })
        .then(function (out) {
          if (!out) { return; }
          if (out.status === 200 && out.data.chapter) {
            chapterStatus.textContent = "Here is your draft. " +
              "Please read it through — it stays an unverified " +
              "draft until you approve it.";
            renderChapter(out.data);
            chapterDraftBox.scrollIntoView({ block: "start",
              behavior: scrollBehavior() });
          } else {
            chapterStatus.textContent = "";
            showChapterError(out.data.error ||
              "The chapter could not be written just now.");
          }
        })
        .catch(function () {
          chapterStatus.textContent = "";
          showChapterError("Liv could not be reached just now.");
        });
    });

  document.getElementById("chapter-approve").addEventListener("click",
    function () {
      showChapterError("");
      chapterStatus.textContent = "Thank you — making your keepsake\u2026";
      chapterCall("/api/chapter/approve")
        .then(function (out) {
          if (out.status === 200 && out.data.share_url) {
            chapterStatus.textContent = "Approved. Your keepsake " +
              "is ready below.";
            renderChapter(out.data);
            chapterKeepsakeBox.scrollIntoView({ block: "start",
              behavior: scrollBehavior() });
            chapterShareLink.focus();
            chapterShareLink.select();
          } else {
            chapterStatus.textContent = "";
            showChapterError(out.data.error ||
              "The approval could not be saved just now.");
          }
        })
        .catch(function () {
          chapterStatus.textContent = "";
          showChapterError("Liv could not be reached just now.");
        });
    });

  chapterIllustrateBtn.addEventListener("click", function () {
    showChapterError("");
    chapterIllustrateBtn.disabled = true;
    chapterStatus.textContent = "Liv is making an illustration " +
      "for your chapter\u2026";
    chapterCall("/api/chapter/illustrate")
      .then(function (out) {
        chapterIllustrateBtn.disabled = false;
        if (out.status === 200 && out.data.chapter &&
            out.data.chapter.illustration) {
          chapterStatus.textContent = "Your illustration is " +
            "ready — it sits at the top of your keepsake.";
          renderChapter(out.data);
          chapterIllustrationBox.scrollIntoView(
            { block: "start", behavior: scrollBehavior() });
        } else {
          chapterStatus.textContent = "";
          showChapterError((out.data && out.data.error) ||
            "The illustration didn't come through — your " +
            "chapter is complete without it.");
        }
      })
      .catch(function () {
        chapterIllustrateBtn.disabled = false;
        chapterStatus.textContent = "";
        showChapterError("The illustration didn't come through " +
          "— your chapter is complete without it.");
      });
  });
})();
