# Computational Chemistry Stories | Истории по вычислительной химии

[Portfolio landing page / Единая витрина](../PORTFOLIO.md)

This series explains computational chemistry through reproducible scientific stories rather than isolated commands or formulas.

Серия объясняет вычислительную химию через воспроизводимые научные истории, а не через набор несвязанных команд и формул.

## Notebook format / Формат блокнотов

Each case follows the same learning route:

1. Scientific question.
2. Physical or mathematical model.
3. Explicit assumptions.
4. Executable Python implementation.
5. Visualisation and interpretation.
6. Model limitations.
7. Questions for independent work.

Каждый кейс строится по единой логике:

1. Научный вопрос.
2. Физическая или математическая модель.
3. Явные допущения.
4. Исполняемая реализация на Python.
5. Визуализация и интерпретация.
6. Ограничения модели.
7. Вопросы для самостоятельного продолжения.

## Available / Доступно

### 01. Benzene π orbitals with the Hückel model

**[Open the notebook](notebooks/01_benzene_huckel_story.ipynb)**

A transparent calculation that converts the molecular graph of benzene into a Hückel Hamiltonian, orbital energies, HOMO/LUMO levels, and atomic-orbital coefficients.

Прозрачный расчёт, который преобразует молекулярный граф бензола в гамильтониан Хюккеля, энергетические уровни, HOMO/LUMO и коэффициенты атомных орбиталей.

Requirements: Python, NumPy, Matplotlib.

## Planned cases / Планируемые кейсы

- Heteroatom substitution: benzene → pyridine in a modified Hückel model.
- From molecular geometry to a PySCF calculation with provenance metadata.
- Basis-set choice as an engineering decision rather than a dropdown option.
- Geometry optimisation, convergence, and verification of a stationary point.
- From calculated transitions to a simulated UV–Vis spectrum.
- Solvent models: what changes and what remains an approximation.
- Comparing experimental and predicted spectra without hiding uncertainty.
- QSAR/QSPR applicability domain through a worked example.

- Замена гетероатома: бензол → пиридин в модифицированной модели Хюккеля.
- От геометрии молекулы к расчёту PySCF с метаданными происхождения.
- Выбор базиса как инженерное решение, а не пункт выпадающего списка.
- Оптимизация геометрии, сходимость и проверка стационарной точки.
- От рассчитанных переходов к моделированию УФ-видимого спектра.
- Модели растворителя: что меняется и что остаётся приближением.
- Сопоставление экспериментального и предсказанного спектров с явной неопределённостью.
- Область применимости QSAR/QSPR на разобранном примере.

## Educational principle / Методический принцип

The notebooks must distinguish clearly between a mathematical result, a chemical interpretation, a validated scientific conclusion, and an engineering decision.

В блокнотах должны быть явно разделены математический результат, химическая интерпретация, валидированный научный вывод и инженерное решение.
