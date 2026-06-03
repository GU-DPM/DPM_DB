# DPM_DB

DPM_DB is a repository for processing raw DPM simulation outputs into standardized CSV tables and loading those processed results into a local SQLite database.

## Repository layout

- `dpm_db/`
  - `__init__.py`
  - `processing.py` — raw simulation CSV processing and transformation logic.
- `local_db/`
  - `dpm_sqlite/` — SQLite loader package implementation.
  - `pyproject.toml` — package metadata and CLI entry point for the loader.
- `exampleData/`
  - `rawSimOutput/example_01/` — example raw DPM simulation outputs.
  - `processedSimOutput/example_01/` — example processed outputs.
- `scripts/`
  - `process_raw.py` — CLI for processing raw simulation directories.
  - `run_single_group.py` — helper for processing one group.
  - `validate_processing.py` — automated validation helper.
  - `load_processed_to_db.py` — CLI wrapper to load processed CSV outputs into SQLite.
- `test_output/` — example processed output files for validation.
- `requirements.txt` — Python dependencies.

## Raw simulation data format

The raw simulation inputs are CSV files produced by the DPM pipeline. Each simulation group is represented by four CSV files:

- `*dosage*.csv` — dosing schedules and drug administration data.
- `*para*.csv` — parameter values for each parameter set.
- `*pop*.csv` — population counts for each strategy over time.
- `*stopt*.csv` — stopping time and survival results.

### Expected filename pattern

The repository expects filenames with underscore-separated components. Example raw file names from `exampleData/rawSimOutput/example_01/10x_atsim/`:

- `mis_PARset_default_PNAS_2drug_002_10000_para_result_dosage_20250107.csv`
- `mis_PARset_default_PNAS_2drug_002_10000_para_result_para_20250107.csv`
- `mis_PARset_default_PNAS_2drug_002_10000_para_result_pop_20250110.csv`
- `mis_PARset_default_PNAS_2drug_002_10000_para_result_stopt_20250107.csv`

The processing code uses the 6th underscore-separated component as the group identifier (for example `_002_`) and the 10th component as the file category (`dosage`, `para`, `pop`, or `stopt`).

## Processed output format

The repository produces three standardized processed tables from raw simulation input:

- `*_simParamOutput.csv` — cleaned parameter table with renamed parameter columns and `Parameter_ID`.
- `*_simTrajectories.csv` — merged trajectory table combining dosage and population values by timepoint and strategy.
- `*_ECsurvival.csv` — survival and EC classification table comparing CPM and DPM strategy outcomes.

### Key transformations

- `dosage` files are expanded to separate timepoint columns and renamed columns like `Parameter_ID` and `Strategy_name`.
- `pop` files are expanded from grouped population vectors into explicit timepoint columns such as `Spop`, `R1pop`, `R2pop`, and `R12pop`.
- `para` files are renamed with standardized columns like `S_pop`, `R1_pop`, `R2_pop`, `R12_pop`, `S_cell_sensitivity_D1`, `R1_transition_to_R1`, and more.
- `stopt` files are normalized to `Parameter_ID`, `Survival_CPM`, and `Survival_DPM`.
- Trajectory outputs add a sentinel final timepoint of `1800` with `Drug1_dosage = -1`.
- EC/survival outputs include computed fields such as `EC_category`, `Bucket`, `DPM_days_improvement`, and `DPM_percent_improvement`.

## Usage

### Install dependencies

```powershell
pip install -r requirements.txt
```

### Process raw simulation data

Process an entire raw directory:

```powershell
python scripts/process_raw.py exampleData/rawSimOutput/example_01 -o exampleData/processedSimOutput/example_01
```

Process a single group by group id:

```powershell
python scripts/process_raw.py exampleData/rawSimOutput/example_01 -o exampleData/processedSimOutput/example_01 --group 002
```

Process a sample of specific parameter IDs:

```powershell
python scripts/process_raw.py exampleData/rawSimOutput/example_01 -o exampleData/processedSimOutput/example_01 --group 022 --parameter-ids 4560026,4560030
```

Process only the first N parameter IDs for a group:

```powershell
python scripts/process_raw.py exampleData/rawSimOutput/example_01 -o exampleData/processedSimOutput/example_01 --group 022 --sample-size 5
```

Limit the number of groups processed:

```powershell
python scripts/process_raw.py exampleData/rawSimOutput/example_01 -o exampleData/processedSimOutput/example_01 --max-groups 2
```

### Python API example

```python
from dpm_db import processing

input_dir = 'exampleData/rawSimOutput/example_01'
output_dir = 'exampleData/processedSimOutput/example_01'
processing.process_directory(input_dir, output_dir=output_dir)
```

### Process a single raw group via Python

```python
from dpm_db import processing

dosage_path = 'exampleData/rawSimOutput/example_01/10x_atsim/mis_PARset_default_PNAS_2drug_002_10000_para_result_dosage_20250107.csv'
para_path = 'exampleData/rawSimOutput/example_01/10x_atsim/mis_PARset_default_PNAS_2drug_002_10000_para_result_para_20250107.csv'
pop_path = 'exampleData/rawSimOutput/example_01/10x_atsim/mis_PARset_default_PNAS_2drug_002_10000_para_result_pop_20250110.csv'
stopt_path = 'exampleData/rawSimOutput/example_01/10x_atsim/mis_PARset_default_PNAS_2drug_002_10000_para_result_stopt_20250107.csv'
output_dir = 'exampleData/processedSimOutput/example_01'

processing.process_DPMsim_output(
    dosage_path,
    para_path,
    pop_path,
    stopt_path,
    output_dir,
    base_sim_name='example_01',
    strategy_filter=['strategy0', 'strategy2.2'],
    parameter_ids=10,
)
```

