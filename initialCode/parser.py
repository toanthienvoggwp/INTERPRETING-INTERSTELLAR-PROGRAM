from __future__ import annotations

from dataclasses import dataclass

from ifp_ast import (
    CHARS,
    CHARS_DECODED,
    TBinOp,
    TBool,
    TIf,
    TInt,
    TLam,
    TString,
    TUnOp,
    TVar,
    Term,
)


@dataclass(frozen=True)
class ParseError(Exception):
    kind: str
    index: int | None = None
    ch: str | None = None

    def __str__(self) -> str:
        if self.kind == "UnexpectedChar":
            return f"UnexpectedChar({self.ch!r}, {self.index})"
        if self.kind == "UnusedInput":
            return f"UnusedInput({self.index})"
        return "UnexpectedEOF"


def p_term(inp: str) -> Term: #inp = input
    # TODO
    token = inp.split()
    if not token:
        raise ParseError("UnexpectedEOF")
    stream = _TokenStream(token)
    ast = _parse_term(stream)
    if stream.has_more():
        raise ParseError("UnusedInput", index = stream.index)
    return ast

def _decode_int(body: str) -> int:
    result = 0
    for ch in body:
        result = result * 94 +(ord(ch) - 33)
    return result

def _decode_str(body: str) -> str:
    result = []
    for ch in body:
        idx = CHARS.index(ch)
        result.append(CHARS_DECODED[idx])
    return "".join(result)

class _TokenStream:
    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.index = 0
        
    def next(self) -> str:
        if self.index >= len(self.tokens):
            raise ParseError("UnexpectedEOF")
        token = self.tokens[self.index]
        self.index += 1
        return token
        
    def has_more(self) -> bool:
        return self.index < len(self.tokens)

def _parse_term(stream: _TokenStream) -> Term:
    token = stream.next()
    ptr = token[0]
    body = token[1:]
    if ptr == "T":
        return TBool(True)
    elif ptr == "F":
        return TBool(False)
    elif ptr == "I":
        return TInt(_decode_int(body))
    elif ptr == "S":
        return TString(_decode_str(body))
    elif ptr == "v":
        return TVar(_decode_int(body))
    elif ptr == "U":
        child = _parse_term(stream)
        return TUnOp(op = body, term = child)
    elif ptr == "B":
        left = _parse_term(stream)
        right = _parse_term(stream)
        return TBinOp(left = left, op = body, right = right)
    elif ptr == "?":
        condition = _parse_term(stream)
        true_branch = _parse_term(stream)
        false_branch = _parse_term(stream)
        return TIf(cond = condition, true_branch = true_branch, false_branch = false_branch)
    elif ptr == "L":
        var_id = _decode_int(body)
        func_body = _parse_term(stream)
        return TLam(var = var_id, body = func_body)
    else:
        raise ParseError("UnexpectedChar", index = stream.index - 1, ch = ptr)