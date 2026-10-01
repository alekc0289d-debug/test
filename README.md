# eMaktab Worker + Ro'yxatdan o'tish API

Bu faqat worker qismi — Telegram bot BU YERDA YO'Q, alohida zipda
(`bot.zip`). Ikkalasi ham bitta Firebase bazasiga ulanadi, shuning
uchun `.env` dagi `FIREBASE_CREDENTIALS`(_JSON) va ayniqsa
`EMAKTAB_ENC_KEY` bot bilan **bir xil** bo'lishi shart.

## O'rnatish

    pip install -r requirements.txt
    cp .env.example .env   # to'ldiring

Kalitlar:

    python -c "import secrets; print(secrets.token_hex(32))"   # EMAKTAB_ENC_KEY
    python -c "import secrets; print(secrets.token_urlsafe(32))"  # API_ADMIN_TOKEN

## Ishga tushirish (mahalliy)

| Nima | Buyruq |
|------|--------|
| Bitta o'quvchi (test) | `python main.py --test --student-id student_abc123` |
| Navbatni bir marta | `python main.py --once` |
| Soatlik worker + captcha tekshiruvi | `python main.py` |
| API server | `python api_server.py` |

## Railway'ga joylash

Bu qism uchun Railway'da **BITTA xizmat YETARLI** — `api_server.py`
o'zi ichida hammasini qiladi: ro'yxatdan o'tish API'si, soatlik sync
va (yangi) captcha javoblarini 3 daqiqada bir tekshirish. Alohida
`main.py` xizmatini qo'shish shart EMAS.

1. Repo'ni GitHub'ga push qiling, Railway → New Project → Deploy from
   GitHub repo.
2. **Settings → Deploy → Custom Start Command**: `python api_server.py`
3. **Settings → Networking → Generate Domain** — sayt shu URL'ga
   murojaat qiladi (`VITE_API_URL`).
4. Variables bo'limiga `.env.example` dagi hamma o'zgaruvchini kiriting
   (bot bilan BIR XIL Firebase va `EMAKTAB_ENC_KEY`).
5. Chrome/Selenium uchun qo'shimcha sozlash kerak bo'lishi mumkin —
   Railway Nixpacks odatda Chromium'ni o'zi topadi, lekin xato chiqsa
   ayting, birga hal qilamiz.

`main.py` shu bilan birga zipda qoladi — Railway'ga qo'ymasangiz ham
bo'ladi, faqat mahalliy/qo'lda ishlatish uchun kerak bo'lishi mumkin
(`--test`, `--once`, `--captcha` bayroqlari; batafsili yuqorida).

Diqqat: Railway'ning bepul sinovi (~$5 kredit) 30 kunda tugaydi.
