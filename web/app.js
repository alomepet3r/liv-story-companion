// Day 1 shell behaviour, with the companion-name choice (Oct 26).
// Screen 1 (consent) gates Screen 2 (conversation): the chat UI is not
// shown until the storyteller agrees, and every /api/chat call carries
// the consent flag, which the server also enforces. The storyteller
// chooses their companion's name on Screen 1 — Livio, Livia, or Liv
// (Liv is the default) — and the choice is sent with every call so the
// server keeps it for the whole session.
// Age posture (Petro, Oct 26): lone users are adults only. The Begin
// button stays disabled until BOTH the consent checkbox and the
// "I confirm I am 18 or older" attestation are checked, and every
// call carries age_confirmed, which the server enforces the same way.
// Media (Day 2, Petro's live test): a media bar under the messages —
// "Add a photo", "Record voice", "Record video". Sharing is staged:
// pick or record → uploaded to /api/media for THIS session → shown
// in a pending tray with a remove option → sent with the next
// message. Media is in-memory on the server and dies with the tab
// session, exactly like the conversation. The first media use in a
// session shows a short notice before anything opens.

(function () {
  "use strict";

  var sessionId = "s-" + Date.now().toString(36) + "-" +
    Math.random().toString(36).slice(2, 8);
  var consented = false;
  var ageConfirmed = false;
  var companionName = "Liv";

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

  function setCompanionName(name) {
    companionName = name;
    var spans = document.querySelectorAll(".js-companion-name");
    for (var i = 0; i < spans.length; i++) {
      spans[i].textContent = name;
    }
  }

  var radios = document.querySelectorAll('input[name="companion"]');
  for (var r = 0; r < radios.length; r++) {
    radios[r].addEventListener("change", function () {
      if (this.checked) { setCompanionName(this.value); }
    });
    if (radios[r].checked) { companionName = radios[r].value; }
  }
  setCompanionName(companionName);

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
        companion: companionName,
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

  document.getElementById("finish-btn").addEventListener("click", function () {
    send("Finish for today", true);
  });

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

  function stageMedia(kind, blob, filename) {
    showMediaError("");
    if (blob.size > MEDIA_CAPS[kind]) {
      showMediaError("That " + MEDIA_NOUN[kind] + " is too large — " +
        "photos can be up to 10 MB, recordings and videos up to 50 MB.");
      return;
    }
    var fd = new FormData();
    fd.append("session_id", sessionId);
    fd.append("consent", consented ? "true" : "false");
    fd.append("age_confirmed", ageConfirmed ? "true" : "false");
    fd.append("kind", kind);
    fd.append("file", blob, filename || ("shared-" + kind));
    fetch("/api/media", { method: "POST", body: fd })
      .then(function (res) {
        return res.json().then(function (data) {
          return { status: res.status, data: data };
        });
      })
      .then(function (out) {
        if (out.status === 200 && out.data.media_id) {
          pendingMedia.push({ id: out.data.media_id, kind: kind });
          renderPending();
          input.focus();
        } else {
          showMediaError(out.data.error ||
            "That did not arrive. Please try again.");
        }
      })
      .catch(function () {
        showMediaError("That did not arrive. Please try again.");
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
      if (invoker) { invoker.focus(); }
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

  function closePanels() {
    for (var k in panels) {
      panels[k].hidden = true;
      barButtons[k].setAttribute("aria-expanded", "false");
    }
    stopRecorder("audio", true);
    stopRecorder("video", true);
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

  // File choices (take / choose for photos; choose for audio/video).
  function wireFileInput(id, kind) {
    var el = document.getElementById(id);
    el.addEventListener("change", function () {
      if (el.files && el.files[0]) {
        stageMedia(kind, el.files[0], el.files[0].name);
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
      R.rec.onstop = null;
      try { R.rec.stop(); } catch (e) { /* already stopped */ }
    }
    R.rec = null;
    stopTracks(kind);
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
          if (R.timer) { clearInterval(R.timer); R.timer = null; }
          R.button.textContent = "Start recording";
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
        R.rec.start(250);
        R.started = Date.now();
        R.button.textContent = "Stop recording";
        R.status.textContent = "Recording… 0:00";
        R.timer = setInterval(function () {
          R.status.textContent = "Recording… " +
            fmtTime(Date.now() - R.started);
        }, 500);
      })
      .catch(function () {
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
        R.rec.stop();
      } else {
        R.preview.hidden = true;
        R.actions.hidden = true;
        startRecorder(kind);
      }
    });
    document.getElementById(kind + "-use").addEventListener("click",
      function () {
        if (R.blob) {
          var mime = R.blob.type || "video/webm";
          stageMedia(kind, R.blob,
            "recorded-" + kind + "." + extFor(mime));
        }
        R.blob = null;
        R.preview.hidden = true;
        R.actions.hidden = true;
        R.status.textContent = R.idleText;
        closePanels();
      });
    document.getElementById(kind + "-discard").addEventListener("click",
      function () {
        R.blob = null;
        R.preview.hidden = true;
        R.actions.hidden = true;
        R.status.textContent = R.idleText;
      });
  }
  wireRecorder("audio");
  wireRecorder("video");

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
})();
