from pathlib import Path
import pandas as pd

DATA_LAKE = (Path(__file__).resolve().parents[2] / "data").resolve()


def get_latest_day_dir(base_dir: Path) -> Path:
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {base_dir}")
    return sorted(subdirs)[-1]


BRONZE_CRIMINALITE_BASE = DATA_LAKE / "raw"
SILVER_CRIMINALITE_BASE = DATA_LAKE / "silver"

BRONZE_CRIMINALITE = get_latest_day_dir(BRONZE_CRIMINALITE_BASE)
date_jour = BRONZE_CRIMINALITE.name
BRONZE_CRIMINALITE = BRONZE_CRIMINALITE / "crim"
SILVER_CRIMINALITE = SILVER_CRIMINALITE_BASE / date_jour


def clean_number(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(",", ".", regex=False)
        .str.replace(" ", "", regex=False)
        .replace(["nan", "None", "", "NaN", "nd", "ND", "<NA>"], pd.NA)
        .pipe(pd.to_numeric, errors="coerce")
    )


def normalize_code_geo(value):
    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value.zfill(5)


def build_silver_criminalite():
    SILVER_CRIMINALITE.mkdir(parents=True, exist_ok=True)

    files = list(BRONZE_CRIMINALITE.glob("*.parquet"))

    if not files:
        raise FileNotFoundError(
            f"Aucun fichier Parquet trouvé dans {BRONZE_CRIMINALITE}"
        )

    frames = []

    for path in files:
        print(f"Lecture : {path.name}")

        df = pd.read_parquet(path)
        df.columns = [col.strip() for col in df.columns]

        required = [
            "CODGEO_2025",
            "annee",
            "indicateur",
            "unite_de_compte",
            "nombre",
            "taux_pour_mille",
            "est_diffuse",
            "insee_pop",
            "insee_log",
            "complement_info_nombre",
            "complement_info_taux"
        ]

        missing = [col for col in required if col not in df.columns]

        if missing:
            raise ValueError(
                f"Colonnes absentes dans {path.name}: {missing}\n"
                f"Colonnes disponibles: {df.columns.tolist()}"
            )

        df = df[required].copy()

        df["code_commune"] = df["CODGEO_2025"].apply(normalize_code_geo)
        df = df[df["code_commune"].between("75101", "75120")].copy()

        df["arrondissement"] = df["code_commune"].str[-2:].astype(int)

        df["annee"] = clean_number(df["annee"]).astype("Int64")
        df["nombre"] = clean_number(df["nombre"])
        df["taux_pour_mille"] = clean_number(df["taux_pour_mille"])
        df["insee_pop"] = clean_number(df["insee_pop"])
        df["insee_log"] = clean_number(df["insee_log"])
        df["complement_info_nombre"] = clean_number(df["complement_info_nombre"])
        df["complement_info_taux"] = clean_number(df["complement_info_taux"])

        df["nombre_final"] = df["nombre"].fillna(df["complement_info_nombre"])
        df["taux_pour_mille_final"] = df["taux_pour_mille"].fillna(
            df["complement_info_taux"]
        )

        mask_recalc = (
            df["taux_pour_mille_final"].isna()
            & df["nombre_final"].notna()
            & df["insee_pop"].notna()
            & (df["insee_pop"] > 0)
        )

        df.loc[mask_recalc, "taux_pour_mille_final"] = (
            df.loc[mask_recalc, "nombre_final"]
            / df.loc[mask_recalc, "insee_pop"]
            * 1000
        )

        df = df[df["annee"].notna()].copy()
        df = df[df["taux_pour_mille_final"].notna()].copy()

        df["annee"] = df["annee"].astype(int)
        df["arrondissement"] = df["arrondissement"].astype(int)

        final_columns = [
            "annee",
            "code_commune",
            "arrondissement",
            "indicateur",
            "unite_de_compte",
            "est_diffuse",
            "nombre_final",
            "taux_pour_mille_final",
            "insee_pop",
            "insee_log"
        ]

        df = df[final_columns].copy()
        frames.append(df)

    if not frames:
        raise RuntimeError("Aucune donnée criminalité chargée.")

    silver = pd.concat(frames, ignore_index=True)

    silver = silver.sort_values(
        ["annee", "arrondissement", "indicateur"]
    ).reset_index(drop=True)

    output = SILVER_CRIMINALITE / "criminalite_silver.parquet"
    silver.to_parquet(output, index=False)

    print(f"Silver criminalité créée : {output}")
    print(f"Lignes : {len(silver)}")
    print("Colonnes :", silver.columns.tolist())
    print("Années :", sorted(silver["annee"].dropna().unique()))
    print("Arrondissements :", sorted(silver["arrondissement"].unique()))
    print(silver.head(10))


if __name__ == "__main__":
    build_silver_criminalite()