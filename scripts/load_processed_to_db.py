import argparse
import os

try:
    from dpm_sqlite.dpm_loader import DPMDatabase, DPMLoader
except ImportError:
    from local_db.dpm_sqlite.dpm_loader import DPMDatabase, DPMLoader


def main():
    parser = argparse.ArgumentParser(description='Load processed DPM simulation outputs into a local SQLite database')
    parser.add_argument('--database', '-d', required=True, help='Path to the SQLite database file')
    parser.add_argument('--sim-id', required=True, help='Simulation identifier')
    parser.add_argument('--parameters', help='Path to processed simParamOutput CSV')
    parser.add_argument('--trajectories', help='Path to processed simTrajectories CSV')
    parser.add_argument('--ecsurvival', help='Path to processed ECsurvival CSV')
    parser.add_argument('--output-dir', help='Directory containing the processed CSV files')
    parser.add_argument('--base-name', help='Prefix for processed files in the output directory')
    args = parser.parse_args()

    if args.output_dir and args.base_name:
        args.parameters = args.parameters or os.path.join(args.output_dir, f'{args.base_name}_simParamOutput.csv')
        args.trajectories = args.trajectories or os.path.join(args.output_dir, f'{args.base_name}_simTrajectories.csv')
        args.ecsurvival = args.ecsurvival or os.path.join(args.output_dir, f'{args.base_name}_ECsurvival.csv')

    missing = [name for name in ('parameters', 'trajectories', 'ecsurvival') if getattr(args, name) is None]
    if missing:
        raise SystemExit(f'Missing required paths: {missing}. Provide explicit paths or --output-dir and --base-name.')

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
