// Story Companion — Day 1 shell behaviour.
// Screen 1 (consent) gates Screen 2 (conversation): the chat UI is not
// shown until the storyteller agrees, and every /api/chat call carries
// the consent flag, which the server also enforces.

(function () {
  "use strict";

  var sessionId = "s-" + Date.now().toString(36) + "-" +
    Math.random().toString(36).slice(2, 8);
  var consented = false;

  var consentScreen = document.getElementById("consent-screen");
  var chatScreen = document.getElementById("chat-screen");
  var messages = document.getElementById("messages");
  var form = document.getElementById("chat-form");
  var input = document.getElementById("chat-input");

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
        consent: consented
      })
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.reply) {
          addMessage("Your companion", data.reply, "companion");
        } else if (data.error) {
          addMessage("Your companion",
            "Something went wrong on my side. Please try again.",
            "companion");
        }
      })
      .catch(function () {
        addMessage("Your companion",
          "I could not be reached just now. Please try again in a moment.",
          "companion");
      });
  }

  document.getElementById("begin-btn").addEventListener("click", function () {
    consented = true;
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
