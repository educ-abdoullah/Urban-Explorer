"""Silver layer pipeline for the Urban-Explorer project.

This script applies the common Silver-cleaning steps to every CSV file:
- standardize column names
- normalize missing values
- trim and clean text fields
- infer basic types (numeric, boolean, date)
- remove duplicates
- optionally keep Paris-only rows
"""

from __future__ import annotations

import csv
import re
import sys
import unicodedata
from pathlib import Path
from typing import Final

import pandas as pd

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
RAW_DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
SILVER_DATA_DIR: Final[Path] = RAW_DATA_DIR / "silver"
KEEP_PARIS_ONLY: Final[bool] = True

MISSING_MARKERS: Final[list[str]] = [
    "",
    " ",
    "NA",
    "N/A",
    "na",
    "n/a",
    "null",
    "NULL",
    "None",
    "none",
    "-",
    "--",
    "Non renseigne",
    "Non renseigné",
]

COMMON_COLUMN_NAMES: Final[dict[str, str]] = {
    "cp": "postal_code",
    "code_post": "postal_code",
    "code_postal": "postal_code",
    "code_posta": "postal_code",
    "commune_nom": "commune_name",
    "libelle_co": "commune_name",
    "localite_a": "commune_name",
    "nomcom": "commune_name",
    "commune": "commune_name",
    "code_commu": "commune_code",
    "commune_insee": "commune_code",
    "insee": "commune_code",
    "code_depar": "department_code",
    "numdep": "department_code",
    "departement": "department_code",
    "num_dept": "department_code",
    "libdepartement": "department_name",
    "dept": "department_name",
    "arro": "arrondissement",
    "lat": "latitude",
    "latitude": "latitude",
    "lng": "longitude",
    "lon": "longitude",
    "long": "longitude",
    "coordonnees": "coordinates",
    "wgs84": "coordinates",
    "x": "x_coord",
    "y": "y_coord",
    "identifiant_espace_vert": "green_space_id",
    "nom_de_l_espace_vert": "nom",
    "typologie_d_espace_vert": "green_space_type",
    "adresse_numero": "address_number",
    "adresse_complement": "address_complement",
    "adresse_type_voie": "street_type",
    "adresse_libelle_voie": "street_name",
    "surface_calculee": "calculated_surface_m2",
    "superficie_totale_reelle": "total_surface_m2",
    "surface_horticole": "horticultural_surface_m2",
    "presence_cloture": "has_fence",
    "annee_de_l_ouverture": "opening_year",
    "annee_de_renovation": "renovation_year",
    "ouverture_24h_24h": "open_24h",
}

PARIS_DEPARTMENT_CODES: Final[set[str]] = {"75", "075"}
PARIS_COMMUNE_CODES: Final[set[str]] = {str(code) for code in range(75101, 75121)} | {"75056"}
PARIS_POSTAL_PREFIX: Final[str] = "75"
PRIORITY_COLUMNS: Final[list[str]] = [
    "objectid",
    "id",
    "green_space_id",
    "nom",
    "type",
    "category",
    "arrondissement",
    "commune_code",
    "commune_name",
    "postal_code",
    "department_code",
    "department_name",
    "address",
    "adresse",
    "adresse_complete",
    "latitude",
    "longitude",
    "coordinates",
    "geo_point",
    "geo_shape",
    "x_coord",
    "y_coord",
]


def to_snake_case(text: str) -> str:
    """Convert a column name to a clean snake_case string."""
    normalized = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def load_csv_safely(file_path: Path) -> pd.DataFrame:
    """Read a CSV by auto-detecting the separator and trying common encodings."""
    last_error: Exception | None = None

    max_csv_field_size = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_csv_field_size)
            break
        except OverflowError:
            max_csv_field_size = int(max_csv_field_size / 10)

    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            if file_path.name == "espaces_verts.csv":
                return pd.read_csv(file_path, sep=";", encoding=encoding)
            return pd.read_csv(file_path, sep=None, engine="python", encoding=encoding)
        except Exception as error:  # pragma: no cover - fallback logic
            last_error = error

    raise ValueError(f"Unable to read {file_path.name}: {last_error}")


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize headers and harmonize common geographic names."""
    cleaned_columns = []

    for column in df.columns:
        normalized = to_snake_case(column)
        cleaned_columns.append(COMMON_COLUMN_NAMES.get(normalized, normalized))

    df = df.copy()
    df.columns = cleaned_columns
    df = df.loc[:, ~df.columns.duplicated()].copy()
    return df


def clean_text_value(value: object) -> object:
    """Normalize text spacing and replace common empty markers with NA."""
    if pd.isna(value):
        return pd.NA

    if isinstance(value, str):
        cleaned = re.sub(r"\s+", " ", value).strip()
        return pd.NA if cleaned in MISSING_MARKERS else cleaned

    return value


def normalize_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Replace empty markers and trim whitespace in object columns."""
    df = df.copy()

    for column in df.columns:
        if df[column].dtype == "object":
            df[column] = df[column].map(clean_text_value)

    return df


