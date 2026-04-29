from pathlib import Path
import pandas as pd

DATA_LAKE = (Path(__file__).resolve().parents[2] / "data").resolve()


def get_latest_day_dir(base_dir: Path) -> Path:
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {base_dir}")
    return sorted(subdirs)[-1]


BRONZE_POP_BASE = DATA_LAKE / "raw"
SILVER_POP_BASE = DATA_LAKE / "silver"

BRONZE_POP = get_latest_day_dir(BRONZE_POP_BASE)
date_jour = BRONZE_POP.name
BRONZE_POP = BRONZE_POP / "pop"
SILVER_POP = SILVER_POP_BASE / date_jour



DATA_FILE = BRONZE_POP / "DS_POPULATIONS_REFERENCE_2023_data.csv"
METADATA_FILE = BRONZE_POP / "DS_POPULATIONS_REFERENCE_2023_metadata.csv"


def normalize_geo(value):
    value = str(value).strip().replace('"', "")

    if value.endswith(".0"):
        value = value[:-2]

    return value.zfill(5)


def build_silver_population():
    SILVER_POP.mkdir(parents=True, exist_ok=True)

    print("DATA_LAKE =", DATA_LAKE)
    print("DATA_FILE =", DATA_FILE)
    print("Existe ?", DATA_FILE.exists())

    if not DATA_FILE.exists():
        raise FileNotFoundError(DATA_FILE)

    print("Taille fichier Ko =", round(DATA_FILE.stat().st_size / 1024, 2))

    df = pd.read_csv(
        DATA_FILE,
        sep=";",
        encoding="utf-8-sig",
        dtype=str
    )

    print("Colonnes =", df.columns.tolist())
    print("Lignes totales =", len(df))
    print(df.head())

    df["code_commune"] = df["GEO"].apply(normalize_geo)

    print("Exemples codes Paris trouvés :")
    print(df[df["code_commune"].between("75101", "75120")].head())

    df = df[
        (df["code_commune"].between("75101", "75120"))
        & (df["POPREF_MEASURE"] == "PMUN")
    ].copy()

    print("Lignes Paris PMUN =", len(df))

    if df.empty:
        print("Aucune ligne trouvée pour Paris PMUN.")
        return

    df["annee"] = df["TIME_PERIOD"].astype(int)
    df["population"] = df["OBS_VALUE"].astype(float).round(0).astype(int)
    df["arrondissement"] = df["code_commune"].str[-2:].astype(int)

    final = df[
        [
            "annee",
            "code_commune",
            "arrondissement",
            "population",
            "POPREF_MEASURE"
        ]
    ].rename(columns={"POPREF_MEASURE": "mesure_population"})

    # Ajout des noms depuis metadata
    if METADATA_FILE.exists():
        meta = pd.read_csv(
            METADATA_FILE,
            sep=";",
            encoding="utf-8-sig",
            dtype=str
        )

        meta_geo = meta[
            (meta["COD_VAR"] == "GEO")
            & (meta["COD_MOD"].apply(normalize_geo).between("75101", "75120"))
        ].copy()

        meta_geo["code_commune"] = meta_geo["COD_MOD"].apply(normalize_geo)

        meta_geo = meta_geo[["code_commune", "LIB_MOD"]].rename(
            columns={"LIB_MOD": "nom_arrondissement"}
        )

        final = final.merge(meta_geo, on="code_commune", how="left")
    else:
        final["nom_arrondissement"] = None

    final = final[
        [
            "annee",
            "code_commune",
            "arrondissement",
            "nom_arrondissement",
            "population",
            "mesure_population"
        ]
    ].sort_values(["annee", "arrondissement"])

    output = SILVER_POP / "population_arrondissement_silver.parquet"
    final.to_parquet(output, index=False)

    print("✅ Silver population créée :", output)
    print("Lignes finales =", len(final))
    print(final)


if __name__ == "__main__":
    build_silver_population()