"""Unit tests for `pyauditor.excel.equipe` (spec competencia-cli-equipe §6:
fonte única dos responsáveis, padrão objetos.py)."""

from pathlib import Path

import pytest

from pyauditor.excel.equipe import EQUIPE_FILENAME, read_equipe


def _escreve(tmp_path: Path, conteudo: str, *, encoding: str = "utf-8") -> Path:
    path = tmp_path / EQUIPE_FILENAME
    path.write_text(conteudo, encoding=encoding)
    return path


_CABECALHO = "FUNÇÃO,NOME,SIAPE"


class TestReadEquipe:
    def test_mapeia_as_quatro_funcoes_normalizando_caixa_e_acento(self, tmp_path: Path) -> None:
        path = _escreve(
            tmp_path,
            f"{_CABECALHO}\n"
            "Gestor do Contrato,João Antônio Carvalho Monteiro de Oliveira,1499628\n"
            "FISCAL TÉCNICO,Maria Souza,1111111\n"
            "fiscal requisitante,José Lima,2222222\n"
            "Fiscal Administrativo,Ana Paula,3333333\n",
        )
        equipe = read_equipe(path)
        assert equipe.warnings == ()
        campos = equipe.responsaveis_fields()
        assert set(campos) == {
            "Gestor do contrato",
            "Fiscal técnico",
            "Fiscal requisitante",
            "Fiscal administrativo",
        }
        assert campos["Gestor do contrato"] == (
            "João Antônio Carvalho Monteiro de Oliveira (1499628)"
        )

    def test_espacos_extras_sao_tolerados(self, tmp_path: Path) -> None:
        path = _escreve(
            tmp_path,
            f"{_CABECALHO}\n  Gestor   do contrato ,Maria Souza,1111111\n",
        )
        equipe = read_equipe(path)
        assert equipe.cell("gestor DO contrato") == "Maria Souza (1111111)"

    def test_celula_formato_nome_siape(self, tmp_path: Path) -> None:
        path = _escreve(tmp_path, f"{_CABECALHO}\nFiscal técnico,Maria Souza,1111111\n")
        assert read_equipe(path).cell("Fiscal técnico") == "Maria Souza (1111111)"

    def test_siape_vazio_celula_fica_so_o_nome(self, tmp_path: Path) -> None:
        path = _escreve(tmp_path, f"{_CABECALHO}\nFiscal técnico,Maria Souza,\n")
        assert read_equipe(path).cell("Fiscal técnico") == "Maria Souza"

    def test_celula_de_campo_ausente_e_vazia(self, tmp_path: Path) -> None:
        path = _escreve(tmp_path, f"{_CABECALHO}\nFiscal técnico,Maria Souza,1111111\n")
        assert read_equipe(path).cell("Gestor do contrato") == ""

    def test_substituto_nao_mapeia_para_campo_da_capa(self, tmp_path: Path) -> None:
        path = _escreve(
            tmp_path,
            f"{_CABECALHO}\n"
            "Gestor do contrato,Titular Um,1\n"
            "Gestor do contrato - Substituto,Substituto Dois,2\n",
        )
        equipe = read_equipe(path)
        assert equipe.responsaveis_fields()["Gestor do contrato"] == "Titular Um (1)"
        # substituto fica no CSV (mapeamento interno) mas nunca sai dele
        assert any("substituto" in chave for chave in equipe.membros)

    def test_bom_utf8_sig_lido_corretamente(self, tmp_path: Path) -> None:
        path = _escreve(
            tmp_path, f"{_CABECALHO}\nFiscal Técnico,Maria Souza,1\n", encoding="utf-8-sig"
        )
        assert read_equipe(path).responsaveis_fields()["Fiscal técnico"] == "Maria Souza (1)"

    def test_linha_totalmente_vazia_e_ignorada(self, tmp_path: Path) -> None:
        path = _escreve(tmp_path, f"{_CABECALHO}\n,,\nFiscal técnico,Maria Souza,1\n")
        equipe = read_equipe(path)
        assert len(equipe.membros) == 1
        assert equipe.warnings != ()

    def test_arquivo_ausente_e_decisao_do_chamador(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_equipe(tmp_path / EQUIPE_FILENAME)


class TestMalformado:
    def test_cabecalho_errado(self, tmp_path: Path) -> None:
        path = _escreve(tmp_path, "FUNCAO,NOME,SIAPE\nFiscal técnico,Maria,1\n")
        with pytest.raises(ValueError, match="cabeçalho"):
            read_equipe(path)

    def test_csv_sem_cabecalho(self, tmp_path: Path) -> None:
        path = _escreve(tmp_path, "")
        with pytest.raises(ValueError, match="cabeçalho"):
            read_equipe(path)

    def test_linha_sem_nome(self, tmp_path: Path) -> None:
        path = _escreve(tmp_path, f"{_CABECALHO}\nFiscal técnico,,1\n")
        with pytest.raises(ValueError, match="sem nome"):
            read_equipe(path)

    def test_funcao_duplicada(self, tmp_path: Path) -> None:
        path = _escreve(
            tmp_path,
            f"{_CABECALHO}\n"
            "Fiscal técnico,Maria Souza,1\n"
            "FISCAL TÉCNICO,Outra Pessoa,2\n",
        )
        with pytest.raises(ValueError, match="duplicada"):
            read_equipe(path)


class TestWarnings:
    def test_campo_canonico_ausente_avisa(self, tmp_path: Path) -> None:
        path = _escreve(tmp_path, f"{_CABECALHO}\nFiscal técnico,Maria Souza,1\n")
        equipe = read_equipe(path)
        avisos = "\n".join(equipe.warnings)
        assert "'Gestor do contrato'" in avisos
        assert "'Fiscal requisitante'" in avisos
        assert "'Fiscal administrativo'" in avisos
        assert "'Fiscal técnico'" not in avisos

    def test_funcao_desconhecida_avisa(self, tmp_path: Path) -> None:
        path = _escreve(tmp_path, f"{_CABECALHO}\nGerente do contrato,X,1\n")
        equipe = read_equipe(path)
        assert any("Gerente do contrato" in w for w in equipe.warnings)

    def test_responsaveis_fields_devolve_so_presentes(self, tmp_path: Path) -> None:
        path = _escreve(tmp_path, f"{_CABECALHO}\nFiscal técnico,Maria Souza,1\n")
        campos = read_equipe(path).responsaveis_fields()
        assert campos == {"Fiscal técnico": "Maria Souza (1)"}
