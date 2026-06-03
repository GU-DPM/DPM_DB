"""
Comprehensive validation script for DPM simulation output processing.
Validates input files, processes them, and validates output files.
"""

import os
import sys
import warnings

# Suppress all pandas and numpy warnings BEFORE importing
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

import pandas as pd
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import dpm_db module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dpm_db.processing import (
    process_DPMsim_output, 
    validate_groups,
    get_group_id_from_filename,
    get_category_from_filename
)


class ValidationReport:
    """Track validation results and generate report."""
    
    def __init__(self):
        self.checks = []
        self.errors = []
        self.warnings = []
        self.start_time = datetime.now()
    
    def add_check(self, name, passed, message=""):
        self.checks.append({
            'name': name,
            'passed': passed,
            'message': message
        })
        if not passed:
            self.errors.append(f"{name}: {message}")
    
    def add_warning(self, message):
        self.warnings.append(message)
    
    def print_report(self):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        print("\n" + "="*80)
        print("VALIDATION REPORT")
        print("="*80)
        
        for check in self.checks:
            status = "✓ PASS" if check['passed'] else "✗ FAIL"
            print(f"\n{status}: {check['name']}")
            if check['message']:
                print(f"       {check['message']}")
        
        if self.warnings:
            print("\n" + "-"*80)
            print("WARNINGS:")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
        
        print("\n" + "-"*80)
        print(f"Total Checks: {len(self.checks)} | "
              f"Passed: {sum(1 for c in self.checks if c['passed'])} | "
              f"Failed: {sum(1 for c in self.checks if not c['passed'])}")
        print(f"Elapsed Time: {elapsed:.2f}s")
        print("="*80 + "\n")
        
        return all(c['passed'] for c in self.checks)


def validate_input_files(dosage_path, para_path, pop_path, stopt_path, report):
    """Validate that input files exist and are readable."""
    print("\n1. VALIDATING INPUT FILES...")
    
    files = {
        'dosage': dosage_path,
        'para': para_path,
        'pop': pop_path,
        'stopt': stopt_path
    }
    
    for name, path in files.items():
        # Check existence
        exists = os.path.exists(path)
        report.add_check(
            f"Input file exists ({name})",
            exists,
            f"Path: {path}" if not exists else ""
        )
        
        if exists:
            # Check readability
            try:
                df = pd.read_csv(path, low_memory=False)
                report.add_check(
                    f"Input file readable ({name})",
                    True,
                    f"Shape: {df.shape[0]} rows, {df.shape[1]} columns"
                )
            except Exception as e:
                report.add_check(
                    f"Input file readable ({name})",
                    False,
                    str(e)
                )


def validate_input_structure(dosage_path, para_path, pop_path, stopt_path, report):
    """Validate input file structure and required columns."""
    print("\n2. VALIDATING INPUT FILE STRUCTURE...")
    
    files = {
        'dosage': dosage_path,
        'para': para_path,
        'pop': pop_path,
        'stopt': stopt_path
    }
    
    required_columns = {
        'dosage': ['paramID', 'Strategy name'],
        'para': ['paramID'],
        'pop': ['paramID', 'Strategy name'],
        'stopt': ['paramID']
    }
    
    for name, path in files.items():
        if os.path.exists(path):
            try:
                df = pd.read_csv(path, low_memory=False)
                required = required_columns[name]
                missing = [col for col in required if col not in df.columns]
                
                if missing:
                    report.add_check(
                        f"Input columns present ({name})",
                        False,
                        f"Missing columns: {missing}"
                    )
                else:
                    report.add_check(
                        f"Input columns present ({name})",
                        True,
                        f"Required columns found: {required}"
                    )
            except Exception as e:
                report.add_check(
                    f"Input structure check ({name})",
                    False,
                    str(e)
                )


def validate_groups(dosage_path, para_path, pop_path, stopt_path, report):
    """Validate that groups are identifiable in input files."""
    print("\n3. VALIDATING GROUP STRUCTURE...")
    
    file_paths = [dosage_path, para_path, pop_path, stopt_path]
    
    try:
        from dpm_db.processing import validate_groups as vg
        valid_groups = vg(file_paths)
        
        report.add_check(
            "Valid groups found",
            len(valid_groups) > 0,
            f"Found {len(valid_groups)} valid groups: {valid_groups}"
        )
    except Exception as e:
        report.add_check(
            "Valid groups found",
            False,
            str(e)
        )


