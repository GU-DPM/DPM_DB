"""CLI for processing raw DPM simulation outputs into processed CSVs."""
import argparse
import os
from dpm_db import processing


def main():
    p = argparse.ArgumentParser(description='Process raw DPM simulation outputs in a directory')
    p.add_argument('input_dir', help='Path to directory containing rawSimOutput files (walked recursively)')
    p.add_argument('-o', '--output-dir', help='Output directory for processed CSVs (optional)')
    p.add_argument('--group', help='Process only a single group id (e.g. 002 or _002_)')
    p.add_argument('--strategies', help='Comma-separated list of Strategy names to keep (optional)')
    p.add_argument('--sample-size', type=int, help='Process only the first N parameter IDs in the selected group')
    p.add_argument('--parameter-ids', help='Comma-separated list of specific Parameter_IDs to process')
    p.add_argument('--max-groups', type=int, help='When processing a directory, limit to the first N groups')
    args = p.parse_args()

    strategy_filter = None
    if args.strategies:
        strategy_filter = [s.strip() for s in args.strategies.split(',')]

    parameter_ids = None
    if args.parameter_ids:
        parameter_ids = [pid.strip() for pid in args.parameter_ids.split(',') if pid.strip()]
    elif args.sample_size is not None:
        parameter_ids = args.sample_size

    input_dir = os.path.abspath(args.input_dir)
    out_dir = args.output_dir
    if args.group:
        gid = f"_{args.group.strip('_')}_"
        files = processing.find_csv_files(input_dir)
        loaded = processing.load_group_dataframes(files, gid, strategy_filter=strategy_filter)
        if set(loaded.keys()) >= {'dosage', 'para', 'pop', 'stopt'}:
            processed = processing.process_group_output(loaded, dir_prefix=os.path.basename(os.path.normpath(input_dir)))
            sim_run_id = gid.strip('_')
            output_dir = out_dir or os.path.join(input_dir, '..', 'processedSimOutput', os.path.basename(os.path.normpath(input_dir)))
            trajectory_path = processing.map_trajectories(
                sim_run_id,
                os.path.basename(os.path.normpath(input_dir)),
                processed['renamed_param'],
                processed['expanded_dosage'],
                processed['expanded_pop'],
                output_dir,
                parameter_ids=parameter_ids,
            )
            processing.collect_EC_and_survival(sim_run_id, os.path.basename(os.path.normpath(input_dir)), processed['renamed_stopt'], trajectory_path, output_dir)
        else:
            raise SystemExit(f"Group {gid} not found or missing required files. Found: {list(loaded.keys())}")
    else:
        processing.process_directory(input_dir, output_dir=out_dir, strategy_filter=strategy_filter, parameter_ids=parameter_ids, max_groups=args.max_groups)


if __name__ == '__main__':
    main()
