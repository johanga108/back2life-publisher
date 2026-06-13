# Подключение Telegram, VK и Instagram

Не отправляйте токены в чат. Храните их только локально в файле `.env`.

## Подготовка файла

В терминале из папки проекта:

```bash
cp .env.example .env
```

После этого откройте `.env` и заполните значения по инструкции ниже.

## Telegram

Что потребуется:

- бот;
- канал;
- право бота публиковать сообщения;
- `TELEGRAM_BOT_TOKEN`;
- `TELEGRAM_CHAT_ID`.

Что сделать:

1. Откройте [@BotFather](https://t.me/BotFather).
2. Выполните команду `/newbot` и сохраните выданный токен.
3. Добавьте бота администратором в Telegram-канал.
4. Разрешите боту публиковать сообщения.
5. Для публичного канала используйте его адрес, например `@back2life`.
6. Для закрытого канала нужен числовой ID вида `-100...`.
7. Заполните:

```dotenv
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=@channelusername
```

## VK

Автопубликация настроена на стену сообщества, не на личную страницу. Для
картинок используется официальный REST API Postmypost: сообщество уже
подключено к сервису, а отдельный пользовательский токен VK не нужен.

Что потребуется:

- сообщество VK;
- подключенное к Postmypost сообщество;
- персональный токен Postmypost.

Что сделать:

1. Войдите в [Postmypost API](https://api.postmypost.io/).
2. Откройте настройки аккаунта.
3. Перейдите в раздел `Access Tokens`.
4. Создайте или скопируйте персональный токен.
5. Заполните:

```dotenv
POSTMYPOST_ACCESS_TOKEN=...
```

Если в Postmypost подключено несколько проектов или несколько сообществ VK,
дополнительно заполните `POSTMYPOST_PROJECT_ID` и `POSTMYPOST_VK_ACCOUNT_ID`.

## Instagram

Автопубликация через официальный API работает только для профессионального
аккаунта Instagram: `Business` или `Creator`. Личный аккаунт нужно переключить
на профессиональный.

Instagram API сам скачивает картинку перед публикацией. Скрипт автоматически
загружает только текущий JPEG в Cloudinary и передает Instagram публичную
HTTPS-ссылку. Будущие посты заранее не раскрываются.

Что потребуется:

- профессиональный Instagram-аккаунт;
- приложение в [Meta for Developers](https://developers.facebook.com/apps/);
- Instagram API with Instagram Login;
- права `instagram_business_basic` и
  `instagram_business_content_publish`;
- `IG_ACCESS_TOKEN`;
- `IG_USER_ID`;
- бесплатный аккаунт Cloudinary.

Что сделать:

1. Переключите Instagram-аккаунт на `Business` или `Creator`, если он личный.
2. Создайте приложение в [Meta for Developers](https://developers.facebook.com/apps/).
3. Подключите продукт Instagram API и настройте Instagram Login.
4. Добавьте профессиональный Instagram-аккаунт и выдайте приложению права
   `instagram_business_basic` и `instagram_business_content_publish`.
5. Получите токен и ID Instagram-пользователя в настройках API.
6. Создайте бесплатный аккаунт в [Cloudinary](https://cloudinary.com/).
7. На странице ключей найдите `Cloud name`, `API Key` и `API Secret`.
8. Заполните:

```dotenv
IG_ACCESS_TOKEN=...
IG_USER_ID=...
IG_API_VERSION=v25.0
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

Токен Instagram нужно обновлять до истечения срока действия. При ошибке токена
автоматизация остановится на текущем посте и не продвинет очередь дальше.

## Facebook: пропускаем

Автопубликация через официальный API работает для Facebook Page. Публикация в
личный профиль через API недоступна.

Сейчас Facebook не входит в обязательную очередь. Для личного профиля
автопубликация через API недоступна. Подключить Facebook можно позже, если
появится Facebook Page.

## Проверка без публикации

После заполнения `.env` выполните:

```bash
python3 scripts/publish_next.py --check-config
```

Команда проверит:

- Telegram-бота и канал;
- подключенное к Postmypost сообщество VK;
- Instagram-аккаунт, загрузку JPEG в Cloudinary и доступность HTTPS-ссылки;

Она ничего не публикует.

После успешной проверки можно включить фоновую задачу. Она будет просыпаться
раз в сутки, но отправлять пост только в разрешенные даты из календаря.

## Редактирование будущих постов

Даты публикации, заголовки и тексты находятся во вкладке `Codex` в Google
Sheets. Перед каждым запуском автоматизация скачивает эту вкладку заново.
Поэтому правки в таблице применяются к будущим публикациям автоматически.

Порядок строк менять не нужно: он связан с локальным планом публикаций. У строк
с картинками для Telegram используются квадратные JPEG-копии `1080x1080`, для
Instagram и VK — вертикальные изображения `1080x1350`. Новая серия тоже должна
получить картинки до публикации; пока изображения не привязаны, Instagram
будет пропускать такие строки, потому что лента Instagram требует медиафайл.

## Официальная документация

- [Telegram Bot API: sendPhoto](https://core.telegram.org/bots/api#sendphoto)
- [Postmypost REST API](https://help.postmypost.io/docs/api)
- [Instagram API: Publish Content](https://www.postman.com/meta/instagram/request/ssvfe9s/publish-media)
