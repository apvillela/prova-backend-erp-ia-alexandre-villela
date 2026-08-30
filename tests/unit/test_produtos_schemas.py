from decimal import Decimal

import pytest
from pydantic import ValidationError

from erp_api.services.produtos.schemas import ProdutoCreate, ProdutoUpdate


def test_produto_valido() -> None:
    produto = ProdutoCreate(nome=" Teclado ", preco=Decimal("199.90"))

    assert produto.nome == "Teclado"
    assert produto.quantidade_em_estoque == 0


@pytest.mark.parametrize("nome", ["123", "12.5", "  ", "1,5"])
def test_nome_numerico_ou_vazio_invalido(nome: str) -> None:
    with pytest.raises(ValidationError):
        ProdutoCreate(nome=nome, preco=Decimal("10"))


def test_preco_negativo_invalido() -> None:
    with pytest.raises(ValidationError):
        ProdutoCreate(nome="Teclado", preco=Decimal("-1"))


def test_update_parcial_valida_nome() -> None:
    with pytest.raises(ValidationError):
        ProdutoUpdate(nome="42")
