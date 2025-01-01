# Çok İşlevli Discord Bot

Bu çok işlevli Discord botu aşağıdaki özellikleri içerir:

## Özellikler
- Gelişmiş moderasyon araçları
- Kullanıcı profil sistemi
- Ekonomi ve oyun özellikleri
- Çeviri ve anket araçları

## 🛡️ Moderasyon Özellikleri
- Otomatik spam koruması
- Küfür/kötü söz filtresi
- Uyarı sistemi
- Anti-raid koruması
- Detaylı log sistemi

## 🎮 Eğlence ve Oyunlar
- Taş-Kağıt-Makas
- Blackjack
- Slot makinesi
- Sayı tahmin oyunu

## 💰 Ekonomi Sistemi
- Mağaza
- Pazar yeri

## 📊 Profil ve Seviye Sistemi
- XP ve seviye sistemi
- Başarımlar
- Detaylı profil kartları

## 🌐 Yardımcı Özellikler
- Çeviri sistemi
- Anket oluşturma
- Kripto para takibi
- Döviz kurları

## 📝 Gereksinimler
- Python 3.8+
- discord.py v2.3.2
- Tüm gereksinimler için `requirements.txt`'i inceleyin

## ⚙️ Kurulum

1. Python 3.8+ sürümünü yükleyin
2. Sanal ortam oluşturun: `python -m venv venv`
3. Sanal ortamı etkinleştirin
4. Gereksinimleri yükleyin: `pip install -r requirements.txt`
5. `.env` dosyasına Discord bot tokeninizi ekleyin

## 🔧 Çalıştırma
```bash
python main.py
```

## 🔧 Yapılandırma

Bot ayarlarını aşağıdaki dosyalardan yapılandırabilirsiniz:
- `config/antiraid.json`: Anti-raid ayarları
- `config/logging.json`: Log sistemi ayarları
- `config/banned_words.json`: Yasaklı kelimeler

Not: Toplam 40 dan fazla discord slash Komutu Vardır. Ve Daha Fazla Küfür Engellemek İçin config Klasöründeki banned_words.json dosyasına daha çok küfür ekleyebilirsiniz.

## 🤝 Katkıda Bulunma

1. Fork'layın
2. Feature branch oluşturun
3. Değişikliklerinizi commit'leyin
4. Branch'inizi push'layın
5. Pull Request açın

## 📄 Lisans

Bu proje GPL-3.0 lisansı altında lisanslanmıştır. Daha fazla bilgi için `LICENSE` dosyasına bakın.
