from __future__ import annotations

import csv
import math
import re
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


@dataclass(frozen=True)
class CMap:
    key_len: int
    mapping: dict[bytes, str]


_FILTER_FLATE = re.compile(rb"/Filter\s*/FlateDecode")
_STREAM_START = re.compile(rb"stream\r?\n")
_STREAM_END = re.compile(rb"\r?\nendstream")

_HEX_TOKEN = re.compile(rb"<([0-9A-Fa-f\s]+)>")
_TITLE_RX = re.compile(r"^(?P<area>.+),\s*(?P<period>\d{4}-\d{2})$")
_AGE_INTERVAL_RX = re.compile(r"^(?P<x>\d+)(?:-(?P<y>\d+)|\+)")

_RESIDENCE_LABELS = ("Total", "Rural", "Urban")


def _hex_to_bytes(h: bytes) -> bytes:
    hs = re.sub(rb"\s+", b"", h)
    if len(hs) % 2 == 1:
        hs += b"0"
    try:
        return bytes.fromhex(hs.decode("ascii"))
    except Exception:
        return b""


def _decode_utf16be_hex(h: bytes) -> str:
    bts = _hex_to_bytes(h)
    if not bts:
        return ""
    return bts.decode("utf-16-be", errors="ignore")


def _iter_flate_decoded_streams(pdf: bytes) -> Iterator[bytes]:
    for m in _FILTER_FLATE.finditer(pdf):
        s = _STREAM_START.search(pdf, m.end())
        if not s:
            continue
        e = _STREAM_END.search(pdf, s.end())
        if not e:
            continue
        comp = pdf[s.end() : e.start()]
        try:
            yield zlib.decompress(comp)
        except Exception:
            continue


def _parse_cmap_blob(blob: bytes) -> CMap | None:
    m = re.search(
        rb"begincodespacerange\s*<([0-9A-Fa-f]{2,})>\s*<([0-9A-Fa-f]{2,})>\s*endcodespacerange",
        blob,
    )
    key_len = len(m.group(1)) // 2 if m else 2

    mapping: dict[bytes, str] = {}

    for block in re.findall(rb"beginbfchar(.*?)endbfchar", blob, flags=re.DOTALL):
        for src, dst in re.findall(rb"<([0-9A-Fa-f\s]+)>\s*<([0-9A-Fa-f\s]+)>", block):
            src_b = _hex_to_bytes(src)
            if not src_b:
                continue
            dst_s = _decode_utf16be_hex(dst)
            if dst_s:
                mapping[src_b] = dst_s

    for block in re.findall(rb"beginbfrange(.*?)endbfrange", blob, flags=re.DOTALL):
        entry_re = re.compile(
            rb"<([0-9A-Fa-f\s]+)>\s*<([0-9A-Fa-f\s]+)>\s*(\[\s*.*?\s*\]|<[^>]+>)",
            re.DOTALL,
        )
        for m in entry_re.finditer(block):
            src1_b = _hex_to_bytes(m.group(1))
            src2_b = _hex_to_bytes(m.group(2))
            if not src1_b or not src2_b or len(src1_b) != len(src2_b):
                continue
            src1 = int.from_bytes(src1_b, "big")
            src2 = int.from_bytes(src2_b, "big")
            rhs = m.group(3).strip()
            if rhs.startswith(b"["):
                dests = _HEX_TOKEN.findall(rhs)
                for off, d in enumerate(dests):
                    key = (src1 + off).to_bytes(len(src1_b), "big")
                    mapping[key] = _decode_utf16be_hex(d)
            else:
                dst_start_hex = rhs[1:-1]  # strip <>
                dst_start = _decode_utf16be_hex(dst_start_hex)
                if len(dst_start) != 1:
                    continue
                base = ord(dst_start)
                for k in range(src1, src2 + 1):
                    mapping[k.to_bytes(len(src1_b), "big")] = chr(base + (k - src1))

    if not mapping:
        return None
    return CMap(key_len=key_len, mapping=mapping)


