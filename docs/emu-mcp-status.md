# Статус: управляемый эмулятор DS (MCP). Обновляется после каждого чекпоинта

План: `docs/emu-mcp-plan.md`. Исходники melonDS: `~/Developer/tools/melonDS` (тег 1.1, коммит b86390e, вне проекта, в git проекта не входят).

## ЭТАП 0 — разведка: ВЫПОЛНЕН (2026-10-17). Ничего не собиралось и не запускалось.
- [x] 0.1 Клон melonDS 1.1 (shallow) в `~/Developer/tools/melonDS`.
- [x] 0.2 API ядра подтверждён по исходникам тега 1.1 (не master):
  - `NDS(NDSArgs&&, void* userdata)`; `NDSArgs` (Args.h): ARM9/ARM7 BIOS (по умолчанию FreeBIOS), Firmware, JIT (std::optional, nullopt = выключен), BitDepth/Interpolation/OutputSampleRate, GDB (optional), Renderer3D (по умолчанию SoftRenderer).
  - Запуск: `nds->SetNDSCart(...)` (NDSCart::ParseROM), `nds->SetupDirectBoot(romname)` (как фронтенд при `Emu.DirectBoot`), `nds->Start()`, затем `u32 RunFrame()` в цикле.
  - Ввод: `SetKeyMask(u32)` (активный низкий уровень, 0xFFF = ничего не нажато), `TouchScreen(x,y)`, `ReleaseScreen()`, `SetLidClosed`.
  - Экраны: `nds->GPU.Framebuffer[nds->GPU.FrontBuffer][0|1]` — 256×192 u32 каждый (так читает Qt-фронтенд в Screen.cpp: [0] верх, [1] низ; перестановку по POWCNT делает сам GPU).
  - Память: `ARM9Read8/16/32`, `ARM9Write*`, `ARM7Read*` (публичные).
  - Сейвстейты: `nds->DoSavestate(Savestate*)`; загрузка из файла = прочитать файл в буфер, `Savestate(buffer, size, false)`, `DoSavestate` (как `EmuInstance::loadState`); сохранение = `Savestate state; DoSavestate(&state);` записать `Buffer()/Length()`.
  - Сейв рома: `SetNDSSave(data,len)`, `GetNDSSave()`; запись наружу — через Platform::WriteNDSSave.
- [x] 0.3 Как Qt-фронтенд создаёт NDS (EmuInstance.cpp ~1285–1475): `loadFirmware` / `generateFirmware(type)` + `customizeFirmware` (язык/имя/дата рождения из `[Instance0.Firmware]` melonDS.toml: язык 1, «melonDS»), NDSArgs{ARM9BIOS, ARM7BIOS, Firmware, JITArgs, BitDepth, Interpolation, freq, GDB}, `new NDS(std::move(ndsargs), this)`; при DirectBoot — `SetupDirectBoot(baseROMName)`, потом `Start()`. Настройки melonDS.toml для повторения: DirectBoot=true, ExternalBIOS выключен (FreeBIOS), ConsoleType=0, JIT выключен, Renderer=0 (софт), язык 1.
- [x] 0.4 CMake: цель `core` — `add_library(core STATIC ...)` в `src/CMakeLists.txt`; единственная внешняя зависимость — вложенный `teakra` (в дереве); при `-DBUILD_QT_SDL=OFF` Qt/SDL не нужны. Опции: `ENABLE_JIT` (cmake_dependent, можно OFF), `ENABLE_OGLRENDERER=OFF`, `ENABLE_GDBSTUB` ON (можно OFF).
- [x] 0.5 Совместимость сейвстейтов: версия формата в исходниках `SAVESTATE_MAJOR 13, MINOR 0`; наш `tools/rebuilt.ml1` (заголовок MELN) — **13.0, совпадает**. Есть и свежий `build/fsar-test.ml1` (слот 1 текущего рома).
- **Новое, чего не было в плане:** ядро требует от «фронтенда» реализации ~45 функций `Platform::` (Platform.h): файлы (OpenFile/FileRead/…), Log, потоки/семафоры/мьютексы, Sleep/время, WriteNDSSave/WriteFirmware/WriteDateTime, MP_*/Net_*, Camera_*, Mic_*, AAC_*, Addon_*, DynamicLibrary_*, SignalStop. Для безголового драйвера это заглушки на стандартной библиотеке C++ (≈150–250 строк), не блокер.
- Итог этапа 0: **решение — идти на этап 1** (драйвер на `core`). Известные риски: (1) сборка `core` и teakra на macOS arm64 (проверим на 1.1), (2) совпадение состояния на GUI-ромe (RTC/firmware/имя), (3) вход в сцены после пересборки рома (этап 3).

