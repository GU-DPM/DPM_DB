# DPM Simulation Output Validation

This document describes how to use the validation script to validate your DPM simulation processing.

## Overview

The `scripts/validate_processing.py` script provides comprehensive validation of:

1. **Input Files** - Verify files exist and are readable
2. **Input Structure** - Check that required columns are present
3. **Group Identification** - Validate that groups can be identified
4. **Processing Execution** - Run the processing function
5. **Output Files** - Verify output files are created
6. **Output Data Integrity** - Check data types, missing values, and structure

## Quick Start

### Quick Validation (File Structure Only)

```bash
python scripts/validate_processing.py \
  path/to/dosage.csv \
  path/to/para.csv \
  path/to/pop.csv \
  path/to/stopt.csv \
  ./output_directory \
  "sim_name" \
  --quick
```

This mode skips processing and only validates input files and structure (completes in ~3 seconds).

### Full Validation (with Processing)

```bash
python scripts/validate_processing.py \
  path/to/dosage.csv \
  path/to/para.csv \
  path/to/pop.csv \
  path/to/stopt.csv \
  ./output_directory \
  "sim_name_20250521_001"
```

This mode runs the full processing function (may take longer).

### Minimal Usage (with defaults)

```bash
python scripts/validate_processing.py \
  path/to/dosage.csv \
  path/to/para.csv \
  path/to/pop.csv \
  path/to/stopt.csv
```

This will create a `./processed_output` directory and use the current timestamp as the simulation name.

## Command Line Arguments

```
python validate_processing.py <dosage_path> <para_path> <pop_path> <stopt_path> [output_dir] [base_sim_name] [--quick]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `dosage_path` | Yes | Path to the dosage CSV file |
| `para_path` | Yes | Path to the parameters CSV file |
| `pop_path` | Yes | Path to the population CSV file |
| `stopt_path` | Yes | Path to the stopping time CSV file |
| `output_dir` | No | Output directory (default: `./processed_output`) |
| `base_sim_name` | No | Base simulation name (default: current timestamp) |
| `--quick` | No | Skip processing function execution (quick validation mode) |

## Example Output

### Quick Mode (--quick)

When using `--quick` mode, the script completes in ~3 seconds and validates only file structure:

```
================================================================================
VALIDATION REPORT
================================================================================

✓ PASS: Input file exists (dosage)

✓ PASS: Input file readable (dosage)
       Shape: 110000 rows, 42 columns

✓ PASS: Input columns present (dosage)
       Required columns found: ['paramID', 'Strategy name']

✓ PASS: Valid groups found
       Found 1 valid groups: ['_002_']

✓ PASS: Processing function callable
       Skipped full processing (--quick mode)

---------------------------------------------------------------------------
Total Checks: 14 | Passed: 14 | Failed: 0
Elapsed Time: 3.38s
================================================================================
```

### Full Mode

When running without `--quick`, the script validates everything including processing output.

## Validation Checks

### Input File Validation
- ✓ Files exist
- ✓ Files are readable
- ✓ Required columns present (`paramID`, `Strategy name`, etc.)

### Group Validation
- ✓ Valid groups can be identified from file structure

### Processing
- ✓ Processing function runs without critical errors
- ✓ Handles timeouts gracefully
- ✓ Reports exceptions with details

### Output Validation
- ✓ Output files created with correct naming pattern
- ✓ Required columns present in output files
- ✓ Data types are valid
- ✓ No unexpected NaN values in critical columns

### Output Data Quality
- ✓ simParamOutput.csv has `Parameter_ID` and `Global_Parameter_ID`
- ✓ ECsurvival.csv has survival and EC category data
- ✓ simTrajectories.csv has timepoint and dosage data

## Example Output

```

## Exit Codes

- `0` - All validations passed
- `1` - One or more validations failed

## When to Use --quick Mode

Use `--quick` mode when:
- You just want to verify that input files are valid and properly structured
- You want a quick sanity check before running full processing
- You're testing on large files and processing is too slow
- You want to verify the script works without waiting for processing to complete

Use full mode (without --quick) when:
- You want to verify the complete pipeline works end-to-end
- You have small to medium-sized input files
- You want to validate that output files are created correctly
- You're running validation as part of a CI/CD pipeline

## Python Usage

You can also use the validation functions programmatically:

```python
from scripts.validate_processing import validate_all

all_passed, report = validate_all(
    dosage_path='path/to/dosage.csv',
    para_path='path/to/para.csv',
    pop_path='path/to/pop.csv',
    stopt_path='path/to/stopt.csv',
    output_dir='./output',
    base_sim_name='my_sim_20250521'
)

if all_passed:
    print("All validations passed!")
else:
    print("Some validations failed. Check the report above.")
```

## Troubleshooting

### "No valid groups found"
- Check that your input files have the expected naming convention with group IDs
- Verify all 4 file types (dosage, para, pop, stopt) are present for each group

### "Processing timed out"
- Large files may take longer to process
- Check file sizes and consider processing a subset with `parameter_ids` option
- Verify data structure matches expected format

### "Missing columns" warnings
- Check that column names match expected values (case-sensitive)
- Some columns may have been renamed during processing

### Mixed type warnings
- These are normal for numeric data that may have some non-numeric values
- The validation script suppresses these warnings
- Check NaN warnings for actual data issues

## Performance Notes

- Processing large files may take several minutes
- The script limits processing to 1 group during validation to complete in reasonable time
- For full processing without limits, use the `process_DPMsim_output()` function directly

## Related Functions

- `process_DPMsim_output()` - Main processing function (dpm_db/processing.py)
- `process_directory()` - Directory-based processing (dpm_db/processing.py)
- `validate_groups()` - Identify valid groups from files (dpm_db/processing.py)
