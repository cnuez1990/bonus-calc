import pandas as pd
import os
import sys
import re
import importlib.util
from collections import Counter


def load_external_args():
    base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    args_path = os.path.join(base_path, "args.py")
    if not os.path.exists(args_path):
        print(f"Error: {args_path} not found!")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("args", args_path)
    args_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(args_module)
    return args_module


def parse_cdk_report(target_advisor, file_path):
    op_code_counts = Counter()
    current_op_code = None
    data_pattern = re.compile(
        r"^\s*([A-Z0-9]{2,6})?\s+(\d{4})\s+(\d{6})\s+(\d{2}[A-Z]{3}\d{2})\s+(\d{1,4})\s+([A-Z0-9]{17})\s+([A-Z0-9]+)")
    try:
        with open(file_path, 'r', encoding='utf-16') as file:
            for line in file:
                if not line.strip() or "***" in line or "PAGE" in line: continue
                match = data_pattern.match(line)
                if match:
                    if match.group(1): current_op_code = match.group(1).strip()
                    if match.group(5) == str(target_advisor) and match.group(7).startswith('C'):
                        if current_op_code: op_code_counts[current_op_code] += 1
        return op_code_counts
    except Exception as e:
        print(f"File Error: {e}")
        return None


def generate_report(config, data_file, mode):
    # Select the correct map based on user choice
    selected_map = config.spiff_map if mode == "COMM" else config.fluid_map
    filename = "Bonus_Report.csv" if mode == "COMM" else "Fluid_Spiffs.csv"

    all_rows = []
    op_codes = list(selected_map.keys())

    for adv_id, adv_name in config.advisors_data.items():
        results = parse_cdk_report(adv_id, data_file)
        total_money = 0
        row_data = {"ID": adv_id, "Name": adv_name}

        for op in op_codes:
            count = results.get(op, 0) if results else 0
            rate = selected_map.get(op, 0)

            # Apply 4WAC minimum rule[cite: 4, 5]
            earned = count * rate if (op != "4WAC" or count >= config.WAC_MIN) else 0

            row_data[f"{op}_U"] = count
            row_data[f"{op}_$"] = round(earned, 2)
            total_money += earned

        row_data["TOTAL_$"] = round(total_money, 2)
        all_rows.append(row_data)


    df = pd.DataFrame(all_rows)

    # Add totals to the bottom row
    num_cols = df.select_dtypes(include=['number']).columns
    df.loc['Total', num_cols] = df[num_cols].sum()
    df.at['Total', 'ID'] = '---'
    df.at['Total', 'Name'] = 'GRAND TOTALS'

    csv_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), filename)
    df.to_csv(csv_path, index=False)

    print(f"\n{'=' * 80}\n REPORT: {filename}\n{'=' * 80}")
    print(df.to_string(index=False))
    print('=' * 80)

if __name__ == "__main__":
    while True:
        config = load_external_args()
        data_file = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "ToFile.Txt")

        print("\nNissan of Fort Myers Bonus System")
        print("1 - Commission Spiff Report")
        print("2 - Fluid Spiff Report")
        print("E - Exit")

        choice = input("Selection: ").strip().upper()
        if choice == 'E': break
        if choice == '1':
            generate_report(config, data_file, "COMM")
        elif choice == '2':
            generate_report(config, data_file, "FLUID")
        if choice in ['1', '2']: input("\nPress Enter to return to menu...")