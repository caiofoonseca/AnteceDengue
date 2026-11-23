from src import config


def test_tres_classes():
    assert len(config.CLASSES) == 3


def test_quantis_ordenados():
    assert config.Q_MID < config.Q_HIGH


def test_caminhos_absolutos():
    for p in (config.ROOT, config.DATA_RAW, config.DATA_PROCESSED,
              config.MODELS_DIR, config.REPORTS_DIR):
        assert p.is_absolute()


def test_nomes_de_experimento():
    assert config.EXP_BASELINE == "01-baseline"
    assert config.EXP_COMPARE == "02-comparacao-modelos"
    assert config.EXP_TUNING == "03-otimizacao-hiperparametros"
