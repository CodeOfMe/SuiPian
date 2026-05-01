from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


class TestToolResult:
    def test_success_result(self):
        from suipian.api import ToolResult

        r = ToolResult(success=True, data={"key": "value"}, metadata={"v": "1"})
        assert r.success is True
        assert r.data == {"key": "value"}
        assert r.error is None

    def test_failure_result(self):
        from suipian.api import ToolResult

        r = ToolResult(success=False, error="something broke")
        assert r.success is False
        assert r.error == "something broke"
        assert r.data is None

    def test_to_dict(self):
        from suipian.api import ToolResult

        r = ToolResult(success=True, data=[1, 2], metadata={"x": 1})
        d = r.to_dict()
        assert set(d.keys()) == {"success", "data", "error", "metadata"}

    def test_default_metadata_isolation(self):
        from suipian.api import ToolResult

        r1 = ToolResult(success=True)
        r2 = ToolResult(success=True)
        r1.metadata["a"] = 1
        assert "a" not in r2.metadata

    def test_to_dict_serializable(self):
        from suipian.api import ToolResult

        r = ToolResult(success=True, data={"nested": [1, 2, 3]})
        d = r.to_dict()
        assert json.dumps(d)


class TestHideAPI:
    def test_hide_basic(self, tmp_path):
        from suipian.api import hide_file

        source = tmp_path / "test.txt"
        source.write_bytes(b"secret data here")
        carrier = tmp_path / "carrier.txt"
        carrier.write_text("Normal text content")
        output = tmp_path / "out.txt"

        result = hide_file(source=source, carrier=carrier, output=output, password="pw123")
        assert result.success is True
        assert output.exists()
        assert "version" in result.metadata

    def test_hide_with_path_object(self, tmp_path):
        from suipian.api import hide_file

        source = tmp_path / "test.bin"
        source.write_bytes(b"\x00\x01\x02\x03")
        carrier = tmp_path / "c.txt"
        carrier.write_text("Carrier")
        output = tmp_path / "out.txt"

        result = hide_file(
            source=Path(str(source)),
            carrier=Path(str(carrier)),
            output=Path(str(output)),
            password="pw",
        )
        assert result.success is True

    def test_hide_source_not_found(self):
        from suipian.api import hide_file

        result = hide_file(
            source="/nonexistent/file.txt",
            carrier="/nonexistent/carrier.txt",
            output="/tmp/out.txt",
            password="pw",
        )
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_hide_empty_password(self, tmp_path):
        from suipian.api import hide_file

        source = tmp_path / "test.txt"
        source.write_bytes(b"data")
        carrier = tmp_path / "carrier.txt"
        carrier.write_text("text")

        result = hide_file(
            source=str(source), carrier=str(carrier), output=str(tmp_path / "out.txt"), password=""
        )
        assert result.success is False
        assert "password" in result.error.lower()

    def test_hide_carrier_not_exist(self, tmp_path):
        from suipian.api import hide_file

        source = tmp_path / "test.txt"
        source.write_bytes(b"data")
        carrier = tmp_path / "nonexistent_carrier.txt"
        output = tmp_path / "out.txt"

        result = hide_file(source=source, carrier=carrier, output=output, password="pw")
        assert result.success is True
        assert output.exists()

    def test_hide_png_file(self, tmp_path):
        from suipian.api import hide_file

        png_data = b"\x89PNG\r\n\x1a\n" + os.urandom(100)
        source = tmp_path / "image.png"
        source.write_bytes(png_data)
        carrier = tmp_path / "readme.txt"
        carrier.write_text("# README\n\nThis is a readme.")
        output = tmp_path / "out.txt"

        result = hide_file(source=source, carrier=carrier, output=output, password="secret")
        assert result.success is True


class TestRevealAPI:
    def test_reveal_basic(self, tmp_path):
        from suipian.api import hide_file, reveal_file

        source = tmp_path / "test.txt"
        source.write_bytes(b"secret data here")
        carrier = tmp_path / "carrier.txt"
        carrier.write_text("Normal text")
        morphed = tmp_path / "out.txt"
        revealed = tmp_path / "revealed.txt"

        hide_file(source=source, carrier=carrier, output=morphed, password="pw123")
        result = reveal_file(morphed=morphed, output=revealed, password="pw123")
        assert result.success is True
        assert revealed.read_bytes() == b"secret data here"
        assert "version" in result.metadata

    def test_reveal_wrong_password(self, tmp_path):
        from suipian.api import hide_file, reveal_file

        source = tmp_path / "test.txt"
        source.write_bytes(b"secret")
        carrier = tmp_path / "carrier.txt"
        carrier.write_text("text")
        morphed = tmp_path / "out.txt"
        revealed = tmp_path / "revealed.txt"

        hide_file(source=source, carrier=carrier, output=morphed, password="correct")
        result = reveal_file(morphed=morphed, output=revealed, password="wrong")
        assert result.success is False

    def test_reveal_nonexistent_file(self):
        from suipian.api import reveal_file

        result = reveal_file(
            morphed="/nonexistent/file.txt",
            output="/tmp/out.txt",
            password="pw",
        )
        assert result.success is False

    def test_reveal_corrupted_file(self, tmp_path):
        from suipian.api import reveal_file

        fake = tmp_path / "fake.txt"
        fake.write_text("This is not a morphed file at all")

        result = reveal_file(morphed=fake, output=tmp_path / "out.txt", password="pw")
        assert result.success is False

    def test_reveal_empty_password(self, tmp_path):
        from suipian.api import reveal_file

        result = reveal_file(morphed="/tmp/dummy", output="/tmp/out", password="")
        assert result.success is False
        assert "password" in result.error.lower()