## ЭТАП 1 — безголовый драйвер: В РАБОТЕ (разрешён пользователем 2026-10-17)
Чекпоинты этапа 1 (будут отмечены по ходу):
- [x] 1.1 cmake `-G Ninja -DBUILD_QT_SDL=OFF -DENABLE_JIT=OFF -DENABLE_OGLRENDERER=OFF -DENABLE_GDBSTUB=OFF -DENABLE_LTO_RELEASE=OFF` в `~/Developer/tools/melonDS/build`; `ninja core teakra` собрал `src/libcore.a` и `src/teakra/src/libteakra.a` за 9 с (macOS arm64, CMake 4.4.3)
- [x] 1.2 `tools/melonds-ctl/main.cpp` (+`build.sh`): Platform-заглушки + создание NDS + загрузка рома + run/keys/touch/shot/save_state/load_state/read9/find. Собрался и слинковался с первой попытки (`tools/melonds-ctl/build.sh`)
- [x] 1.3 `build/fsar-test.nds` грузится и идёт безголово: на кадре 3600 интро-ролик (мост, надписи TRUTH/perplexity), `dumps/emu/t3.png`. (До русского текста ещё нужно дойти нажатием Start — этап 2)
- [x] 1.4 **ПРОЙДЕНО:** `load_state` старого GUI-сейвстейта `tools/rebuilt.ml1` (копия) на `rebuilt.nds` загружается без ошибок; через 300 кадров верхний экран — диалог «I'm Sumio Mondo.», нижний — карта Lost Pass; `find` нашёл строку по адресу `0x022EE754` (ровно как в AGENTS.md). Совместимость сейвстейтов GUI→драйвер подтверждена. Скрины: `dumps/emu/s2.png`
- [~] 1.5 Скорость (интерпретатор, JIT выключен): 175–335 кадров/с (интро 335, сцены с 3D 157–205) — это 3–5× реального времени (60 fps). Достаточно, но не рекорд; при необходимости можно собрать с JIT (ENABLE_JIT, arm64)

## ЭТАП 2 — MCP-сервер: ВЫПОЛНЕН (2026-10-17), ждёт перезапуска Claude Code
- [x] 2.1 `tools/venv/bin/pip install "mcp<2"` (mcp 1.30.0; ветка 2.x переименовала FastMCP в MCPServer, API другой — используем 1.x)
- [x] 2.2 `scripts/emu_mcp.py` (FastMCP, stdio): инструменты `emu_open`, `emu_run`, `emu_press`, `emu_touch`, `emu_screenshot` (картинка PNG в ответе), `emu_load_state`, `emu_save_state`, `emu_read_mem`, `emu_find_text`, `emu_script` (макросы из команд драйвера)
- [x] 2.3 Проверено реальным MCP-клиентом (`mcp.client.stdio`): инструменты видны, `emu_open` + `emu_run 900` + `emu_press Start` + `emu_screenshot` вернули ImageContent (PNG), экран «Нажмите START» (`dumps/emu/mcp_test.png`); `emu_find_text` отвечает
- [x] 2.4 `claude mcp add --scope project fsar-emu -- tools/venv/bin/python -I scripts/emu_mcp.py` → `.mcp.json` в корне проекта
- [ ] 2.5 Перезапустить Claude Code в этом проекте (/mcp покажет fsar-emu), затем в новом сеансе вызвать `emu_open` и `emu_screenshot`

## Что дальше
- Этап 3: попадание в нужные сцены (сейвстейты-вехи, макросы ввода, поведение после пересборки рома).

## Журнал
- 2026-10-17: пользователь одобрил этап 0 «с чекпоинтами и сохранением статуса»; выполнены 0.1–0.5.
- 2026-10-17: пользователь одобрил этап 1; 1.1 выполнен (libcore.a собран за 9 с, ошибок нет).
- 2026-10-17: этап 1 выполнен: драйвер собран, ром загружается, GUI-сейвстейт загружается, кадр совпал. Исходник драйвера — `tools/melonds-ctl/` (в git: main.cpp, build.sh; бинарь не в git).
- 2026-10-17: этап 2 выполнен: сервер написан, проверен клиентом MCP, зарегистрирован в .mcp.json. Нужен перезапуск Claude Code.
