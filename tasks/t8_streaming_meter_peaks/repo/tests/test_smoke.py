import json
from io import StringIO

from metering.summary import main, read_ndjson, summarize


def test_original_report_accepts_ndjson():
    source = StringIO('{"meter":"A","tick":1,"watts":100}\n\n'
                      '{"meter":"B","tick":1,"watts":50}\n')
    assert summarize(read_ndjson(source)) == {"count": 2, "total_watts": 150}


def test_cli_keeps_original_format(tmp_path, capsys):
    path = tmp_path / "readings.ndjson"
    path.write_text('{"meter":"A","tick":1,"watts":100}\n')
    main(path)
    assert json.loads(capsys.readouterr().out) == {"count": 1, "total_watts": 100}
