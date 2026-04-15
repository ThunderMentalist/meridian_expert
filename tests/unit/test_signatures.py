from meridian_expert.investigation.signatures import extract_module_signature


def test_extract_module_signature_captures_docstring_imports_and_symbols() -> None:
    source = '''"""Module doc."""
import meridian.model.model
from meridian.analysis import analyzer

class Demo:
    def method(self, x, *, flag, **kwargs):
        return x

def top(a, /, b, *args, c, **kwargs):
    return a
'''

    signature = extract_module_signature(source, path="demo.py")

    assert signature.module_docstring == "Module doc."
    assert "meridian.model.model" in signature.top_level_imports
    assert "meridian.analysis:analyzer" in signature.top_level_imports

    kinds = {item.name: item.kind for item in signature.symbols}
    assert kinds["Demo"] == "class"
    assert kinds["Demo.method"] == "method"
    assert kinds["top"] == "function"

    top = next(item for item in signature.symbols if item.name == "top")
    assert top.args == ["a", "b", "*args", "c", "**kwargs"]