class TestValidateAPI:
    def test_validate_valid(self, tmp_path):
        from suipian.api import hide_file, validate_morph

        source = tmp_path / "test.bin"
        source.write_bytes(b"\x00\x01\x02\x03")
        carrier = tmp_path / "carrier.txt"
        carrier.write_text("Just a text file")
        morphed = tmp_path / "morphed.txt"

        hide_file(source=source, carrier=carrier, output=morphed, password="pwd")
        result = validate_morph(file=morphed)
        assert result.success is True
        assert result.data["valid"] is True
        assert result.data["info"]["original_name"] == "test.bin"

    def test_validate_invalid_file(self, tmp_path):
        from suipian.api import validate_morph

        fake = tmp_path / "fake.txt"
        fake.write_text("This is not a morphed file at all")

        result = validate_morph(file=fake)
        assert result.success is False

    def test_validate_nonexistent_file(self):
        from suipian.api import validate_morph

        result = validate_morph(file="/nonexistent/file.txt")
        assert result.success is False


class TestGetInfoAPI:
    def test_get_info(self, tmp_path):
        from suipian.api import get_info, hide_file

        source = tmp_path / "test.bin"
        source.write_bytes(b"\x00\x01\x02\x03")
        carrier = tmp_path / "carrier.txt"
        carrier.write_text("Just text")
        morphed = tmp_path / "morphed.txt"

        hide_file(source=source, carrier=carrier, output=morphed, password="pwd")
        result = get_info(file=morphed)
        assert result.success is True
        assert result.data["original_name"] == "test.bin"
        assert "version" in result.data

    def test_get_info_nonexistent(self):
        from suipian.api import get_info

        result = get_info(file="/nonexistent/file.txt")
        assert result.success is False


class TestToolsSchema:
    def test_tools_is_list(self):
        from suipian.tools import TOOLS

        assert isinstance(TOOLS, list)
        assert len(TOOLS) >= 3

    def test_tool_names(self):
        from suipian.tools import TOOLS

        names = [t["function"]["name"] for t in TOOLS]
        assert "suipian_hide_file" in names
        assert "suipian_reveal_file" in names
        assert "suipian_validate" in names
        assert "suipian_get_info" in names

    def test_tool_structure(self):
        from suipian.tools import TOOLS

        for tool in TOOLS:
            assert tool["type"] == "function"
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"
            assert "properties" in func["parameters"]
            assert "required" in func["parameters"]

    def test_required_fields_in_properties(self):
        from suipian.tools import TOOLS

        for tool in TOOLS:
            func = tool["function"]
            props = func["parameters"]["properties"]
            for req in func["parameters"]["required"]:
                assert req in props, f"Required '{req}' not in properties"


