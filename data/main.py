from collector.census.main import CensusCollector


def main():
    collector = CensusCollector()
    return collector.collect(
        type="population",
        level="tract",
        year=2020,
        state="CA",
        county=None,
        tract=None,
    )


if __name__ == "__main__":
    df = main()
    print(df)
