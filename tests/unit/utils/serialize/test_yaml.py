import pytest

from dvc.utils.serialize import (
    EncodingError,
    YAMLFileCorruptedError,
    load_yaml,
    parse_yaml,
    parse_yaml_for_update,
    dump_yaml,
    dumps_yaml,
    loads_yaml,
    modify_yaml,
)

from collections import OrderedDict

def test_parse_yaml_duplicate_key_error():
    text = """\
    mykey:
    - foo
    mykey:
    - bar
    """
    with pytest.raises(YAMLFileCorruptedError):
        parse_yaml(text, "mypath")


def test_parse_yaml_invalid_unicode(tmp_dir):
    filename = "invalid_utf8.yaml"
    tmp_dir.gen(filename, b"\x80some: stuff")

    with pytest.raises(EncodingError) as excinfo:
        load_yaml(tmp_dir / filename)

    assert filename in excinfo.value.path
    assert excinfo.value.encoding == "utf-8"

def test_parse_yaml_empty():
    """Test that parse_yaml returns an empty dict when given an empty string."""
    result = parse_yaml("", "dummy")
    assert result == {}

def test_dumps_and_loads_yaml():
    """Test that dumps_yaml and loads_yaml can correctly round-trip a Python dict."""
    data = {"a": [1, 2, 3], "b": {"nested": "value"}}
    dumped = dumps_yaml(data)
    # loads_yaml with typ="safe" should read the normal structure
    loaded = loads_yaml(dumped, typ="safe")
    assert loaded == data

def test_dump_yaml(tmp_dir):
    """Test that dump_yaml writes valid YAML content to a file."""
    filename = "test_dump.yaml"
    data = {"key": "value"}
    dump_yaml(tmp_dir / filename, data)
    content = (tmp_dir / filename).read_text(encoding="utf-8")
    loaded = loads_yaml(content, typ="safe")
    assert loaded == data

def test_modify_yaml(tmp_dir):
    """Test that modify_yaml correctly updates the YAML file contents."""
    filename = "modify_test.yaml"
    initial_data = {"initial": "data"}
    # Create the file with initial data
    dump_yaml(tmp_dir / filename, initial_data)

    # Modify the YAML file using the context manager
    with modify_yaml(tmp_dir / filename) as data:
        data["modified"] = "new_value"

    # Read and check that the file was updated
    modified_content = (tmp_dir / filename).read_text(encoding="utf-8")
    loaded_modified = loads_yaml(modified_content, typ="safe")
    expected = initial_data.copy()
    expected["modified"] = "new_value"
    assert loaded_modified == expected

def test_parse_yaml_for_update_empty():
    """Test that parse_yaml_for_update returns an empty dict for empty YAML content."""
    result = parse_yaml_for_update("", "dummy")
    assert result == {}
def test_dumps_yaml_long_string():
    """Test that dumps_yaml does not wrap long strings due to the max width setting."""
    long_string = "a" * 500
    data = {"text": long_string}
    dumped = dumps_yaml(data)
    # Ensure that the dumped YAML line containing "text:" is not split into multiple lines.
    lines = dumped.splitlines()
    text_lines = [line for line in lines if line.startswith("text:")]
    assert text_lines, "No line starting with 'text:' found"
    # Check that one of the text lines is long enough (i.e. not wrapped)
    assert any(len(line) > 100 for line in text_lines), "Long string appears to be wrapped"

def test_parse_yaml_for_update_order():
    """Test that parse_yaml_for_update preserves the order of keys in the YAML content."""
    # Provide YAML content with keys in a known order.
    text = "b: 2\na: 1\nc: 3\n"
    result = parse_yaml_for_update(text, "dummy")
    keys = list(result.keys())
    # The expected order should be as in the text (leading spaces are ignored)
    assert keys == ['b', 'a', 'c'], f"Expected order ['b', 'a', 'c'] but got {keys}"

def test_dump_yaml_with_ordered_dict(tmp_dir):
    """Test that dump_yaml correctly serializes an OrderedDict, preserving key order."""
    filename = "ordered_dict.yaml"
    data = OrderedDict([("first", 1), ("second", 2), ("third", 3)])
    dump_yaml(tmp_dir / filename, data)
    content = (tmp_dir / filename).read_text(encoding="utf-8")
    loaded = loads_yaml(content, typ="safe")
    # In Python 3.7+ dictionaries preserve insertion order.
    assert list(loaded.keys()) == list(data.keys()), "Key order was not preserved in dump and load"
    assert loaded == dict(data), "Loaded data does not match the original data"

