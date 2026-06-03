import os
import re
from collections import defaultdict
import pandas as pd

header_pattern = re.compile(r"\((.*?)\)\s+at\s+t=(\d+)")


def find_csv_files(root_dir):
    files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if f.lower().endswith('.csv'):
                files.append(os.path.join(dirpath, f))
    return files


def get_group_id_from_filename(filename):
    fields = filename.split('_')
    if len(fields) >= 6:
        return f"_{fields[5]}_"
    return None


def get_category_from_filename(filename):
    fields = filename.split('_')
    if len(fields) >= 10:
        return os.path.splitext(fields[9])[0]
    return None


def validate_groups(file_paths):
    required_fields = {"dosage", "para", "pop", "stopt"}
    group_map = defaultdict(set)
    for path in file_paths:
        fn = os.path.basename(path)
        group_id = get_group_id_from_filename(fn)
        category = get_category_from_filename(fn)
        if group_id and category and category in required_fields:
            group_map[group_id].add(category)
    valid_groups = [gid for gid, fields in group_map.items() if fields == required_fields]
    return valid_groups


def load_group_dataframes(file_paths, target_group_id, strategy_filter=None):
    dataframes = {}
    for path in file_paths:
        fn = os.path.basename(path)
        group_id = get_group_id_from_filename(fn)
        category = get_category_from_filename(fn)
        if group_id == target_group_id and category:
            try:
                df = pd.read_csv(path)
            except Exception:
                continue
            if category in {"dosage", "pop"}:
                if strategy_filter is not None and 'Strategy name' in df.columns:
                    df = df[df['Strategy name'].isin(strategy_filter)]
                # trim long files if needed (preserve columns containing timepoints)
                dataframes[category] = df
            elif category == 'stopt':
                dataframes['stopt'] = df
            elif category == 'para':
                dataframes['para'] = df
    return dataframes


def expand_columns(df):
    new_df = df.copy()
    new_columns = []
    for col in list(df.columns):
        match = header_pattern.match(col)
        if match:
            var_names = [v.strip() for v in match.group(1).split(',')]
            t_number = match.group(2)
            expanded_values = df[col].apply(lambda x: [v.strip() for v in str(x).strip('()').split(',')])
            temp_data = {}
            for i, var in enumerate(var_names):
                name = var
                if ' dosage' in name:
                    name = name.replace(' dosage', '')
                else:
                    name = name + 'pop'
                new_col_name = f"{name}_{t_number}"
                temp_data[new_col_name] = expanded_values.apply(lambda vals: vals[i] if i < len(vals) else None)
            new_columns.append(pd.DataFrame(temp_data))
            new_df.drop(columns=[col], inplace=True)
    if new_columns:
        new_df = pd.concat([new_df] + new_columns, axis=1)
    return new_df