def _collect_cmaps(pdf: bytes, decoded_streams: Iterable[bytes]) -> list[CMap]:
    blobs: list[bytes] = []

    for m in re.finditer(rb"begincmap", pdf):
        start = m.start()
        end = pdf.find(b"endcmap", start)
        if end != -1:
            blob = pdf[start : end + len(b"endcmap")]
            if len(blob) < 100_000:
                blobs.append(blob)

    for dec in decoded_streams:
        if b"begincmap" not in dec:
            continue
        start = dec.find(b"begincmap")
        end = dec.find(b"endcmap", start)
        if end != -1:
            blob = dec[start : end + len(b"endcmap")]
            if len(blob) < 100_000:
                blobs.append(blob)

    uniq: list[bytes] = []
    seen: set[bytes] = set()
    for b in blobs:
        if b in seen:
            continue
        seen.add(b)
        uniq.append(b)

    out: list[CMap] = []
    for b in uniq:
        cm = _parse_cmap_blob(b)
        if cm is not None:
            out.append(cm)
    return out


def _decode_hex_text(bts: bytes, *, cmap: CMap) -> str:
    if cmap.key_len <= 0 or len(bts) % cmap.key_len != 0:
        return ""
    parts = []
    for i in range(0, len(bts), cmap.key_len):
        key = bts[i : i + cmap.key_len]
        parts.append(cmap.mapping.get(key, ""))
    return "".join(parts)


def _score_text(s: str) -> int:
    score = 0
    for ch in s:
        if ch.isalnum():
            score += 2
        elif ch in " .,-/()":
            score += 1
        elif ch.isspace():
            score += 0
        else:
            score -= 1
    return score


def _best_cmap_for_stream(*, cmaps: list[CMap], sample_hex: list[bytes]) -> CMap | None:
    if not sample_hex or not cmaps:
        return None
    best: CMap | None = None
    best_score = -10**9
    for cm in cmaps:
        sc = 0
        for bts in sample_hex:
            txt = _decode_hex_text(bts, cmap=cm)
            if txt:
                sc += _score_text(txt)
        if sc > best_score:
            best_score = sc
            best = cm
    return best


def _skip_ws_and_comments(data: bytes, i: int) -> int:
    n = len(data)
    while i < n:
        b = data[i]
        if b in b"\x00\t\n\r\f ":
            i += 1
            continue
        if b == 0x25:  # %
            while i < n and data[i] not in b"\r\n":
                i += 1
            continue
        break
    return i


def _parse_literal_string(data: bytes, i: int) -> tuple[bytes, int]:
    i += 1  # skip '('
    depth = 1
    out = bytearray()
    n = len(data)
    while i < n and depth > 0:
        b = data[i]
        if b == 0x5C and i + 1 < n:  # backslash
            out.append(data[i + 1])
            i += 2
            continue
        if b == 0x28:  # (
            depth += 1
            out.append(b)
            i += 1
            continue
        if b == 0x29:  # )
            depth -= 1
            if depth == 0:
                i += 1
                break
            out.append(b)
            i += 1
            continue
        out.append(b)
        i += 1
    return bytes(out), i


def _parse_hex_string(data: bytes, i: int) -> tuple[bytes, int]:
    i += 1  # skip '<'
    buf = bytearray()
    n = len(data)
    while i < n:
        b = data[i]
        if b == 0x3E:  # '>'
            i += 1
            break
        buf.append(b)
        i += 1
    return _hex_to_bytes(bytes(buf)), i


def _parse_simple_token(data: bytes, i: int) -> tuple[bytes, int]:
    n = len(data)
    start = i
    while i < n and data[i] not in b"\x00\t\n\r\f []()<>/{}%":
        i += 1
    return data[start:i], i