## Manual validation

To validate processed outputs, compare generated files against known-good examples in `exampleData/processedSimOutput/example_01/` or the `test_output/` directory.

Validation steps:

1. Confirm output files exist for each processed group:
   - `*_simParamOutput.csv`
   - `*_simTrajectories.csv`
   - `*_ECsurvival.csv`
2. Verify header columns:
   - `simParamOutput` contains `Parameter_ID`, `Global_Parameter_ID`, and renamed parameter fields.
   - `simTrajectories` contains `Parameter_ID`, `Strategy_name`, `timepoint`, and `Drug1_dosage`.
   - `ECsurvival` contains `Parameter_ID`, `Survival_CPM`, `Survival_DPM`, and `EC_category`.
3. Check row counts and sample `Parameter_ID` values against expected reference files.
4. Use `scripts/validate_processing.py` for input readability, structure, group detection, and output integrity checks.

## Local SQLite loader

The local SQLite loader ingests processed DPM outputs into three tables:

- `Parameters`
- `Trajectories`
- `ECsurvival`

### Loader package layout

- `local_db/dpm_sqlite/` — SQLite loader source.
- `local_db/pyproject.toml` — package metadata and CLI entry point.
- `scripts/load_processed_to_db.py` — direct execution wrapper.

### Install the loader

```bash
python -m pip install -e local_db
```

### Load processed outputs into SQLite via script

```bash
python scripts/load_processed_to_db.py \
  --database results.db \
  --sim-id example_01_002 \
  --parameters exampleData/processedSimOutput/example_01/example_01_002_simParamOutput.csv \
  --trajectories exampleData/processedSimOutput/example_01/example_01_002_simTrajectories.csv \
  --ecsurvival exampleData/processedSimOutput/example_01/example_01_002_ECsurvival.csv
```

Or use a directory and base prefix:

```bash
python scripts/load_processed_to_db.py \
  --database results.db \
  --sim-id example_01_002 \
  --output-dir exampleData/processedSimOutput/example_01 \
  --base-name example_01_002
```

### Package CLI entry point

After installation, the package exposes the `dpm-db-load` command:

```bash
dpm-db-load \
  --database results.db \
  --sim-id example_01_002 \
  --output-dir exampleData/processedSimOutput/example_01 \
  --base-name example_01_002
```

### Notes

- The loader creates table schemas automatically from processed CSV headers.
- All values are stored as text for portability and repeatable ingestion.
- Existing rows are replaced on repeated loads using composite primary keys.
- TODO: add support for a CLI mode that accepts explicit processed output files or a single file path, not just an output directory with a base prefix.

## Adapting old queries to the local database

The `oldCode/` notebooks contain legacy query and analysis logic that can be adapted to the local SQLite database.

### Recommended approach

1. Identify the query logic in the notebook, including which raw or processed tables it used and how the joins were structured.
2. Map the original tables to the local SQLite tables:
   - legacy parameter files → `Parameters`
   - legacy trajectory/population data → `Trajectories`
   - legacy stopping / survival output → `ECsurvival`
3. Convert any notebook SQL or dataframe operations into local SQLite SQL or Python query code.

### Example Python query script

```python
from local_db.dpm_sqlite.dpm_loader import DPMDatabase

with DPMDatabase('results.db') as db:
    rows = db.query(
        """
        SELECT e.Parameter_ID,
               e.EC_category,
               e.Survival_CPM,
               e.Survival_DPM,
               t.Strategy_name,
               AVG(t.Spop) AS avg_Spop
        FROM ECsurvival e
        JOIN Trajectories t
          ON e.sim_id = t.sim_id
         AND e.Parameter_ID = t.Parameter_ID
        WHERE e.sim_id = 'example_01_002'
          AND t.Strategy_name = 'DPM'
        GROUP BY e.Parameter_ID, e.EC_category, e.Survival_CPM, e.Survival_DPM, t.Strategy_name
        """
    )

    for row in rows:
        print(dict(row))
```

### Converting notebook analysis to APIs

For reusable scripts or APIs:

- create a module under `scripts/` or a new package function that accepts `database`, `sim_id`, and query parameters
- keep the SQL logic centralized in one place for each analysis use case
- expose a CLI or Python function so notebooks can be replaced with reproducible scripts

### Practical query patterns

- use `sim_id` to scope queries to a single simulation run
- join `Parameters` to `Trajectories` on `sim_id` and `Parameter_ID`
- join `Parameters` or `Trajectories` to `ECsurvival` to get survival outcomes alongside trajectory metrics
- aggregate time-series values in `Trajectories` using `GROUP BY` and SQL functions such as `AVG`, `SUM`, or `MAX`

## Contact

Use this repository to standardize DPM simulation outputs before downstream analysis, modeling, or database ingestion.