def process_group_output(group_output_data, dir_prefix=None):
    expanded_dosage = expand_columns(group_output_data['dosage'])
    expanded_dosage.rename(columns={'paramID': 'Parameter_ID', 'Strategy name': 'Strategy_name'}, inplace=True)

    expanded_pop = expand_columns(group_output_data['pop'])
    expanded_pop.rename(columns={'paramID': 'Parameter_ID', 'Strategy name': 'Strategy_name'}, inplace=True)

    # rename para columns (mapping taken from the original notebook)
    param_col_names = {
        'paramID': 'Parameter_ID',
        'Spop': 'S_pop',
        'R1pop': 'R1_pop',
        'R2pop': 'R2_pop',
        'R12pop': 'R12_pop',
        'g0_S': 'g0',
        'Sa.S.D1.': 'S_cell_sensitivity_D1',
        'Sa.S.D2.': 'S_cell_sensitivity_D2',
        'Sa.R1.D1.': 'R1_cell_sensitivity_D1',
        'Sa.R1.D2.': 'R1_cell_sensitivity_D2',
        'Sa.R2.D1.': 'R2_cell_sensitivity_D1',
        'Sa.R2.D2.': 'R2_cell_sensitivity_D2',
        'Sa.R12.D1.': 'R12_cell_sensitivity_D1',
        'Sa.R12.D2.': 'R12_cell_sensitivity_D2',
        'T.S..S.': 'S_transition_to_S',
        'T.S..R1.': 'R1_transition_to_S',
        'T.S..R2.': 'R2_transition_to_S',
        'T.S..R12.': 'R21_transition_to_S',
        'T.R1..S.': 'S_transition_to_R1',
        'T.R1..R1.': 'R1_transition_to_R1',
        'T.R1..R2.': 'R2_transition_to_R1',
        'T.R1..R12.': 'R12_transition_to_R1',
        'T.R2..S.': 'S_transition_to_R2',
        'T.R2..R1.': 'R1_transition_to_R2',
        'T.R2..R2.': 'R2_transition_to_R2',
        'T.R2..R12.': 'R12_transition_to_R2',
        'T.R12..S.': 'S_transition_to_R12',
        'T.R12..R1.': 'R1_transition_to_R12',
        'T.R12..R2.': 'R2_transition_to_R12',
        'T.R12..R12.': 'R12_transition_to_R12'
    }
    renamed_param = group_output_data['para'].rename(columns=param_col_names)

    renamed_stopt = group_output_data['stopt'].copy()
    # try to standardize stopt columns if possible
    stopt_cols = list(renamed_stopt.columns)
    if 'paramID' in stopt_cols:
        strategy_cols = [c for c in stopt_cols if str(c).startswith('strategy')]
        if len(strategy_cols) >= 2:
            keep = ['paramID'] + strategy_cols[:2]
            renamed_stopt = renamed_stopt[keep].copy()
            renamed_stopt.columns = ['Parameter_ID', 'Survival_CPM', 'Survival_DPM']
        else:
            # fallback to first three columns
            renamed_stopt = renamed_stopt.iloc[:, :3].copy()
            renamed_stopt.columns = ['Parameter_ID', 'Survival_CPM', 'Survival_DPM']
    else:
        if len(stopt_cols) >= 3:
            renamed_stopt = renamed_stopt.iloc[:, :3].copy()
            renamed_stopt.columns = ['Parameter_ID', 'Survival_CPM', 'Survival_DPM']

    if dir_prefix:
        # add global parameter id to each dataframe
        for df in (expanded_dosage, expanded_pop, renamed_param, renamed_stopt):
            if 'Parameter_ID' in df.columns:
                df['Global_Parameter_ID'] = df['Parameter_ID'].astype(str).apply(lambda x: f"{dir_prefix}_{x}")

    return {
        'expanded_dosage': expanded_dosage,
        'expanded_pop': expanded_pop,
        'renamed_param': renamed_param,
        'renamed_stopt': renamed_stopt,
    }


def get_dosage_df(dosage_df):
    # melt Drug1 columns into rows, extract timepoint
    drug1_cols = [c for c in dosage_df.columns if 'Drug1' in c]
    if 'Parameter_ID' not in dosage_df.columns and 'paramID' in dosage_df.columns:
        dosage_df = dosage_df.rename(columns={'paramID': 'Parameter_ID', 'Strategy name': 'Strategy_name'})
    melted = dosage_df.melt(id_vars=['Parameter_ID', 'Strategy_name'], value_vars=drug1_cols, var_name='timepoint', value_name='Drug1_dosage')
    melted['timepoint'] = melted['timepoint'].str.extract(r'_(\d+)').astype(int)
    # add final t = 1800 marker with dosage -1
    new_rows = melted[['Parameter_ID', 'Strategy_name']].drop_duplicates().copy()
    new_rows['timepoint'] = 1800
    new_rows['Drug1_dosage'] = -1
    melted = pd.concat([melted, new_rows], ignore_index=True)
    melted = melted.sort_values(['Parameter_ID', 'Strategy_name', 'timepoint']).reset_index(drop=True)
    strategy_map = {'strategy0': 'CPM', 'strategy2.2': 'DPM'}
    if 'Strategy_name' in melted.columns:
        melted['Strategy_name'] = melted['Strategy_name'].replace(strategy_map)
    return melted


