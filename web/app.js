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
  var form = document.getElementById("chat-form");
  var input = document.getElementById("chat-input");

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

  function addMessage(who, text, cls) {
    var div = document.createElement("div");
    div.className = "msg " + cls;
    var label = document.createElement("span");
    label.className = "who";
    label.textContent = who;
    var body = document.createElement("span");
    body.textContent = text;
    div.appendChild(label);
    div.appendChild(body);
    messages.appendChild(div);
    div.scrollIntoView({ block: "end", behavior: "smooth" });
  }

  function send(message, showMine) {
    if (showMine && message.trim() !== "") {
      addMessage("You", message, "storyteller");
    }
    return fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        message: message,
        consent: consented,
        age_confirmed: ageConfirmed,
        companion: companionName
      })
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
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
    if (text.trim() === "") { return; }
    input.value = "";
    send(text, true).then(function () { input.focus(); });
  });

  document.getElementById("finish-btn").addEventListener("click", function () {
    send("Finish for today", true);
  });
})();
