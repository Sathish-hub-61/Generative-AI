from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple


@dataclass
class DocEntry:
    description: str
    source_line: str  # "line_no: original text"

    def to_dict(self):
        return asdict(self)


def parse_docs(text: str) -> Tuple[Dict[str, DocEntry], List[str]]:
    """Parse documentation text into {lowercase_field: DocEntry}.

    Accepts three separators: ':', '-', '|'.
    Lines that cannot be parsed go into unparsed_lines.
    """
    docs: Dict[str, DocEntry] = {}
    unparsed: List[str] = []

    for idx, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue

        matched = False
        for sep in [":", "-", "|"]:
            if sep in stripped:
                parts = stripped.split(sep, 1)
                field = parts[0].strip()
                desc = parts[1].strip() if len(parts) == 2 else ""
                if field and desc:
                    docs[field.lower()] = DocEntry(
                        description=desc,
                        source_line=f"{idx}: {raw_line.rstrip()}",
                    )
                    matched = True
                    break

        if not matched:
            unparsed.append(f"{idx}: {raw_line.rstrip()}")

    return docs, unparsed