def convert_boolean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert columns such as true/false, oui/non, 0/1 into booleans."""
    df = df.copy()
    truthy = {"true", "vrai", "oui", "yes", "1"}
    falsy = {"false", "faux", "non", "no", "0"}

    for column in df.columns:
        if df[column].dtype != "object":
            continue

        non_null = df[column].dropna().astype(str).str.lower().str.strip()
        if non_null.empty:
            continue

        unique_values = set(non_null.unique())
        if unique_values and unique_values.issubset(truthy | falsy):
            df[column] = non_null.map(lambda value: value in truthy).reindex(df.index)

    return df


def convert_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert obvious date columns to datetime."""
    df = df.copy()

    for column in df.columns:
        if "date" in column and df[column].dtype == "object":
            converted = pd.to_datetime(df[column], errors="coerce")
            if converted.notna().sum() > 0:
                df[column] = converted

    return df


def convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Try to cast text columns to numeric when most values look numeric."""
    df = df.copy()

    for column in df.columns:
        if df[column].dtype != "object":
            continue

        cleaned_series = (
            df[column]
            .astype("string")
            .str.replace("\u202f", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        converted = pd.to_numeric(cleaned_series, errors="coerce")

        original_non_null = df[column].notna().sum()
        converted_non_null = converted.notna().sum()

        if original_non_null > 0 and converted_non_null / original_non_null >= 0.8:
            df[column] = converted

    return df


def extract_lat_lon_from_geo_point(df: pd.DataFrame) -> pd.DataFrame:
    """Split `geo_point` strings into usable latitude and longitude columns."""
    if "geo_point" not in df.columns:
        return df

    df = df.copy()
    extracted = df["geo_point"].astype("string").str.extract(
        r"(?P<latitude>-?\d+(?:\.\d+)?)\s*,\s*(?P<longitude>-?\d+(?:\.\d+)?)"
    )

    parsed_latitude = pd.to_numeric(extracted["latitude"], errors="coerce")
    parsed_longitude = pd.to_numeric(extracted["longitude"], errors="coerce")

    if "latitude" in df.columns:
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce").fillna(parsed_latitude)
    else:
        df["latitude"] = parsed_latitude

    if "longitude" in df.columns:
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce").fillna(parsed_longitude)
    else:
        df["longitude"] = parsed_longitude

    return df


def filter_paris_only(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only Paris rows when a geographic identifier is available."""
    conditions: list[pd.Series] = []

    if "department_code" in df.columns:
        department = df["department_code"].astype("string").str.extract(r"(\d+)", expand=False)
        conditions.append(department.isin(PARIS_DEPARTMENT_CODES))

    if "postal_code" in df.columns:
        postal_code = df["postal_code"].astype("string").str.extract(r"(\d{5})", expand=False)
        conditions.append(postal_code.str.startswith(PARIS_POSTAL_PREFIX, na=False))

    if "commune_code" in df.columns:
        commune_code = df["commune_code"].astype("string").str.extract(r"(\d+)", expand=False)
        conditions.append(commune_code.isin(PARIS_COMMUNE_CODES))

    if "commune_name" in df.columns:
        commune_name = df["commune_name"].astype("string").str.upper().str.strip()
        conditions.append(commune_name.str.startswith("PARIS", na=False))

    if not conditions:
        return df.copy()

    paris_mask = conditions[0].fillna(False)
    for condition in conditions[1:]:
        paris_mask = paris_mask | condition.fillna(False)

    return df.loc[paris_mask].copy().reset_index(drop=True)


def reorder_columns_consistently(df: pd.DataFrame) -> pd.DataFrame:
    """Place common identifier/geography columns first, then sort the rest."""
    priority_columns = [column for column in PRIORITY_COLUMNS if column in df.columns]
    remaining_columns = sorted(column for column in df.columns if column not in priority_columns)
    return df[priority_columns + remaining_columns]


