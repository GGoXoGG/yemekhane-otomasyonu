import { istek } from "./ortak.js";

const form = document.querySelector("#giris");
const bildirim = document.querySelector("#bildirim");
const dugme = form.querySelector("button");

form.addEventListener("submit", async (olay) => {
  olay.preventDefault();
  dugme.disabled = true;
  bildirim.hidden = true;
  try {
    await istek("/api/giris", "POST", Object.fromEntries(new FormData(form)));
    location.replace("/menu.html");
  } catch (hata) {
    bildirim.textContent = hata.message;
    bildirim.className = "bildirim bildirim-hata";
    bildirim.hidden = false;
  } finally {
    dugme.disabled = false;
  }
});
