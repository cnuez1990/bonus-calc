import sys
import re
import os
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
        return 0.0225  # 2.25%
    elif 56000 <= sales <= 61999:
        return 0.0175  # 1.75%
    elif 54000 <= sales <= 55999:
        return 0.0125  # 1.25%
    else:
        return 0.0000  # Below minimum threshold[cite: 1]


def parse_cdk_report(target_advisor, file_path):
    op_code_counts = Counter()
    current_op_code = None
    # Regex to handle alphanumeric codes (4WAC) and Advisor IDs[cite: 1]
    data_pattern = re.compile(
        r"^\s*([A-Z0-9]{2,6})?\s+(\d{4})\s+(\d{6})\s+(\d{2}[A-Z]{3}\d{2})\s+(\d{1,4})\s+([A-Z0-9]{17})\s+([A-Z0-9]+)")

    try:
        with open(file_path, 'r', encoding='utf-16') as file:
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


def process_advisor(adv_id, adv_info, config, data_file):
    results = parse_cdk_report(adv_id, data_file)
    if results is not None:
        sales_amount = adv_info['sales']
        bonus_rate = get_commission_rate(sales_amount)
        sales_comm = sales_amount * bonus_rate
        total_spiffs = 0

        print(f"\n=============================================")
        print(f"ADVISOR: {adv_id} ({adv_info.get('name', 'N/A')})")
        print(f"Total Sales: ${sales_amount:,.2f}")
        print(f"Commission:  ${sales_comm:,.2f} (Rate: {bonus_rate * 100:.2f}%)")
        print("-" * 45)

        for op, count in results.items():
            value_per_unit = config.spiff_map.get(op, 0)
            if value_per_unit > 0:
                earned = 0
                status = ""
                if op == "4WAC":
                    if count >= config.WAC_MIN:
                        earned = count * value_per_unit
                        status = "(MIN MET)"
                    else:
                        status = f"(MIN {config.WAC_MIN} NOT MET)"
                else:
                    earned = count * value_per_unit

                print(f"OP {op:6}: {count:2} units -> ${earned:,.2f} {status}")
                total_spiffs += earned

        print("-" * 45)
        print(f"TOTAL SPIFFS:      ${total_spiffs:,.2f}")
        print(f"GRAND TOTAL BONUS: ${sales_comm + total_spiffs:,.2f}")


if __name__ == "__main__":
    # Load initial data
    config = load_external_args()
    data_file = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "ToFile.Txt")

    while True:
        print("\n" + "=" * 50)
        print("   Nissan of Fort Myers Bonus Calculator")
        print("=" * 50)
        print("0 - Run ALL Advisors")
        print("ID - Run Specific Advisor (e.g., 2742)")
        print("E - Exit Program")
        print("=" * 50)

        target = input("Selection: ").strip().upper()

        if target == 'E':
            print("Exiting...")
            break

            # Reload config each loop so you can edit args.py without restarting the program[cite: 1]
        config = load_external_args()

        if target == "0":
            print("\nProcessing ALL advisors from args.py...")
            for adv_id, info in config.advisors_data.items():
                process_advisor(adv_id, info, config, data_file)
        elif target in config.advisors_data:
            process_advisor(target, config.advisors_data[target], config, data_file)
        else:
            print(f"\nError: '{target}' is not a valid Advisor ID or command.")

            print("\n" + "-" * 50)
            input("Calculation finished. Press Enter to return to menu...")