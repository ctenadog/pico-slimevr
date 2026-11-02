# pico-slimevr

### ⬇️ [Скачать pico-slimevr.bat](https://github.com/ctenadog/pico-slimevr/raw/main/pico-slimevr.bat)

Простой файл-лаунчер для Windows. Двойной клик — и всё. **Python не нужен:**
`.bat` сам скачает готовый `pico-slimevr.exe` и запустит его.
Инструкция: [ЗАПУСК.md](ЗАПУСК.md).

---

Настройка **PICO Motion Trackers** так, чтобы они работали через **SlimeVR Server**
(как обычные Slime-трекеры), а не только как «сырые» Vive-трекеры в SteamVR.

## Как это вообще работает (важно прочитать)

Протокол PICO-трекеров закрытый. Сторонняя программа не может забрать данные
с трекеров напрямую. Поэтому «сделать как SlimeVR» — это не написать новый
драйвер, а правильно соединить уже существующие звенья:

```
PICO Motion Trackers (пояс + щиколотки)
        │  шлем PICO
        ▼
PICO Connect (ПК)         ── отдаёт трекеры в SteamVR как эмулированные Vive-трекеры
        ▼
SteamVR                   ── видит трекеры (Vive Tracker)
        ▼
SlimeVR Feeder App        ── забирает позиции из SteamVR и передаёт в SlimeVR Server
        ▼
SlimeVR Server            ── считает скелет по пропорциям тела
        ├── SteamVR-драйвер SlimeVR  → эмулирует Slime-трекеры в SteamVR
        └── VRChat OSC               → трекеры напрямую в VRChat
```

Итог: игра видит трекеры как SlimeVR, со скелетом и авто-пропорциями — то,
что вы и хотели. Ниже — что поставить и как это настроить.

> Нужна короткая пошаговая инструкция «что делает и как запустить»?
> Смотрите **[ЗАПУСК.md](ЗАПУСК.md)**. Подробная схема и список изменяемых
> файлов — командой `pico-slimevr --explain`.

## Что нужно установить

1. **PICO Connect** (стример PICO для ПК) — официальный сайт PICO.
2. **SteamVR** — Steam → Library → Tools → SteamVR. Запустить один раз.
3. **SlimeVR Server** — установщик с <https://slimevr.dev>.
   При установке оставьте включёнными галочки **SteamVR Driver** и
   **SlimeVR Feeder App** — они и делают всю магию.

## Быстрый старт с этим инструментом

Инструмент проверяет цепочку и чинит то, что можно починить безопасно
(правка `settings.json`, регистрация драйвера SlimeVR).

```bash
pip install -e .
pico-slimevr            # проверить состояние
pico-slimevr --dry-run  # показать, что будет изменено
pico-slimevr --fix      # применить безопасные исправления
pico-slimevr --gui      # графический интерфейс (Windows)
```

Что делает `--fix`:

* включает `bodyTracking = true` в
  `%APPDATA%\PICO Connect\settings.json` (перед правкой делает `.bak`);
* регистрирует драйвер SlimeVR в SteamVR (`vrpathreg adddriver`, а если он
  недоступен — добавляет путь в `openvrpaths.vrpath`);
* выставляет роли трекеров (`TrackerRole_Waist`, `..._LeftFoot`,
  `..._RightFoot`, колени, грудь) в `steamvr.vrsettings`.

Дополнительные команды:

```bash
pico-slimevr --explain                     # как всё работает (схема + список файлов)
pico-slimevr --roles                       # только роли трекеров
pico-slimevr --roles WAIST,LEFT_FOOT       # только выбранные точки
pico-slimevr --ports                       # проверить порты VRChat OSC (9000/9001)
pico-slimevr --osc-profile vrchat_osc.json # записать шаблон настроек OSC
```

## Как удалить (откат всех изменений)

Инструмент меняет только три файла, и перед каждой правкой кладёт рядом копию
`.bak`. Команда `--uninstall` возвращает эти файлы в исходное состояние:

```bash
pico-slimevr --uninstall --dry-run   # посмотреть, что будет откачено
pico-slimevr --uninstall             # откатить (файлы восстанавливаются из .bak)
pico-slimevr --uninstall --purge-backups   # откатить и удалить сами .bak
```

Что делает откат:

* `%APPDATA%\PICO Connect\settings.json` — восстанавливается из `.bak`
  (если бэкапа нет — просто ставится `bodyTracking = false`);
* `%LOCALAPPDATA%\openvr\openvrpaths.vrpath` — путь к драйверу SlimeVR
  убирается (плюс `vrpathreg removedriver`);
* `<Steam>\config\steamvr.vrsettings` — роли трекеров восстанавливаются из
  `.bak` или удаляются наши записи.

Полное удаление самой программы:

```bash
pip uninstall pico-slimevr
```

Сами PICO Connect, SteamVR и SlimeVR инструмент не устанавливает и не удаляет —
их удаляют их собственными деинсталляторами.

Чего инструмент **не** делает (и почему):

* не копирует профили `swift` — они защищены лицензией PICO, их нужно
  положить вручную (см. ниже);
* не трогает прошивку и не читает данные трекеров напрямую.

## Запуск без установки: pico-slimevr.bat