def get_pop_df_for_parameter(pop_df, initial_pop_df, parameter_id):
    strategy_map = {'strategy0': 'CPM', 'strategy2.2': 'DPM'}
    sub = pop_df[pop_df['Parameter_ID'] == parameter_id].copy()
    if sub.empty:
        return pd.DataFrame()
    if 'Strategy_name' in sub.columns:
        sub['Strategy_name'] = sub['Strategy_name'].replace(strategy_map)

    init_row = initial_pop_df[initial_pop_df['Parameter_ID'] == parameter_id].copy()
    if init_row.empty:
        return pd.DataFrame()
    init_row = init_row.rename(columns={
        'S_pop': 'Spop_0',
        'R1_pop': 'R1pop_0',
        'R2_pop': 'R2pop_0',
        'R12_pop': 'R12pop_0'
    })
    sub = pd.merge(sub, init_row, on=['Parameter_ID'], how='left')

    pop_cols = [col for col in sub.columns if re.match(r'^(Spop|R1pop|R2pop|R12pop)(_\d+|_0)$', str(col))]
    if not pop_cols:
        return pd.DataFrame()

    melted_S = sub.melt(id_vars=['Parameter_ID', 'Strategy_name'], value_vars=[col for col in pop_cols if str(col).startswith('Spop')], var_name='timepoint', value_name='Spop')
    melted_S['timepoint'] = melted_S['timepoint'].str.extract(r'_(\d+)').astype(int)
    melted_R1 = sub.melt(id_vars=['Parameter_ID', 'Strategy_name'], value_vars=[col for col in pop_cols if str(col).startswith('R1pop')], var_name='timepoint', value_name='R1pop')
    melted_R1['timepoint'] = melted_R1['timepoint'].str.extract(r'_(\d+)').astype(int)
    melted_R2 = sub.melt(id_vars=['Parameter_ID', 'Strategy_name'], value_vars=[col for col in pop_cols if str(col).startswith('R2pop')], var_name='timepoint', value_name='R2pop')
    melted_R2['timepoint'] = melted_R2['timepoint'].str.extract(r'_(\d+)').astype(int)
    melted_R12 = sub.melt(id_vars=['Parameter_ID', 'Strategy_name'], value_vars=[col for col in pop_cols if str(col).startswith('R12pop')], var_name='timepoint', value_name='R12pop')
    melted_R12['timepoint'] = melted_R12['timepoint'].str.extract(r'_(\d+)').astype(int)

    merged = pd.merge(melted_S, melted_R1, on=['Parameter_ID', 'Strategy_name', 'timepoint'])
    merged = pd.merge(merged, melted_R2, on=['Parameter_ID', 'Strategy_name', 'timepoint'])
    merged = pd.merge(merged, melted_R12, on=['Parameter_ID', 'Strategy_name', 'timepoint'])
    merged = merged.sort_values(['Parameter_ID', 'Strategy_name', 'timepoint']).reset_index(drop=True)
    return merged


def get_pop_df(pop_df, initial_pop_df):
    strategy_map = {'strategy0': 'CPM', 'strategy2.2': 'DPM'}
    if 'Strategy_name' in pop_df.columns:
        pop_df['Strategy_name'] = pop_df['Strategy_name'].replace(strategy_map)

    initial_pop_df = initial_pop_df.rename(columns={'S_pop': 'Spop_0', 'R1_pop': 'R1pop_0', 'R2_pop': 'R2pop_0', 'R12_pop': 'R12pop_0'})
    pop_df = pd.merge(pop_df, initial_pop_df, on=['Parameter_ID'], how='left')

    melted_S = pop_df.melt(id_vars=['Parameter_ID', 'Strategy_name'], value_vars=[col for col in pop_df.columns if 'Spop' in col], var_name='timepoint', value_name='Spop')
    melted_S['timepoint'] = melted_S['timepoint'].str.extract(r'_(\d+)').astype(int)
    melted_R1 = pop_df.melt(id_vars=['Parameter_ID', 'Strategy_name'], value_vars=[col for col in pop_df.columns if 'R1pop' in col], var_name='timepoint', value_name='R1pop')
    melted_R1['timepoint'] = melted_R1['timepoint'].str.extract(r'_(\d+)').astype(int)
    melted_R2 = pop_df.melt(id_vars=['Parameter_ID', 'Strategy_name'], value_vars=[col for col in pop_df.columns if 'R2pop' in col], var_name='timepoint', value_name='R2pop')
    melted_R2['timepoint'] = melted_R2['timepoint'].str.extract(r'_(\d+)').astype(int)
    melted_R12 = pop_df.melt(id_vars=['Parameter_ID', 'Strategy_name'], value_vars=[col for col in pop_df.columns if 'R12pop' in col], var_name='timepoint', value_name='R12pop')
    melted_R12['timepoint'] = melted_R12['timepoint'].str.extract(r'_(\d+)').astype(int)

    merged = pd.merge(melted_S, melted_R1, on=['Parameter_ID', 'Strategy_name', 'timepoint'])
    merged = pd.merge(merged, melted_R2, on=['Parameter_ID', 'Strategy_name', 'timepoint'])
    merged = pd.merge(merged, melted_R12, on=['Parameter_ID', 'Strategy_name', 'timepoint'])
    merged = merged.sort_values(['Parameter_ID', 'Strategy_name', 'timepoint']).reset_index(drop=True)
    return merged


