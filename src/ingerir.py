from pathlib import Path
import zipfile
import json
import shutil
import logging
from datetime import datetime

from config import BRONZE, PRATA


log = logging.getLogger(__name__)

# ── Caminhos ──────────────────────────────────────────────────────────────────
BRONZE_PRF = BRONZE / "PRF"
BRONZE_DNIT = BRONZE / "DNIT"

# ── Data de coleta manual ─────────────────────────────────────────────────────
DATA_COLETA_PRF  = "2026-09-11"
DATA_COLETA_DNIT = "2026-09-11"

FONTE_PRF  = "https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf"
FONTE_DNIT = "https://servicos.dnit.gov.br/dnitcloud/index.php/s/oTpPRmYs5AAdiNr?path=%2FSNV%20Planilhas%20(2011-Atual)%20(XLS)"

# ── Helpers ───────────────────────────────────────────────────────────────────

def localizar_zips(pasta: Path) -> list[Path]:
    zips = sorted(pasta.glob("*.zip"))
    if not zips:
        raise FileNotFoundError(f"Nenhum .zip encontrado em {pasta}")
    log.info("%s: %s arquivo(s) encontrado(s)", pasta.name, len(zips))
    for z in zips:
        log.debug("%s: arquivo %s", pasta.name, z.name)
    return zips


def extrair(zip_path: Path, destino: Path) -> list[Path]:
    """Extrai um zip na pasta destino/<stem>/ e retorna os arquivos extraídos."""
    pasta_saida = destino / zip_path.stem
    pasta_saida.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(pasta_saida)

    arquivos = list(pasta_saida.glob("**/*.csv")) + list(pasta_saida.glob("**/*.xls")) + list(pasta_saida.glob("**/*.xlsx"))
    log.info(
        "%s: %s extraido para %s (%s arquivo(s))",
        destino.name,
        zip_path.name,
        pasta_saida,
        len(arquivos),
    )
    return arquivos

def registrar_proveniencia(fonte: Path, csvs: list[Path], destino: Path, data_coleta: str, url_fonte: str):
    info = {
        "url_fonte": url_fonte,
        "fonte": str(fonte),
        "arquivos_extraidos": [str(c) for c in csvs],
        "baixado_em": data_coleta,
        "extraido_em": datetime.now().isoformat(),
    }
    arquivo = destino / "proveniencia.json"

    # Acumula em vez de sobrescrever — mantém histórico de todas as fontes
    historico: list = []
    if arquivo.exists():
        historico = json.loads(arquivo.read_text(encoding="utf-8"))
    historico.append(info)

    arquivo.write_text(json.dumps(historico, indent=2, ensure_ascii=False), encoding="utf-8")

# ── Pipeline ──────────────────────────────────────────────────────────────────

def ingerir_fonte(bronze_pasta: Path, label: str, data_coleta: str, url_fonte: str):
    log.info("Ingestao: iniciando %s", label)

    zips = localizar_zips(bronze_pasta)
    todos_csvs: list[Path] = []

    for zip_path in zips:
        csvs = extrair(zip_path, bronze_pasta)
        registrar_proveniencia(zip_path, csvs, bronze_pasta, data_coleta, url_fonte)
        todos_csvs.extend(csvs)

    log.info(
        "Ingestao: %s concluida com %s arquivo(s) extraido(s)",
        label,
        len(todos_csvs),
    )
    return todos_csvs


def main():
    ingerir_fonte(BRONZE_PRF,  label="PRF",  data_coleta=DATA_COLETA_PRF,  url_fonte=FONTE_PRF)
    ingerir_fonte(BRONZE_DNIT, label="DNIT", data_coleta=DATA_COLETA_DNIT, url_fonte=FONTE_DNIT)


if __name__ == "__main__":
    main()