class TestToolsDispatch:
    def test_dispatch_hide_file(self):
        from suipian.tools import dispatch

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source = tmp_path / "test.bin"
            source.write_bytes(b"test dispatch data")

            carrier = tmp_path / "carrier.txt"
            carrier.write_text("Carrier content")
            output = tmp_path / "out.txt"

            result = dispatch(
                "suipian_hide_file",
                {
                    "source": str(source),
                    "carrier": str(carrier),
                    "output": str(output),
                    "password": "pw",
                },
            )
            assert result["success"] is True

    def test_dispatch_reveal_file(self):
        from suipian.tools import dispatch

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source = tmp_path / "test.bin"
            source.write_bytes(b"test reveal data")

            carrier = tmp_path / "carrier.txt"
            carrier.write_text("Carrier content")
            morphed = tmp_path / "out.txt"
            revealed = tmp_path / "revealed.bin"

            dispatch(
                "suipian_hide_file",
                {
                    "source": str(source),
                    "carrier": str(carrier),
                    "output": str(morphed),
                    "password": "pw",
                },
            )

            result = dispatch(
                "suipian_reveal_file",
                {
                    "morphed": str(morphed),
                    "output": str(revealed),
                    "password": "pw",
                },
            )
            assert result["success"] is True
            assert revealed.read_bytes() == b"test reveal data"

    def test_dispatch_validate(self):
        from suipian.tools import dispatch

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source = tmp_path / "test.bin"
            source.write_bytes(b"\x00" * 4)

            carrier = tmp_path / "carrier.txt"
            carrier.write_text("text")
            morphed = tmp_path / "out.txt"

            dispatch(
                "suipian_hide_file",
                {
                    "source": str(source),
                    "carrier": str(carrier),
                    "output": str(morphed),
                    "password": "pw",
                },
            )

            result = dispatch("suipian_validate", {"file": str(morphed)})
            assert result["success"] is True
            assert result["data"]["valid"] is True

    def test_dispatch_get_info(self):
        from suipian.tools import dispatch

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source = tmp_path / "test.bin"
            source.write_bytes(b"\x00" * 4)

            carrier = tmp_path / "carrier.txt"
            carrier.write_text("text")
            morphed = tmp_path / "out.txt"

            dispatch(
                "suipian_hide_file",
                {
                    "source": str(source),
                    "carrier": str(carrier),
                    "output": str(morphed),
                    "password": "pw",
                },
            )

            result = dispatch("suipian_get_info", {"file": str(morphed)})
            assert result["success"] is True
            assert result["data"]["original_name"] == "test.bin"

    def test_dispatch_unknown_tool(self):
        from suipian.tools import dispatch

        with pytest.raises(ValueError, match="Unknown tool"):
            dispatch("nonexistent_tool", {})

    def test_dispatch_json_string_args(self):
        from suipian.tools import dispatch

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source = tmp_path / "test.bin"
            source.write_bytes(b"json test")

            carrier = tmp_path / "carrier.txt"
            carrier.write_text("text")
            output = tmp_path / "out.txt"

            args = json.dumps(
                {
                    "source": str(source),
                    "carrier": str(carrier),
                    "output": str(output),
                    "password": "pw",
                }
            )
            result = dispatch("suipian_hide_file", args)
            assert isinstance(result, dict)
            assert "success" in result

    def test_dispatch_error_case(self):
        from suipian.tools import dispatch

        result = dispatch(
            "suipian_hide_file",
            {
                "source": "/nonexistent/file.txt",
                "carrier": "/nonexistent/carrier.txt",
                "output": "/tmp/out.txt",
                "password": "pw",
            },
        )
        assert result["success"] is False