def _parse_array(data: bytes, i: int) -> tuple[list[tuple[str, bytes]], int]:
    assert data[i] == 0x5B  # [
    i += 1
    items: list[tuple[str, bytes]] = []
    n = len(data)
    while i < n:
        i = _skip_ws_and_comments(data, i)
        if i >= n:
            break
        b = data[i]
        if b == 0x5D:  # ]
            i += 1
            break
        if b == 0x28:  # (
            s, i = _parse_literal_string(data, i)
            items.append(("lit", s))
            continue
        if b == 0x3C and i + 1 < n and data[i + 1] != 0x3C:  # <...>
            h, i = _parse_hex_string(data, i)
            items.append(("hex", h))
            continue
        tok, i = _parse_simple_token(data, i)
        if not tok:
            i += 1
            continue
        # Keep only string-ish things; TJ arrays also include numbers, which we ignore.
        items.append(("tok", tok))
    return items, i


def _extract_text_ops(content: bytes, *, cmap: CMap | None) -> list[str]:
    """
    Extracts a best-effort sequence of displayed strings from a PDF content stream.

    This is not a full PDF text extractor; it is tuned for this repo's SRS life-table PDFs:
    - literal strings: ( ... ) Tj / TJ
    - hex strings: < ... > Tj / TJ with ToUnicode decoding
    """
    out: list[str] = []
    i = 0
    n = len(content)
    stack: list[tuple[str, object]] = []

    while i < n:
        i = _skip_ws_and_comments(content, i)
        if i >= n:
            break
        b = content[i]

        if b == 0x28:  # (
            s, i = _parse_literal_string(content, i)
            stack.append(("lit", s))
            continue
        if b == 0x3C:  # <
            if i + 1 < n and content[i + 1] == 0x3C:  # <<
                i += 2
                continue
            h, i = _parse_hex_string(content, i)
            stack.append(("hex", h))
            continue
        if b == 0x5B:  # [
            arr, i = _parse_array(content, i)
            stack.append(("arr", arr))
            continue

        tok, i = _parse_simple_token(content, i)
        if not tok:
            i += 1
            continue
        op = tok.decode("latin-1", errors="ignore")

        if op == "Tj" and stack:
            kind, val = stack.pop()
            if kind == "lit":
                out.append(bytes(val).decode("latin-1", errors="ignore"))
            elif kind == "hex" and cmap is not None:
                out.append(_decode_hex_text(bytes(val), cmap=cmap))
        elif op == "TJ" and stack and stack[-1][0] == "arr":
            arr = stack.pop()[1]
            parts: list[str] = []
            for k, v in arr:  # type: ignore[misc]
                if k == "lit":
                    parts.append(bytes(v).decode("latin-1", errors="ignore"))
                elif k == "hex" and cmap is not None:
                    parts.append(_decode_hex_text(bytes(v), cmap=cmap))
            if parts:
                out.append("".join(parts))
        else:
            # Prevent runaway memory on streams with many operands.
            if len(stack) > 250:
                stack = stack[-80:]

    return out


def extract_srs_pdf_segments(pdf_path: str | Path) -> list[str]:
    """
    Extract a normalized sequence of text segments from the SRS Abridged Life Tables PDF.
    """
    pdf_path = Path(pdf_path)
    pdf = pdf_path.read_bytes()
    decoded_streams = list(_iter_flate_decoded_streams(pdf))
    cmaps = _collect_cmaps(pdf, decoded_streams)

    segments: list[str] = []
    for dec in decoded_streams:
        if b"Tj" not in dec and b"TJ" not in dec:
            continue

        sample_hex: list[bytes] = []
        for m in re.finditer(rb"<([0-9A-Fa-f\s]{4,})>", dec):
            bts = _hex_to_bytes(m.group(1))
            if bts and 2 <= len(bts) <= 40:
                sample_hex.append(bts)
            if len(sample_hex) >= 200:
                break
        cmap = _best_cmap_for_stream(cmaps=cmaps, sample_hex=sample_hex)

        for t in _extract_text_ops(dec, cmap=cmap):
            s = re.sub(r"\s+", " ", t).strip()
            if s:
                segments.append(s)

    return segments


