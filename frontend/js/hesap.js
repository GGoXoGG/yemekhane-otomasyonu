import { bakiyeGoster, baslat, bildir, eleman, gun, istek, para, tablo, zaman } from "./ortak.js";

const durumlar = { aktif: "Aktif", kullanildi: "Kullanıldı", iptal: "İptal" };
const hareketTurleri = { yukleme: "Yükleme", rezervasyon: "Rezervasyon", iade: "İade" };

async function rezervasyonlar() {
  const hedef = document.querySelector("#rezervasyon-listesi");
  const { rezervasyonlar } = await istek("/api/rezervasyonlar");
  const satirlar = rezervasyonlar.map((kayit) => {
    const durum = eleman("span", durumlar[kayit.durum], `rozet ${kayit.durum}`);
    const dugme = eleman("button", "İptal et", "dugme dugme-ikincil");
    dugme.hidden = !kayit.iptal_edilebilir;
    dugme.addEventListener("click", async () => {
      dugme.disabled = true;
      try {
        const sonuc = await istek(`/api/rezervasyonlar/${kayit.id}/iptal`, "POST");
        durum.textContent = durumlar[sonuc.durum];
        durum.className = `rozet ${sonuc.durum}`;
        bakiyeGoster(sonuc.bakiye);
        dugme.hidden = true;
        bildir(`${sonuc.mesaj} İade ${para(sonuc.iade)}. Güncel bakiye ${para(sonuc.bakiye)}.`, true);
      } catch (hata) {
        bildir(hata.message);
      } finally {
        dugme.disabled = false;
      }
    });
    return [gun(kayit.tarih), kayit.yemekhane, kayit.ogun, para(kayit.ucret), durum, dugme];
  });
  hedef.replaceChildren(satirlar.length
    ? tablo(["Tarih", "Yemekhane", "Öğün", "Ücret", "Durum", "İşlem"], satirlar)
    : eleman("p", "Henüz rezervasyonunuz yok.", "bos"));
}

async function hareketleriGoster() {
  const { hareketler } = await istek("/api/bakiye/hareketler");
  const satirlar = hareketler.map((hareket) => {
    const tutar = Number(hareket.tutar);
    const tutarMetni = eleman("strong", (tutar > 0 ? "+" : "") + para(tutar),
      tutar > 0 ? "tutar-arti" : "tutar-eksi");
    return [zaman(hareket.olusturma), hareketTurleri[hareket.tur], tutarMetni, hareket.aciklama || "—"];
  });
  document.querySelector("#hareketler").replaceChildren(satirlar.length
    ? tablo(["Tarih", "İşlem", "Tutar", "Açıklama"], satirlar)
    : eleman("p", "Henüz bakiye hareketiniz yok.", "bos"));
}

async function bakiye() {
  const form = document.querySelector("#bakiye-formu");
  const dugme = form.querySelector("button");
  form.addEventListener("submit", async (olay) => {
    olay.preventDefault();
    dugme.disabled = true;
    try {
      const { bakiye, mesaj } = await istek("/api/bakiye/yukle", "POST", { tutar: form.elements.tutar.value });
      bakiyeGoster(bakiye);
      bildir(`${mesaj} Güncel bakiye ${para(bakiye)}.`, true);
      form.reset();
      await hareketleriGoster();
    } catch (hata) {
      bildir(hata.message);
    } finally {
      dugme.disabled = false;
    }
  });
  await hareketleriGoster();
}

function puaniGoster(panel, puan, yorum) {
  panel.querySelector("form")?.remove();
  panel.append(eleman("strong", `Değerlendirildi · ${puan}/5`));
  if (yorum) panel.append(eleman("p", yorum, "yardim"));
}

function degerlendirmeKarti(menu) {
  const panel = eleman("article", null, "panel");
  panel.append(eleman("h2", `${menu.yemekhane} · ${menu.ogun}`));
  panel.append(eleman("p", gun(menu.tarih), "soluk"));
  if (menu.puan !== null) {
    puaniGoster(panel, menu.puan, menu.yorum);
    return panel;
  }
  const form = eleman("form", null, "deger-form");
  const puan = eleman("select");
  puan.id = `puan-${menu.menu_id}`;
  puan.required = true;
  puan.append(new Option("Seçin", ""));
  for (let sayi = 1; sayi <= 5; sayi++) puan.append(new Option(sayi, sayi));
  const yorum = eleman("textarea");
  yorum.id = `yorum-${menu.menu_id}`;
  yorum.maxLength = 500;
  yorum.rows = 2;
  const puanEtiketi = eleman("label", "Puan");
  puanEtiketi.htmlFor = puan.id;
  const yorumEtiketi = eleman("label", "Yorum (isteğe bağlı)");
  yorumEtiketi.htmlFor = yorum.id;
  const dugme = eleman("button", "Değerlendirmeyi gönder", "dugme");
  form.append(puanEtiketi, puan, yorumEtiketi, yorum, dugme);
  panel.append(form);
  form.addEventListener("submit", async (olay) => {
    olay.preventDefault();
    dugme.disabled = true;
    try {
      const { mesaj } = await istek("/api/degerlendirmeler", "POST", {
        menu_id: menu.menu_id, puan: puan.value, yorum: yorum.value,
      });
      puaniGoster(panel, puan.value, yorum.value.trim());
      bildir(mesaj, true);
    } catch (hata) {
      bildir(hata.message);
      dugme.disabled = false;
    }
  });
  return panel;
}

async function degerlendirmeler() {
  const { degerlendirmeler } = await istek("/api/degerlendirmeler");
  document.querySelector("#degerlendirmeler").replaceChildren(...(degerlendirmeler.length
    ? degerlendirmeler.map(degerlendirmeKarti)
    : [eleman("p", "Değerlendirebileceğiniz kullanılmış bir menü yok.", "panel bos")]));
}

baslat({ rezervasyonlar, bakiye, degerlendirme: degerlendirmeler }[document.body.dataset.sayfa]);