def map_trajectories(sim_run_id, dir_prefix, param_df, dosage_df, pop_df, output_dir, parameter_ids=None):
    dosage_df = get_dosage_df(dosage_df)
    if parameter_ids is None:
        parameter_ids = list(pd.unique(dosage_df['Parameter_ID']))
    elif isinstance(parameter_ids, int):
        parameter_ids = list(pd.unique(dosage_df['Parameter_ID']))[:parameter_ids]
    else:
        target_ids = {str(pid) for pid in parameter_ids}
        parameter_ids = [pid for pid in pd.unique(dosage_df['Parameter_ID']) if str(pid) in target_ids]

    output_path = os.path.join(output_dir, f"{dir_prefix}_{sim_run_id}_simTrajectories.csv")
    os.makedirs(output_dir, exist_ok=True)
    first_chunk = True
    written_rows = 0
    for pid in parameter_ids:
        dsub = dosage_df[dosage_df['Parameter_ID'] == pid]
        if dsub.empty:
            continue
        psub = get_pop_df_for_parameter(pop_df, param_df[['Parameter_ID', 'S_pop', 'R1_pop', 'R2_pop', 'R12_pop']], pid)
        if psub.empty:
            continue
        merged = pd.merge(dsub, psub, on=['Parameter_ID', 'Strategy_name', 'timepoint'])
        if merged.empty:
            continue
        merged['Source_Run'] = sim_run_id
        if dir_prefix:
            merged['Global_Parameter_ID'] = merged['Parameter_ID'].astype(str).apply(lambda x: f"{dir_prefix}_{x}")
        merged.to_csv(output_path, mode='w' if first_chunk else 'a', header=first_chunk, index=False)
        first_chunk = False
        written_rows += len(merged)
    if written_rows == 0:
        return pd.DataFrame()
    return output_path


def collect_EC_and_survival(sim_run_id, dir_prefix, stopt_df, trajectories_source, output_dir):
    if isinstance(trajectories_source, str):
        trajectories_df = pd.read_csv(trajectories_source)
    else:
        trajectories_df = trajectories_source
    # compute EC categories using trajectories
    param_id_list = []
    category_list = []
    basket_list = []
    for param_id in pd.unique(trajectories_df['Parameter_ID']):
        param_id_list.append(param_id)
        t0 = trajectories_df[(trajectories_df['Parameter_ID'] == param_id) & (trajectories_df['timepoint'] == 0)]
        t45 = trajectories_df[(trajectories_df['Parameter_ID'] == param_id) & (trajectories_df['timepoint'] == 45)]
        try:
            CPM_drug_0 = t0[t0['Strategy_name'] == 'CPM']['Drug1_dosage'].iloc[0]
            DPM_drug_0 = t0[t0['Strategy_name'] == 'DPM']['Drug1_dosage'].iloc[0]
            CPM_drug_45 = t45[t45['Strategy_name'] == 'CPM']['Drug1_dosage'].iloc[0]
            DPM_drug_45 = t45[t45['Strategy_name'] == 'DPM']['Drug1_dosage'].iloc[0]
        except Exception:
            category_list.append('undetermined')
            basket_list.append('')
            continue
        if CPM_drug_0 == DPM_drug_0 and CPM_drug_45 == DPM_drug_45:
            category_list.append('both_same')
        elif CPM_drug_0 == DPM_drug_0 and CPM_drug_45 != DPM_drug_45:
            category_list.append('first_same_only')
        elif CPM_drug_0 != DPM_drug_0 and CPM_drug_45 == DPM_drug_45:
            category_list.append('second_same_only')
        else:
            category_list.append('both_diff')
        basket_list.append(f"{CPM_drug_0}_{DPM_drug_0}_{CPM_drug_45}_{DPM_drug_45}")

    category_df = pd.DataFrame({'Parameter_ID': param_id_list, 'EC_category': category_list, 'Bucket': basket_list})
    survival_df = pd.merge(stopt_df, category_df, on=['Parameter_ID'])
    survival_df['DPM_days_improvement'] = survival_df['Survival_DPM'] - survival_df['Survival_CPM']
    survival_df['DPM_percent_improvement'] = (survival_df['Survival_DPM'] - survival_df['Survival_CPM']) / survival_df['Survival_DPM']
    survival_df['Source_Run'] = sim_run_id
    if dir_prefix:
        survival_df['Global_Parameter_ID'] = survival_df['Parameter_ID'].astype(str).apply(lambda x: f"{dir_prefix}_{x}")
    os.makedirs(output_dir, exist_ok=True)
    survival_df.to_csv(os.path.join(output_dir, f"{dir_prefix}_{sim_run_id}_ECsurvival.csv"), index=False)
    return survival_df


