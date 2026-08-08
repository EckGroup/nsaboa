// Nkosuo Mma Foundation — shared behaviour
var WHATSAPP_NUMBER = "0574168196";
var WHATSAPP_INTL = "233574168196";

function whatsappLink(message) {
  return "https://wa.me/" + WHATSAPP_INTL + "?text=" + encodeURIComponent(message);
}
function openWhatsApp(message) {
  window.open(whatsappLink(message), "_blank", "noopener,noreferrer");
}
function toast(msg) {
  var el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(el._t);
  el._t = setTimeout(function () { el.classList.remove("show"); }, 3200);
}

document.addEventListener("DOMContentLoaded", function () {
  // mobile menu
  var btn = document.querySelector(".menu-btn");
  var menu = document.getElementById("mobile-nav");
  if (btn && menu) {
    btn.addEventListener("click", function () {
      menu.classList.toggle("is-open");
      btn.textContent = menu.classList.contains("is-open") ? "\u2715" : "\u2630";
    });
  }

  // current year
  var y = document.getElementById("year");
  if (y) y.textContent = new Date().getFullYear();

  // pre-built whatsapp links
  document.querySelectorAll("[data-wa]").forEach(function (a) {
    a.href = whatsappLink(a.getAttribute("data-wa"));
    a.target = "_blank";
    a.rel = "noopener noreferrer";
  });

  // contact form
  var contact = document.getElementById("contact-form");
  if (contact) {
    contact.addEventListener("submit", function (e) {
      e.preventDefault();
      var name = contact.name_.value.trim();
      var message = contact.message.value.trim();
      if (!name || !message) { toast("Please add your name and a short message."); return; }
      openWhatsApp(
        "Hello Nkosuo Mma Foundation.\n\nName: " + name +
        "\nTopic: " + contact.topic.value +
        "\nLocation: " + (contact.location.value.trim() || "\u2014") +
        "\n\n" + message
      );
      toast("Opening WhatsApp so you can send your message.");
    });
  }

  // donate page
  var donate = document.getElementById("donate-form");
  if (donate) {
    var chips = document.querySelectorAll(".chip");
    chips.forEach(function (c) {
      c.addEventListener("click", function () {
        chips.forEach(function (x) { x.classList.remove("is-active"); });
        c.classList.add("is-active");
        donate.kind.value = c.textContent.trim();
      });
    });
    document.querySelectorAll(".tier").forEach(function (t) {
      t.addEventListener("click", function () {
        donate.amount.value = t.getAttribute("data-amount");
        toast(t.getAttribute("data-amount") + " selected \u2014 finish the form below.");
        donate.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    });
    donate.addEventListener("submit", function (e) {
      e.preventDefault();
      var name = donate.name_.value.trim();
      var amount = donate.amount.value.trim();
      if (!name || !amount) { toast("Please add your name and what you'd like to give."); return; }
      openWhatsApp(
        "Hello Nkosuo Mma Foundation, I would like to donate.\n\nName: " + name +
        "\nType: " + donate.kind.value +
        "\nAmount / items: " + amount +
        "\nNote: " + (donate.note.value.trim() || "\u2014")
      );
      toast("Opening WhatsApp to confirm your pledge.");
    });
  }
});
