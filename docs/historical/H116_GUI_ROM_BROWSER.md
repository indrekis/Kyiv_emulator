# H116-H1 — Qt ROM-set and declarative-scenario browser

Status: HOST UI integration (not historical hardware verification). The retained
Qt6 frontend and persistent `Kyiv_t` backend are used; no arithmetic or ROM
semantics are implemented here.

## UI workflow

- **Змінна ПЗП** dynamically lists the validated `examples/rom_catalog/sets/*.json`
  catalog sets. The default choice **Лише ROM.txt** preserves the old backend.
- The provenance label explicitly reports `SOURCE_TRANSCRIPTION`,
  `FUNCTIONAL_RECONSTRUCTION`, etc., and the number of missing words in the
  occupied slots. Missing source words must **not** be read as historical zeroes.
- **Приклад** includes the two existing H9/H23 demonstrations and the validated
  declarative C2a scenarios from `examples/rom_scenarios/*.json`. The tooltip
  identifies each scenario's origin/description. A scenario selects its ROM
  set, pinned RAM program, and entry point; it **does not automatically replay
  the C2a oracle**, and does not implement C2b operator-action playback.
  Validated FP scenarios use `LOADFP` and their declared `end_pointer`, entering
  the reconstructed program interpreter at `C=3300` with panel NK `3000` selected.
- **Оновити каталог** reloads disk manifests. New modules/sets/scenarios need
  only the existing `.k41` + JSON data; Qt C++ does not need special cases.
- **Завантажити** for a selected set invokes Python C1a to prepare an
  SHA-pinned ROM image into a new directory under `tempkyiv/`. For a selected
  C2a scenario, C2a validation checks the RAM-program SHA and prepares a
  private verified copy of the program. After all input checks, the GUI
  explicitly replaces the previous persistent backend session and queues `LOAD` or `LOADFP`.
  The backend installs the selected set at CPU initialization and retains
  ordinary `STEP`, `STATE`, `DUMP`, `SETNK`, `CLEARNK`, `SAVE`, `RESTORE`.
- Switching the ROM set intentionally starts a **new CPU session**, with old
  RAM/registers/checkpoint discarded. This is not hardware hot swapping or a
  transaction on an already executing CPU. Invalid catalog input does not
  close the currently running session.
- Manual `.k41` open remains the previous GUI behavior; it does not imply a
  SHA-pinned scenario, and is not a substitute for historical provenance.

## Dependencies and boundary

`tools/historical/qt_rom_browser_v1.py` is a small shell-free bridge importing
C1a and C2a validators. Qt invokes `python -B` through `QProcess` with explicit
arguments (no shell expansion) and a 30-second timeout. The backend option is
that of H116-C2b: `--rom-set-image FILE --rom-set-sha256 SHA`.

H116-H1L adds `LOADFP` support to `gui/qt6/kyiv_gui_backend.cpp` and a
pinned demonstration file `examples/dual_euler_reconstructed/EULER_DUAL_MODE.k41`.
There are exactly six production integration files (frontend, backend, bridge,
test, document, demonstration image). The CPU, fixed ROM, FP-ROM module,
C1a/C1b and C2a/C2b implementations are unchanged. The FP ROM set is a
**functional reconstruction**, not proven original hardware or an authentic
installed historical ROM.

## Dual Euler: same code, two routes on the same Kyiv CPU

The same 38-word RAM image is selected twice from the UI. `Dual Euler · CPU`
starts at `0200` (fixed-point initializer, then shared body `0230..0236`);
`Dual Euler · МП` selects `fp_functional`, enters at `C=3300` with the panel
NK `3000` pointing to `0210` (FP initializer, then that same body). The actual
program body is unchanged. The host does **not** implement FP arithmetic.

Native H116 Dual Euler evidence shows 32 CPU instructions directly and 858
CPU instructions via the software interpreter; both produce mathematical
`y(1)=81/256` after four Euler iterations. The raw word at RAM `0100` is
`02420000000000` (fixed-point y stored at half scale), versus
`12100000000077` (FP word); do not compare these raw words as equal.
The direct run reaches machine STOP (`T=1`); the interpreter run finishes
at the HOST-detected dispatcher boundary `C=3305, T=0, END_POINTER=1`. The
latter is **not** a machine STOP. The FP mode requires a selected verified
functional ROM set, explicit declared end pointer, and correct panel init.

The Qt UI does not automatically check the mathematical oracle; manual
verification uses the memory tab. Custom user ROM SHA-256 remains optional
per project policy; internal native test fixtures and reproducibility images
stay SHA-pinned.


## Практична демонстрація: Ейлер трьома способами (H116-H1L)

**Мета показу:** обчислити тим самим методом Ейлера чотири кроки для
`y'(t) = -y(t)`, `y(0) = 1`, `h = 1/4`, тобто
`y_(n+1) = y_n - h*y_n`. Незалежний математичний результат:
`y(1) = (3/4)^4 = 81/256 = 0.31640625`.

