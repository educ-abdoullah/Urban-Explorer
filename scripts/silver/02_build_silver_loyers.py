from pathlib import Path
import pandas as pd

DATA_LAKE = (Path(__file__).resolve().parents[2] / "data").resolve()


def get_latest_day_dir(base_dir: Path) -> Path:
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {base_dir}")
    return sorted(subdirs)[-1]


BRONZE_LOYERS_BASE = DATA_LAKE / "raw"
SILVER_LOYERS_BASE = DATA_LAKE / "silver"

BRONZE_LOYERS = get_latest_day_dir(BRONZE_LOYERS_BASE)
date_jour = BRONZE_LOYERS.name
BRONZE_LOYERS = BRONZE_LOYERS / "loyers_olap"
SILVER_LOYERS = SILVER_LOYERS_BASE / date_jour

YEARS=[2021,2022,2023,2024]


COLUMN_MAPPING = {
    "Data_year": "annee",
    "agglomeration": "perimetre",
    "Zone_calcul": "zone_olap",
    "Zone_complementaire": "zone_complementaire",
    "Type_habitat": "type_habitat",
    "nombre_pieces_local": "nb_pieces_local",
    "nombre_pieces_homogene": "nb_pieces",
    "loyer_median": "loyer_m2_median",
    "loyer_moyen": "loyer_m2_moyen",
    "loyer_mensuel_median": "loyer_mensuel_median",
    "moyenne_loyer_mensuel": "loyer_mensuel_moyen",
    "surface_moyenne": "surface_moyenne",
    "nombre_observations": "nb_observations",
    "nombre_logements": "nb_logements",
    "methodologie_production": "methodologie_production"
}


NUMERIC_COLUMNS = [
    "loyer_m2_median",
    "loyer_m2_moyen",
    "loyer_mensuel_median",
    "loyer_mensuel_moyen",
    "surface_moyenne",
    "nb_observations",
    "nb_logements"
]


def read_csv_flexible(path: Path) -> pd.DataFrame:
    encodings = ["cp1252", "latin1", "utf-8-sig", "utf-8"]

    last_error = None

    for encoding in encodings:
        try:
            return pd.read_csv(
                path,
                sep=";",
                encoding=encoding,
                dtype=str
            )
        except Exception as e:
            last_error = e

    raise last_error


def clean_numeric(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(",", ".", regex=False)
        .str.replace(" ", "", regex=False)
        .replace(["nan", "None", "", "-", "NaN"], pd.NA)
        .pipe(pd.to_numeric, errors="coerce")
    )


def build_zone_mapping_from_zonage(zonage_path: Path, year: int) -> pd.DataFrame:
    df = read_csv_flexible(zonage_path)

    df.columns = [col.strip() for col in df.columns]

    required_columns = ["Commune", "Lib_com", "Zone", "Lib_zone"]
    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise ValueError(f"Colonnes absentes dans {zonage_path.name}: {missing}")

    mapping = df[required_columns].copy()

    mapping["annee"] = year
    mapping["code_commune"] = mapping["Commune"].astype(str).str.strip()
    mapping["nom_commune"] = mapping["Lib_com"].astype(str).str.strip()
    mapping["zone_num"] = mapping["Zone"].astype(str).str.strip()

    mapping["arrondissement"] = (
        mapping["code_commune"]
        .str[-2:]
        .astype(int)
    )

    mapping["zone_olap"] = (
        "L7501.1."
        + (100 + mapping["zone_num"].astype(int)).astype(str)
    )

    mapping = mapping[
        [
            "annee",
            "code_commune",
            "arrondissement",
            "nom_commune",
            "zone_num",
            "zone_olap",
            "Lib_zone"
        ]
    ].rename(columns={"Lib_zone": "lib_zone"})

    return mapping


def build_silver_loyers() -> None:
    SILVER_LOYERS.mkdir(parents=True, exist_ok=True)

    loyers_frames = []
    mapping_frames = []

    for year in YEARS:
        year_dir = BRONZE_LOYERS / str(year)

        base_path = year_dir / f"Base_OP_{year}_L7501.csv"
        zonage_path = year_dir / f"L7501Zonage{year}.csv"

        if not base_path.exists():
            print(f"Fichier manquant : {base_path}")
            continue

        print(f"Lecture loyers : {base_path.name}")

        df = read_csv_flexible(base_path)
        df.columns = [col.strip() for col in df.columns]

        missing_columns = [col for col in COLUMN_MAPPING if col not in df.columns]

        if missing_columns:
            raise ValueError(
                f"Colonnes absentes dans {base_path.name}: {missing_columns}\n"
                f"Colonnes disponibles: {df.columns.tolist()}"
            )

        df = df.rename(columns=COLUMN_MAPPING)
        df = df[list(COLUMN_MAPPING.values())].copy()

        df["annee"] = pd.to_numeric(df["annee"], errors="coerce").astype("Int64")

        # On garde uniquement les vraies zones de calcul Paris :
        # L7501.1.101 à L7501.1.114
        df = df[
            df["zone_olap"]
            .astype(str)
            .str.match(r"L7501\.1\.1\d{2}$", na=False)
        ].copy()

        # Nettoyage du nombre de pièces
        df["nb_pieces"] = (
            df["nb_pieces"]
            .astype(str)
            .str.strip()
            .replace(["nan", "None", "", "ALL", "All"], "Tous")
        )

        df["nb_pieces_local"] = (
            df["nb_pieces_local"]
            .astype(str)
            .str.strip()
            .replace(["nan", "None", "", "ALL", "All"], "Tous")
        )

        for col in NUMERIC_COLUMNS:
            df[col] = clean_numeric(df[col])

        loyers_frames.append(df)

        # Mapping arrondissement -> zone OLAP
        if zonage_path.exists():
            print(f"Lecture mapping : {zonage_path.name}")
            mapping = build_zone_mapping_from_zonage(zonage_path, year)
            mapping_frames.append(mapping)
        else:
            print(f"Mapping zonage absent pour {year} : {zonage_path.name}")

    if not loyers_frames:
        raise RuntimeError("Aucune donnée de loyers n'a été chargée.")

    loyers_all = pd.concat(loyers_frames, ignore_index=True)

    loyers_output = SILVER_LOYERS / "loyers_clean.parquet"
    loyers_all.to_parquet(loyers_output, index=False)

    print(f"Silver loyers créé : {loyers_output}")
    print(f"Lignes loyers : {len(loyers_all)}")

    if mapping_frames:
        mapping_all = pd.concat(mapping_frames, ignore_index=True)
        mapping_output = SILVER_LOYERS / "mapping_arrondissement_zone.parquet"
        mapping_all.to_parquet(mapping_output, index=False)

        print(f"Silver mapping créé : {mapping_output}")
        print(f"Lignes mapping : {len(mapping_all)}")
    else:
        print("Aucun mapping arrondissement-zone créé.")


if __name__ == "__main__":
    build_silver_loyers()