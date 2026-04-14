from django.test import TestCase
from apps.analysis.pdf_processor import (
    _parse_currency,
    _is_blacklisted,
    _parse_contracheque,
    _detect_descontos_indevidos,
    ExtractedData,
    _parse_personal_info,
)


class CurrencyParserTest(TestCase):
    def test_parse_simple(self):
        self.assertAlmostEqual(_parse_currency("1.234,56"), 1234.56)

    def test_parse_no_thousands(self):
        self.assertAlmostEqual(_parse_currency("456,78"), 456.78)

    def test_parse_integer_like(self):
        self.assertAlmostEqual(_parse_currency("1.000,00"), 1000.0)


class BlacklistTest(TestCase):
    def test_blacklisted_iof(self):
        self.assertTrue(_is_blacklisted("IOF"))

    def test_blacklisted_encargos(self):
        self.assertTrue(_is_blacklisted("ENCARGOS DE FINANCIAMENTO"))

    def test_not_blacklisted(self):
        self.assertFalse(_is_blacklisted("SALARIO BASE"))
        self.assertFalse(_is_blacklisted("INSS"))


class PersonalInfoParserTest(TestCase):
    def test_extract_cpf(self):
        text = "CPF: 123.456.789-00\nNome: JOAO DA SILVA"
        data = ExtractedData()
        _parse_personal_info(text, data)
        self.assertEqual(data.cpf, "123.456.789-00")

    def test_extract_competencia(self):
        text = "Competência: 03/2024"
        data = ExtractedData()
        _parse_personal_info(text, data)
        self.assertEqual(data.competencia, "03/2024")

    def test_extract_valor_liquido(self):
        text = "Valor Líquido: R$ 5.230,45"
        data = ExtractedData()
        _parse_personal_info(text, data)
        self.assertAlmostEqual(data.valor_liquido, 5230.45)


class DescontosIndevidosTest(TestCase):
    def test_detect_seguro_prestamista(self):
        text = "SEGURO PRESTAMISTA R$ 67,50"
        descontos = _detect_descontos_indevidos(text)
        self.assertTrue(any(d.tipo == "Seguro Indevido" for d in descontos))

    def test_detect_juros_abusivos(self):
        text = "Taxa juros: 3,50% a.m."
        descontos = _detect_descontos_indevidos(text)
        self.assertTrue(any(d.tipo == "Juros Abusivos" for d in descontos))

    def test_no_false_positive_normal_rate(self):
        text = "Taxa juros: 1,80% a.m."
        descontos = _detect_descontos_indevidos(text)
        self.assertFalse(any(d.tipo == "Juros Abusivos" for d in descontos))


class ContrachequeParserTest(TestCase):
    SAMPLE = """
CÓDIGO  DESCRIÇÃO                    GANHOS      DESCONTOS
0001    VENCIMENTO BASICO            8.450,00
0217    CONSIGNADO BMG                           456,78
0268    CARTAO RMC CAIXA                         312,45
0322    CARTAO RCC BRADESCO                      189,90
"""

    def test_parse_contracheque_credits(self):
        transacoes = _parse_contracheque(self.SAMPLE, "03/2024")
        creditos = [t for t in transacoes if t.tipo == "credito"]
        self.assertTrue(len(creditos) > 0)

    def test_parse_contracheque_debits(self):
        transacoes = _parse_contracheque(self.SAMPLE, "03/2024")
        debitos = [t for t in transacoes if t.tipo == "debito"]
        self.assertTrue(len(debitos) > 0)

    def test_rmc_code_tagged(self):
        transacoes = _parse_contracheque(self.SAMPLE, "03/2024")
        rmc = [t for t in transacoes if t.codigo_rmc is not None]
        self.assertTrue(len(rmc) > 0)