Перший запуск — початковий приклад FP Euler із H115. **Другий і третій
запуски — один і той самий 38-слівний файл**
[`EULER_DUAL_MODE.k41`](../../examples/dual_euler_reconstructed/EULER_DUAL_MODE.k41):
він містить два 8-командні ініціалізатори `0200–0207` та `0210–0217`,
7 незмінних машинних слів спільного тіла `0230–0236` і числові дані.
Тіло виконує чотири ітерації. Другий і третій режими **не** є двома
перекомпільованими версіями алгоритму. Навпаки, одні й ті самі слова тіла
інтерпретуються процесором безпосередньо або програмною МП, що також
працює **на цьому самому емульованому `Kyiv_t`**. Окремого HOST FP-виконавця
немає.

### Підготовка (MSYS2 MINGW64)

1. Відкрити термінал **MSYS2 MINGW64** у корені checkout та запустити
   продукційний Qt GUI командою `bash gui/qt6/run.sh`. Це постійний
   інтерфейс репозиторію, а не приватний GUI у `tempkyiv/`.
2. Для усіх трьох показів у GUI вибрати **«Команд/пакет» = 32** та
   **«Темп» = «Швидко»**. Вибір прикладу автоматично задає образ, ROM
   і початковий вхід; **не потрібно** вручну підмінювати RAM, регістр `C`
   або НК `3000`.
3. Після кожного виконання перейти на вкладку **«Пам’ять»**, ввести
   адресу `0100` в поле початкової адреси (вісімкове) і натиснути
   **«Оновити пам’ять»**. Для часу перевірити також адресу `0102`.
   Перед наступним прикладом знову обрати його та натиснути
   **«Завантажити»** — це створює нову CPU-сесію.

### Запуск 1 — звичайний FP Euler (контроль H115)

1. У **«Приклад»** обрати **«Сценарій · fp_euler»** і перевірити ROM-set
   `fp_functional` (**функціональна реконструкція**, не підтверджена
   історична ПЗП).
2. Натиснути **«Завантажити»**. Хоча FP-програма починається в `0230`,
   реальний лічильник команд CPU стартує з **`C=3300`**: у змінній ПЗП
   знаходиться інтерпретатор МП, а НК `3000` вказує на FP-програму.
3. Натиснути **«Пуск F6»** та дочекатися автоматичного завершення:
   **623 машинні команди**, `C=3305`, `T=0`, `END_POINTER=1`.
4. У пам'яті перевірити `0100 = 12100000000077` (`y=81/256`) та
   `0102 = 10000000000101` (`t=1`).

**Пояснення:** МП реалізує FP-арифметику послідовностями звичайних
команд «Києва». `END_POINTER=1` — ознака HOST на межі диспетчера
`C=3305`, **не** виконання машинної команди STOP і не встановлення `T`.
Це контрольний запуск первісного `EULER_IMAGE.k41`; він **не є** тим самим
образом, що в наступних двох запусках.

### Запуск 2 — Dual Euler безпосередньо на CPU (fixed-point)

1. У **«Приклад»** обрати **«Dual Euler · CPU (експеримент)»**.
   Показати шлях образу: `examples/dual_euler_reconstructed/EULER_DUAL_MODE.k41`.
   Обраний ROM — **«Лише ROM.txt»**.
2. Натиснути **«Завантажити»**. Вхід **`C=0200`** виконає 8 команд
   fixed-point ініціалізації `0200–0207`, потім передасть керування
   на спільне тіло `0230–0236`.
3. Натиснути **«Пуск F6»**. Очікуються **32 машинні команди**
   (8 ініціалізацій + 24 команди тіла), зупинка командою `0236: STOP`,
   `T=1`.
4. Перевірити `0100 = 02420000000000`. Цей код зберігає
   `y_machine=81/512`; **фізичний результат `y=2*y_machine=81/256`**.
   Комірка `0102 = 10000000000000` зберігає `t_machine=1/2`, отже
   фізичне `t=2*t_machine=1`.

**Пояснення:** арифметика апарата — з фіксованою комою. Для вміщення
початкового `y=1` у дробову шкалу 41-бітового слова програма зберігає
`y/2`; час також зберігається як `t/2`. Результат треба інтерпретувати
з урахуванням масштабу. Жодна команда МП тут не виконується.

### Запуск 3 — той самий Dual Euler через програмну МП

1. Обрати **«Dual Euler · МП (експеримент)»**. **Переконатися, що шлях
   `EULER_DUAL_MODE.k41` не змінився** від запуску 2. Обраний ROM-set —
   `fp_functional`.
2. Натиснути **«Завантажити»**. Поле **«Старт» = `0210`** означає
   вхід **FP-програми**, а не фізичний `C`. Backend вибере пультове
   джерело НК `3000`, задасть покажчик `0210` і запустить
   **CPU з `C=3300`**. Інтерпретатор виконає ініціалізацію
   `0210–0217`, а потім ті самі слова тіла `0230–0236`.
