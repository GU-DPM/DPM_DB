import csv
import os
import sqlite3
from pathlib import Path


DEFAULT_TABLE_NAMES = {
    'parameters': 'Parameters',
    'trajectories': 'Trajectories',
    'ecsurvival': 'ECsurvival',
}


class DPMDatabase:
    def __init__(self, path):
        self.path = path
        self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.commit()
            self.conn.close()
            self.conn = None

    def connect(self):
        os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA foreign_keys=OFF')
        self.conn.row_factory = sqlite3.Row

    def execute(self, sql, params=None):
        if params is None:
            params = []
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return cursor

    def create_table(self, table_name, columns, primary_keys=None):
        quoted_columns = [f'"{col}" TEXT' for col in columns]
        pk_clause = ''
        if primary_keys:
            quoted_keys = ', '.join(f'"{pk}"' for pk in primary_keys)
            pk_clause = f', PRIMARY KEY ({quoted_keys})'
        ddl = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(quoted_columns)}{pk_clause})'
        self.execute(ddl)
        self.conn.commit()

    def insert_rows(self, table_name, columns, rows, replace=True):
        if not rows:
            return 0
        placeholder = ', '.join(['?'] * len(columns))
        quoted = ', '.join(f'"{col}"' for col in columns)
        verb = 'INSERT OR REPLACE' if replace else 'INSERT'
        sql = f'{verb} INTO "{table_name}" ({quoted}) VALUES ({placeholder})'
        cursor = self.conn.cursor()
        for row in rows:
            values = [row.get(col, None) for col in columns]
            cursor.execute(sql, values)
        self.conn.commit()
        return cursor.rowcount

    def query(self, sql, params=None):
        cursor = self.execute(sql, params)
        return cursor.fetchall()


class DPMLoader:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _read_csv(path):
        with open(path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            return [row for row in reader], reader.fieldnames

    @staticmethod
    def _sanitize_columns(columns):
        return [col.strip() if isinstance(col, str) else col for col in columns]

    def _load_csv(self, path, table_name, sim_id, primary_keys):
        rows, fieldnames = self._read_csv(path)
        if not rows:
            return 0

        columns = self._sanitize_columns([name for name in fieldnames if name is not None])
        if 'sim_id' not in columns:
            columns = ['sim_id'] + columns

        self.db.create_table(table_name, columns, primary_keys=primary_keys)

        normalized_rows = []
        for row in rows:
            normalized = {col: row.get(col, '').strip() if col in row else '' for col in columns}
            normalized['sim_id'] = sim_id
            normalized_rows.append(normalized)

        return self.db.insert_rows(table_name, columns, normalized_rows)

    def load_parameters(self, parameters_path, sim_id, table_name=None):
        table_name = table_name or DEFAULT_TABLE_NAMES['parameters']
        return self._load_csv(
            Path(parameters_path),
            table_name,
            sim_id,
            primary_keys=['sim_id', 'Parameter_ID'],
        )

    def load_trajectories(self, trajectories_path, sim_id, table_name=None):
        table_name = table_name or DEFAULT_TABLE_NAMES['trajectories']
        return self._load_csv(
            Path(trajectories_path),
            table_name,
            sim_id,
            primary_keys=['sim_id', 'Parameter_ID', 'Strategy_name', 'timepoint'],
        )

    def load_ecsurvival(self, ecsurvival_path, sim_id, table_name=None):
        table_name = table_name or DEFAULT_TABLE_NAMES['ecsurvival']
        return self._load_csv(
            Path(ecsurvival_path),
            table_name,
            sim_id,
            primary_keys=['sim_id', 'Parameter_ID'],
        )

    def load_processed_run(self, sim_id, parameters_path, trajectories_path, ecsurvival_path):
        imported = {}
        imported['parameters'] = self.load_parameters(parameters_path, sim_id)
        imported['trajectories'] = self.load_trajectories(trajectories_path, sim_id)
        imported['ecsurvival'] = self.load_ecsurvival(ecsurvival_path, sim_id)
        return imported


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Load processed DPM outputs into a local SQLite database')
    parser.add_argument('--database', '-d', required=True, help='Path to the SQLite database file')
    parser.add_argument('--sim-id', required=True, help='Simulation identifier')
    parser.add_argument('--parameters', help='Path to the processed simParamOutput CSV')
    parser.add_argument('--trajectories', help='Path to the processed simTrajectories CSV')
    parser.add_argument('--ecsurvival', help='Path to the processed ECsurvival CSV')
    parser.add_argument('--output-dir', help='Directory containing the three processed CSV outputs')
    parser.add_argument('--base-name', help='Base file name prefix for processed outputs in the output directory')
    args = parser.parse_args()

    if args.output_dir and args.base_name:
        args.parameters = args.parameters or os.path.join(args.output_dir, f'{args.base_name}_simParamOutput.csv')
        args.trajectories = args.trajectories or os.path.join(args.output_dir, f'{args.base_name}_simTrajectories.csv')
        args.ecsurvival = args.ecsurvival or os.path.join(args.output_dir, f'{args.base_name}_ECsurvival.csv')

    missing = [name for name in ('parameters', 'trajectories', 'ecsurvival') if getattr(args, name) is None]
    if missing:
        raise SystemExit(f'Missing required paths: {missing}. Provide either explicit file paths or --output-dir/--base-name.')

    for path in (args.parameters, args.trajectories, args.ecsurvival):
        if not os.path.exists(path):
            raise SystemExit(f'Missing file: {path}')

    with DPMDatabase(args.database) as db:
        loader = DPMLoader(db)
        results = loader.load_processed_run(
            sim_id=args.sim_id,
            parameters_path=args.parameters,
            trajectories_path=args.trajectories,
            ecsurvival_path=args.ecsurvival,
        )

    print('Loaded processed outputs into SQLite database:')
    print(f'  database: {args.database}')
    print(f'  sim_id: {args.sim_id}')
    print(f'  parameters rows: {results["parameters"]}')
    print(f'  trajectories rows: {results["trajectories"]}')
    print(f'  ecsurvival rows: {results["ecsurvival"]}')


if __name__ == '__main__':
    main()
