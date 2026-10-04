# Selenium (Chrome) Railway'ning standart Python muhitida ishlamaydi —
# u yerda Chrome brauzerining o'zi umuman o'rnatilmagan. Shuning uchun
# Railway'ga "oddiy Python" emas, balki shu Dockerfile orqali, Chrome
# oldindan o'rnatilgan holda joylaymiz.
#
# Railway bu faylni avtomatik topadi va ishlatadi (Nixpacks o'rniga).
# Agar Railway xizmat sozlamalarida "Custom Start Command" qo'yilgan
# bo'lsa, SHUNI O'CHIRING — aks holda u shu fayldagi CMD'ni almashtirib
# yuboradi va Chrome muhiti ishlatilmay qoladi.

FROM python:3.13-slim

# Google Chrome (stable) + kerakli umumiy kutubxonalar
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget gnupg ca-certificates fonts-liberation \
        libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
        libgbm1 libasound2 libxkbcommon0 libxcomposite1 libxdamage1 \
        libxfixes3 libxrandr2 libu2f-udev libvulkan1 xdg-utils \
    && wget -q -O /usr/share/keyrings/google-chrome.gpg.key \
        https://dl.google.com/linux/linux_signing_key.pub \
    && gpg --dearmor --output /usr/share/keyrings/google-chrome.gpg \
        /usr/share/keyrings/google-chrome.gpg.key \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* /usr/share/keyrings/google-chrome.gpg.key

ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROME_HEADLESS=true

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "api_server.py"]