def _parse_float_token(token: str) -> float | None:
    t = token.strip()
    if not t or t == "...":
        return None
    try:
        return float(t)
    except Exception:
        m = re.search(r"-?\d+(?:\.\d+)?", t)
        return float(m.group(0)) if m else None


def _parse_int_token(token: str) -> int | None:
    t = token.strip()
    if not t or t == "...":
        return None
    t = re.sub(r"[^\d-]", "", t)
    if not t:
        return None
    try:
        return int(t)
    except Exception:
        return None


def _split_lx_nlx(digits: str, *, n: int | None) -> tuple[int, int] | None:
    digits = re.sub(r"\D", "", digits)
    if len(digits) < 2:
        return None

    candidates: list[tuple[float, int, int]] = []
    max_lx_len = min(6, len(digits) - 1)
    for lx_len in range(1, max_lx_len + 1):
        lx = int(digits[:lx_len])
        nlx = int(digits[lx_len:])
        if lx <= 0 or lx > 100_000:
            continue
        if nlx <= 0:
            continue

        if n is not None and n > 0:
            # Sanity bounds: nLx is at most n*lx; allow tiny tolerance for rounding.
            if nlx > (n * lx + 10):
                continue
            ratio = nlx / (n * lx)
            if ratio < 0.2 or ratio > 1.05:
                continue
            score = 1.0 - abs(1.0 - ratio)  # closer to 1 is better
        else:
            if nlx > 1_000_000:
                continue
            score = float(lx_len)  # prefer longer lx for open interval

        candidates.append((score, lx, nlx))

    if not candidates:
        return None
    _, lx, nlx = max(candidates, key=lambda x: x[0])
    return lx, nlx


def _parse_combined_row_token(token: str) -> tuple[str, int, int | None, int | None, int | None] | None:
    """
    Parses the combined first-column token of each row, e.g.:
    - '0-10.0308510000097320' -> age='0-1', nqx=0.03085, lx=100000, nLx=97320
    - '85+ ...19979113568'    -> age='85+', nqx=None, lx=19979, nLx=113568
    Returns: (age_interval, n_years, nqx_maybe, lx, nLx)
    """
    token = token.strip()
    age_interval: str
    rest: str

    open_m = re.match(r"^(?P<x>\d+)\+\s*(?P<rest>.*)$", token)
    if open_m:
        age_interval = f"{open_m.group('x')}+"
        rest = open_m.group("rest").strip()
        n_years = -1
    else:
        hy_m = re.match(r"^(?P<x>\d+)-(?P<tail>.*)$", token)
        if not hy_m:
            return None
        x = int(hy_m.group("x"))
        tail = hy_m.group("tail")
        # The age interval is immediately followed by nqx, which starts with '0.'.
        # We use the first '0.' occurrence to avoid capturing it as part of the end-age
        # (e.g., parsing '0-10.03...' as 0-10).
        qpos = tail.find("0.")
        if qpos <= 0:
            return None
        y_str = tail[:qpos].strip()
        if not y_str.isdigit():
            return None
        y = int(y_str)
        if y <= x:
            return None
        age_interval = f"{x}-{y}"
        rest = tail[qpos:].strip()
        n_years = y - x

    nqx: float | None
    if rest.startswith("..."):
        nqx = None
        rest = rest[3:].strip()
    else:
        m_q = re.match(r"^(\d\.\d{5})(.*)$", rest)
        if not m_q:
            return None
        nqx = float(m_q.group(1))
        rest = m_q.group(2).strip()

    split = _split_lx_nlx(rest, n=(n_years if n_years > 0 else None))
    if split is None:
        return None
    lx, nlx = split
    return age_interval, n_years, nqx, lx, nlx


