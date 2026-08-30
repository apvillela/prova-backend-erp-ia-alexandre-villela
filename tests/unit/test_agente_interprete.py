import pytest

from erp_api.services.agente.interprete import interpretar
from erp_api.services.agente.interprete_llm import parsear_chamada


@pytest.mark.parametrize(
    ("pergunta", "ferramenta", "parametros"),
    [
        (
            "Quais produtos estão com estoque abaixo de 10 unidades?",
            "consultar_estoque_baixo",
            {"limite": 10},
        ),
        ("produtos com menos de 5 unidades", "consultar_estoque_baixo", {"limite": 5}),
        ("o que está com estoque baixo?", "consultar_estoque_baixo", {}),
        ("quantos produtos temos cadastrados?", "contar_produtos", {}),
        (
            "produtos entre 50 e 200",
            "buscar_produtos",
            {"preco_min": 50.0, "preco_max": 200.0},
        ),
        ("quais são mais baratos que R$ 100?", "buscar_produtos", {"preco_max": 100.0}),
        ("produtos acima de 900", "buscar_produtos", {"preco_min": 900.0}),
        ("qual o preço do teclado?", "buscar_produtos", {"nome": "teclado"}),
        ("buscar monitor", "buscar_produtos", {"nome": "monitor"}),
        (
            "qual o histórico de movimentações do teclado?",
            "historico_movimentacoes",
            {"produto": "teclado"},
        ),
        ("movimentações de estoque", "historico_movimentacoes", {}),
    ],
)
def test_interpreta_perguntas(
    pergunta: str, ferramenta: str, parametros: dict[str, object]
) -> None:
    chamada = interpretar(pergunta)

    assert chamada is not None
    assert chamada.ferramenta == ferramenta
    assert chamada.parametros == parametros
    assert chamada.confianca > 0.5


def test_pergunta_fora_do_dominio_retorna_none() -> None:
    assert interpretar("qual a previsão do tempo amanhã?") is None


@pytest.mark.parametrize(
    ("conteudo", "esperado"),
    [
        ('{"ferramenta": "contar_produtos", "parametros": {}}', "contar_produtos"),
        ('{"ferramenta": "buscar_produtos", "parametros": {"nome": "cabo"}}', "buscar_produtos"),
        ('{"ferramenta": null}', None),
        ('{"ferramenta": "dropar_tabela", "parametros": {}}', None),  # fora do registry
        ('{"ferramenta": "contar_produtos", "parametros": "x"}', None),  # parâmetros inválidos
        ("não é json", None),
        ('["lista"]', None),
    ],
)
def test_parsear_chamada_llm(conteudo: str, esperado: str | None) -> None:
    chamada = parsear_chamada(conteudo)

    if esperado is None:
        assert chamada is None
    else:
        assert chamada is not None
        assert chamada.ferramenta == esperado
