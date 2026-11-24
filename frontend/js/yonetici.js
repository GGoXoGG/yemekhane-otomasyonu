import { baslat, bildir, eleman, gun, istek, secenekler, tablo } from "./ortak.js";

const secim = document.querySelector("#menu-sec");
const form = document.querySelector("#menu-formu");
const yemekSecimi = document.querySelector("#yemek-secimi");
const menuler = new Map();
let seciliMenu;

function secimiYaz() {
  secim.replaceChildren(new Option("Yeni menü oluştur", ""));
  for (const menu of menuler.values()) {
    secim.append(new Option(`${menu.tarih} · ${menu.yemekhane} · ${menu.ogun}`, menu.id));
  }
}

function formuDoldur() {
  seciliMenu = menuler.get(Number(secim.value));
  form.reset();
  document.querySelector("#menu-form-basligi").textContent = seciliMenu ? "Menüyü düzenle" : "Yeni menü";
  document.querySelector("#menu-kimligi").disabled = Boolean(seciliMenu);
  if (!seciliMenu) return;
  for (const ad of ["tarih", "yemekhane_id", "ogun_id", "ogrenci_fiyati", "personel_fiyati"]) {
    form.elements[ad].value = seciliMenu[ad];
  }
  for (const kutu of yemekSecimi.querySelectorAll("input")) {
    kutu.checked = seciliMenu.yemek_idleri.includes(Number(kutu.value));
  }
}

async function raporYukle() {
  try {
    const { raporlar } = await istek("/api/yonetici/raporlar");
    const satirlar = raporlar.map((kayit) => [
      gun(kayit.tarih), kayit.yemekhane, kayit.ogun, kayit.kapasite, kayit.rezerve, kayit.bos_yer,
      `%${Number(kayit.doluluk_yuzde).toLocaleString("tr-TR")}`,
      kayit.ortalama_puan === null ? "—" : Number(kayit.ortalama_puan).toLocaleString("tr-TR"),
      kayit.oy_sayisi,
    ]);
    document.querySelector("#raporlar").replaceChildren(satirlar.length
      ? tablo(["Tarih", "Yemekhane", "Öğün", "Kapasite", "Rezerve", "Boş yer", "Doluluk", "Ort. puan", "Oy"], satirlar)
      : eleman("p", "Henüz raporlanacak menü yok.", "bos"));
  } catch (hata) {
    bildir(hata.message);
  }
}

async function menuKaydet(olay) {
  olay.preventDefault();
  const dugme = form.querySelector("button");
  const veri = Object.fromEntries(new FormData(form));
  const secilenYemekler = Array.from(yemekSecimi.querySelectorAll("input:checked"), (kutu) => Number(kutu.value));
  delete veri.yemek;
  const duzenlenen = seciliMenu;
  dugme.disabled = secim.disabled = true;
  try {
    const adres = "/api/yonetici/menuler" + (duzenlenen ? `/${duzenlenen.id}` : "");
    const sonuc = await istek(adres, duzenlenen ? "PUT" : "POST", { ...veri, yemek_idleri: secilenYemekler });
    const menu = duzenlenen || {
      id: sonuc.menu_id, tarih: veri.tarih, yemekhane_id: Number(veri.yemekhane_id), ogun_id: Number(veri.ogun_id),
      yemekhane: form.elements.yemekhane_id.selectedOptions[0].text,
      ogun: form.elements.ogun_id.selectedOptions[0].text,
    };
    menuler.set(menu.id, {
      ...menu, ogrenci_fiyati: veri.ogrenci_fiyati, personel_fiyati: veri.personel_fiyati, yemek_idleri: secilenYemekler,
    });
    secimiYaz();
    secim.value = menu.id;
    formuDoldur();
    bildir(sonuc.mesaj, true);
    await raporYukle();
  } catch (hata) {
    bildir(hata.message);
  } finally {
    dugme.disabled = secim.disabled = false;
  }
}

baslat(async () => {
  const [yerler, ogunler, yemekler, liste] = await Promise.all(
    ["/api/yemekhaneler", "/api/ogunler", "/api/yonetici/yemekler", "/api/yonetici/menuler"].map((url) => istek(url)),
  );
  secenekler(form.elements.yemekhane_id, yerler.yemekhaneler, "Yemekhane seçin");
  secenekler(form.elements.ogun_id, ogunler.ogunler, "Öğün seçin");
  for (const yemek of yemekler.yemekler) {
    const label = eleman("label");
    const kutu = eleman("input");
    kutu.type = "checkbox";
    kutu.name = "yemek";
    kutu.value = yemek.id;
    label.append(kutu, eleman("span", yemek.ad));
    yemekSecimi.append(label);
  }
  for (const menu of liste.menuler) menuler.set(menu.id, menu);
  secimiYaz();
  secim.addEventListener("change", formuDoldur);
  form.addEventListener("submit", menuKaydet);
  document.querySelector("#rapor-yenile").addEventListener("click", raporYukle);
  await raporYukle();
});
