from pathlib import Path
import pandas as pd
from data_profiling import ProfileReport

RELATORIOS = Path("relatorios")

FONTES = [
    {"bronze": Path("dados/bronze/PRF"),  "padrao": "**/*.csv",  "label": "PRF"},
    {"bronze": Path("dados/bronze/DNIT"), "padrao": "**/*.xls",  "label": "DNIT"},
]


def mais_recente(bronze: Path, padrao: str) -> Path:
    arquivos = sorted(bronze.glob(padrao))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo encontrado em {bronze} com padrão {padrao}")
    return arquivos[-1]


def gerar(caminho: Path, label: str) -> Path:
    if caminho.suffix == ".csv":
        df = pd.read_csv(caminho, encoding="latin-1", sep=";")
    else:
        df = pd.read_excel(caminho, header=2)

    perfil = ProfileReport(df, title=f"{label} — {caminho.name}")
    RELATORIOS.mkdir(exist_ok=True)
    saida = RELATORIOS / f"{label}_{caminho.stem}.html"
    perfil.to_file(saida)
    return saida


def main():
    for fonte in FONTES:
        caminho = mais_recente(fonte["bronze"], fonte["padrao"])
        print(f"[{fonte['label']}] perfilando: {caminho.name}")
        saida = gerar(caminho, fonte["label"])
        print(f"[{fonte['label']}] relatório → {saida}")


if __name__ == "__main__":
    main()