def test_modify_yaml_invalid(tmp_dir):
    """Test that modify_yaml raises YAMLFileCorruptedError when the YAML file is invalid."""
    filename = "invalid_modify.yaml"
    # Write YAML content with duplicate keys which should be treated as corrupted.
    invalid_content = "key: value\nkey: another_value"
    tmp_dir.gen(filename, invalid_content)
    with pytest.raises(YAMLFileCorruptedError):
        with modify_yaml(tmp_dir / filename) as data:
            data["new"] = "test"

def test_loads_yaml_error():
    """Test that loads_yaml raises an error when given syntactically invalid YAML content."""
    invalid_yaml = "key: value: another"
    with pytest.raises(Exception):
        loads_yaml(invalid_yaml)
def test_modify_yaml_empty_file(tmp_dir):
    """Test that modify_yaml correctly updates an empty YAML file."""
    filename = "empty.yaml"
    # Create an empty file
    tmp_dir.gen(filename, "")
    with modify_yaml(tmp_dir / filename) as data:
        # Start with an empty dict and add a new key
        data["new_key"] = "new_value"
    content = (tmp_dir / filename).read_text(encoding="utf-8")
    loaded = loads_yaml(content, typ="safe")
    assert loaded == {"new_key": "new_value"}

def test_loads_yaml_null():
    """Test that loads_yaml returns None when YAML content is 'null'."""
    result = loads_yaml("null", typ="safe")
    assert result is None

def test_parse_yaml_scalar():
    """Test that parse_yaml correctly parses YAML scalar values."""
    result = parse_yaml("5", "dummy")
    assert result == 5

def test_dump_yaml_empty_dict(tmp_dir):
    """Test that dump_yaml correctly writes an empty dictionary to a file."""
    filename = "empty_dict.yaml"
    # Dump an empty dictionary
    dump_yaml(tmp_dir / filename, {})
    content = (tmp_dir / filename).read_text(encoding="utf-8")
    loaded = loads_yaml(content, typ="safe")
    # Depending on ruamel.yaml's behavior, an empty file can be written as {} or as a null value.
    assert loaded == {} or loaded is None

def test_dumps_yaml_with_complex_structure():
    """Test that dumps_yaml handles a complex nested structure correctly, including lists and OrderedDicts."""
    data = {
        "list": [
            OrderedDict([("key1", "value1"), ("key2", "value2")]),
            {"a": 1, "b": 2},
        ],
        "number": 42,
        "string": "a" * 300,
    }
    dumped = dumps_yaml(data)
    loaded = loads_yaml(dumped, typ="safe")
    # To account for possible type differences, convert OrderedDict to dict for comparison.
    expected = {
        "list": [
            dict(OrderedDict([("key1", "value1"), ("key2", "value2")])),
            {"a": 1, "b": 2},
        ],
        "number": 42,
        "string": "a" * 300,
    }
    assert loaded == expected
def test_dumps_yaml_exception(monkeypatch):
    """Test that dumps_yaml propagates exceptions from the dumper (_get_yaml)."""
    from dvc.utils.serialize import dumps_yaml
    import dvc.utils.serialize._yaml as yaml_mod
    def fake_get_yaml():
        raise Exception("dump error")
    monkeypatch.setattr(yaml_mod, "_get_yaml", fake_get_yaml)
    with pytest.raises(Exception, match="dump error"):
        dumps_yaml({"a": 1})

def test_round_trip_types():
    """Test that YAML round-trip preserves various data types (bools, None, int, and float)."""
    from dvc.utils.serialize import dumps_yaml, loads_yaml
    data = {"bool_true": True, "bool_false": False, "none": None, "int": 42, "float": 3.14}
    dumped = dumps_yaml(data)
    loaded = loads_yaml(dumped, typ="safe")
    assert loaded == data

def test_parse_yaml_explicit_str_tag():
    """Test that parse_yaml can parse YAML with an explicit string tag (!!str)."""
    from dvc.utils.serialize import parse_yaml
    text = "key: !!str 123"
    result = parse_yaml(text, "dummy")
    assert result == {"key": "123"}

def test_loads_yaml_multiline_literal():
    """Test that loads_yaml correctly handles multiline literal blocks."""
    from dvc.utils.serialize import loads_yaml
    yaml_text = "key: |\n  line1\n  line2\n"
    result = loads_yaml(yaml_text, typ="safe")
    # ruamel.yaml might preserve a final newline, so we allow both possibilities
    assert result["key"] in ("line1\nline2\n", "line1\nline2")