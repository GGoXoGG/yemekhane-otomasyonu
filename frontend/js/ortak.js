const roller = { ogrenci: "Öğrenci", personel: "Personel", yonetici: "Yönetici" };
const baglantilar = [
  ["menu", "Günün menüsü"],
  ["haftalik", "Haftalık menü"],
  ["rezervasyonlar", "Rezervasyonlarım"],
  ["bakiye", "Bakiye"],
  ["degerlendirme", "Değerlendirme"],
  ["yonetici", "Yönetici paneli"],
];
const tarihBicimi = new Intl.DateTimeFormat("tr-TR", { dateStyle: "long" });
const paraBicimi = new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY" });
let csrf;

export function eleman(tur, metin, sinif) {
  const dugum = document.createElement(tur);
  if (metin !== undefined && metin !== null) dugum.textContent = metin;
  if (sinif) dugum.className = sinif;
  return dugum;
}

export async function istek(adres, method = "GET", veri = {}) {
  const headers = {};
  const ayar = { method, headers, cache: "no-store" };
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    if (csrf) headers["X-CSRF-Token"] = csrf;
    ayar.body = JSON.stringify(veri);
  }
  const yanit = await fetch(adres, ayar);
  if (!yanit.ok) {
    const govde = await yanit.json().catch(() => null);
    const hata = new Error(govde?.mesaj || "Sunucu isteği tamamlayamadı.");
    hata.durum = yanit.status;
    if (hata.durum === 401 && document.body.dataset.sayfa) location.replace("/");
    throw hata;
  }
  return yanit.json();
}

export function bildir(metin, basarili = false) {
  const hedef = document.querySelector("#bildirimler");
  hedef.replaceChildren(eleman("p", metin, basarili ? "bildirim bildirim-basari" : "bildirim bildirim-hata"));
}

export function para(deger) {
  return paraBicimi.format(Number(deger));
}

export function gun(deger) {
  return tarihBicimi.format(new Date(deger.slice(0, 10) + "T12:00:00"));
}

export function zaman(deger) {
  return `${gun(deger)} · ${deger.slice(11, 16)}`;
}

export function bakiyeGoster(deger) {
  document.querySelector("#ust-bakiye").textContent = para(deger);
  const toplam = document.querySelector("#bakiye-toplam");
  if (toplam) toplam.textContent = para(deger);
}

export function secenekler(select, kayitlar, ilkSecenek) {
  select.replaceChildren();
  if (ilkSecenek) select.append(new Option(ilkSecenek, ""));
  for (const { id, ad } of kayitlar) select.append(new Option(ad, id));
}

export function tablo(basliklar, satirlar) {
  const sarici = eleman("div", null, "tablo-kaydir");
  const tablo = eleman("table");
  const thead = tablo.createTHead().insertRow();
  for (const baslik of basliklar) {
    const hucre = eleman("th", baslik);
    hucre.scope = "col";
    thead.append(hucre);
  }
  const tbody = tablo.createTBody();
  for (const satir of satirlar) {
    const tr = tbody.insertRow();
    for (const deger of satir) {
      const td = tr.insertCell();
      if (deger instanceof Node) td.append(deger);
      else td.textContent = deger ?? "—";
    }
  }
  sarici.append(tablo);
  return sarici;
}

export async function baslat(yukle) {
  try {
    const { kullanici, csrf: token } = await istek("/api/oturum");
    csrf = token;
    const sayfa = document.body.dataset.sayfa;
    if (sayfa === "yonetici" && kullanici.rol !== "yonetici") {
      throw new Error("Bu sayfa için yönetici yetkisi gerekiyor.");
    }
    const ust = document.querySelector("#ust");
    const marka = eleman("a", "Yemekhane Otomasyonu", "ust-marka");
    marka.href = "/menu.html";
    const kisi = eleman("span", `${kullanici.ad} ${kullanici.soyad} · ${roller[kullanici.rol]}`, "ust-kisi");
    const bakiye = eleman("span", null, "ust-bakiye");
    bakiye.id = "ust-bakiye";
    bakiye.setAttribute("aria-label", "Güncel bakiye");
    const cikis = eleman("button", "Çıkış", "cikis-dugmesi");
    cikis.type = "button";
    cikis.addEventListener("click", async () => {
      try {
        await istek("/api/cikis", "POST");
        location.replace("/");
      } catch (hata) {
        bildir(hata.message);
      }
    });
    ust.append(marka, kisi, bakiye, cikis);
    bakiyeGoster(kullanici.bakiye);
    const gezinti = document.querySelector("#gezinti");
    for (const [kimlik, yazi] of baglantilar) {
      if (kimlik === "yonetici" && kullanici.rol !== "yonetici") continue;
      const a = eleman("a", yazi);
      a.href = `/${kimlik}.html`;
      if (kimlik === sayfa) a.setAttribute("aria-current", "page");
      gezinti.append(a);
    }
    ust.hidden = gezinti.hidden = document.querySelector("#icerik").hidden = false;
    await yukle(kullanici);
  } catch (hata) {
    if (hata.durum === 401) return;
    if (!document.querySelector("#icerik").hidden) {
      bildir(hata.message);
      return;
    }
    const hedef = document.querySelector("#ilk-hata");
    hedef.textContent = hata.message;
    const don = eleman("a", "Günün menüsüne dön");
    don.href = "/menu.html";
    hedef.append(" ", don);
    hedef.hidden = false;
  }
}
