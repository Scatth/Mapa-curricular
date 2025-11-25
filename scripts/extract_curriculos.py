#!/usr/bin/env python3
"""Extrai informações estruturadas dos PDFs de currículo do diretório `curriculo/`.

Saída: arquivos JSON (um por curso) no diretório `dados/`, contendo:
- Metadados básicos (nome do curso, turno, nível, modalidade quando disponível)
- Resumo de cargas horárias exigidas (OB, OP, EST, COMP, TOTAL)
- Disciplinas agrupadas por período, optativas, estágios, complementares etc.
- Pré-requisitos por código da disciplina.

O formato gerado foi pensado para alimentar o HTML do mapa curricular, evitando
reprocessar os PDFs a cada carregamento.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTTextContainer

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "curriculo"
OUT_DIR = ROOT / "dados"

CODE_RX = re.compile(r"^[A-Z]{2,4}\d{4,6}")
TYPE_RX = re.compile(r"^[A-Z]{2,3}$")
PERIOD_RX = re.compile(r"PER[IÍ]ODO\s*:?\s*(\d+)", re.IGNORECASE)
PAGE_RX = re.compile(r"P[áa]gina", re.IGNORECASE)
TOTAL_PERIOD_RX = re.compile(r"^Total do Per[ií]odo", re.IGNORECASE)
NO_PREREQ_RX = re.compile(r"n[aã]o possui pr[eé]-?requisit", re.IGNORECASE)

REQUIRED_PATTERNS = {
    "obrigatorias": re.compile(r"(DISCIPLINAS?.*OBRIGAT[ÓO]RIAS?|^OBRIGAT[ÓO]RIAS?)[^0-9]*(\d{2,4})", re.IGNORECASE),
    "optativas": re.compile(r"(DISCIPLINAS?.*OP[T]?ATIVAS?|^OP[T]?ATIVAS?)[^0-9]*(\d{2,4})", re.IGNORECASE),
    "estagio": re.compile(r"EST[ÁA]GIO[^0-9]*(\d{2,4})", re.IGNORECASE),
    "complementares": re.compile(r"(ATIVIDADES?.*COMPLEMENTAR(?:ES)?|^COMPLEMENTARES?)[^0-9]*(\d{2,4})", re.IGNORECASE),
    "tcc": re.compile(r"(TRABALHO\s+DE\s+CONCLUS|TCC)[^0-9]*(\d{2,4})", re.IGNORECASE),
    "total": re.compile(r"CARGA\s+HOR[ÁA]RIA\s+TOTAL.*?(\d{3,4})", re.IGNORECASE),
}

SECTION_TOKENS = [
    ("OB", re.compile(r"(DISCIPLINAS?.*OBRIGAT[ÓO]RIAS?|^OBRIGAT[ÓO]RIAS?)", re.IGNORECASE)),
    ("OP", re.compile(r"(DISCIPLINAS?.*OP[T]?ATIVAS?|^OP[T]?ATIVAS?)", re.IGNORECASE)),
    ("EST", re.compile(r"EST[ÁA]GIO", re.IGNORECASE)),
    ("COMP", re.compile(r"(ATIVIDADES?.*COMPLEMENT|^COMPLEMENTARES?)", re.IGNORECASE)),
    ("TCC", re.compile(r"TRABALHO\s+DE\s+CONCLUS", re.IGNORECASE)),
]

CODE_ONLY_RX = re.compile(r"^([A-Z]{2,4}\d{4,6})\b")
TYPE_TOKENS_RX = r"(?:OB|OP|EC|EL|OC|OE|TC|TCC)"
HEADER_LINE_GUARD = re.compile(rf"^([A-Z]{{2,4}}\d{{4,6}}).*\b{TYPE_TOKENS_RX}\b")


@dataclass
class Discipline:
    code: str
    name: str
    section: str
    period: Optional[int]
    type: str
    credits: Optional[int]
    pre_numbers: List[int] = field(default_factory=list)
    post_numbers: List[int] = field(default_factory=list)
    total_hours: Optional[int] = None
    prerequisites: List[str] = field(default_factory=list)
    slug: str = field(init=False)

    def __post_init__(self) -> None:
        self.slug = slugify(self.name)

    def to_dict(self) -> Dict:
        return {
            "code": self.code,
            "name": self.name,
            "slug": self.slug,
            "section": self.section,
            "period": self.period,
            "type": self.type,
            "credits": self.credits,
            "hours_before_type": self.pre_numbers,
            "hours_after_type": self.post_numbers,
            "total_hours": self.total_hours,
            "prerequisites": self.prerequisites,
        }


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_only = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only).strip("-")
    slug = ascii_only.lower() or "item"
    return slug


def clean_line(line: str) -> str:
    line = line.replace("\u00A0", " ")  # nbsp -> space
    line = re.sub(r"\s+", " ", line.strip())
    return line


def detect_section(line: str, current: str) -> str:
    for section, pattern in SECTION_TOKENS:
        if pattern.search(line):
            return section
    return current


def parse_meta(lines: List[str]) -> Dict[str, Optional[str]]:
    meta = {
        "curso": None,
        "turno": None,
        "nivel": None,
        "modalidade": None,
        "grau": None,
        "funcionamento": None,
    }
    for line in lines[:40]:
        lo = line.lower()
        if meta["curso"] is None and "vers" in lo:
            m = re.search(r"-\s*(.+?)\s+vers", line, flags=re.IGNORECASE)
            if m:
                meta["curso"] = m.group(1).strip()
        if meta["turno"] is None and "turno:" in lo:
            meta["turno"] = line.split(":", 1)[1].strip()
        if meta["nivel"] is None and "n\u00edvel:" in lo:
            meta["nivel"] = line.split(":", 1)[1].strip()
        if meta["modalidade"] is None and "modalidade:" in lo:
            meta["modalidade"] = line.split(":", 1)[1].strip()
        if meta["grau"] is None and "grau conferido:" in lo:
            meta["grau"] = line.split(":", 1)[1].strip()
        if meta["funcionamento"] is None and "funcionamento:" in lo:
            meta["funcionamento"] = line.split(":", 1)[1].strip()
    # fallback para nome do curso: usa nome do arquivo caso não encontrado
    if not meta["curso"]:
        meta["curso"] = None
    return meta


def parse_discipline_line(line: str, section: str, period: Optional[int]) -> Optional[Discipline]:
    parts = line.split()
    if len(parts) < 3 or not CODE_RX.match(parts[0]):
        return None

    type_idx = None
    for idx in range(len(parts) - 1, 0, -1):
        token = parts[idx]
        if TYPE_RX.fullmatch(token):
            type_idx = idx
            break
    if type_idx is None:
        return None

    after = parts[type_idx + 1 :]
    if after and all(t.isdigit() for t in after):
        post_numbers = list(map(int, after))
    else:
        post_numbers = []

    pre_tokens = parts[1:type_idx]
    name_tokens = list(pre_tokens)
    numbers: List[int] = []
    while name_tokens and name_tokens[-1].isdigit():
        numbers.insert(0, int(name_tokens.pop()))

    name = " ".join(name_tokens).strip()
    if not name:
        return None

    chs = None
    digits_body = numbers[:]
    if len(digits_body) >= 4:
        candidate = digits_body[-1]
        rest = digits_body[:-1]
        for span in range(3, min(6, len(rest)) + 1):
            if sum(rest[-span:]) == candidate:
                chs = candidate
                digits_body = rest
                break

    hour_parts: List[int] = []
    credit: Optional[int] = None
    extra_prefix: List[int] = []

    if digits_body:
        if chs is not None:
            idx = len(digits_body) - 1
            accumulated = 0
            while idx >= 0:
                value = digits_body[idx]
                hour_parts.insert(0, value)
                accumulated += value
                idx -= 1
                if accumulated >= chs:
                    break

            while idx >= 0 and digits_body[idx] == 0:
                hour_parts.insert(0, digits_body[idx])
                idx -= 1

            if idx >= 0:
                credit = digits_body[idx]
                extra_prefix = digits_body[:idx]
        else:
            if len(digits_body) >= 5:
                hour_parts = digits_body[-4:]
                credit = digits_body[-5]
                extra_prefix = digits_body[:-5]
            elif len(digits_body) >= 4:
                hour_parts = digits_body[-3:]
                credit = digits_body[-4]
                extra_prefix = digits_body[:-4]
            elif len(digits_body) >= 3:
                hour_parts = digits_body[-2:]
                credit = digits_body[-3]
                extra_prefix = digits_body[:-3]
            else:
                hour_parts = digits_body[:]
                extra_prefix = []

    if extra_prefix:
        name = f"{name} {' '.join(str(n) for n in extra_prefix)}".strip()

    total_hours: Optional[int]
    if chs is not None:
        total_hours = chs
    elif hour_parts:
        total_hours = sum(hour_parts)
    else:
        total_hours = None

    return Discipline(
        code=parts[0],
        name=name,
        section=section,
        period=period if section == "OB" else None,
        type=parts[type_idx],
        credits=credit,
        pre_numbers=hour_parts,
        post_numbers=post_numbers,
        total_hours=total_hours,
    )


def extract_prerequisites(lines: List[str], start_index: int) -> List[str]:
    prereqs: List[str] = []
    idx = start_index
    while idx < len(lines):
        raw = lines[idx]
        if not raw:
            idx += 1
            continue
        if PAGE_RX.search(raw) or TOTAL_PERIOD_RX.match(raw):
            break
        if PERIOD_RX.search(raw):
            break
        if HEADER_LINE_GUARD.match(raw):
            break
        if NO_PREREQ_RX.search(raw):
            prereqs.clear()
            idx += 1
            continue
        code_match = CODE_ONLY_RX.match(raw)
        if code_match:
            prereqs.append(code_match.group(1))
            idx += 1
            continue
        # ignora linhas auxiliares (ex.: "Disciplina:" etc.)
        lower = raw.lower()
        if lower.startswith("disciplina:"):
            code_match = re.search(r"[A-Z]{2,4}\d{4,6}", raw)
            if code_match:
                prereqs.append(code_match.group(0))
                idx += 1
                continue
            idx += 1
            continue
        if lower.startswith("bloco"):
            code_match = re.search(r"[A-Z]{2,4}\d{4,6}", raw)
            if code_match:
                prereqs.append(code_match.group(0))
                idx += 1
                continue
            idx += 1
            continue
        # se nada disso, encerra bloco
        break
    return prereqs


def pdf_to_lines(pdf_path: Path) -> List[str]:
    items = []
    laparams = LAParams(char_margin=2.0, line_margin=0.3, word_margin=0.1)

    for page in extract_pages(str(pdf_path), laparams=laparams):
        page_id = getattr(page, "pageid", 0)
        for element in page:
            if not isinstance(element, LTTextContainer):
                continue
            for text_line in element:
                text = text_line.get_text().strip()
                if not text:
                    continue
                y = round(getattr(text_line, "y1", 0.0), 1)
                x = round(getattr(text_line, "x0", 0.0), 1)
                items.append((page_id, y, x, text.replace("\n", " ")))

    items.sort(key=lambda t: (t[0], -t[1], t[2]))

    lines: List[str] = []
    buffer: List[tuple[float, str]] = []
    current_page = None
    current_y = None
    tol = 1.4  # tolerância para considerar a mesma linha horizontal

    def flush() -> None:
        nonlocal buffer
        if not buffer:
            return
        buffer.sort(key=lambda tup: tup[0])
        line_text = " ".join(text for _, text in buffer)
        line_text = clean_line(line_text)
        if line_text:
            lines.append(line_text)
        buffer = []

    for page_id, y, x, text in items:
        if current_page is None:
            current_page = page_id
            current_y = y
            buffer.append((x, text))
            continue

        if page_id != current_page or current_y is None or abs(y - current_y) > tol:
            flush()
            current_page = page_id
            current_y = y
            buffer.append((x, text))
        else:
            buffer.append((x, text))

    flush()
    return [ln for ln in lines if ln and not PAGE_RX.search(ln)]


def parse_pdf(pdf_path: Path) -> Dict:
    lines = pdf_to_lines(pdf_path)

    meta = parse_meta(lines)
    required: Dict[str, Optional[int]] = {k: None for k in REQUIRED_PATTERNS}
    disciplines: List[Discipline] = []
    by_code: Dict[str, Discipline] = {}

    current_section = "OB"
    current_period: Optional[int] = None
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        line = lines[i]
        current_section = detect_section(line, current_section)

        # atualiza resumo de carga quando possível
        for label, rx in REQUIRED_PATTERNS.items():
            if required[label] is None:
                match = rx.search(line)
                if match:
                    try:
                        grp_index = match.lastindex or 1
                        required[label] = int(match.group(grp_index))
                    except ValueError:
                        pass

        upper_line = line.upper()
        if "CARGA HOR" in upper_line:
            nums = [int(n) for n in re.findall(r"\d+", line)]
            if nums:
                val = max(nums)
                if current_section == "OB" and required["obrigatorias"] is None:
                    required["obrigatorias"] = val
                elif current_section == "OP" and required["optativas"] is None:
                    required["optativas"] = val
                elif current_section == "EST" and required["estagio"] is None:
                    required["estagio"] = val
                elif current_section == "COMP" and required["complementares"] is None:
                    required["complementares"] = val

        # atualiza período quando aparecer
        pm = PERIOD_RX.search(line)
        if pm:
            try:
                current_period = int(pm.group(1))
            except ValueError:
                current_period = None
            i += 1
            continue

        disc = parse_discipline_line(line, current_section, current_period)
        if disc is None:
            i += 1
            continue

        # captura pré-requisitos a partir das linhas subsequentes
        prereqs = extract_prerequisites(lines, i + 1)
        disc.prerequisites.extend(prereqs)

        disciplines.append(disc)
        by_code[disc.code] = disc

        # pula linhas já consumidas (1 header + qtd de prereqs)
        i += 1 + len(prereqs)

    # pós-processa pré-requisitos para complementar com nomes (quando possível)
    prereq_map: Dict[str, Dict[str, str]] = {}
    for disc in disciplines:
        mapped: List[Dict[str, str]] = []
        for code in disc.prerequisites:
            target = by_code.get(code)
            mapped.append({
                "code": code,
                "name": target.name if target else None,
                "slug": target.slug if target else slugify(code),
            })
        prereq_map[disc.code] = mapped

    bucket_totals = {"obrigatorias": 0, "optativas": 0, "estagio": 0, "complementares": 0, "tcc": 0}
    bucket_map = {
        "OB": "obrigatorias",
        "TCC": "tcc",
        "OP": "optativas",
        "EST": "estagio",
        "COMP": "complementares",
    }
    grand_total = 0
    for disc in disciplines:
        total = disc.total_hours
        if total is None:
            total = sum(disc.pre_numbers) + sum(disc.post_numbers)
        if total:
            grand_total += total
        bucket_key = bucket_map.get(disc.section)
        if bucket_key and total:
            bucket_totals[bucket_key] += total

    for key, value in bucket_totals.items():
        if value and required[key] is None:
            required[key] = value
    if grand_total and required["total"] is None:
        required["total"] = grand_total

    # estrutura final agrupada
    periods: Dict[int, List[Dict]] = {}
    optativas: List[Dict] = []
    estagios: List[Dict] = []
    complementares: List[Dict] = []
    outros: Dict[str, List[Dict]] = {}

    for disc in disciplines:
        payload = disc.to_dict()
        payload["prerequisites"] = prereq_map.get(disc.code, [])
        if disc.section == "OB" and disc.period is not None:
            periods.setdefault(disc.period, []).append(payload)
        elif disc.section == "OP":
            optativas.append(payload)
        elif disc.section == "EST":
            estagios.append(payload)
        elif disc.section == "COMP":
            complementares.append(payload)
        else:
            outros.setdefault(disc.section, []).append(payload)

    # ordena períodos numericamente
    ordered_periods = [
        {
            "period": period,
            "disciplines": sorted(items, key=lambda d: (d["type"], d["name"]))
        }
        for period, items in sorted(periods.items())
    ]

    result = {
        "source_pdf": pdf_path.name,
        "curso": meta.get("curso") or pdf_path.stem,
        "metadados": meta,
        "resumo_cargas": required,
        "periodos": ordered_periods,
        "optativas": sorted(optativas, key=lambda d: d["name"]),
        "estagios": sorted(estagios, key=lambda d: (d["period"] or 0, d["name"])),
        "complementares": sorted(complementares, key=lambda d: d["name"]),
        "outros": {k: sorted(v, key=lambda d: d["name"]) for k, v in sorted(outros.items())},
    }

    return result


def main() -> None:
    if not PDF_DIR.exists():
        raise SystemExit(f"Diretório não encontrado: {PDF_DIR}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        raise SystemExit("Nenhum PDF encontrado em curriculo/.")

    all_index = []

    for pdf_path in pdf_files:
        data = parse_pdf(pdf_path)
        course_slug = slugify(data["curso"])
        out_path = OUT_DIR / f"{course_slug or pdf_path.stem}.json"
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        all_index.append({
            "curso": data["curso"],
            "slug": course_slug,
            "arquivo": out_path.name,
            "resumo_cargas": data["resumo_cargas"],
        })
        print(f"Gerado {out_path.relative_to(ROOT)}")

    # índice geral para facilitar carga dinâmica
    index_path = OUT_DIR / "index.json"
    with index_path.open("w", encoding="utf-8") as fh:
        json.dump({"cursos": all_index}, fh, ensure_ascii=False, indent=2)
    print(f"Gerado {index_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
