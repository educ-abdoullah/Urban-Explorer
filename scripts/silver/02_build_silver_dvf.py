from pathlib import Path
import pandas as pd

DATA_LAKE = (Path(__file__).resolve().parents[2] / "data").resolve()


def get_latest_day_dir(base_dir: Path) -> Path:
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"Aucun sous-dossier trouvé dans {base_dir}")
    return sorted(subdirs)[-1]


BRONZE_DVF_BASE = DATA_LAKE / "raw"
SILVER_DVF_BASE = DATA_LAKE / "silver"

BRONZE_DVF = get_latest_day_dir(BRONZE_DVF_BASE)
date_jour = BRONZE_DVF.name
BRONZE_DVF = BRONZE_DVF / "vf"
SILVER_DVF = SILVER_DVF_BASE / date_jour

YEARS = [2022, 2023, 2024, 2025]


USEFUL_COLUMNS = [
    "Date mutation",
    "Nature mutation",
    "Valeur fonciere",
    "No voie",
    "B/T/Q",
    "Type de voie",
    "Code voie",
    "Voie",
    "Code postal",
    "Commune",
    "Code departement",
    "Code commune",
    "Nombre de lots",
    "Code type local",
    "Type local",
    "Surface reelle bati",
    "Nombre pieces principales",
    "Surface terrain"
]


def clean_number(series):
    return (
        series.astype(str)
        .str.replace(",", ".", regex=False)
        .str.replace(" ", "", regex=False)
        .replace(["nan", "None", "", "NaN"], pd.NA)
        .pipe(pd.to_numeric, errors="coerce")
    )


def normalize_code_commune(code_departement, code_commune):
    dep = str(code_departement).strip().replace(".0", "")
    com = str(code_commune).strip().replace(".0", "")

    # Paris : Code departement = 75, Code commune = 101 à 120
    # Résultat attendu : 75101 à 75120
    if dep == "75":
        return "75" + com.zfill(3)

    return dep.zfill(2) + com.zfill(3)


def build_adresse(row):
    parts = [
        row.get("No voie", ""),
        row.get("B/T/Q", ""),
        row.get("Type de voie", ""),
        row.get("Voie", "")
    ]

    return " ".join(
        str(x).strip()
        for x in parts
        if pd.notna(x) and str(x).strip() not in ["", "nan", "None"]
    )


def read_dvf_file(path):
    return pd.read_csv(
        path,
        sep="|",
        encoding="utf-8",
        dtype=str,
        low_memory=False
    )


def build_silver_dvf():
    SILVER_DVF.mkdir(parents=True, exist_ok=True)

    frames = []

    for year in YEARS:
        path = BRONZE_DVF / f"ValeursFoncieres-{year}.txt"

        if not path.exists():
            print(f"Fichier absent : {path}")
            continue

        print(f"Lecture DVF {year} : {path.name}")

        df = read_dvf_file(path)

        missing = [col for col in USEFUL_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(
                f"Colonnes absentes dans {path.name}: {missing}\n"
                f"Colonnes disponibles: {df.columns.tolist()}"
            )

        df = df[USEFUL_COLUMNS].copy()

        # Paris uniquement
        df = df[df["Code departement"].astype(str).str.strip() == "75"].copy()

        # Ventes uniquement
        df = df[
            df["Nature mutation"]
            .astype(str)
            .str.contains("Vente", case=False, na=False)
        ].copy()

        # On garde appartements + maisons en Silver
        df = df[df["Type local"].isin(["Appartement", "Maison"])].copy()

        df["annee"] = pd.to_datetime(
            df["Date mutation"],
            dayfirst=True,
            errors="coerce"
        ).dt.year

        df["valeur_fonciere"] = clean_number(df["Valeur fonciere"])
        df["surface_reelle_bati"] = clean_number(df["Surface reelle bati"])
        df["nombre_pieces"] = clean_number(df["Nombre pieces principales"])
        df["surface_terrain"] = clean_number(df["Surface terrain"])
        df["nombre_lots"] = clean_number(df["Nombre de lots"])

        df["code_commune"] = df.apply(
            lambda row: normalize_code_commune(
                row["Code departement"],
                row["Code commune"]
            ),
            axis=1
        )

        df["arrondissement"] = df["code_commune"].str[-2:].astype(int)
        df["adresse"] = df.apply(build_adresse, axis=1)

        df["prix_m2"] = df["valeur_fonciere"] / df["surface_reelle_bati"]

        df = df[df["annee"].notna()].copy()
        df = df[df["valeur_fonciere"].notna()].copy()
        df = df[df["surface_reelle_bati"].notna()].copy()
        df = df[df["surface_reelle_bati"] > 0].copy()
        df = df[df["prix_m2"].notna()].copy()

        df = df[(df["prix_m2"] >= 1000) & (df["prix_m2"] <= 30000)].copy()

        df = df.rename(columns={
            "Date mutation": "date_mutation",
            "Nature mutation": "nature_mutation",
            "Code postal": "code_postal",
            "Commune": "commune",
            "Type local": "type_local",
            "Code type local": "code_type_local"
        })

        final_columns = [
            "annee",
            "date_mutation",
            "nature_mutation",
            "code_commune",
            "arrondissement",
            "code_postal",
            "commune",
            "adresse",
            "type_local",
            "code_type_local",
            "valeur_fonciere",
            "surface_reelle_bati",
            "nombre_pieces",
            "surface_terrain",
            "nombre_lots",
            "prix_m2"
        ]

        df = df[final_columns].copy()
        frames.append(df)

    if not frames:
        raise RuntimeError("Aucune donnée DVF chargée.")

    silver = pd.concat(frames, ignore_index=True)

    output = SILVER_DVF / "dvf_silver.parquet"
    silver.to_parquet(output, index=False)

    print(f"✅ Silver DVF créée : {output}")
    print(f"✅ Lignes : {len(silver)}")
    print(silver["type_local"].value_counts())
    print("Exemples code_commune :")
    print(silver[["code_commune", "arrondissement", "commune"]].drop_duplicates().head(20))


if __name__ == "__main__":
    build_silver_dvf()