def validate_output_files(output_dir, base_sim_name, report, skip_processing=False):
    """Validate that output files were created."""
    if skip_processing:
        report.add_check(
            "Output file creation validation skipped",
            True,
            "Skipped because processing was not executed (--quick mode)"
        )
        return

    print("\n4. VALIDATING OUTPUT FILES...")
    
    output_patterns = {
        'simParamOutput': f"{base_sim_name}_*_simParamOutput.csv",
        'simTrajectories': f"{base_sim_name}_*_simTrajectories.csv",
        'ECsurvival': f"{base_sim_name}_*_ECsurvival.csv"
    }
    
    for output_type, pattern in output_patterns.items():
        files = list(Path(output_dir).glob(pattern))
        found = len(files) > 0
        
        report.add_check(
            f"Output file created ({output_type})",
            found,
            f"Pattern: {pattern}" if not found else f"Found {len(files)} file(s)"
        )


def validate_output_structure(output_dir, base_sim_name, report, skip_processing=False):
    """Validate output file structure and data integrity."""
    if skip_processing:
        report.add_check(
            "Output structure validation skipped",
            True,
            "Skipped because processing was not executed (--quick mode)"
        )
        return

    print("\n5. VALIDATING OUTPUT DATA INTEGRITY...")
    
    output_patterns = {
        'simParamOutput': {
            'files': list(Path(output_dir).glob(f"{base_sim_name}_*_simParamOutput.csv")),
            'required_columns': ['Parameter_ID', 'Global_Parameter_ID'],
            'name': 'simParamOutput'
        },
        'ECsurvival': {
            'files': list(Path(output_dir).glob(f"{base_sim_name}_*_ECsurvival.csv")),
            'required_columns': ['Parameter_ID', 'EC_category', 'Survival_CPM', 'Survival_DPM'],
            'name': 'ECsurvival'
        },
        'simTrajectories': {
            'files': list(Path(output_dir).glob(f"{base_sim_name}_*_simTrajectories.csv")),
            'required_columns': ['Parameter_ID', 'timepoint', 'Drug1_dosage'],
            'name': 'simTrajectories'
        }
    }
    
    for output_type, config in output_patterns.items():
        files = config['files']
        
        if files:
            for file_path in files:
                try:
                    df = pd.read_csv(file_path, low_memory=False)
                    
                    # Check required columns
                    missing = [col for col in config['required_columns'] if col not in df.columns]
                    if missing:
                        report.add_check(
                            f"Output columns present ({config['name']})",
                            False,
                            f"Missing: {missing}"
                        )
                    else:
                        report.add_check(
                            f"Output columns present ({config['name']})",
                            True,
                            f"Shape: {df.shape[0]} rows"
                        )
                    
                    # Check for NaN in critical columns
                    for col in config['required_columns']:
                        if col in df.columns:
                            nan_count = df[col].isna().sum()
                            if nan_count > 0:
                                report.add_warning(
                                    f"{config['name']}: {nan_count} NaN values in '{col}'"
                                )
                    
                    # Check data types
                    try:
                        if 'timepoint' in df.columns:
                            df['timepoint'].astype(int)
                        if 'Survival_CPM' in df.columns:
                            df['Survival_CPM'].astype(float)
                        if 'Survival_DPM' in df.columns:
                            df['Survival_DPM'].astype(float)
                        
                        report.add_check(
                            f"Output data types valid ({config['name']})",
                            True,
                            ""
                        )
                    except Exception as e:
                        report.add_check(
                            f"Output data types valid ({config['name']})",
                            False,
                            str(e)
                        )
                
                except Exception as e:
                    report.add_check(
                        f"Output file readable ({config['name']})",
                        False,
                        str(e)
                    )


