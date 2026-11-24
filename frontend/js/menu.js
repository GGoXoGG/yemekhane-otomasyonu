import { bakiyeGoster, baslat, bildir, eleman, gun, istek, para, secenekler, zaman } from "./ortak.js";

const haftalik = document.body.dataset.sayfa === "haftalik";
const yemekhane = document.querySelector("#yemekhane");
const ogun = document.querySelector("#ogun");
const baslangic = document.querySelector("#baslangic");
const liste = document.querySelector("#menuler");
let sonIstek = 0;

function yemekListesi(yemekler) {
  const liste = eleman("ul", null, haftalik ? "yemek-ozet" : "yemek-listesi");
  for (const yemek of yemekler) {
    const satir = eleman("li");
    if (haftalik) {
      satir.textContent = yemek.yemek;
    } else {
      const ust = eleman("div", null, "yemek-ust");
      ust.append(eleman("strong", yemek.yemek), eleman("span", `${yemek.kalori} kcal`));
      const ayrinti = [yemek.kategori, yemek.vejetaryen ? "Vejetaryen" : "Vejetaryen değil",
        yemek.alerjenler ? `Alerjenler: ${yemek.alerjenler}` : "Alerjen bilgisi yok"];
      satir.append(ust, eleman("p", ayrinti.join(" · "), "yemek-detay"));
    }
    liste.append(satir);
  }
  return yemekler.length ? liste : eleman("p", "Bu menüye henüz yemek eklenmemiş.", "bos");
}

function rezervasyonAlani(menu) {
  const alan = eleman("div");
  const satir = eleman("div", null, "menu-alt");
  const durum = eleman("p", menu.rezervasyon_notu, "rezervasyon-kural soluk");
  durum.hidden = !menu.rezervasyon_notu;
  const dugme = eleman("button", "Rezervasyon yap", "dugme");
  dugme.disabled = !menu.rezerve_edilebilir;
  dugme.addEventListener("click", async () => {
    dugme.disabled = true;
    try {
      const sonuc = await istek("/api/rezervasyonlar", "POST", { menu_id: menu.menu_id });
      bakiyeGoster(sonuc.bakiye);
      durum.textContent = "Rezervasyon durumu: Aktif";
      durum.hidden = false;
      bildir(`${sonuc.mesaj} Ücret ${para(sonuc.ucret)}. Güncel bakiye ${para(sonuc.bakiye)}.`, true);
    } catch (hata) {
      bildir(hata.message);
      dugme.disabled = false;
    }
  });
  satir.append(eleman("strong", para(menu.fiyat)), eleman("span", `${menu.bos_yer} boş yer`), dugme);
  alan.append(satir, eleman("p", `Rezervasyon sonu ${zaman(menu.rezervasyon_son)}`, "yardim"), durum);
  return alan;
}

function kart(menu) {
  const kart = eleman("article", null, "panel menu-kart");
  kart.append(eleman("h2", `${menu.yemekhane} · ${menu.ogun}`));
  kart.append(eleman("p", `${gun(menu.tarih)} · Toplam ${menu.toplam_kalori} kcal`, "soluk"));
  kart.append(yemekListesi(menu.yemekler));
  if (haftalik) kart.append(rezervasyonAlani(menu));
  return kart;
}

async function menuleriYukle() {
  const sira = ++sonIstek;
  const filtre = new URLSearchParams();
  if (yemekhane.value) filtre.set("yemekhane_id", yemekhane.value);
  if (ogun.value) filtre.set("ogun_id", ogun.value);
  if (baslangic?.value) filtre.set("baslangic", baslangic.value);
  try {
    const { menuler } = await istek(`/api/menu/${haftalik ? "haftalik" : "gunluk"}?${filtre}`);
    if (sira !== sonIstek) return;
    liste.replaceChildren(...(menuler.length
      ? menuler.map(kart) : [eleman("p", "Seçilen tarih ve filtreler için menü bulunamadı.", "panel bos")]));
  } catch (hata) {
    if (sira === sonIstek) bildir(hata.message);
  }
}

baslat(async () => {
  const [yerler, ogunler] = await Promise.all([istek("/api/yemekhaneler"), istek("/api/ogunler")]);
  secenekler(yemekhane, yerler.yemekhaneler, haftalik ? "Tüm yemekhaneler" : null);
  if (haftalik && yerler.yemekhaneler.length) yemekhane.value = yerler.yemekhaneler[0].id;
  secenekler(ogun, ogunler.ogunler, haftalik ? "Tüm öğünler" : null);
  if (baslangic) {
    baslangic.value = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Istanbul" }).format(new Date());
  }
  for (const alan of [yemekhane, ogun, baslangic].filter(Boolean)) alan.addEventListener("change", menuleriYukle);
  await menuleriYukle();
});
