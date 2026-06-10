# Q2SC SaaS Platform

Q2SC — исследовательская SaaS/desktop-платформа для вычислительной химии и предиктивной спектроскопии: подготовка молекул, квантовые задания, QSAR/QSPR, хемометрия, скрининг, библиотека референсных данных, трассируемость и React-интерфейс.

Репозиторий остается alpha-grade исследовательской системой. В нем уже есть настоящий расчетный профиль PySCF, но встроенная QSAR-модель использует демонстрационную калибровочную матрицу. Любой расчетный метод и спектральный профиль требуют отдельной научной валидации.

## Состав

- `backend/` — FastAPI orchestrator, RDKit molecule preparation, PubChem/ChEMBL/PDB adapters, reference library, QSAR-core and Celery routing.
- `frontend/` — Electron + Vite + React + TypeScript, 3Dmol.js molecular/electron-density scene and spectral dashboards.
- `worker_dft/` — PySCF heavy worker for real HF/DFT, cube fields, harmonic modes and TDHF/TDDFT states.
- `infra/` — PostgreSQL schema, Docker Compose, Nginx config.
- `scripts/` — автоматическая настройка окружения и запуск в dev/docker режимах.
- `docs/` — предметный граф, quantum architecture, converted books, API, scaling and traceability.

## Быстрый запуск без Docker

Linux/macOS:

```bash
bash scripts/setup.sh
bash scripts/dev.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

После запуска:

- Backend API: `http://127.0.0.1:8000/docs`
- Electron UI: запускается через Vite/Electron.

## Docker запуск

```bash
cp .env.example .env
docker compose up --build
```

Основные сервисы:

- `q2sc-api` — FastAPI orchestrator.
- `q2sc-worker-ai` — быстрый worker для QSAR/PLS/AD задач.
- `q2sc-worker-dft` — heavy PySCF worker для квантовых расчетов.
- `q2sc-postgres` — PostgreSQL.
- `q2sc-redis` — брокер/cache для очередей.
- `q2sc-minio` — S3-compatible хранилище спектров.

## Два базовых сценария

1. **Design / Direct prediction**: структура + окружение + прибор → предсказанный спектр, VIP-интерпретация, AD-контроль, audit trail.
2. **Analytics / Reverse interpretation**: экспериментальный спектр + ограничения → предобработка, поиск кандидатов, match score, паркинг неизвестных гипотез.
3. **Molecule / Quantum**: SMILES или PubChem → 2D/3D структура → HF/DFT → энергия, орбитали, плотность, диполь, заряды, IR/UV-профиль.

## Масштабирование

- FastAPI endpoints используют async I/O.
- CPU-bound QSAR операции вынесены в thread/process executors.
- Для распределенного режима предусмотрены Celery workers.
- Docker Compose содержит scale-ready структуру; для production нужно вынести secrets в Vault/KMS, подключить persistent volumes, observability и ingress.

## Важное ограничение

Реализованный quantum-профиль по умолчанию описывает один газофазный конформер. Для утверждений о растворе, белке, кристалле, масс-спектре, абсолютных интенсивностях или кинетике нужны соответствующие solvent/QM-MM/periodic/fragmentation workflows и валидация по экспериментальным данным.
