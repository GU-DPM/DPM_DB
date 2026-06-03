# SQLite Research Summary: Local DPM Results Database

## Task
Migrate EC/misspecification processing scripts from Google Colab + BigQuery
to a local laptop database for DPM simulation output — eliminating ongoing
cloud storage and query costs.

---

## How the 4 DPM Output Files Map to 3 DB Tables

```
parameters.csv      →  Parameters   (one row per arm per sim_id)
populations.csv  ┐
dosage.csv       ┘  →  Trajectories (one row per patient × time_point; joined on sim_id+patient_id+time_point)
populations.csv  ┐
stopping_time.csv┘  →  ECsurvival   (one row per patient; event cols from populations, stopping_time joined in)
```

### Table: Parameters
Stores model priors and fitted parameters per simulation arm.

| Column | Source | Notes |
|---|---|---|
| sim_id | parameters.csv | Run identifier |
| arm | parameters.csv | e.g. "control", "treatment" |
| alpha, beta, gamma | parameters.csv | Model coefficients |
| prior_mean, prior_sd | parameters.csv | Bayesian prior info |

### Table: Trajectories
Stores the longitudinal patient tumor/population trajectory, merged with dosing.

| Column | Source | Notes |
|---|---|---|
| sim_id | populations.csv | Run identifier |
| patient_id | populations.csv | Patient ID |
| arm | populations.csv | Treatment arm |
| time_point | populations.csv | Discrete time step |
| population_size | populations.csv | Tumor burden / cell count |
| dose | dosage.csv | Joined on (sim_id, patient_id, time_point) |

### Table: ECsurvival
Stores per-patient survival outcomes (event/censoring), one row per patient.

| Column | Source | Notes |
|---|---|---|
| sim_id | populations.csv | Run identifier |
| patient_id | populations.csv | Patient ID |
| arm | populations.csv | Treatment arm |
| event_time | populations.csv | Time of event |
| event_observed | populations.csv | 1=event, 0=censored |
| stopping_time | stopping_time.csv | Joined on (sim_id, patient_id) |

---

## SQLite Design Decisions

### PRIMARY KEYS
All three tables use composite primary keys on `(sim_id, ...)` so multiple
simulation runs can coexist in one database and re-loading a run is safe
(`INSERT OR REPLACE`).

### WAL Mode
```python
conn.execute("PRAGMA journal_mode=WAL")
```
Write-Ahead Logging allows concurrent readers while a write is in progress —
important if analysis scripts query while a loader is inserting.

### No External Dependencies
The loader uses only Python stdlib (`sqlite3`, `csv`, `io`, `pathlib`).
This keeps the pip package lightweight and Colab-compatible with no installs.

### In-Memory Mode
```python
db = DPMDatabase(":memory:")  # for testing / ephemeral analysis
db = DPMDatabase("results.db")  # for persistent storage
```

---

## Package Structure

```
dpm_sqlite/
├── dpm_loader.py        # Core module (DPMDatabase, DPMLoader classes)
├── test_dpm_loader.py   # Integration tests with synthetic DPM data
├── pyproject.toml       # pip-installable package config
└── RESEARCH.md          # This document
```

### Installing (editable, for development)
```bash
pip install -e .
```

### Usage
```python
from dpm_loader import DPMDatabase, DPMLoader

with DPMDatabase("results.db") as db:
    loader = DPMLoader(db)

    # Load one simulation run from its 4 output files
    loader.load_run(
        sim_id=42,
        parameters_path="run_42/parameters.csv",
        dosage_path="run_42/dosage.csv",
        populations_path="run_42/populations.csv",
        stopping_time_path="run_42/stopping_time.csv",
    )

    # Or load from a directory with standard filenames
    loader.load_directory("run_42/", sim_id=42)

    # Query results directly
    rows = db.query("""
        SELECT e.patient_id, e.arm, e.event_time, e.event_observed,
               AVG(t.population_size) AS avg_pop
        FROM ECsurvival e
        JOIN Trajectories t USING (sim_id, patient_id)
        WHERE e.sim_id = 42
        GROUP BY e.patient_id
    """)
```

---

## Comparison: SQLite vs BigQuery for This Use Case

| Factor | BigQuery | SQLite |
|---|---|---|
| Cost | ~$5/TB queried + storage | Free |
| Setup | GCP project, auth, billing | None |
| Portability | Cloud-only | One `.db` file |
| Offline use | No | Yes |
| Scale ceiling | Petabytes | ~1TB practical |
| SQL compatibility | Near-standard | Standard |
| Colab compatible | Yes (with auth) | Yes (stdlib) |
| Team sharing | Easy via GCS | Copy file or use shared drive |

**Verdict:** For a research lab running simulations on a laptop, SQLite is
strictly better than BigQuery. BigQuery would only be justified if the
dataset exceeded what SQLite can handle (~tens of millions of rows) or if
real-time multi-user write access were needed.

---

## Next Steps for the Larger Migration

1. **Confirm CSV schemas** against actual DPM output files — column names
   may differ from the assumed schema above. Adjust `DPMLoader` column
   references accordingly.

2. **Batch loading**: If processing many simulation runs, wrap `load_run`
   in a loop and commit in batches for performance.

3. **Indexes**: Add indexes on frequently queried columns after confirming
   query patterns, e.g.:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_traj_arm ON Trajectories(arm);
   CREATE INDEX IF NOT EXISTS idx_ec_arm   ON ECsurvival(arm);
   ```

4. **Migration from BigQuery**: Export existing BigQuery tables as CSV,
   then use `DPMLoader` to import into SQLite. The `INSERT OR REPLACE`
   strategy handles duplicates safely.

5. **Integration with EC/misspecification scripts**: Replace BigQuery client
   calls with `DPMDatabase.query()` and standard SQL.