3. Натиснути **«Пуск F6»**. Очікуються **858 машинних команд CPU**,
   `C=3305`, `T=0`, `END_POINTER=1`. Це диспетчерська межа МП,
   а **не** STOP процесора.
4. Перевірити `0100 = 12100000000077` (`y=81/256`).
   У цьому конкретному спільному образі
   `0102 = 10000000000100` кодує `t_machine=1/2`, тобто
   **фізичне `t=1`** після масштабування часу. На відміну від
   контрольного запуску 1, тут збережено `t/2`, а не `t`.

**Пояснення:** опкоди FP-команд програмно інтерпретуються звичайними
машинними командами `Kyiv_t`; FP-формат чисел відрізняється від
fixed-point. Однакові слова інструкцій `0230–0236` тут мають
іншу *арифметичну семантику* завдяки інтерпретатору.

### Порівняння на завершення показу

| Критерій | 1. FP Euler (H115) | 2. Dual CPU | 3. Dual через МП |
|---|---|---|---|
| RAM-образ | `EULER_IMAGE.k41` | `EULER_DUAL_MODE.k41` | **той самий `EULER_DUAL_MODE.k41`** |
| Точка входу | FP `0230` / CPU `3300` | CPU `0200` | FP `0210` / CPU `3300` |
| Спільне тіло Dual | Ні, окремий еталон | `0230–0236` | **`0230–0236`** |
| Машинних команд CPU | **623** | **32** | **858** |
| Завершення | `END_POINTER`, `T=0` | STOP, `T=1` | `END_POINTER`, `T=0` |
| Слово `0100` | `12100000000077` | `02420000000000` | `12100000000077` |
| Інтерпретація `y(1)` | `81/256` | `2 × 81/512 = 81/256` | `81/256` |
| Слово `0102` | `10000000000101` (`t=1`) | `10000000000000` (`t/2=1/2`) | `10000000000100` (`t/2=1/2`) |

**Ключовий висновок для аудиторії:** віртуальна машина — це не ще один
фізичний процесор. МП є програмою у змінній ПЗП: вона читає команди
користувацької FP-програми й реалізує їх звичайними машинними командами
«Києва». Порівнювати **623, 32 і 858** цікаво як кількість виконаних
машинних команд, але не як безпосередній бенчмарк швидкодії: тут є
різні ініціалізатори, числові формати й маршрути.

**Контроль відтворюваності:** H116-H1K-R1 — ручний GUI acceptance 6/6;
H116-H1L — native PASS (H9, FP Euler, FP affine, FP RK4, Dual CPU/МП).
Результат підтверджено на **емуляторі**, не на фізичній ЕОМ «Київ»;
`fp_functional` — функціональна реконструкція ПЗП. GUI відображає
слова пам'яті, але математичний оракул автоматично не перевіряє —
тому його значення наведено явно вище. Ручну перевірку інтегрованого продукційного Qt GUI (H9, FP Euler,
Dual CPU, Dual через МП, перемикання й закриття без `OK QUIT`)
**підтверджено користувачем 2026-11-09**. Це повідомлений ручний PASS,
а не окремий автоматизований evidence чи апаратний oracle.

## Перевірка та відтворюваність

З кореня репозиторію в **MSYS2 MINGW64**:

```bash
python -B -m unittest discover -s tests/historical -p 'test_h116_qt_rom_browser.py' -v
bash gui/qt6/run.sh --smoke-only
bash gui/qt6/run.sh
```

Перша команда перевіряє Python-bridge, друга — збірку Qt і наявний
native smoke (H9/checkpoint), третя запускає продукційний Qt GUI.
Ці команди **не** замінюють повну FP native-матрицю H116-H1L.

Для ручного acceptance у GUI перевірити: H9 з Save/Restore;
`fp_euler` (623 команд, `END_POINTER=1`, `T=0`);
Dual Euler CPU (32 команди, STOP, `T=1`);
Dual Euler через МП (858 команд, `END_POINTER=1`, `T=0`);
перемикання сценаріїв та закриття без `OK QUIT`.
**Ручний PASS продукційного GUI повідомлено користувачем 2026-11-09**;
цей результат не є незалежним машинним чи апаратним доказом.

Зафіксовані локальні evidence (поза Git, якщо їх не долучено окремо):
`tempkyiv/H116_H1L_PRODUCTION_NATIVE_EVIDENCE_V1.zip` (повна native-матриця),
`tempkyiv/H116_H1M_DEMO_GUIDE_EVIDENCE_V1.zip` (документація),
`tempkyiv/H116_H1N_FINAL_GIT_AUDIT_EVIDENCE_V1.zip` (read-only diff/index audit).
Для перевірок нового checkout **не потрібен** неіснуючий у репозиторії `stage.py`.
Автоматизоване відтворення операторських дій і показ семантичного
математичного oracle у GUI — окремі майбутні етапи.