class TestCLIFlags:
    def _run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "suipian"] + list(args),
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_version_flag(self):
        r = self._run_cli("-V")
        assert r.returncode == 0
        assert "1.0.0" in r.stdout

    def test_help_has_unified_flags(self):
        r = self._run_cli("--help")
        assert r.returncode == 0
        assert "--quiet" in r.stdout or "-q" in r.stdout
        assert "--verbose" in r.stdout or "-v" in r.stdout

    def test_subcommand_help_has_flags(self):
        r = self._run_cli("hide", "--help")
        assert r.returncode == 0
        assert "--json" in r.stdout
        assert "--output" in r.stdout or "-o" in r.stdout
        assert "--password" in r.stdout or "-p" in r.stdout

    def test_hide_requires_output_and_password(self):
        r = self._run_cli("hide", "a.txt", "b.txt")
        assert r.returncode == 2

    def test_reveal_requires_output_and_password(self):
        r = self._run_cli("reveal", "a.txt")
        assert r.returncode == 2

    def test_json_output(self, tmp_path):
        source = tmp_path / "test.txt"
        source.write_bytes(b"cli json test")
        carrier = tmp_path / "carrier.txt"
        carrier.write_text("carrier")
        output = tmp_path / "out.txt"

        r = self._run_cli(
            "hide",
            str(source),
            str(carrier),
            "-o",
            str(output),
            "-p",
            "pw123",
            "--json",
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["success"] is True

    def test_info_command(self, tmp_path):
        source = tmp_path / "test.txt"
        source.write_bytes(b"cli info test")
        carrier = tmp_path / "carrier.txt"
        carrier.write_text("carrier")
        morphed = tmp_path / "out.txt"

        self._run_cli(
            "hide",
            str(source),
            str(carrier),
            "-o",
            str(morphed),
            "-p",
            "pw123",
        )
        r = self._run_cli("info", str(morphed))
        assert r.returncode == 0
        assert "test.txt" in r.stdout

    def test_validate_command(self, tmp_path):
        source = tmp_path / "test.txt"
        source.write_bytes(b"cli validate test")
        carrier = tmp_path / "carrier.txt"
        carrier.write_text("carrier")
        morphed = tmp_path / "out.txt"

        self._run_cli(
            "hide",
            str(source),
            str(carrier),
            "-o",
            str(morphed),
            "-p",
            "pw123",
        )
        r = self._run_cli("validate", str(morphed))
        assert r.returncode == 0
        assert "Valid: Yes" in r.stdout


class TestPackageExports:
    def test_version(self):
        import suipian

        assert hasattr(suipian, "__version__")
        assert isinstance(suipian.__version__, str)

    def test_toolresult(self):
        from suipian import ToolResult

        assert callable(ToolResult)

    def test_api_functions_exported(self):
        from suipian import get_info, hide_file, reveal_file, validate_morph

        assert callable(hide_file)
        assert callable(reveal_file)
        assert callable(validate_morph)
        assert callable(get_info)

    def test_all_defined(self):
        import suipian

        assert hasattr(suipian, "__all__")
        expected = {
            "ToolResult",
            "hide_file",
            "reveal_file",
            "validate_morph",
            "get_info",
            "__version__",
        }
        assert set(suipian.__all__) == expected


class TestEndToEnd:
    def test_full_workflow_png(self, tmp_path):
        from suipian.api import hide_file, reveal_file, validate_morph

        png_header = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
        original_data = png_header + os.urandom(500)
        source = tmp_path / "image.png"
        source.write_bytes(original_data)

        carrier = tmp_path / "readme.txt"
        carrier.write_text(
            "# Project README\n\nThis is a completely normal looking text file.\n"
            "It contains documentation and looks totally innocent.\n\n"
            "## Installation\n\npip install something\n\n"
            "## Usage\n\nJust read the docs.\n"
        )

        morphed = tmp_path / "output.txt"

        result = hide_file(source=source, carrier=carrier, output=morphed, password="secret123")
        assert result.success is True

        content = morphed.read_text()
        assert "-----BEGIN SUIPIAN HEADER-----" in content
        assert "-----END SUIPIAN FOOTER-----" in content
        assert "This is a completely normal looking text file" in content

        val_result = validate_morph(file=morphed)
        assert val_result.success is True
        assert val_result.data["info"]["original_name"] == "image.png"

        revealed = tmp_path / "restored.png"
        result2 = reveal_file(morphed=morphed, output=revealed, password="secret123")
        assert result2.success is True
        assert revealed.read_bytes() == original_data

    def test_full_workflow_binary(self, tmp_path):
        from suipian.api import get_info, hide_file, reveal_file

        binary_data = bytes(range(256)) * 4
        source = tmp_path / "binary.dat"
        source.write_bytes(binary_data)

        carrier = tmp_path / "notes.txt"
        carrier.write_text("Meeting notes from today.\nEverything went fine.\n")

        morphed = tmp_path / "output.txt"

        result = hide_file(source=source, carrier=carrier, output=morphed, password="pw123")
        assert result.success is True

        info = get_info(file=morphed)
        assert info.success is True
        assert info.data["original_name"] == "binary.dat"

        revealed = tmp_path / "restored.dat"
        result2 = reveal_file(morphed=morphed, output=revealed, password="pw123")
        assert result2.success is True
        assert revealed.read_bytes() == binary_data

    def test_full_workflow_pdf(self, tmp_path):
        from suipian.api import hide_file, reveal_file

        pdf_data = b"%PDF-1.4" + os.urandom(200)
        source = tmp_path / "doc.pdf"
        source.write_bytes(pdf_data)

        carrier = tmp_path / "essay.txt"
        carrier.write_text("This is an essay about many things.")

        morphed = tmp_path / "output.txt"

        hide_file(source=source, carrier=carrier, output=morphed, password="mypass")
        revealed = tmp_path / "restored.pdf"
        reveal_file(morphed=morphed, output=revealed, password="mypass")
        assert revealed.read_bytes() == pdf_data

    def test_morphed_file_carrier_preserved(self, tmp_path):
        from suipian.api import hide_file

        carrier_content = "# Important Document\n\nThis is critical text.\nDo not modify."
        source = tmp_path / "secret.bin"
        source.write_bytes(b"top secret data")
        carrier = tmp_path / "important.txt"
        carrier.write_text(carrier_content)
        morphed = tmp_path / "out.txt"

        result = hide_file(source=source, carrier=carrier, output=morphed, password="pw")
        assert result.success is True

        morphed_content = morphed.read_text()
        assert morphed_content.startswith(carrier_content)

    def test_large_file_roundtrip(self, tmp_path):
        from suipian.api import hide_file, reveal_file

        large_data = os.urandom(100_000)
        source = tmp_path / "large.bin"
        source.write_bytes(large_data)
        carrier = tmp_path / "carrier.txt"
        carrier.write_text("Carrier for large file")
        morphed = tmp_path / "out.txt"
        revealed = tmp_path / "restored.bin"

        hide_file(source=source, carrier=carrier, output=morphed, password="pw")
        reveal_file(morphed=morphed, output=revealed, password="pw")
        assert revealed.read_bytes() == large_data
