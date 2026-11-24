import { baslat, bildir, eleman, istek } from "./ortak.js";

const form = document.querySelector("#alerjen-formu");
const liste = document.querySelector("#alerjenler");
const dugme = form.querySelector("button");

function secimleriGoster(alerjenler) {
  liste.replaceChildren(...alerjenler.map(({ id, ad, secili }) => {
    const etiket = eleman("label");
    const kutu = eleman("input");
    kutu.type = "checkbox";
    kutu.name = "alerjen";
    kutu.value = id;
    kutu.checked = Boolean(secili);
    etiket.append(kutu, ad);
    return etiket;
  }));
}

baslat(async () => {
  secimleriGoster((await istek("/api/profil/alerjenler")).alerjenler);
  dugme.disabled = false;
  form.addEventListener("submit", async (olay) => {
    olay.preventDefault();
    dugme.disabled = true;
    const alerjen_idleri = new FormData(form).getAll("alerjen");
    try {
      const sonuc = await istek("/api/profil/alerjenler", "PUT", { alerjen_idleri });
      secimleriGoster(sonuc.alerjenler);
      bildir(sonuc.mesaj, true);
    } catch (hata) {
      bildir(hata.message);
    } finally {
      dugme.disabled = false;
    }
  });
});