В корне репозитория лежит `pico-slimevr.bat` — простой лаунчер для Windows.
Скачайте его, положите в любую папку и запустите (двойным кликом или из
PowerShell):

```powershell
.\pico-slimevr.bat              # проверить
.\pico-slimevr.bat --fix        # починить
.\pico-slimevr.bat --gui        # окошко
```

Что делает `.bat`:

* один раз скачивает готовый `pico-slimevr.exe` из раздела Releases
  (нужен интернет) и запускает его;
* **Python не требуется**;
* если скачать не удалось, но Python всё же установлен — запускает через него.

Это обычный текстовый файл — его можно открыть в блокноте и прочитать.

Готовый `.exe` можно скачать и напрямую:
`https://github.com/ctenadog/pico-slimevr/releases/latest/download/pico-slimevr.exe`

## Сборка .exe для Windows

Сборка идёт автоматически в GitHub Actions при каждом пуше в `main` и
публикуется в релиз `latest` (см. `.github/workflows/build.yml`).

Локально (на Windows):

```bash
pip install -e . pyinstaller
python packaging/build.py     # → dist/pico-slimevr.exe
```

## Ручные шаги, которые нужно сделать один раз

### 1. Откалибровать трекеры на шлеме

Наденьте трекеры (пояс + 2 на щиколотки), включите их, откройте на шлеме
приложение Motion Tracker и пройдите калибровку. Для ПК это обязательно —
на ПК трекеры не калибруются сами.

### 2. Включить передачу тела в PICO Connect

`%APPDATA%\PICO Connect\settings.json` → `"bodyTracking": true`
(это и делает `pico-slimevr --fix`).

### 3. Профили `swift` (если трекеры не видны в играх)

В каталоге
`C:\Program Files\PICO Connect\openvr_driver\resources\input\`
должен быть `pico_tracker_profile.json` и папка `swift` с профилями
(`pico_tracker_left_foot_profile.json`, `..._right_foot_...`,
`..._waist_...`, `..._chest_...`, `..._left_knee_...`,
`..._right_knee_...`, `vive_tracker_handed_profile.json` и др.).

Если папки/файлов нет — SteamVR не увидит ноги и пояс. Возьмите их из
профильного гайда сообщества (например, репозиторий
`Elbios/pico-motion-trackers-steamvr-guide`) и скопируйте в `...\input\swift\`.

### 4. Убедиться, что SlimeVR видит трекеры PICO

1. Запустите **SteamVR**.
2. Запустите **SlimeVR Server**. Feeder App подхватит Vive-трекеры из SteamVR
   и отдаст их в SlimeVR.
3. В SteamVR: **Settings → Manage Add-ons** — драйвер `SlimeVR` включён.
4. В SlimeVR: **Settings → SteamVR Trackers** — включите нужные виртуальные
   трекеры (Waist, Feet; Chest/Knees при необходимости).
5. В SteamVR: **Settings → Controllers → Manage Trackers** — задайте роли
   трекерам (Waist, Left foot, Right foot). Это можно сделать и командой
   `pico-slimevr --roles`, но менять роли нужно при выключенном SteamVR.
6. Сделайте **Reset** в SlimeVR, стоя прямо.

### 5. Игра

* **VRChat (PC)**: включите OSC-трекеры в SlimeVR ИЛИ используйте
  SteamVR-драйвер SlimeVR; в игре нажмите «Calibrate FBT» и сделайте T-pose.
* Другие игры: убедитесь, что у игры включён FBT; лишние трекеры лучше
  отключить — многие игры ждут только стопы (и иногда пояс).

## Частые проблемы

| Симптом | Причина / решение |
|---|---|
| Трекеры не видны в SteamVR | Не включён `bodyTracking`; нет профилей `swift`; не откалиброваны на шлеме |
| Видны в SteamVR, но игра их игнорирует | У игры нет FBT или включены лишние трекеры — оставьте только Waist/Feet |
| В SlimeVR трекеров нет | Не установлен/не запущен Feeder App; драйвер SlimeVR выключен в Add-ons |
| Пояс «уезжает» при сидении | Сделайте Reset в SlimeVR и калибровку FBT в игре |
| Неверная высота пола в ПК VR | Откалибруйте пол через OVR Advanced Settings |

## Структура проекта

```
src/pico_slimevr/
  paths.py     — поиск путей PICO Connect / SteamVR / SlimeVR / vrsettings
  detect.py    — проверки без изменений (scan + checks)
  actions.py   — безопасные исправления (idempotent, с бэкапами)
  trackers.py  — роли трекеров в steamvr.vrsettings
  osc.py       — шаблон и порты VRChat OSC
  doctor.py    — scan / run / apply_roles / отчёт
  cli.py       — командная строка
  gui.py       — графический интерфейс (Tkinter)
packaging/     — PyInstaller spec и сборка .exe
tests/         — тесты на реальной временной файловой системе
pico-slimevr.bat — лаунчер для Windows (скачивает и запускает .exe)
ЗАПУСК.md      — пошаговая инструкция «что делает и как запустить»
```

## Тесты

```bash
pip install pytest
python -m pytest -q
```

Тесты работают на настоящей временной файловой системе (не моки): создают
макет Windows-путей и проверяют детект, исправления, идемпотентность и `--dry-run`.