def process_DPMsim_output(dosage_path, para_path, pop_path, stopt_path, output_dir, base_sim_name=None, strategy_filter=None, parameter_ids=None, max_groups=None):
    """
    Process DPM simulation output from individual file paths.
    
    Parameters:
    -----------
    dosage_path : str
        Path to the dosage CSV file
    para_path : str
        Path to the parameters CSV file
    pop_path : str
        Path to the population CSV file
    stopt_path : str
        Path to the stopping time CSV file
    output_dir : str
        Directory to save processed output
    base_sim_name : str, optional
        Base simulation name for output files. Defaults to current date + sequential number (YYYYMMDD_NNN).
    strategy_filter : list, optional
        List of strategies to filter on
    parameter_ids : int or list, optional
        Process all groups, a specific number of groups, or specific parameter IDs
    max_groups : int, optional
        Maximum number of groups to process (takes precedence if parameter_ids is not specified)
    """
    from datetime import datetime
    
    if base_sim_name is None:
        date_str = datetime.now().strftime("%Y%m%d")
        base_sim_name = f"{date_str}_001"
    
    # Load the dataframes from provided paths
    try:
        dosage_df = pd.read_csv(dosage_path)
        para_df = pd.read_csv(para_path)
        pop_df = pd.read_csv(pop_path)
        stopt_df = pd.read_csv(stopt_path)
    except Exception as e:
        print(f"Error loading CSV files: {e}")
        return
    
    # Determine valid groups from the dataframes
    file_paths = [dosage_path, para_path, pop_path, stopt_path]
    valid_groups = validate_groups(file_paths)
    
    if not valid_groups:
        print("No valid groups found in the provided files")
        return
    
    if max_groups is not None:
        valid_groups = valid_groups[:max_groups]
    
    os.makedirs(output_dir, exist_ok=True)
    
    for gid in valid_groups:
        sim_run_id = gid.strip('_')
        loaded = load_group_dataframes(file_paths, gid, strategy_filter=strategy_filter)
        
        if set(loaded.keys()) >= {'dosage', 'para', 'pop', 'stopt'}:
            processed = process_group_output(loaded, dir_prefix=base_sim_name)
            processed['renamed_param'].to_csv(os.path.join(output_dir, f"{base_sim_name}_{sim_run_id}_simParamOutput.csv"), index=False)
            
            traj_source = map_trajectories(
                sim_run_id,
                base_sim_name,
                processed['renamed_param'],
                processed['expanded_dosage'],
                processed['expanded_pop'],
                output_dir,
                parameter_ids=parameter_ids,
            )
            
            collect_EC_and_survival(sim_run_id, base_sim_name, processed['renamed_stopt'], traj_source, output_dir)


def process_directory(root_dir, output_dir=None, strategy_filter=None, parameter_ids=None, max_groups=None):
    files = find_csv_files(root_dir)
    valid_groups = validate_groups(files)
    if max_groups is not None:
        valid_groups = valid_groups[:max_groups]
    base_prefix = os.path.basename(os.path.normpath(root_dir))
    if output_dir is None:
        output_dir = os.path.join(root_dir, '..', 'processedSimOutput', base_prefix)
    os.makedirs(output_dir, exist_ok=True)

    for gid in valid_groups:
        sim_run_id = gid.strip('_')
        group_files = [p for p in files if get_group_id_from_filename(os.path.basename(p)) == gid]
        loaded = load_group_dataframes(group_files, gid, strategy_filter=strategy_filter)
        if set(loaded.keys()) >= {'dosage', 'para', 'pop', 'stopt'}:
            processed = process_group_output(loaded, dir_prefix=base_prefix)
            processed['renamed_param'].to_csv(os.path.join(output_dir, f"{base_prefix}_{sim_run_id}_simParamOutput.csv"), index=False)
            traj_source = map_trajectories(
                sim_run_id,
                base_prefix,
                processed['renamed_param'],
                processed['expanded_dosage'],
                processed['expanded_pop'],
                output_dir,
                parameter_ids=parameter_ids,
            )
            collect_EC_and_survival(sim_run_id, base_prefix, processed['renamed_stopt'], traj_source, output_dir)
