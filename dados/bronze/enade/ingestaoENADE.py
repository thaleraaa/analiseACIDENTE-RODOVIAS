import requests
import urllib3
import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

try:
    import py7zr
except ImportError:
    raise ImportError("Instale py7zr: pip install py7zr")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BRONZE_CENSO = Path("dados/bronze/censo")
BRONZE_ENADE = Path("dados/bronze/enade")
BRONZE_ENADE.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados",
}

ENADE_URLS = {
    2009: "https://download.inep.gov.br/microdados/microdados_enade_2009.zip",
    2012: "https://download.inep.gov.br/microdados/microdados_enade_2012_LGPD.zip",
    2015: "https://download.inep.gov.br/microdados/microdados_enade_2015_LGPD.zip",
    2018: "https://download.inep.gov.br/microdados/microdados_enade_2018_LGPD.zip",
    2021: "https://download.inep.gov.br/microdados/microdados_enade_2021.zip",
}

# Sufixos a manter: dados em .txt e .csv, dicionário em .xlsx e .ods
SUFIXOS_OK = {".TXT", ".CSV", ".XLSX", ".ODS"}
PREFIXOS_SKIP = {"~$", "thumbs"}

def censo_ok(ano: int) -> bool:
    prov = BRONZE_CENSO / f"proveniencia_censo_{ano}.json"
    if not prov.exists():
        return False
    try:
        dados = json.loads(prov.read_text(encoding="utf-8"))
        return bool(dados.get("arquivos_bronze"))
    except Exception:
        return False

def is_7z(path: Path) -> bool:
    with open(path, "rb") as f:
        return f.read(6) == b"7z\xbc\xaf'\x1c"

def extrair_e_filtrar(zip_path: Path, destino_dir: Path) -> list[Path]:
    print(f"  → Detectando formato de {zip_path.name}...")
    destino_dir.mkdir(exist_ok=True)
    arquivos_ok = []

    def deve_incluir(nome_arquivo: str) -> bool:
        p = Path(nome_arquivo)
        sufixo = p.suffix.upper()
        nome = p.name
        return (
            sufixo in SUFIXOS_OK
            and not any(nome.lower().startswith(s) for s in PREFIXOS_SKIP)
        )

    if is_7z(zip_path):
        print(f"  → Formato: 7z")
        with py7zr.SevenZipFile(zip_path, mode="r") as z:
            nomes = [n for n in z.getnames() if deve_incluir(n)]
            z.extract(targets=nomes, path=destino_dir)
        # Achata subpastas — move tudo pra destino_dir raiz
        for arquivo in destino_dir.rglob("*"):
            if arquivo.is_file() and deve_incluir(arquivo.name):
                destino_final = destino_dir / arquivo.name
                if arquivo != destino_final:
                    arquivo.rename(destino_final)
                arquivos_ok.append(destino_final)
                print(f"     ✓ {arquivo.name}")
        # Remove subpastas vazias
        for pasta in sorted(destino_dir.rglob("*"), reverse=True):
            if pasta.is_dir():
                try:
                    pasta.rmdir()
                except OSError:
                    pass
    else:
        print(f"  → Formato: zip")
        with zipfile.ZipFile(zip_path, "r") as z:
            for membro in z.namelist():
                if membro.endswith("/") or not deve_incluir(membro):
                    continue
                dados = z.read(membro)
                nome = Path(membro).name
                destino_arquivo = destino_dir / nome
                destino_arquivo.write_bytes(dados)
                arquivos_ok.append(destino_arquivo)
                print(f"     ✓ {nome}")

    zip_path.unlink()
    print(f"  → Arquivo original removido após extração")
    return arquivos_ok

def limpar_extraidos_antigos(ano: int):
    pasta_antiga = BRONZE_ENADE / str(ano)
    if pasta_antiga.exists():
        shutil.rmtree(pasta_antiga)
        print(f"  → Pasta antiga removida")

def registrar(url: str, zip_nome: str, arquivos: list[Path], ano: int):
    info = {
        "fonte": url,
        "arquivo_zip_original": zip_nome,
        "arquivos_bronze": [str(a.relative_to(BRONZE_ENADE)) for a in arquivos],
        "tamanho_total_bytes": sum(a.stat().st_size for a in arquivos),
        "extraido_em": datetime.now().isoformat(),
    }
    prov_path = BRONZE_ENADE / f"proveniencia_enade_{ano}.json"
    prov_path.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  → Proveniência salva: {prov_path.name}")

def baixar(ano: int) -> bool:
    url = ENADE_URLS[ano]
    zip_path = BRONZE_ENADE / f"enade_{ano}.zip"
    prov = BRONZE_ENADE / f"proveniencia_enade_{ano}.json"

    if not censo_ok(ano):
        print(f"\n[{ano}] ✗ Censo {ano} não processado — par ignorado.")
        return False

    if prov.exists() and not zip_path.exists():
        try:
            dados = json.loads(prov.read_text(encoding="utf-8"))
            if dados.get("arquivos_bronze"):
                print(f"\n[{ano}] já extraído anteriormente, pulando.")
                return True
        except Exception:
            pass
        prov.unlink(missing_ok=True)

    limpar_extraidos_antigos(ano)

    if zip_path.exists():
        print(f"\n[{ano}] arquivo encontrado localmente, extraindo...")
        try:
            arquivos = extrair_e_filtrar(zip_path, BRONZE_ENADE / str(ano))
            registrar(url, zip_path.name, arquivos, ano)
            print(f"[{ano}] ✓ Concluído")
            return True
        except Exception as e:
            print(f"[{ano}] ✗ Erro na extração: {e}")
            return False

    print(f"\n[{ano}] Baixando {url} ...")
    try:
        with requests.get(url, headers=HEADERS, stream=True, timeout=300, verify=False) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0))
            with open(zip_path, "wb") as f, tqdm(
                total=total, unit="B", unit_scale=True, desc=str(ano)
            ) as bar:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
                    bar.update(len(chunk))
    except Exception as e:
        print(f"[{ano}] ✗ Erro no download: {e}")
        zip_path.unlink(missing_ok=True)
        return False

    try:
        arquivos = extrair_e_filtrar(zip_path, BRONZE_ENADE / str(ano))
        registrar(url, zip_path.name, arquivos, ano)
        print(f"[{ano}] ✓ Concluído")
        return True
    except Exception as e:
        print(f"[{ano}] ✗ Erro na extração: {e}")
        return False

# ─── Execução ────────────────────────────────────────────────────────────────
anos_ok = []
anos_falha = []

for ano in ENADE_URLS:
    ok = baixar(ano)
    (anos_ok if ok else anos_falha).append(ano)

print("\n" + "="*50)
print(f"✓ Concluídos: {anos_ok}")
print(f"✗ Ignorados/falha: {anos_falha}")
print(f"\nPares válidos Censo+ENADE: {anos_ok}")