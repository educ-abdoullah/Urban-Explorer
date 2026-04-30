import json
import shutil
import ssl
import urllib.parse
import urllib.request
from pathlib import Path
import os

# ── Configuration ─────────────────────────────────────────────
DOSSIER_SCRIPT = os.path.dirname(os.path.abspath(__file__))
DEST_DIR = os.path.abspath(os.path.join(DOSSIER_SCRIPT, "../../data/raw"))

DATAGOUV_DATASETS = [
    "https://www.data.gouv.fr/datasets/carte-des-pharmacies-de-paris-idf",
    "https://www.data.gouv.fr/datasets/les-etablissements-hospitaliers-franciliens-idf",
]

OPENDATASOFT_DATASETS = [
    {
        "domain": "opendata.paris.fr",
        "dataset_id": "espaces_verts",
        "format": "geojson",
    },
    {
        "domain": "opendata.apur.org",
        "dataset_id": "Apur::bdcom-2023",
        "format": "csv",
    },
    {
        "domain": "data.iledefrance.fr",
        "dataset_id": "recensement_des_equipements_sportifs_a_paris",
        "format": "csv",
    },
]
# ──────────────────────────────────────────────────────────────


def fetch(url: str):
    try:
        return urllib.request.urlopen(url)
    except Exception as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            ctx = ssl._create_unverified_context()
            return urllib.request.urlopen(url, context=ctx)
        raise


def save(url: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Téléchargement : {url[:90]}\n  -> {target}")
    with fetch(url) as r, open(target, "wb") as f:
        shutil.copyfileobj(r, f)
    return target


# ── data.gouv.fr ──────────────────────────────────────────────

def slug_from_url(s: str) -> str:
    parts = urllib.parse.urlparse(s).path.strip("/").split("/")
    if "datasets" in parts:
        return parts[parts.index("datasets") + 1]
    return parts[-1]


def get_best_resource(slug: str) -> dict:
    with fetch(f"https://www.data.gouv.fr/api/1/datasets/{slug}/") as r:
        resources = json.load(r).get("resources", [])
    for fmt_target in ["csv", "text/csv", "geojson"]:
        for res in resources:
            fmt = (res.get("format") or "").lower()
            if fmt == fmt_target or fmt_target in (res.get("url") or "").lower():
                return res
    if resources:
        return resources[0]
    raise RuntimeError(f"Aucune ressource trouvée pour '{slug}'.")


def download_datagouv(url: str, dest_dir: str = DEST_DIR) -> Path:
    slug     = slug_from_url(url)
    resource = get_best_resource(slug)
    src_url  = resource["url"]
    filename = src_url.split("/")[-1].split("?")[0] or slug
    return save(src_url, Path(dest_dir) / filename)


# ── Opendatasoft ───────────────────────────────────────────────

def download_opendatasoft(dataset: dict, dest_dir: str = DEST_DIR) -> Path:
    domain     = dataset["domain"]
    dataset_id = dataset["dataset_id"]
    fmt        = dataset["format"]
    url = (
        f"https://{domain}/api/explore/v2.1/catalog/datasets/"
        f"{urllib.parse.quote(dataset_id, safe='')}/exports/{fmt}"
        f"?limit=-1&timezone=Europe/Paris"
    )
    filename = f"{dataset_id.split('::')[-1]}.{fmt}"
    return save(url, Path(dest_dir) / filename)


# ── Main ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== data.gouv.fr ===")
    for url in DATAGOUV_DATASETS:
        try:
            path = download_datagouv(url)
            print(f"✅ Sauvegardé : {path}\n")
        except Exception as e:
            print(f"❌ Erreur ({url}) : {e}\n")

    print("=== Opendatasoft ===")
    for ds in OPENDATASOFT_DATASETS:
        try:
            path = download_opendatasoft(ds)
            print(f"✅ Sauvegardé : {path}\n")
        except Exception as e:
            print(f"❌ Erreur ({ds['dataset_id']}) : {e}\n")