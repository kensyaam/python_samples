import json

import pandas as pd

if __name__ == "__main__":
    # file_path = "data/sample.xlsx"
    # sheet_name = "Sheet2"
    file_path = "data/test_spec.xlsx"
    sheet_name = "Sheet1"

    try:
        # Read the Excel file
        df = pd.read_excel(file_path, sheet_name=sheet_name, index_col=0, header=0)

        if df is not None:
            print("Data imported successfully:")
            print(df.head())
        else:
            print("Failed to import data.")
    except Exception as e:
        print(f"Error importing Excel file: {e}")

    print("\nDictionary format:")
    print(json.dumps(df.to_dict(orient="records"), indent=4, ensure_ascii=False))

    # output_json_path = None  # None to not save and return the data
    # output_str = df.to_json(
    #     path_or_buf=output_json_path,
    #     # orient="index",
    #     orient="table",
    #     force_ascii=False,
    #     index=True,
    #     indent=4,
    # )
    # print("\nData exported to JSON format:")
    # print(output_str)

    output_json_path = "output.json"
    df.to_json(
        path_or_buf=output_json_path,
        # orient="index",
        orient="table",
        force_ascii=False,
        index=True,
        indent=4,
    )

    # No.ごとにデータをグループ化
    nested_dict: dict = {}
    for x, y in df.groupby("No.", group_keys=False):
        nested_dict[x] = y.to_dict(orient="records")
    print("\nNested dictionary:")
    print(json.dumps(nested_dict, indent=4, ensure_ascii=False))
