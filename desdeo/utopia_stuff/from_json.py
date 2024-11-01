"""A script to take simulated treatment alternatives from different maps based on stand ids."""

import polars as pl
import json
from pathlib import Path

if __name__ == "__main__":
    with Path.open("C:/MyTemp/code/UTOPIA/Iisakkila/Iisakkila.geojson") as file:
        data = json.load(file)
    name = data["name"]
    stands = []
    for d in data["features"]:
        stands.append(d["properties"]["standid"])
    dirs = ["N5444H", "N6222B"]

    units = []
    dfs = []
    for dir in dirs:
        df = pl.read_csv(Path(f"C:/MyTemp/code/UTOPIA/alternatives/{dir}/alternatives.csv"))
        dfs.append(df)
    df: pl.DataFrame = pl.concat(dfs)
    for stand in stands:
        if not df.filter(pl.col("unit") == float(stand)).is_empty():
            units.append(df.filter(pl.col("unit") == float(stand)))
    df: pl.DataFrame = pl.concat(units)
    #df = df.unique(subset=["unit", "schedule"],maintain_order=True)
    #df.write_csv(Path("C:/MyTemp/code/UTOPIA/alternatives/Iisakkila-diff-npv/alternatives.csv"))

    units = []
    dfs = []
    for dir in dirs:
        df = pl.read_csv(Path(f"C:/MyTemp/code/UTOPIA/alternatives/{dir}/alternatives_key.csv"))
        dfs.append(df)
    df: pl.DataFrame = pl.concat(dfs)
    for stand in stands:
        if not df.filter(pl.col("unit") == float(stand)).is_empty():
            units.append(df.filter(pl.col("unit") == float(stand)))
    df: pl.DataFrame = pl.concat(units)
    #df = df.unique(subset=["unit", "schedule"],maintain_order=True)
    #df.write_csv(Path("C:/MyTemp/code/UTOPIA/alternatives/Iisakkila-diff-npv/alternatives_key.csv"))
