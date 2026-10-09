// JavaScript mínimo da loja: menu mobile, galeria e proteção contra duplo clique.

document.addEventListener("DOMContentLoaded", function () {
  // Menu mobile
  var toggle = document.getElementById("menu-toggle");
  var menu = document.getElementById("mobile-menu");
  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var open = menu.classList.toggle("hidden") === false;
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // Galeria do produto
  var mainImage = document.getElementById("main-image");
  if (mainImage) {
    document.querySelectorAll(".gallery-thumb").forEach(function (thumb) {
      thumb.addEventListener("click", function () {
        mainImage.src = thumb.dataset.full;
        document.querySelectorAll(".gallery-thumb").forEach(function (t) {
          t.classList.remove("border-primary");
          t.classList.add("border-transparent");
        });
        thumb.classList.remove("border-transparent");
        thumb.classList.add("border-primary");
      });
    });
  }

  // Desabilitar botões de envio durante o processamento (evita pedidos duplicados)
  document.querySelectorAll("form.js-checkout-form").forEach(function (form) {
    form.addEventListener("submit", function () {
      var button = form.querySelector('button[type="submit"]');
      if (button && !form.dataset.submitted) {
        form.dataset.submitted = "1";
        button.disabled = true;
        button.textContent = "Processando…";
      }
    });
  });
});
