import pandas as pd
import os
import sys
import re
import importlib.util
from collections import Counter


def load_external_args():
    # Locates args.py in the same directory as the executable
    base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    args_path = os.path.join(base_path, "args.py")
    if not os.path.exists(args_path):
        print(f"Error: {args_path} not found! Ensure args.py is in this folder.")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("args", args_path)
    args_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(args_module)
    return args_module


def get_commission_rate(sales):
    """Calculates commission percentage based on dealership tiers"""
    if sales >= 62000:
        return 0.0225
    elif 56000 <= sales <= 61999:
        return 0.0175
    elif 54000 <= sales <= 55999:
        return 0.0125
    return 0.0000


def parse_cdk_report(target_advisor, file_path):
    op_code_counts = Counter()
    current_op_code = None
    # Regex to handle alphanumeric codes and Advisor IDs
    data_pattern = re.compile(
        r"^\s*([A-Z0-9]{2,6})?\s+(\d{4})\s+(\d{6})\s+(\d{2}[A-Z]{3}\d{2})\s+(\d{1,4})\s+([A-Z0-9]{17})\s+([A-Z0-9]+)")

    try:
        with open(file_path, 'r', encoding='utf-16') as file:  # CDK reports often UTF-16[cite: 2]
            for line in file:
                if not line.strip() or "***" in line or "PAGE" in line:
                    continue
                match = data_pattern.match(line)
                if match:
                    if match.group(1):
                        current_op_code = match.group(1).strip()
                    if match.group(5) == str(target_advisor) and match.group(7).startswith('C'):
                        if current_op_code:
                            op_code_counts[current_op_code] += 1
        return op_code_counts
    except Exception as e:
        print(f"File Error: {e}")
        return None


def run_and_export_report(config, data_file):
    all_rows = []
    op_codes = list(config.spiff_map.keys())  #

    for adv_id, info in config.advisors_data.items():  #
        results = parse_cdk_report(adv_id, data_file)  # [cite: 2, 3]
        sales = info['sales']  # [cite: 1]
        comm_rate = get_commission_rate(sales)  # [cite: 2]
        comm_earned = round(sales * comm_rate, 2)  # [cite: 2]

        total_spiffs = 0
        spiff_data = {}

        # Calculate individual spiffs first to get the total
        for op in op_codes:
            count = results.get(op, 0) if results else 0
            rate = config.spiff_map.get(op, 0)  # [cite: 1]
            earned = count * rate if (op != "4WAC" or count >= config.WAC_MIN) else 0  # [cite: 1, 2]

            spiff_data[f"{op}_U"] = count
            spiff_data[f"{op}_$"] = round(earned, 2)
            total_spiffs += earned

        # Build the final row structure
        row = {
            "ID": adv_id,
            "Name": info['name'],
            "BONUS_GRAND_TOTAL": round(comm_earned + total_spiffs, 2),
            "Total Sales": sales,
            "Comm_$": comm_earned,
            "Spiffs_Total": round(total_spiffs, 2),
        }

        # Merge the op-code columns at the end
        row.update(spiff_data)
        all_rows.append(row)

    df = pd.DataFrame(all_rows)

    # Add Total Row[cite: 2]
    numeric_cols = df.select_dtypes(include=['number']).columns
    df.loc['Total', numeric_cols] = df[numeric_cols].sum()
    df.at['Total', 'ID'] = '---'
    df.at['Total', 'Name'] = 'GRAND TOTALS'

    csv_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "Bonus_Report.csv")
    df.to_csv(csv_path, index=False)

    print("\n" + "=" * 90)
    print(f" REPORT EXPORTED TO: {csv_path}")
    print("=" * 90)
    print(df.to_string(index=False))  # Display the CSV content in console[cite: 2]
    print("=" * 90)


if __name__ == "__main__":
    while True:
        config = load_external_args()  # Reload to catch changes in args.py[cite: 2]
        data_file = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "ToFile.Txt")  # [cite: 2, 3]

        print("\nNissan of Fort Myers Bonus System")
        print("1 - Generate Report (CSV + Console)")
        print("E - Exit")

        cmd = input("Selection: ").strip().upper()
        if cmd == 'E': break
        if cmd == '1':
            run_and_export_report(config, data_file)
            input("\nPress Enter to return to menu...")