def clean_dataset(file_path: Path, keep_paris_only: bool = True) -> tuple[pd.DataFrame, dict[str, int]]:
    """Apply the common Silver-layer cleaning steps to one dataset."""
    df = load_csv_safely(file_path)
    rows_before = len(df)

    df = standardize_column_names(df)
    df = normalize_missing_values(df)
    df = convert_boolean_columns(df)
    df = convert_date_columns(df)
    df = convert_numeric_columns(df)
    df = extract_lat_lon_from_geo_point(df)

    if keep_paris_only:
        df = filter_paris_only(df)

    if file_path.name == "BDCOM_2023.csv":
        df = df.drop(columns=[
            "c_ord", "qua", "seq", "sit", "typecodact", "ens", "bio", "surf", "cc_id", "cc_niv", "niv47","niv8", "niv2"
        ], errors="ignore")
    elif file_path.name == "carte-des-pharmacies-de-paris.csv":
        df = df.drop(columns=[
            "nofinesset","nofinessej","rslongue","complrs","department_code","department_name","commune_name","telephone","telecopie","dateouv","dateautor","datemaj",
        ], errors="ignore")
    elif file_path.name == "Colleges_ile-de-France.csv":
        df = df.drop(columns=[
            "id","numero_uai","appellatio","patronyme_","lieu_dit_u","localite_a","libelle_co","code_depar","code_acade","commune_code"
        ], errors="ignore")
    elif file_path.name == "Ecoles_elementaires_et_maternelles_ile-de-France.csv":
        df = df.drop(columns=[
            "id","numero_uai","appellatio","patronyme_","lieu_dit_u","boite_post","localite_a","libelle_co","localisati","nature_uai","code_depar","code_acade","code_commu"
        ], errors="ignore")
    elif file_path.name == "espaces_verts.csv":
        unwanted_types = [
        "Périphérique",
        "Décorations sur la voie publique",
        "Murs végétalisés",
        "Jardinets décoratifs"
        ]
        df = df[~df["green_space_type"].isin(unwanted_types)]
        df = df.drop(columns=[
            "ancien_nom_de_l_espace_vert","annee_de_changement_de_nom","nombre_d_entites","id_division","id_atelier_horticole","ida3d_enb","site_villes","id_eqpt","url_plan","last_edited_user","last_edited_date",
        ], errors="ignore")
    elif file_path.name == "les_etablissements_hospitaliers_franciliens.csv":
        df = df.drop(columns=[
            "finess_et","finess_ej","adresse_administrative_1","adresse_administrative_2","num_type","num_siret","code_ape","code_tarif","lib_tarification","code_psph","date_ouverture","num_voie","cpt_num","type_voie","voie","department_code","department_name",
        ], errors="ignore")
    elif file_path.name == "Lycees_ile-de-France.csv":
        df = df.drop(columns=[
            "finess_et","finess_ej","patronyme","lieu_dit_u","boite_post","commune_name","appariemen","localisati","nature_uai","department_code","code_acade","libelle_ac","contrat","id","nom",
        ], errors="ignore")
    elif file_path.name == "recensement_des_equipements_sportifs_a_paris.csv":
        df = df.drop(columns=[
            "numero_de_l_installation_sportive","commune_code","date_de_creation_de_la_fiche_d_enquete","date_de_changement_d_etat_de_la_fiche_d_enquete","date_de_l_enquete","accessibilite_de_l_installation_en_transport_en_commun","installation_particuliere","type_de_particularite_de_l_installation_brute","type_de_particularite_de_l_installation","siret_installation","unite_administrative_immatriculee_uai","numero_de_l_equipement_sportif","code_du_type_d_equipement_sportif",
            "qpv","qpv_a_200_metres","gen_2024fin_labellisation","activite_niveau","department_code","eclairage_de_l_aire_d_evolution","equipement_d_acces_libre","arrete_d_ouverture_au_public","locaux_complementaires","ouverture_exclusivement_saisonniere","presence_de_douches","presence_de_sanitaires","gestion_en_dsp","accessibilite_aux_personnes_a_mobilite_reduite_a_l_accueil","accessibilite_aux_personnes_a_mobilite_reduite_a_l_aire_de_jeu","accessibilite_aux_personnes_a_mobilite_reduite_aux_cheminements","accessibilite_aux_personnes_a_mobilite_reduite_aux_douches","accessibilite_aux_personnes_a_mobilite_reduite_aux_sanitaires","accessibilite_aux_personnes_a_mobilite_reduite_aux_tribunes","accessibilite_aux_personnes_a_mobilite_reduite_aux_vestiaires","accessibilite_aux_personnes_en_situation_de_handicap_sensoriel_a_l_aire_de_jeu","accessibilite_aux_personnes_en_situation_de_handicap_sensoriel_aux_cheminements","accessibilite_aux_personnes_en_situation_de_handicap_sensoriel_aux_sanitaires","accessibilite_aux_personnes_en_situation_de_handicap_sensoriel_signaletique","accessibilite_aux_personnes_en_situation_de_handicap_sensoriel_aux_tribunes","accessibilite_aux_personnes_en_situation_de_handicap_sensoriel_aux_vestiaires","date_de_l_homologation_prefectorale","date_des_derniers_gros_travaux","categorie_erp_de_l_etablissement","hauteur_de_l_aire_d_evolution","largeur_de_l_aire_d_evolution","longueur_de_l_aire_d_evolution","surface_de_l_aire_d_evolution","nombre_de_couloirs_pistes_postes_jeux_pas","nombre_de_places_assises_en_tribune","nombre_de_vestiaires_arbitres_enseignants","nombre_de_vestiaires_sportifs","sae_nombre_de_couloirs_de_la_structure","sae_hauteur_maximale_de_la_structure","sae_surface_totale_de_la_structure","longueur_du_bassin","largeur_du_bassin","surface_du_bassin","profondeur_minimale_du_bassin","profondeur_maximale_du_bassin","longueur_de_la_piste","adresse_internet_de_l_equipement","annee_de_mise_en_service","nom_du_proprietaire","observation_equipement",
            "type_d_erp_de_l_etablissement","types_de_locaux_complementaires","motifs_des_derniers_gros_travaux","types_de_chauffage_source_d_energie","type_d_utilisation","type_de_pas_de_tir","nature_de_l_equipement_sportif","nature_du_sol","periode_de_mise_en_service","periode_de_l_homologation_prefectorale","periode_des_derniers_gros_travaux","type_de_proprietaire","type_de_proprietaire_secondaire","type_de_gestionnaire","type_du_co_gestionnaire","equipement_inscrit_au_pdesi_pdipr","equip_aps_code","epci_insee"
        ], errors="ignore")
        df = df.drop(columns=[
            "epci_nom","bassin_de_vie_code","bassin_de_vie_nom","arrondissement_code","arrondissement_nom","departement_code_complet","departement_nom","rectorat_nom","region_code","region_nom","densite_niveau","densite_categorie","zrr_simplifie","accessibilite_aux_personnes_a_mobilite_reduite","accessibilite_aux_personnes_en_situation_de_handicap_sensoriel","rnb_id","observation_installation","categorie","discipline","accessibilite_de_l_installation_en_fonction_du_type_handicap","installation_hors_service","famille_d_equipement_sportif","type_d_equipement_sportif"
        ], errors="ignore")
        
    
    rows_before_dedup = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    duplicates_removed = rows_before_dedup - len(df)

    df = reorder_columns_consistently(df)

    summary = {
        "rows_before": rows_before,
        "rows_after": len(df),
        "duplicates_removed": duplicates_removed,
    }
    return df, summary


def run_silver_pipeline() -> None:
    """Clean every raw CSV and save the result in data/silver/."""
    SILVER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(path for path in RAW_DATA_DIR.glob("*.csv"))
    if not csv_files:
        print("No CSV files found in the data folder.")
        return

    print("Starting Silver pipeline...\n")

    for file_path in csv_files:
        cleaned_df, summary = clean_dataset(file_path, keep_paris_only=KEEP_PARIS_ONLY)
        csv_output_path = SILVER_DATA_DIR / file_path.name
        parquet_output_path = SILVER_DATA_DIR / f"{file_path.stem}.parquet"

        cleaned_df.to_csv(csv_output_path, index=False)
        cleaned_df.to_parquet(parquet_output_path, index=False)

        print(
            f"- {file_path.name}: "
            f"{summary['rows_before']} rows -> {summary['rows_after']} rows | "
            f"duplicates removed: {summary['duplicates_removed']} | "
            f"saved: {csv_output_path.name}, {parquet_output_path.name}"
        )

    print(f"\nSilver files saved to: {SILVER_DATA_DIR}")


if __name__ == "__main__":
    run_silver_pipeline()
