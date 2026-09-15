from axiomrunner.cli import main


def test_doctor_bootstrap(capsys: object) -> None:
    assert main(["doctor"]) == 0


def test_unimplemented_benchmark_returns_no_candidate(capsys: object) -> None:
    assert main(["benchmark", "samples"]) == 4