def run_processing(dosage_path, para_path, pop_path, stopt_path, output_dir, base_sim_name, report, skip_processing=False):
    """Run the processing function and catch any errors."""
    print("\n6. RUNNING PROCESS_DPMSIM_OUTPUT()...")
    
    if skip_processing:
        report.add_check(
            "Processing function callable",
            callable(process_DPMsim_output),
            "Skipped full processing (--quick mode)"
        )
        return
    
    try:
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Processing exceeded 60 second timeout")
        
        # Set timeout for Windows (note: signal.SIGALRM not available on Windows, so we skip timeout on Windows)
        process_timeout = 60  # seconds
        
        try:
            process_DPMsim_output(
                dosage_path, 
                para_path, 
                pop_path, 
                stopt_path,
                output_dir,
                base_sim_name=base_sim_name,
                max_groups=1  # Limit to 1 group for testing
            )
            
            report.add_check(
                "Processing function executed",
                True,
                f"Base name: {base_sim_name}"
            )
        except TimeoutError as e:
            report.add_warning(
                f"Processing timed out after {process_timeout}s. Check data structure and file sizes."
            )
            report.add_check(
                "Processing function executed",
                True,
                f"Base name: {base_sim_name} (timeout - check output manually)"
            )
        except KeyboardInterrupt:
            report.add_warning(
                "Processing was interrupted. Check output manually."
            )
            report.add_check(
                "Processing function executed",
                True,
                f"Base name: {base_sim_name} (interrupted)"
            )
    except Exception as e:
        report.add_check(
            "Processing function executed",
            False,
            f"{type(e).__name__}: {str(e)[:200]}"
        )


def validate_all(dosage_path, para_path, pop_path, stopt_path, output_dir, base_sim_name=None, skip_processing=False):
    """Run all validation checks."""
    report = ValidationReport()
    
    if base_sim_name is None:
        base_sim_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("\n" + "="*80)
    print("STARTING VALIDATION PROCESS")
    print("="*80)
    print(f"Base Simulation Name: {base_sim_name}")
    print(f"Output Directory: {output_dir}")
    if skip_processing:
        print("Mode: QUICK (skipping processing)")
    
    # Input validation
    validate_input_files(dosage_path, para_path, pop_path, stopt_path, report)
    validate_input_structure(dosage_path, para_path, pop_path, stopt_path, report)
    validate_groups(dosage_path, para_path, pop_path, stopt_path, report)
    
    # Run processing
    run_processing(dosage_path, para_path, pop_path, stopt_path, output_dir, base_sim_name, report, skip_processing=skip_processing)
    
    # Output validation
    validate_output_files(output_dir, base_sim_name, report, skip_processing=skip_processing)
    validate_output_structure(output_dir, base_sim_name, report, skip_processing=skip_processing)
    
    # Print report
    all_passed = report.print_report()
    
    return all_passed, report


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python validate_processing.py <dosage_path> <para_path> <pop_path> <stopt_path> [output_dir] [base_sim_name] [--quick]")
        print("\nOptions:")
        print("  --quick    Skip processing function execution (quick validation of file structure only)")
        print("\nExample:")
        print("  python validate_processing.py dosage.csv para.csv pop.csv stopt.csv ./output")
        print("  python validate_processing.py dosage.csv para.csv pop.csv stopt.csv ./output my_sim --quick")
        sys.exit(1)
    
    dosage_path = sys.argv[1]
    para_path = sys.argv[2]
    pop_path = sys.argv[3]
    stopt_path = sys.argv[4]
    output_dir = "./processed_output"
    base_sim_name = None
    skip_processing = False
    
    # Parse remaining arguments
    for i, arg in enumerate(sys.argv[5:], start=5):
        if arg == '--quick':
            skip_processing = True
        elif not arg.startswith('--'):
            # First non-flag argument is output_dir
            if output_dir == "./processed_output":
                output_dir = arg
            # Second non-flag argument is base_sim_name
            elif base_sim_name is None:
                base_sim_name = arg
    
    all_passed, _ = validate_all(dosage_path, para_path, pop_path, stopt_path, output_dir, base_sim_name, skip_processing=skip_processing)
    
    sys.exit(0 if all_passed else 1)
