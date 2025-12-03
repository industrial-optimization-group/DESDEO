"""An utility function to generate descriptions related to UTOPIA matters"""

def generate_descriptions(mapjson: dict, sid: str, stand: str, holding: str, extension: str) -> dict:
    descriptions = {}
    if holding:
        for feat in mapjson["features"]:
            if False:  # noqa: SIM108
                ext = f".{feat["properties"][extension]}"
            else:
                ext = ""
            descriptions[feat["properties"][sid]] = (
                f"Ala {feat["properties"][holding].split("-")[-1]} kuvio {feat["properties"][stand]}{ext}: "
            )
    else:
        for feat in mapjson["features"]:
            if False:  # noqa: SIM108
                ext = f".{feat["properties"][extension]}"
            else:
                ext = ""
            descriptions[feat["properties"][sid]
                         ] = f"Kuvio {feat["properties"][stand]}{ext}: "
    return descriptions