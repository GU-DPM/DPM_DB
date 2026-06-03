DPM_DB processing
=================

This repository contains tools to process raw DPM simulation CSV outputs into standardized processed CSVs.

Quick start (using the existing Anaconda installation in VS Code):

1. Install Python dependencies in your active environment (or use the workspace Anaconda):

```powershell
pip install -r requirements.txt
```

2. Run the full directory processor:

```powershell
#$env:PYTHONPATH='C:\Users\simbox\Documents\GitHub\DPM_DB'
&C:/ProgramData/anaconda3/Scripts/conda.exe run -p C:\ProgramData\anaconda3 --no-capture-output python c:\Users\simbox\.vscode\extensions\ms-python.python-*/python_files/get_output_via_markers.py scripts/process_raw.py exampleData/rawSimOutput/example_01 -o exampleData/processedSimOutput/example_01
```

3. Or run a single group (faster test) using `--group` (example: `002`):

```powershell
#$env:PYTHONPATH='C:\Users\simbox\Documents\GitHub\DPM_DB'
&C:/ProgramData/anaconda3/Scripts/conda.exe run -p C:\ProgramData\anaconda3 --no-capture-output python c:\Users\simbox\.vscode\extensions\ms-python.python-*/python_files/get_output_via_markers.py scripts/process_raw.py exampleData/rawSimOutput/example_01 -o exampleData/processedSimOutput/example_01 --group 002
```

4. Run a single group but only specific Parameter_IDs (comma-separated) or a small sample:

```powershell
&C:/ProgramData/anaconda3/Scripts/conda.exe run -p C:\ProgramData\anaconda3 --no-capture-output python ... scripts/process_raw.py exampleData/rawSimOutput/example_01 -o exampleData/processedSimOutput/example_01 --group 022 --parameter-ids 4560026,4560030
```

```powershell
&C:/ProgramData/anaconda3/Scripts/conda.exe run -p C:\ProgramData\anaconda3 --no-capture-output python ... scripts/process_raw.py exampleData/rawSimOutput/example_01 -o exampleData/processedSimOutput/example_01 --group 022 --sample-size 5
```

5. Limit the number of groups when processing a directory (process first N groups):

```powershell
&C:/ProgramData/anaconda3/Scripts/conda.exe run -p C:\ProgramData\anaconda3 --no-capture-output python ... scripts/process_raw.py exampleData/rawSimOutput/example_01 -o exampleData/processedSimOutput/example_01 --max-groups 2
```

Notes:
- The CLI also accepts `--strategies` to filter strategy names (comma-separated).
- If Python cannot import `dpm_db`, set `PYTHONPATH` to the repository root before running.