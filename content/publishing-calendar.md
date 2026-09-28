# Back2Life publishing calendar

The main Telegram/Instagram queue normally publishes every three days. If the
next calculated date is Sunday, the post moves one day earlier to Saturday, so
future intervals are always two or three days. Published dates are preserved.

All main-queue publications are scheduled for 19:00 Europe/Moscow.

Assumptions:

- Future Sunday dates are skipped by moving them to Saturday.
- Month-end dates are allowed.
- The publisher runs frequently from cron-job.org through GitHub Actions;
  ordinary runs before the scheduled time exit without publishing.
- Dates, titles, and texts are editable in the Google Sheets tab `Codex`;
  that tab is authoritative and future dates in the local JSON calendar mirror
  it, while published dates stay as history.
- Images are local repo assets; Instagram uses 4:5 images and Telegram/VK
  use 1:1 images with the same title style rendered on top.
- The standalone daily Threads queue is separate and is not changed here.

| # | Date | Post | Type |
| --- | --- | --- | --- |
| 01 | 2026-06-08 | Единственный пинцет на 1000 женщин | image |
| 02 | 2026-06-10 | Сначала почувствовать себя | image |
| 03 | 2026-06-12 | Как туалетная бумага стала валютой | image |
| 04 | 2026-06-14 | Устала не от дел | image |
| 05 | 2026-06-16 | День доставки заказов | image |
| 06 | 2026-06-18 | Цель, которую не хочется достигать | image |
| 07 | 2026-06-20 | Как я научилась воровать | image |
| 08 | 2026-06-23 | Маленькие желания | image |
| 09 | 2026-06-26 | Тюремная индустрия красоты | image |
| 10 | 2026-06-30 | Практика в очереди | image |
| 11 | 2026-07-02 | Что меня больше всего удивило в женщинах из 40+ стран | image |
| 12 | 2026-07-05 | Шум как жизнь | image |
| 13 | 2026-07-11 | Кодовые имена охранников | image |
| 14 | 2026-07-13 | Когда накрывает тревогой | image |
| 15 | 2026-07-16 | 56 женщин. 4 душа. 5 часов очереди. | image |
| 16 | 2026-07-20 | Перестать спорить с погодой | image |
| 17 | 2026-07-23 | Как я написала 160 запросов и реально изменила систему | image |
| 18 | 2026-07-27 | Пауза перед ответом | image |
| 19 | 2026-07-30 | Чему меня научила невозможность повлиять на ситуацию | image |
| 20 | 2026-08-03 | Не идеальный режим | image |
| 21 | 2026-08-08 | Работа на кухне как элитная должность | image |
| 22 | 2026-08-11 | Когда не хочется практиковать | image |
| 23 | 2026-08-14 | Мечты | image |
| 24 | 2026-08-17 | Усталость или потеря смысла | image |
| 25 | 2026-08-21 | Шутки | image |
| 26 | 2026-08-24 | Прогулка без цели | image |
| 27 | 2026-08-27 | Обыски | image |
| 28 | 2026-08-31 | Почему «надо собраться» не работает | image |
| 29 | 2026-09-03 | Сны | image |
| 30 | 2026-09-08 | Практика в дороге | image |
| 31 | 2026-09-10 | Кто как помнит о свободе | image |
| 32 | 2026-09-28 | Как я выбираю цель недели | image |
| 33 | 2026-10-01 | Что меня удивило в людях больше всего | image |
| 34 | 2026-10-03 | Что тело знает раньше головы | image |
| 35 | 2026-10-06 | Как я научилась ценить шум собственных детей | image |
| 36 | 2026-10-09 | Не торопить жизнь | image |
| 37 | 2026-10-12 | Аллергия на испанский | image |
| 38 | 2026-10-15 | Быт как практика | image |
| 39 | 2026-10-17 | Путешествие по США в наручниках | image |
| 40 | 2026-10-20 | Фраза, которая возвращает | image |
| 41 | 2026-10-23 | Усталость от усталости | image |
| 42 | 2026-10-26 | Радость требует внимания | image pending |
| 43 | 2026-10-29 | Как не сойти с ума, когда ничего не происходит | image |
| 44 | 2026-10-31 | Контроль или забота | image pending |
| 45 | 2026-11-03 | День уборки | image |
| 46 | 2026-11-06 | Что происходит на живой группе | image pending |
| 47 | 2026-11-09 | Прогулки | image |
| 48 | 2026-11-12 | Не быть эффективной любой ценой | image pending |
| 49 | 2026-11-14 | Пересчёты | image |
| 50 | 2026-11-17 | Перед трудным сообщением | image pending |
| 51 | 2026-11-20 | Средства связи | image |
| 52 | 2026-11-23 | Слышать не только слова | image pending |
| 53 | 2026-11-26 | Дни рождения | image |
| 54 | 2026-11-28 | Как понять, что практика работает | image pending |
| 55 | 2026-12-01 | Укрепление защиты после попыток побега | image |
| 56 | 2026-12-04 | Семейная жизнь как тренажёр внимания | image pending |
| 57 | 2026-12-07 | Не менять себя, а слышать | image |
| 58 | 2026-12-10 | Тренинг личностного роста: как перестать менять себя силой | image pending |
| 59 | 2026-12-12 | Осознанность — это не про спокойствие: что это на самом деле | image pending |
| 60 | 2026-12-15 | Чем коучинг отличается от мотивации и терапии | image pending |
| 61 | 2026-12-18 | Практики благодарности: почему они иногда раздражают и как делать их по-настоящему | image pending |
| 62 | 2026-12-21 | Простые техники саморегуляции для повседневной жизни | image pending |
| 63 | 2026-12-24 | Личностный рост без насилия над собой: как развиваться, не ломая себя | image pending |
