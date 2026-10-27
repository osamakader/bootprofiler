from click.testing import CliRunner

from bootprofiler.cli import analyze


def test_top_must_be_positive(tmp_path):
    blame = tmp_path / "blame.txt"
    blame.write_text("1.000s foo.service\n")
    result = CliRunner().invoke(analyze, ["--systemd-blame", str(blame), "--top", "0", "--format", "pretty"])
    assert result.exit_code == 2
    assert "--top" in result.output
