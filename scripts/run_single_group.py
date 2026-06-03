import os
from dpm_db import processing

def main():
    # adjust these paths / group id as needed
    subdir = 'exampleData/rawSimOutput/example_01/10x_atsim'
    target_group = '_002_'
    outdir = 'exampleData/processedSimOutput/example_01'
    files = [os.path.join(subdir, f) for f in os.listdir(subdir) if f.endswith('.csv')]
    loaded = processing.load_group_dataframes(files, target_group, strategy_filter=['strategy0','strategy2.2'])
    if set(loaded.keys()) >= {'dosage','para','pop','stopt'}:
        processed = processing.process_group_output(loaded, dir_prefix='example_01')
        sim_run_id = target_group.strip('_')
        traj = processing.map_trajectories(sim_run_id, 'example_01', processed['renamed_param'], processed['expanded_dosage'], processed['expanded_pop'], outdir)
        processing.collect_EC_and_survival(sim_run_id, 'example_01', processed['renamed_stopt'], traj, outdir)
        print('Done processing', target_group)
    else:
        print('Missing required files for', target_group, 'found:', list(loaded.keys()))

if __name__ == '__main__':
    main()
