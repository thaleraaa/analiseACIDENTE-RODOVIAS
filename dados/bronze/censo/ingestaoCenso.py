import requests
import urllib3
import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BRONZE = Path("dados/bronze/censo")
BRONZE.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados",
}

ANOS = list(range(2009, 2022, 3))  # 2009, 2012, 2015, 2018, 2021

def url_censo(ano):
    return (
        f"https://download.inep.gov.br/microdados/"
        f"microdados_censo_da_educacao_superior_{ano}.zip"
    )

def checar_existe(url):
    try:
        r = requests.head(url, headers=HEADERS, verify=False, timeout=15)
        return r.status_code == 200
    except Exception:
        return False

def extrair_e_filtrar(zip_path: Path, destino_dir: Path) -> list[Path]:
    print(f"  → Extraindo {zip_path.name}...")
    destino_dir.mkdir(exist_ok=True)

    SUFIXOS_OK = {".CSV", ".XLSX"}
    PREFIXOS_SKIP = {"~$", "thumbs"}
    NOMES_SKIP = {"IES"}  # ignora MICRODADOS_CADASTRO_IES_*.CSV

    arquivos_ok = []

    with zipfile.ZipFile(zip_path, "r") as z:
        for membro in z.namelist():
            p = Path(membro)
            nome = p.name
            sufixo = p.suffix.upper()

            if (
                membro.endswith("/")
                or sufixo not in SUFIXOS_OK
                or any(nome.lower().startswith(s) for s in PREFIXOS_SKIP)
                or any(skip in nome.upper() for skip in NOMES_SKIP)  # <-- novo
            ):
                continue

            dados = z.read(membro)
            destino_arquivo = destino_dir / nome
            destino_arquivo.write_bytes(dados)
            arquivos_ok.append(destino_arquivo)
            print(f"     ✓ {nome}")

    zip_path.unlink()
    print(f"  → .zip removido após extração")
    return arquivos_ok

def limpar_extraidos_antigos(ano: int):
    """Remove subpasta com estrutura antiga (caso já tenha sido extraído antes)."""
    pasta_antiga = BRONZE / str(ano)
    if pasta_antiga.exists():
        shutil.rmtree(pasta_antiga)
        print(f"  → Pasta antiga {pasta_antiga} removida")

def registrar(url: str, zip_nome: str, arquivos: list[Path], ano: int):
    info = {
        "fonte": url,
        "arquivo_zip_original": zip_nome,
        "arquivos_bronze": [str(a.relative_to(BRONZE)) for a in arquivos],
        "tamanho_total_bytes": sum(a.stat().st_size for a in arquivos),
        "extraido_em": datetime.now().isoformat(),
    }
    prov_path = BRONZE / f"proveniencia_censo_{ano}.json"
    prov_path.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  → Proveniência salva: {prov_path.name}")

def baixar(ano: int) -> bool:
    url = url_censo(ano)
    zip_path = BRONZE / f"censo_{ano}.zip"
    prov = BRONZE / f"proveniencia_censo_{ano}.json"

    # Já processado corretamente
    if prov.exists() and not zip_path.exists():
        # Verifica se proveniência não está vazia
        try:
            dados = json.loads(prov.read_text(encoding="utf-8"))
            if dados.get("arquivos_bronze"):
                print(f"\n[{ano}] já extraído anteriormente, pulando.")
                return True
        except Exception:
            pass
        # Proveniência vazia ou inválida — limpa e reprocessa
        prov.unlink(missing_ok=True)

    # Limpa extração antiga com estrutura de subpastas
    limpar_extraidos_antigos(ano)

    # Zip já baixado mas não extraído
    if zip_path.exists():
        print(f"\n[{ano}] .zip encontrado localmente, extraindo...")
        try:
            arquivos = extrair_e_filtrar(zip_path, BRONZE / str(ano))
            registrar(url, zip_path.name, arquivos, ano)
            print(f"[{ano}] ✓ Concluído")
            return True
        except Exception as e:
            print(f"[{ano}] ✗ Erro na extração: {e}")
            return False

    print(f"\n[{ano}] Verificando disponibilidade...")
    if not checar_existe(url):
        print(f"[{ano}] ✗ Não encontrado no servidor — ignorado.")
        return False

    print(f"[{ano}] Baixando...")
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
        arquivos = extrair_e_filtrar(zip_path, BRONZE / str(ano))
        registrar(url, zip_path.name, arquivos, ano)
        print(f"[{ano}] ✓ Concluído")
        return True
    except Exception as e:
        print(f"[{ano}] ✗ Erro na extração: {e}")
        return False

# ─── Execução ────────────────────────────────────────────────────────────────
anos_ok = []
anos_falha = []

for ano in ANOS:
    ok = baixar(ano)
    (anos_ok if ok else anos_falha).append(ano)

print("\n" + "="*50)
print(f"✓ Concluídos: {anos_ok}")
print(f"✗ Ignorados/falha: {anos_falha}")