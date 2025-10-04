
> [!WARNING]  
> Сделайте резервную копию ядра перед манипуляциями с активами

# Kuma Assets Archiver

Скрипт для архивирования **assets** (активов) в **Kaspersky Unified Monitoring and Analysis Platform (KUMA)**.  
Позволяет архивировать активы, игнорируя ограничение KUMA: [Активы, добавленные вручную в веб-интерфейсе или с помощью API, не архивируются.](https://support.kaspersky.com/help/KUMA/4.0/ru-RU/263817.htm)


## Требования

- KUMA 4.0 без HA ядра
- python 3.7+


## Использование

1. Создайте API токен с правами на: 
- /users/whoami
- /assets

2. Подготовьте KUMA Core:

Скачайте репозиторий и установите зависимости
```
git clone https://github.com/KUMA-Community/kuma-assets-archiver.git && cd kuma-assets-archiver && pip install -r requirements.txt
```

3. Запустите скрипт

```
python3 main.py --address <core ip/core fqdn> --port 7223 --token <api-token> --days_to_archive 45 --db <db path>
```

```
$ python3 main.py -h

usage: main.py [-h] [--address ADDRESS] [--port PORT] [--token TOKEN] [--days_to_archive DAYS_TO_ARCHIVE] [--db DB]

kuma assets archiver

options:
  -h, --help            show this help message and exit
  --address ADDRESS     kuma core ip/fqdn
  --port PORT           kuma public api port
  --token TOKEN         api token
  --days_to_archive DAYS_TO_ARCHIVE
                        days to archive
  --db DB               kuma sqlite db
```

4. Автоматизация  


Вы можете автоматизировать выполнение этого скрипта через cron или systemd timer