def parse_srs_abridged_life_tables_segments(segments: list[str]) -> list[dict[str, object]]:
    """
    Parse the SRS 'Abridged Life Tables, 2018-22' blocks into long-form rows.

    Output rows:
    - area, period, residence, sex, age_interval, age_start, age_end, n, nqx, lx, nLx, ex, mx, age_mid
    """
    rows: list[dict[str, object]] = []

    i = 0
    while i + 1 < len(segments):
        m = _TITLE_RX.match(segments[i])
        if not m or segments[i + 1] != "Age-Interval":
            i += 1
            continue

        area = m.group("area").strip()
        period = m.group("period")
        i += 2  # skip title + Age-Interval

        # Skip header tokens until we hit the first residence label.
        while i < len(segments) and segments[i] not in _RESIDENCE_LABELS:
            i += 1
        if i >= len(segments):
            break

        while i < len(segments) and segments[i] in _RESIDENCE_LABELS:
            residence = segments[i]
            i += 1

            while i < len(segments):
                # Next block or next table?
                if segments[i] in _RESIDENCE_LABELS:
                    break
                if _TITLE_RX.match(segments[i]) and i + 1 < len(segments) and segments[i + 1] == "Age-Interval":
                    break

                row_token = segments[i]
                combined = _parse_combined_row_token(row_token)
                if combined is None:
                    i += 1
                    continue

                age_interval, n_years, total_nqx, total_lx, total_nlx = combined
                i += 1
                if i + 8 >= len(segments):
                    break

                total_ex = _parse_float_token(segments[i])
                male_nqx = _parse_float_token(segments[i + 1])
                male_lx = _parse_int_token(segments[i + 2])
                male_nlx = _parse_int_token(segments[i + 3])
                male_ex = _parse_float_token(segments[i + 4])
                female_nqx = _parse_float_token(segments[i + 5])
                female_lx = _parse_int_token(segments[i + 6])
                female_nlx = _parse_int_token(segments[i + 7])
                female_ex = _parse_float_token(segments[i + 8])
                i += 9

                age_m = _AGE_INTERVAL_RX.match(age_interval)
                if not age_m:
                    continue
                age_start = int(age_m.group("x"))
                age_end = int(age_m.group("y")) if age_m.group("y") is not None else None
                n = (age_end - age_start) if age_end is not None else None
                age_mid = (age_start + n / 2.0) if n is not None else None

                def mx_from_nqx(nqx: float | None) -> float | None:
                    if n is None or nqx is None:
                        return None
                    if n <= 0:
                        return None
                    if nqx <= 0 or nqx >= 1:
                        return None
                    return float(-math.log(1.0 - nqx) / n)

                for sex, nqx, lx, nlx, ex in [
                    ("Total", total_nqx, total_lx, total_nlx, total_ex),
                    ("Male", male_nqx, male_lx, male_nlx, male_ex),
                    ("Female", female_nqx, female_lx, female_nlx, female_ex),
                ]:
                    rows.append(
                        {
                            "area": area,
                            "period": period,
                            "residence": residence,
                            "sex": sex,
                            "age_interval": age_interval,
                            "age_start": age_start,
                            "age_end": age_end,
                            "n": n,
                            "nqx": nqx,
                            "lx": lx,
                            "nLx": nlx,
                            "ex": ex,
                            "mx": mx_from_nqx(nqx),
                            "age_mid": age_mid,
                        }
                    )

        # Continue scanning for more tables.

    return rows


def load_srs_abridged_life_tables_pdf(pdf_path: str | Path) -> list[dict[str, object]]:
    segments = extract_srs_pdf_segments(pdf_path)
    return parse_srs_abridged_life_tables_segments(segments)


def write_rows_csv(rows: list[dict[str, object]], out_path: str | Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        out_path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
