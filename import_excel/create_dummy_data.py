import pandas as pd


def create_dummy_data():
    data = {
        "No.": [1, 2, 3],
        "値１": ["sample_A", "sample_B", "sample_C"],
        "値２": ["hello world", "test command arg", "data definition text"],
    }
    df = pd.DataFrame(data)
    df.to_excel("data.xlsx", index=False)
    print("Dummy data 'data.xlsx' created successfully.")


if __name__ == "__main__":
    create_dummy_data()
